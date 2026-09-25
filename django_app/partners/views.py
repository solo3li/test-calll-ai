import os
import json
import secrets
import logging
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse as _DjangoJsonResponse

def JsonResponse(data, *args, **kwargs):
    dumps_params = kwargs.pop('json_dumps_params', None)
    if dumps_params is None:
        dumps_params = {'ensure_ascii': False}
    else:
        dumps_params.setdefault('ensure_ascii', False)
    return _DjangoJsonResponse(data, *args, json_dumps_params=dumps_params, **kwargs)

def get_full_recording_url(request, rec_url):
    if not rec_url:
        return ""
    if rec_url.startswith("http://") or rec_url.startswith("https://"):
        return rec_url
    return request.build_absolute_uri(rec_url)

from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.paginator import Paginator
from livekit import api

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.views import SpectacularAPIView
from .models import PartnerProfile, PartnerClientRelationship
from .decorators import partner_required, partner_client_access_required
from .services.webhook import dispatch_partner_webhook
from .openapi_spec import get_partner_openapi_spec
from .serializers import (
    PartnerDashboardResponseSerializer,
    PartnerSettingsUpdateRequestSerializer,
    PartnerClientRegisterRequestSerializer,
    PartnerClientResponseSerializer,
    PartnerClientsListResponseSerializer,
    PartnerClientProfileSerializer,
    PartnerClientProfileCreateRequestSerializer,
    PartnerClientMemorySerializer,
    PartnerClientMemoryCreateRequestSerializer,
    PartnerClientDocumentSerializer,
    PartnerClientRAGQueryRequestSerializer,
    PartnerClientTrunkSerializer,
    PartnerClientNumberSerializer,
    PartnerClientEmployeeSerializer,
    PartnerClientQueueSerializer,
    PartnerClientMCPServerSerializer,
    PartnerClientCallSessionSerializer,
    BaseSuccessResponseSerializer,
    BaseErrorResponseSerializer,
    PartnerClientCampaignSerializer,
    PartnerClientCampaignCreateRequestSerializer,
    PartnerClientCampaignDetailResponseSerializer,
    PartnerClientCampaignsListResponseSerializer
)
import inngest
from asgiref.sync import async_to_sync

from agents.models import AgentProfile, UserMCPServer, SystemSetting
from agents.views import fetch_mcp_tools_sync
from crm.models import CallSession, CustomerMemory, OutboundCampaign, CampaignContact, UserCampaignLimit
from crm.inngest_jobs import inngest_client, broadcast_campaign_update
from knowledge.models import Document, DocumentChunk
from knowledge.rag_utils import extract_text_from_file, chunk_text, get_embeddings_batch
from telephony.models import InboundPBXTrunk, OutboundSIPTrunk
from telephony.services import initiate_outbound_call
from django.utils import timezone
from crm.file_parser import parse_leads_file, normalize_phone, is_valid_phone
from call_center.models import CallQueue, EmployeeProfile, QueueMembership
from google import genai
from google.genai import types
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)


# =========================================================================
# Web UI Endpoints (Authenticated Platform Users in room.html)
# =========================================================================

@login_required(login_url='/login/')
def apply_partner(request):
    """Regular user submits application to become a partner/reseller."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body) if request.body else request.POST
    except Exception:
        data = {}

    company_name = data.get('company_name', '').strip()
    website = data.get('website', '').strip()
    description = data.get('description', '').strip()

    if not company_name:
        return JsonResponse({"status": "error", "message": "اسم الشركة أو الخدمة مطلوب."}, status=400)

    profile, created = PartnerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'company_name': company_name,
            'website': website,
            'description': description,
            'status': 'pending',
        }
    )
    if not created:
        profile.company_name = company_name
        profile.website = website
        profile.description = description
        if profile.status == 'rejected':
            profile.status = 'pending'
        profile.save()

    return JsonResponse({
        "status": "success",
        "message": "تم تقديم طلبك بنجاح وهو قيد المراجعة من الإدارة.",
        "partner": profile.to_dict()
    })


@login_required(login_url='/login/')
def get_partner_dashboard(request):
    """Fetch partner profile status, KPIs, clients list, and recent sub-client calls."""
    partner = PartnerProfile.objects.filter(user=request.user).first()
    if not partner:
        return JsonResponse({"status": "unregistered", "message": "المستخدم ليس شريكاً مسجلاً."})

    # Available MCP servers owned by this partner (to pick one as shared)
    mcp_servers = list(UserMCPServer.objects.filter(user=request.user).values('id', 'name', 'is_active', 'server_url'))

    clients_qs = PartnerClientRelationship.objects.filter(partner=partner).select_related('client').order_by('-created_at')
    clients_data = [c.to_dict() for c in clients_qs]

    # Partner's wallet balance
    from billing.models import UserWallet
    wallet, _ = UserWallet.objects.get_or_create(user=request.user)

    # Sub-clients calls
    client_users = [c.client for c in clients_qs]
    calls_qs = CallSession.objects.filter(user__in=client_users).order_by('-started_at')[:50]
    calls_data = []
    for call in calls_qs:
        calls_data.append({
            "call_id": call.room_name,
            "client_name": call.user.first_name or call.user.username,
            "client_id": call.user_id,
            "direction": call.get_direction_display(),
            "caller_phone": call.caller_phone or "",
            "started_at": call.started_at.strftime("%Y-%m-%d %H:%M"),
            "duration_seconds": call.duration_seconds,
            "billed_minutes": call.billed_minutes,
            "cost": float(call.cost),
            "summary": call.summary or "",
        })

    total_sub_minutes = sum(c['total_minutes'] for c in clients_data)
    total_sub_spent = sum(c['total_spent'] for c in clients_data)

    return JsonResponse({
        "status": "success",
        "partner": partner.to_dict(),
        "wallet": {
            "balance": float(wallet.balance),
            "currency": wallet.currency,
        },
        "kpis": {
            "total_clients": len(clients_data),
            "total_minutes": total_sub_minutes,
            "total_sub_spent": round(total_sub_spent, 4),
            "custom_rate": float(partner.custom_rate_per_minute),
        },
        "mcp_servers": mcp_servers,
        "clients": clients_data,
        "recent_calls": calls_data,
    })


@login_required(login_url='/login/')
def update_partner_settings(request):
    """Partner updates webhook URL, shared MCP server, or regenerates API key."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    partner = PartnerProfile.objects.filter(user=request.user, status='approved').first()
    if not partner:
        return JsonResponse({"status": "error", "message": "الحساب غير معتمد كشريك نشط."}, status=403)

    try:
        data = json.loads(request.body) if request.body else request.POST
    except Exception:
        data = {}

    if 'webhook_url' in data:
        partner.webhook_url = data.get('webhook_url', '').strip()
    
    if 'shared_mcp_server_id' in data:
        mcp_id = data.get('shared_mcp_server_id')
        if mcp_id:
            mcp = UserMCPServer.objects.filter(id=mcp_id, user=request.user).first()
            partner.shared_mcp_server = mcp
        else:
            partner.shared_mcp_server = None

    if data.get('regenerate_api_key'):
        partner.api_key = f"sk_live_prt_{secrets.token_urlsafe(32)}"

    partner.save()
    return JsonResponse({"status": "success", "message": "تم حفظ إعدادات الشريك بنجاح.", "partner": partner.to_dict()})


@login_required(login_url='/login/')
def test_partner_webhook(request):
    """Test ping partner webhook URL."""
    partner = PartnerProfile.objects.filter(user=request.user, status='approved').first()
    if not partner:
        return JsonResponse({"status": "error", "message": "الحساب غير معتمد كشريك."}, status=403)

    if not partner.webhook_url:
        return JsonResponse({"status": "error", "message": "لم يتم إدخال رابط Webhook بعد."}, status=400)

    dispatch_partner_webhook(partner, "test.ping", {
        "message": "اختبار فحص الاتصال بالـ Webhook من منصة الذكاء الاصطناعي بنجاح.",
        "partner_code": partner.partner_code,
    })
    return JsonResponse({"status": "success", "message": "تم إرسال إشعار فحص الـ Webhook التجريبي بنجاح."})


@login_required(login_url='/login/')
def update_client_cap(request):
    """Partner updates spending cap, minute cap, or toggle is_active for a client."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    partner = PartnerProfile.objects.filter(user=request.user, status='approved').first()
    if not partner:
        return JsonResponse({"status": "error", "message": "الحساب غير معتمد كشريك."}, status=403)

    try:
        data = json.loads(request.body) if request.body else request.POST
    except Exception:
        data = {}

    client_id = data.get('client_id')
    client_rel = PartnerClientRelationship.objects.filter(partner=partner, client_id=client_id).first()
    if not client_rel:
        return JsonResponse({"status": "error", "message": "العميل غير موجود أو لا يتبع حسابك."}, status=404)

    if 'spending_cap' in data:
        val = data.get('spending_cap')
        client_rel.spending_cap = Decimal(str(val)) if (val is not None and str(val).strip() != '') else None

    if 'minute_cap' in data:
        val = data.get('minute_cap')
        client_rel.minute_cap = int(val) if (val is not None and str(val).strip() != '') else None

    if 'is_active' in data:
        client_rel.is_active = bool(data.get('is_active'))

    client_rel.save()
    return JsonResponse({"status": "success", "message": "تم تحديث سقف العميل بنجاح.", "client": client_rel.to_dict()})


# =========================================================================
# Headless Partner REST API (/api/partner/v1/...)
# Secured strictly with X-Partner-Key Header and Tenant Isolation
# =========================================================================

@csrf_exempt
@partner_required
def api_partner_register_client(request):
    """
    POST /api/partner/v1/clients/register/
    Headless client onboarding via Partner SaaS backend.
    Accepts: { external_reference, name, email, phone, spending_cap, minute_cap }
    Returns: { status: 'success', client_id: int, name: str, partner_code: str }
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

    external_ref = str(data.get('external_reference', '')).strip()
    name = str(data.get('name', '')).strip() or f"عميل {external_ref or 'جديد'}"
    email = str(data.get('email', '')).strip()
    spending_cap = data.get('spending_cap')
    minute_cap = data.get('minute_cap')

    # Check if already registered under this partner with external_ref
    if external_ref:
        existing_rel = PartnerClientRelationship.objects.select_related('client').filter(
            partner=request.partner,
            external_reference=external_ref
        ).first()
        if existing_rel:
            return JsonResponse({
                "status": "success",
                "message": "Client already registered",
                "client_id": existing_rel.client_id,
                "name": existing_rel.client.first_name or existing_rel.client.username,
                "partner_code": request.partner.partner_code,
                "client": existing_rel.to_dict(),
            })

    # Create distinct sub-client user
    username_seed = f"prt_{request.partner.id}_{external_ref or secrets.token_hex(4)}"
    # ensure unique username
    base_username = username_seed[:140]
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{counter}"
        counter += 1

    client_user = User.objects.create(
        username=username,
        first_name=name[:30],
        email=email or f"{username}@partner.internal"
    )
    client_user.set_unusable_password()
    client_user.save()

    # Create relationship record
    client_rel = PartnerClientRelationship.objects.create(
        partner=request.partner,
        client=client_user,
        external_reference=external_ref,
        spending_cap=Decimal(str(spending_cap)) if spending_cap is not None else None,
        minute_cap=int(minute_cap) if minute_cap is not None else None,
        is_active=True
    )

    # Initialize default agent profile for client
    AgentProfile.objects.create(
        user=client_user,
        name=f"مساعد {name}",
        is_active=True,
        dialect='egyptian',
        voice_name='Aoede',
        custom_instructions=f"أنت المساعد الصوتي الذكي الخاص بـ '{name}'، تتحدث بلباقة ووضوح لخدمة العملاء."
    )

    # Dispatch confirmation Webhook
    dispatch_partner_webhook(request.partner, "client.registered", {
        "client_id": client_user.id,
        "external_reference": external_ref,
        "name": name,
        "username": username,
        "spending_cap": float(client_rel.spending_cap) if client_rel.spending_cap else None,
    })

    return JsonResponse({
        "status": "success",
        "client_id": client_user.id,
        "external_reference": external_ref,
        "name": name,
        "partner_code": request.partner.partner_code,
        "client": client_rel.to_dict()
    }, status=201)


@csrf_exempt
@partner_required
def api_partner_list_clients(request):
    """
    GET /api/partner/v1/clients/
    Lists all sub-clients registered under this partner.
    """
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    clients = PartnerClientRelationship.objects.filter(partner=request.partner).select_related('client')
    return JsonResponse({
        "status": "success",
        "partner_code": request.partner.partner_code,
        "count": clients.count(),
        "clients": [c.to_dict() for c in clients]
    })


@csrf_exempt
@partner_client_access_required
def api_partner_client_calls(request, client_id):
    """
    GET /api/partner/v1/clients/<int:client_id>/calls/
    Returns full CDR, transcript, and AI summary list for the target sub-client.
    """
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    calls = CallSession.objects.filter(user=request.client_user).order_by('-started_at')[:100]
    calls_list = []
    for call in calls:
        calls_list.append({
            "call_id": call.room_name,
            "direction": call.direction,
            "direction_display": call.get_direction_display(),
            "caller_phone": call.caller_phone or "",
            "destination_phone": call.destination_phone or "",
            "call_goal": call.call_goal or "",
            "started_at": call.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": call.ended_at.strftime("%Y-%m-%d %H:%M:%S") if call.ended_at else None,
            "duration_seconds": call.duration_seconds,
            "billed_minutes": call.billed_minutes,
            "cost": float(call.cost),
            "summary": call.summary or "",
            "transcript_text": call.transcript_text or "",
            "recording_url": get_full_recording_url(request, call.recording_url),
            "dialogue_turns": call.dialogue_turns,
        })

    return JsonResponse({
        "status": "success",
        "client_id": client_id,
        "total_calls": len(calls_list),
        "total_billed_minutes": sum(c['billed_minutes'] for c in calls_list),
        "calls": calls_list,
    })


@csrf_exempt
@partner_client_access_required
def api_partner_client_call_dial(request, client_id):
    """
    POST /api/partner/v1/clients/<int:client_id>/calls/dial/
    Trigger an autonomous AI outbound call for this specific sub-client.
    Verifies partner wallet balance & client caps beforehand.
    Dispatches 'call.outbound_initiated' partner webhook upon success.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed. Use POST."}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON body format"}, status=400)

    phone_number = str(data.get('phone_number') or '').strip()
    if not phone_number:
        return JsonResponse({"status": "error", "message": "phone_number is required"}, status=400)

    call_goal = str(data.get('call_goal') or '').strip()
    profile_id = data.get('profile_id')
    gateway_type = str(data.get('gateway_type') or 'auto').strip()
    gateway_id = data.get('gateway_id')

    try:
        res = initiate_outbound_call(
            user=request.client_user,
            phone_number=phone_number,
            call_goal=call_goal,
            profile_id=profile_id,
            gateway_type=gateway_type,
            gateway_id=gateway_id,
            partner=request.partner,
            client_rel=request.client_rel,
        )
        http_status = res.pop('http_status', 201)
        if res.get('status') == 'success':
            dispatch_partner_webhook(request.partner, "call.outbound_initiated", {
                "client_id": client_id,
                "call_id": res.get('call_id'),
                "destination_phone": res.get('destination_phone'),
                "call_goal": res.get('call_goal', ''),
                "rate_per_minute": float(request.partner.custom_rate_per_minute),
            })
            res['client_id'] = client_id
        return JsonResponse(res, status=http_status)
    except Exception as e:
        logger.exception(f"Error in api_partner_client_call_dial for client {client_id}: {e}")
        return JsonResponse({"status": "error", "message": f"Client outbound call initiation failed: {str(e)}"}, status=500)


@csrf_exempt
@partner_client_access_required
def api_partner_client_call_hangup(request, client_id=None):
    """
    POST /api/partner/v1/clients/<int:client_id>/calls/hangup/
    Terminate an active call session immediately for this sub-client.
    Accepts:
    {
        "call_id": "room_name_or_call_session_id"
    }
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed. Use POST."}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON body format"}, status=400)

    room_name = str(data.get('call_id') or data.get('room_name') or '').strip()
    if not room_name:
        return JsonResponse({"status": "error", "message": "call_id or room_name is required"}, status=400)

    from call_center.views import api_hangup_call
    return api_hangup_call(request)


@csrf_exempt
@partner_required
def api_partner_studio(request, client_id=None):
    """
    GET /api/partner/v1/studio/ or /api/partner/v1/clients/<int:client_id>/profiles/studio/
    Returns full studio customization metadata:
    - 30 Google HD studio voices with styles and gender classifications
    - 11 Supported languages
    - 29 Regional dialects grouped hierarchically
    - Sample roles and styles for free-text inspiration
    """
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    from agents.views import GOOGLE_VOICES, LANGUAGE_DIALECTS_MAP
    return JsonResponse({
        "status": "success",
        "google_voices": GOOGLE_VOICES,
        "languages": [{"id": l[0], "label": l[1]} for l in AgentProfile.LANGUAGE_CHOICES],
        "language_dialects_map": LANGUAGE_DIALECTS_MAP,
        "genders": [{"id": g[0], "label": g[1]} for g in AgentProfile.GENDER_CHOICES],
        "verbosities": [
            {"id": "concise", "label": "مختصر ⚡ (ردود مباشرة في 1-2 جملة)", "description": "10-25 كلمة، رد مباشر وسريع بدون حشو أو أسئلة زائدة"},
            {"id": "balanced", "label": "متوازن ⚖️ (رد طبيعي ومهذب)", "description": "2-3 جمل طبيعية توازن بين السرعة واللطف"},
            {"id": "detailed", "label": "مفصل 📖 (شرح وافٍ واستشاري)", "description": "تفاصيل وخطوات وخيارات واقتراحات"}
        ],
        "sample_roles": [
            "ممثل خدمة عملاء محترف لمتجر الكتروني",
            "مستشار تسويق ومبيعات عقارية خبير في الفلل والأراضي",
            "مساعد شخصي ذكي وودود لحجز المواعيد وتنظيم المهام",
            "مستشار دعم فني وتقني متخصص لحل المشاكل التقنية"
        ],
        "sample_styles": [
            "ودود ولطيف ومرح، يبعث على الراحة والابتسامة في الحديث",
            "رسمي ومهني وجاد، خالٍ من المزاح المفرط، ويركز على الوقار والاحترام",
            "مباشر وسريع وموجز، يقدم الإجابة بكلمات قليلة ومفيدة دون إطالة",
            "حماسي ونشيط ومتفائل، يظهر طاقة إيجابية عالية في الرد"
        ]
    })


@csrf_exempt
@partner_client_access_required
def api_partner_client_profile(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/profiles/
    GET: List all agent profiles for client (supports ?is_active=true/false).
         Also returns 'active_profile' and 'profile' for backward compatibility.
    POST: Create a new agent profile for client.
    """
    if request.method == 'GET':
        qs = AgentProfile.objects.filter(user=request.client_user)
        is_active_param = request.GET.get('is_active')
        if is_active_param is not None:
            val = is_active_param.strip().lower() in ('true', '1', 'yes')
            qs = qs.filter(is_active=val)

        profiles = list(qs)
        active_profile = AgentProfile.objects.filter(user=request.client_user, is_active=True).first()
        if not active_profile and profiles:
            active_profile = profiles[0]

        profile_data = active_profile.to_dict() if active_profile else None
        if profile_data and 'system_prompt' not in profile_data:
            profile_data['system_prompt'] = profile_data.get('custom_instructions', '')

        profiles_list = []
        for p in profiles:
            d = p.to_dict()
            d['system_prompt'] = p.custom_instructions
            profiles_list.append(d)

        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "total": len(profiles_list),
            "profile": profile_data,  # backward compatibility
            "active_profile": profile_data,
            "profiles": profiles_list,
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        name = data.get('name') or f"مساعد {request.client_user.first_name or request.client_user.username}"
        voice_name = data.get('voice_name', 'Aoede').strip()
        gender = data.get('gender', 'female').strip()
        language = data.get('language', 'arabic').strip()
        dialect = data.get('dialect', 'egyptian').strip()
        persona_role = str(data.get('persona_role', 'خدمة عملاء ومبيعات المتجر')).strip()
        speaking_style = str(data.get('speaking_style', 'ودود ولطيف ومرح')).strip()
        verbosity = str(data.get('verbosity', 'balanced')).strip()
        custom_instructions = data.get('custom_instructions') or data.get('system_prompt', '')
        is_active = data.get('is_active', True)

        profile = AgentProfile.objects.create(
            user=request.client_user,
            name=name,
            voice_name=voice_name,
            gender=gender,
            language=language,
            dialect=dialect,
            persona_role=persona_role,
            speaking_style=speaking_style,
            verbosity=verbosity,
            custom_instructions=custom_instructions,
            is_active=is_active
        )

        p_dict = profile.to_dict()
        p_dict['system_prompt'] = profile.custom_instructions

        return JsonResponse({
            "status": "success",
            "message": "Agent profile created successfully",
            "client_id": client_id,
            "profile": p_dict,
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_profile_detail(request, client_id, profile_id):
    """
    GET, PUT, PATCH, DELETE /api/partner/v1/clients/<int:client_id>/profiles/<int:profile_id>/
    GET: Retrieve specific profile.
    PUT/PATCH: Update specific profile.
    DELETE: Delete specific profile.
    """
    profile = AgentProfile.objects.filter(user=request.client_user, id=profile_id).first()
    if not profile:
        return JsonResponse({"status": "error", "message": "Agent profile not found"}, status=404)

    if request.method == 'GET':
        p_dict = profile.to_dict()
        p_dict['system_prompt'] = profile.custom_instructions
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "profile": p_dict
        })

    elif request.method in ('PUT', 'PATCH'):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        for field in ['name', 'voice_name', 'gender', 'language', 'dialect', 'persona_role', 'speaking_style', 'verbosity']:
            if field in data:
                setattr(profile, field, str(data[field]).strip())
        if 'custom_instructions' in data or 'system_prompt' in data:
            profile.custom_instructions = data.get('custom_instructions') or data.get('system_prompt', '')
        if 'is_active' in data:
            profile.is_active = bool(data['is_active'])

        profile.save()

        p_dict = profile.to_dict()
        p_dict['system_prompt'] = profile.custom_instructions
        return JsonResponse({
            "status": "success",
            "message": "Profile updated successfully",
            "client_id": client_id,
            "profile": p_dict
        })

    elif request.method == 'DELETE':
        was_active = profile.is_active
        profile.delete()
        if was_active:
            next_profile = AgentProfile.objects.filter(user=request.client_user).order_by('-updated_at').first()
            if next_profile:
                next_profile.is_active = True
                next_profile.save()

        return JsonResponse({
            "status": "success",
            "message": "Agent profile deleted successfully",
            "client_id": client_id,
            "deleted_profile_id": profile_id
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_profile_activate(request, client_id, profile_id):
    """
    POST /api/partner/v1/clients/<int:client_id>/profiles/<int:profile_id>/activate/
    Activate a specific agent profile for this client.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = AgentProfile.objects.filter(user=request.client_user, id=profile_id).first()
    if not profile:
        return JsonResponse({"status": "error", "message": "Agent profile not found"}, status=404)

    profile.is_active = True
    profile.save()

    p_dict = profile.to_dict()
    p_dict['system_prompt'] = profile.custom_instructions

    return JsonResponse({
        "status": "success",
        "message": "Agent profile activated successfully",
        "client_id": client_id,
        "profile": p_dict
    })


@csrf_exempt
@partner_client_access_required
def api_partner_client_memory(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/memory/
    GET:
      - If 'phone' or 'phone_number' query param provided: retrieve specific customer memory context (backward compatible).
      - Otherwise: list customer memories with pagination (?page=1&limit=20) and search (?q=...).
    POST:
      - Upsert customer memory record by phone_number.
    """
    if request.method == 'GET':
        raw_phone = request.GET.get('phone') or request.GET.get('phone_number')
        if raw_phone:
            phone = str(raw_phone).strip()
            if not phone.startswith('+') and phone.isdigit() and len(phone) >= 9:
                phone = '+' + phone

            mem = CustomerMemory.objects.filter(user=request.client_user, phone_number=phone).first()
            if not mem and phone != 'web_dashboard' and len(phone) >= 7:
                mem = CustomerMemory.objects.filter(user=request.client_user, phone_number__endswith=phone[-8:]).first()

            perm_text = ""
            c_name = ""
            if mem:
                c_name = mem.customer_name
                if isinstance(mem.permanent_profile, dict):
                    perm_text = mem.permanent_profile.get('notes') or mem.permanent_profile.get('permanent_memory') or str(mem.permanent_profile)
                    if not c_name:
                        c_name = mem.permanent_profile.get('customer_name', '')

            return JsonResponse({
                "status": "success",
                "client_id": client_id,
                "phone_number": phone,
                "customer_name": c_name,
                "permanent_memory": perm_text,
                "immediate_notes": mem.last_interaction_summary if mem else "",
                "total_calls": mem.total_calls_count if mem else 0,
                "memory": mem.to_dict() if mem else None,
            })

        # List all memories with query search & pagination
        qs = CustomerMemory.objects.filter(user=request.client_user)
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(customer_name__icontains=q) | Q(phone_number__icontains=q))

        try:
            page_num = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page_num = 1

        try:
            limit = min(100, max(1, int(request.GET.get('limit', 20))))
        except (ValueError, TypeError):
            limit = 20

        paginator = Paginator(qs, limit)
        page_obj = paginator.get_page(page_num)

        memories_list = [m.to_dict() for m in page_obj.object_list]

        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "total": paginator.count,
            "page": page_num,
            "limit": limit,
            "total_pages": paginator.num_pages,
            "memories": memories_list
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        raw_phone = data.get('caller_phone') or data.get('phone_number') or 'web_dashboard'
        phone = str(raw_phone).strip()
        if not phone.startswith('+') and phone.isdigit() and len(phone) >= 9:
            phone = '+' + phone

        mem = CustomerMemory.objects.filter(user=request.client_user, phone_number=phone).first()
        if not mem and phone != 'web_dashboard' and len(phone) >= 7:
            mem = CustomerMemory.objects.filter(user=request.client_user, phone_number__endswith=phone[-8:]).first()

        created = False
        if not mem:
            mem = CustomerMemory.objects.create(
                user=request.client_user,
                phone_number=phone,
                customer_name=data.get('customer_name', '')
            )
            created = True

        if 'customer_name' in data:
            mem.customer_name = str(data['customer_name']).strip()

        if 'permanent_profile' in data and isinstance(data['permanent_profile'], dict):
            prof = data['permanent_profile']
            if mem.customer_name and not prof.get('customer_name'):
                prof['customer_name'] = mem.customer_name
            mem.permanent_profile = prof
        elif 'permanent_memory' in data:
            prof = mem.permanent_profile if isinstance(mem.permanent_profile, dict) else {}
            prof['notes'] = data['permanent_memory']
            prof['customer_name'] = mem.customer_name
            mem.permanent_profile = prof

        if 'immediate_notes' in data:
            mem.last_interaction_summary = data['immediate_notes']
        elif 'last_interaction_summary' in data:
            mem.last_interaction_summary = data['last_interaction_summary']

        if 'total_calls_count' in data:
            try:
                mem.total_calls_count = int(data['total_calls_count'])
            except (ValueError, TypeError):
                pass

        mem.save()

        perm_text = mem.permanent_profile.get('notes', '') if isinstance(mem.permanent_profile, dict) else str(mem.permanent_profile)
        return JsonResponse({
            "status": "success",
            "message": "Customer memory created successfully" if created else "Customer memory updated successfully",
            "client_id": client_id,
            "phone_number": phone,
            "customer_name": mem.customer_name,
            "permanent_memory": perm_text,
            "immediate_notes": mem.last_interaction_summary,
            "memory": mem.to_dict()
        }, status=201 if created else 200)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_memory_detail(request, client_id, memory_id):
    """
    GET, PUT, PATCH, DELETE /api/partner/v1/clients/<int:client_id>/memory/<int:memory_id>/
    GET: Retrieve customer memory by ID.
    PUT/PATCH: Update customer memory fields by ID.
    DELETE: Delete customer memory record.
    """
    mem = CustomerMemory.objects.filter(user=request.client_user, id=memory_id).first()
    if not mem:
        return JsonResponse({"status": "error", "message": "Customer memory not found"}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "memory": mem.to_dict()
        })

    elif request.method in ('PUT', 'PATCH'):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        if 'customer_name' in data:
            mem.customer_name = str(data['customer_name']).strip()
        if 'phone_number' in data:
            phone = str(data['phone_number']).strip()
            if not phone.startswith('+') and phone.isdigit() and len(phone) >= 9:
                phone = '+' + phone
            mem.phone_number = phone

        if 'permanent_profile' in data and isinstance(data['permanent_profile'], dict):
            prof = data['permanent_profile']
            if mem.customer_name and not prof.get('customer_name'):
                prof['customer_name'] = mem.customer_name
            mem.permanent_profile = prof
        elif 'permanent_memory' in data:
            prof = mem.permanent_profile if isinstance(mem.permanent_profile, dict) else {}
            prof['notes'] = data['permanent_memory']
            prof['customer_name'] = mem.customer_name
            mem.permanent_profile = prof

        if 'immediate_notes' in data:
            mem.last_interaction_summary = data['immediate_notes']
        elif 'last_interaction_summary' in data:
            mem.last_interaction_summary = data['last_interaction_summary']

        if 'total_calls_count' in data:
            try:
                mem.total_calls_count = int(data['total_calls_count'])
            except (ValueError, TypeError):
                pass

        mem.save()

        return JsonResponse({
            "status": "success",
            "message": "Customer memory updated successfully",
            "client_id": client_id,
            "memory": mem.to_dict()
        })

    elif request.method == 'DELETE':
        mem.delete()
        return JsonResponse({
            "status": "success",
            "message": "Customer memory deleted successfully",
            "client_id": client_id,
            "deleted_memory_id": memory_id
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# =========================================================================
# Headless RAG Knowledge Base API for Sub-Clients
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_documents(request, client_id):
    """
    GET, POST, DELETE /api/partner/v1/clients/<int:client_id>/documents/
    GET: list all documents for client
    POST: upload document and generate pgvector embeddings for client
    DELETE: delete document
    """
    if request.method == 'GET':
        docs = Document.objects.filter(user=request.client_user).order_by('-created_at')
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "count": docs.count(),
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "file_type": d.file_type,
                    "file_size": d.file_size,
                    "chunks_count": d.chunks.count(),
                    "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
                }
                for d in docs
            ]
        })
    elif request.method == 'POST':
        file_obj = request.FILES.get('file')
        title = request.POST.get('title', '').strip()
        raw_text = (request.POST.get('content') or request.POST.get('text') or '').strip()

        if not file_obj and not raw_text and request.body:
            try:
                body_data = json.loads(request.body.decode('utf-8'))
                title = title or body_data.get('title', '').strip()
                raw_text = (body_data.get('content') or body_data.get('text') or '').strip()
            except Exception:
                pass

        if not file_obj and not raw_text:
            return JsonResponse({
                "status": "error",
                "code": "missing_payload",
                "message": "يجب إرفاق ملف مستند (file) بصيغة PDF, DOCX, TXT, MD أو إرسال نص مباشر (content)."
            }, status=400)

        try:
            if file_obj:
                filename = file_obj.name
                ext = os.path.splitext(filename)[1].lower()
                allowed_exts = ['.pdf', '.docx', '.doc', '.txt', '.md']
                if ext not in allowed_exts:
                    return JsonResponse({
                        "status": "error",
                        "code": "unsupported_file_type",
                        "message": f"صيغة الملف '{ext}' غير مدعومة. الصيغ المدعومة هي: PDF, DOCX, TXT, MD"
                    }, status=400)

                title = title or filename
                text = extract_text_from_file(file_obj, filename)
                file_size = file_obj.size
                file_type = ext.lstrip('.')
                saved_file = file_obj
            else:
                title = title or "مستند نصي معرفي"
                text = raw_text.strip()
                file_size = len(text.encode('utf-8'))
                file_type = "txt"
                saved_file = None

            if not text:
                return JsonResponse({
                    "status": "error",
                    "code": "empty_document",
                    "message": "لم يتم العثور على أي نصوص صالحة داخل المستند أو النص المدخل."
                }, status=400)

            chunks = chunk_text(text, chunk_size=500, overlap=50)
            if not chunks:
                return JsonResponse({"status": "error", "message": "فشل تقطيع نصوص المستند."}, status=400)

            doc = Document.objects.create(
                user=request.client_user,
                title=title,
                file=saved_file,
                file_type=file_type,
                file_size=file_size,
                status='ready'
            )

            # Generate embeddings via Gemini
            client = genai.Client(api_key=SystemSetting.get_gemini_api_key())
            embeddings = get_embeddings_batch(client, chunks, batch_size=50)

            chunk_objs = [
                DocumentChunk(
                    document=doc,
                    user=request.client_user,
                    chunk_index=i,
                    content=c,
                    embedding=emb
                )
                for i, (c, emb) in enumerate(zip(chunks, embeddings))
            ]
            DocumentChunk.objects.bulk_create(chunk_objs)

            return JsonResponse({
                "status": "success",
                "message": f"تم رفع المستند '{title}' وفهرسته بالمتجهات للعميل بنجاح.",
                "client_id": client_id,
                "document": {
                    "id": doc.id,
                    "title": doc.title,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "status": "ready",
                    "chunks_count": len(chunks),
                    "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M")
                }
            }, status=201)
        except Exception as e:
            logger.error(f"Error in partner document upload for client {client_id}: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": f"حدث خطأ أثناء فهرسة المستند: {str(e)}"}, status=500)

    elif request.method == 'DELETE':
        doc_id = request.GET.get('document_id')
        if not doc_id:
            return JsonResponse({"status": "error", "message": "document_id is required"}, status=400)
        doc = Document.objects.filter(id=doc_id, user=request.client_user).first()
        if not doc:
            return JsonResponse({"status": "error", "message": "Document not found"}, status=404)
        doc.delete()
        return JsonResponse({"status": "success", "message": f"Document {doc_id} deleted."})

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# =========================================================================
# Headless Telephony & PBX Trunks API for Sub-Clients
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_telephony(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/telephony/
    GET: list inbound PBX trunks & outbound SIP trunks for client
    POST: configure inbound PBX or outbound trunk
    """
    if request.method == 'GET':
        inbound_trunks = [t.to_dict() for t in InboundPBXTrunk.objects.filter(user=request.client_user)]
        outbound_trunks = [t.to_dict() for t in OutboundSIPTrunk.objects.filter(user=request.client_user)]
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "inbound_trunks": inbound_trunks,
            "outbound_trunks": outbound_trunks,
        })
    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        trunk_type = data.get('trunk_type', 'inbound')
        name = data.get('name') or "سنترال الشريك (Partner PBX)"

        if trunk_type == 'inbound':
            auth_mode = data.get('auth_mode', 'ip')
            pbx_ip = data.get('pbx_ip', '')
            inbound_numbers = data.get('inbound_numbers', '')
            trunk = InboundPBXTrunk.objects.create(
                user=request.client_user,
                name=name,
                auth_mode=auth_mode,
                pbx_ip=pbx_ip,
                inbound_numbers=inbound_numbers,
                auth_username=data.get('auth_username', ''),
                auth_password=data.get('auth_password', ''),
                is_active=True
            )
            return JsonResponse({
                "status": "success",
                "message": "Inbound PBX trunk created successfully",
                "trunk": trunk.to_dict(),
            }, status=201)
        else:
            sip_host = data.get('sip_host', '')
            if not sip_host:
                return JsonResponse({"status": "error", "message": "sip_host is required for outbound trunk"}, status=400)
            trunk = OutboundSIPTrunk.objects.create(
                user=request.client_user,
                name=name,
                sip_host=sip_host,
                sip_port=int(data.get('sip_port', 5060)),
                transport=data.get('transport', 'UDP'),
                auth_username=data.get('auth_username', ''),
                auth_password=data.get('auth_password', ''),
                caller_id=data.get('caller_id', ''),
                is_active=True
            )
            return JsonResponse({
                "status": "success",
                "message": "Outbound SIP trunk created successfully",
                "trunk": trunk.to_dict(),
            }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# =========================================================================
# Headless Call Center Employees CRUD API for Sub-Clients
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_employees(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/employees/
    GET: List all employees belonging to this sub-client.
    POST: Create a new employee with extension, credentials, and department.
    """
    if request.method == 'GET':
        employees = EmployeeProfile.objects.filter(
            employer=request.client_user,
            is_active=True
        ).order_by('extension')
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "total_employees": employees.count(),
            "employees": [e.to_dict() for e in employees]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        display_name = str(data.get('display_name') or '').strip()
        extension = str(data.get('extension') or '').strip()
        department = str(data.get('department') or 'المبيعات').strip()
        status_val = str(data.get('status') or 'ready').strip()
        password = str(data.get('password') or f"emp_{secrets.token_hex(4)}").strip()
        username = str(data.get('username') or f"c{client_id}_e{extension}_{secrets.token_hex(2)}").strip()

        if not display_name or not extension:
            return JsonResponse({"status": "error", "message": "display_name and extension are required"}, status=400)

        # Check unique extension for this client
        if EmployeeProfile.objects.filter(employer=request.client_user, extension=extension, is_active=True).exists():
            return JsonResponse({
                "status": "error",
                "message": f"Extension '{extension}' is already registered for this client."
            }, status=409)

        # Create auth user for this employee
        if User.objects.filter(username=username).exists():
            username = f"{username}_{secrets.token_hex(3)}"

        emp_user = User.objects.create_user(
            username=username,
            password=password,
            first_name=display_name
        )

        employee = EmployeeProfile.objects.create(
            user=emp_user,
            employer=request.client_user,
            extension=extension,
            display_name=display_name,
            department=department,
            status=status_val,
            avatar_url=f"https://api.dicebear.com/7.x/bottts/png?seed={extension}",
            is_active=True
        )

        return JsonResponse({
            "status": "success",
            "message": f"Employee '{display_name}' created successfully (ext: {extension}).",
            "client_id": client_id,
            "employee": {
                **employee.to_dict(),
                "temporary_password": password
            }
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_employee_detail(request, client_id, employee_id):
    """
    GET, POST/PUT/PATCH, & DELETE /api/partner/v1/clients/<int:client_id>/employees/<int:employee_id>/
    GET: Retrieve employee details and queue memberships.
    POST/PUT/PATCH: Update employee fields (display_name, department, status, extension, password).
    DELETE: Delete employee and associated account.
    """
    employee = EmployeeProfile.objects.filter(id=employee_id, employer=request.client_user).first()
    if not employee:
        return JsonResponse({"status": "error", "message": "Employee not found for this client"}, status=404)

    if request.method == 'GET':
        memberships = employee.queue_memberships.filter(is_active=True).select_related('queue')
        queues_list = [{"id": m.queue.id, "name": m.queue.name, "code": m.queue.code, "order": m.order} for m in memberships]
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "employee": employee.to_dict(),
            "queues": queues_list
        })

    elif request.method in ['POST', 'PUT', 'PATCH']:
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        if 'display_name' in data:
            employee.display_name = str(data['display_name']).strip()
            employee.user.first_name = employee.display_name
            employee.user.save(update_fields=['first_name'])

        if 'department' in data:
            employee.department = str(data['department']).strip()

        if 'status' in data:
            employee.status = str(data['status']).strip()

        if 'extension' in data:
            new_ext = str(data['extension']).strip()
            if new_ext != employee.extension:
                if EmployeeProfile.objects.filter(employer=request.client_user, extension=new_ext, is_active=True).exclude(id=employee.id).exists():
                    return JsonResponse({"status": "error", "message": f"Extension '{new_ext}' is already taken"}, status=409)
                employee.extension = new_ext

        if 'password' in data and data['password']:
            employee.user.set_password(str(data['password']).strip())
            employee.user.save(update_fields=['password'])

        employee.save()

        return JsonResponse({
            "status": "success",
            "message": "Employee updated successfully",
            "client_id": client_id,
            "employee": employee.to_dict()
        })

    elif request.method == 'DELETE':
        name = employee.display_name
        ext = employee.extension
        user_to_del = employee.user
        employee.delete()
        if user_to_del:
            user_to_del.delete()

        return JsonResponse({
            "status": "success",
            "message": f"Employee '{name}' (ext: {ext}) deleted successfully.",
            "client_id": client_id
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# =========================================================================
# Headless Call Center Queues Full CRUD API for Sub-Clients
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_queues(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/queues/
    GET: list call queues for client with member count.
    POST: create or update call queue with optional initial members list.
    """
    if request.method == 'GET':
        queues = CallQueue.objects.filter(user=request.client_user).prefetch_related('memberships__employee')
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "total_queues": queues.count(),
            "queues": [q.to_dict() for q in queues]
        })
    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        name = data.get('name', 'طابور خدمة العملاء')
        code = str(data.get('code', '200')).strip()
        description = str(data.get('description', '')).strip()
        queue, created = CallQueue.objects.update_or_create(
            user=request.client_user,
            code=code,
            defaults={
                'name': name,
                'description': description,
                'strategy': data.get('strategy', 'round_robin'),
                'ring_timeout_seconds': int(data.get('ring_timeout_seconds', 15)),
                'total_timeout_seconds': int(data.get('total_timeout_seconds', 60)),
                'fallback_action': data.get('fallback_action', 'ai_assistant')
            }
        )

        # Handle optional initial members assignment
        if 'members' in data and isinstance(data['members'], list):
            # Sync memberships
            QueueMembership.objects.filter(queue=queue).delete()
            for idx, emp_id in enumerate(data['members']):
                emp = EmployeeProfile.objects.filter(id=emp_id, employer=request.client_user).first()
                if emp:
                    QueueMembership.objects.create(queue=queue, employee=emp, order=idx + 1)

        return JsonResponse({
            "status": "success",
            "message": "Call queue created successfully" if created else "Call queue updated successfully",
            "queue": queue.to_dict()
        }, status=201 if created else 200)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_queue_detail(request, client_id, queue_id):
    """
    GET, POST/PUT/PATCH, & DELETE /api/partner/v1/clients/<int:client_id>/queues/<int:queue_id>/
    GET: Get queue details and member list.
    POST/PUT: Update queue settings and optional members.
    DELETE: Remove queue and associated memberships.
    """
    queue = CallQueue.objects.filter(id=queue_id, user=request.client_user).first()
    if not queue:
        return JsonResponse({"status": "error", "message": "Call queue not found for this client"}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "queue": queue.to_dict()
        })

    elif request.method in ['POST', 'PUT', 'PATCH']:
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        if 'name' in data:
            queue.name = str(data['name']).strip()
        if 'code' in data:
            new_code = str(data['code']).strip()
            if new_code != queue.code:
                if CallQueue.objects.filter(user=request.client_user, code=new_code).exclude(id=queue.id).exists():
                    return JsonResponse({"status": "error", "message": f"Queue code '{new_code}' already exists"}, status=409)
                queue.code = new_code
        if 'description' in data:
            queue.description = str(data['description']).strip()
        if 'strategy' in data:
            queue.strategy = data['strategy']
        if 'ring_timeout_seconds' in data:
            queue.ring_timeout_seconds = int(data['ring_timeout_seconds'])
        if 'total_timeout_seconds' in data:
            queue.total_timeout_seconds = int(data['total_timeout_seconds'])
        if 'fallback_action' in data:
            queue.fallback_action = data['fallback_action']

        queue.save()

        # Update members if provided
        if 'members' in data and isinstance(data['members'], list):
            QueueMembership.objects.filter(queue=queue).delete()
            for idx, emp_id in enumerate(data['members']):
                emp = EmployeeProfile.objects.filter(id=emp_id, employer=request.client_user).first()
                if emp:
                    QueueMembership.objects.create(queue=queue, employee=emp, order=idx + 1)

        return JsonResponse({
            "status": "success",
            "message": "Call queue updated successfully",
            "client_id": client_id,
            "queue": queue.to_dict()
        })

    elif request.method == 'DELETE':
        name = queue.name
        code = queue.code
        queue.delete()
        return JsonResponse({
            "status": "success",
            "message": f"Call queue '{name}' (code: {code}) deleted successfully.",
            "client_id": client_id
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_queue_members(request, client_id, queue_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/queues/<int:queue_id>/members/
    GET: List active employee members in queue.
    POST: Manage members (action: 'add', 'remove', 'set').
    """
    queue = CallQueue.objects.filter(id=queue_id, user=request.client_user).first()
    if not queue:
        return JsonResponse({"status": "error", "message": "Call queue not found for this client"}, status=404)

    if request.method == 'GET':
        memberships = queue.memberships.filter(is_active=True).select_related('employee')
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "queue_id": queue.id,
            "queue_name": queue.name,
            "total_members": memberships.count(),
            "members": [m.to_dict() for m in memberships]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        action = data.get('action', 'add')

        if action == 'add':
            emp_id = data.get('employee_id')
            emp = EmployeeProfile.objects.filter(id=emp_id, employer=request.client_user).first()
            if not emp:
                return JsonResponse({"status": "error", "message": "Employee not found for this client"}, status=404)

            membership, created = QueueMembership.objects.get_or_create(
                queue=queue,
                employee=emp,
                defaults={'order': int(data.get('order', queue.memberships.count() + 1)), 'is_active': True}
            )
            if not created and not membership.is_active:
                membership.is_active = True
                membership.save(update_fields=['is_active'])

            return JsonResponse({
                "status": "success",
                "message": f"Employee '{emp.display_name}' added to queue '{queue.name}'",
                "membership": membership.to_dict()
            }, status=201 if created else 200)

        elif action == 'remove':
            emp_id = data.get('employee_id')
            QueueMembership.objects.filter(queue=queue, employee_id=emp_id).delete()
            return JsonResponse({
                "status": "success",
                "message": f"Employee #{emp_id} removed from queue '{queue.name}'"
            })

        elif action == 'set':
            member_ids = data.get('member_ids', [])
            QueueMembership.objects.filter(queue=queue).delete()
            created_members = []
            for idx, emp_id in enumerate(member_ids):
                emp = EmployeeProfile.objects.filter(id=emp_id, employer=request.client_user).first()
                if emp:
                    m = QueueMembership.objects.create(queue=queue, employee=emp, order=idx + 1)
                    created_members.append(m.to_dict())

            return JsonResponse({
                "status": "success",
                "message": f"Queue '{queue.name}' members synchronized ({len(created_members)} members)",
                "members": created_members
            })

        return JsonResponse({"status": "error", "message": f"Unknown action: {action}"}, status=400)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# =========================================================================
# Live Voice Session Token for Sub-Clients (Direct WebRTC Call Launch)
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_token(request, client_id):
    """
    POST /api/partner/v1/clients/<int:client_id>/token/
    Generates LiveKit token for the sub-client to start a live voice session.
    Verifies partner wallet balance & client caps beforehand.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    # 1. Guard client caps
    from billing.models import UserWallet
    partner_wallet, _ = UserWallet.objects.get_or_create(user=request.partner.user)
    next_cost = request.partner.custom_rate_per_minute

    if request.client_rel.is_cap_exceeded(next_cost):
        return JsonResponse({
            "status": "error",
            "code": "CAP_EXCEEDED",
            "message": "Client has reached their assigned spending or minute quota."
        }, status=403)

    if partner_wallet.balance < next_cost:
        return JsonResponse({
            "status": "error",
            "code": "PARTNER_BALANCE_LOW",
            "message": "Partner balance is insufficient to start a new voice session."
        }, status=402)

    # Generate token
    room_name = f"partner_{request.partner.id}_{client_id}_{secrets.token_hex(4)}"
    identity = f"client_{client_id}_{secrets.token_hex(2)}"

    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
        .with_identity(identity) \
        .with_name(request.client_user.first_name or request.client_user.username) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))

    jwt_token = token.to_jwt()

    return JsonResponse({
        "status": "success",
        "client_id": client_id,
        "room_name": room_name,
        "livekit_url": settings.LIVEKIT_URL,
        "token": jwt_token,
    })


# =========================================================================
# Headless RAG Semantic Query API for Sub-Clients
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_rag_query(request, client_id):
    """
    POST /api/partner/v1/clients/<int:client_id>/rag/query/
    Partner API to query the sub-client's RAG knowledge base semantically.
    Accepts: {"query": str, "top_k": int}
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        query = str(data.get('query', '')).strip()
        top_k = int(data.get('top_k', 3))

        if not query:
            return JsonResponse({"status": "error", "message": "query is required"}, status=400)

        # Generate query embedding via Gemini
        client = genai.Client(api_key=SystemSetting.get_gemini_api_key())
        embed_res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        if not embed_res or not embed_res.embeddings:
            return JsonResponse({"status": "error", "message": "Failed to generate query embedding"}, status=500)

        query_vec = embed_res.embeddings[0].values

        # Cosine distance search in pgvector
        chunks = DocumentChunk.objects.filter(user=request.client_user) \
            .annotate(distance=CosineDistance('embedding', query_vec)) \
            .filter(distance__lte=0.55) \
            .order_by('distance')[:top_k]

        results = []
        for c in chunks:
            similarity = round(1.0 - float(c.distance), 4) if hasattr(c, 'distance') and c.distance is not None else 1.0
            results.append({
                "chunk_id": c.id,
                "document_id": c.document_id,
                "document_title": c.document.title if c.document else "",
                "content": c.content,
                "similarity": similarity
            })

        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "query": query,
            "total_matches": len(results),
            "results": results
        })
    except Exception as e:
        logger.error(f"Error in partner RAG query for client {client_id}: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"Query failed: {str(e)}"}, status=500)


# =========================================================================
# Headless Phone Numbers & DID Linking API for Sub-Clients
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_numbers(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/telephony/numbers/
    GET: List all active phone numbers (DIDs / Caller IDs) linked to this client.
    POST: Link/assign a phone number to client's inbound PBX trunk or outbound trunk.
    """
    if request.method == 'GET':
        inbound_trunks = InboundPBXTrunk.objects.filter(user=request.client_user)
        outbound_trunks = OutboundSIPTrunk.objects.filter(user=request.client_user)

        numbers = []
        for ib in inbound_trunks:
            if ib.inbound_numbers:
                for num in ib.inbound_numbers.split(','):
                    cleaned = num.strip()
                    if cleaned:
                        numbers.append({
                            "phone_number": cleaned,
                            "type": "inbound_did",
                            "trunk_type": "inbound_pbx",
                            "trunk_id": ib.id,
                            "trunk_name": ib.name,
                            "destination_type": ib.destination_type,
                            "is_active": ib.is_active,
                        })

        for ob in outbound_trunks:
            if ob.caller_id:
                numbers.append({
                    "phone_number": ob.caller_id,
                    "type": "outbound_caller_id",
                    "trunk_type": "outbound_sip",
                    "trunk_id": ob.id,
                    "trunk_name": ob.name,
                    "is_active": ob.is_active,
                })

        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "total_numbers": len(numbers),
            "numbers": numbers
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        phone_number = str(data.get('phone_number', '')).strip()
        trunk_type = data.get('trunk_type', 'inbound')
        trunk_id = data.get('trunk_id')

        if not phone_number:
            return JsonResponse({"status": "error", "message": "phone_number is required"}, status=400)

        if trunk_type == 'inbound':
            trunk = None
            if trunk_id:
                trunk = InboundPBXTrunk.objects.filter(id=trunk_id, user=request.client_user).first()
            if not trunk:
                trunk = InboundPBXTrunk.objects.filter(user=request.client_user).first()
            if not trunk:
                # Create an inbound PBX trunk for this client
                trunk = InboundPBXTrunk.objects.create(
                    user=request.client_user,
                    name=f"سنترال العميل ({phone_number})",
                    auth_mode='ip',
                    inbound_numbers=phone_number,
                    is_active=True
                )
            else:
                existing_nums = [n.strip() for n in trunk.inbound_numbers.split(',') if n.strip()]
                if phone_number not in existing_nums:
                    existing_nums.append(phone_number)
                    trunk.inbound_numbers = ",".join(existing_nums)
                    trunk.save(update_fields=['inbound_numbers'])

            return JsonResponse({
                "status": "success",
                "message": f"Phone number {phone_number} linked to inbound trunk {trunk.name}",
                "client_id": client_id,
                "trunk": trunk.to_dict()
            }, status=201)

        else:
            trunk = None
            if trunk_id:
                trunk = OutboundSIPTrunk.objects.filter(id=trunk_id, user=request.client_user).first()
            if not trunk:
                trunk = OutboundSIPTrunk.objects.filter(user=request.client_user).first()
            if not trunk:
                trunk = OutboundSIPTrunk.objects.create(
                    user=request.client_user,
                    name=f"خط صادر ({phone_number})",
                    sip_host="sip.provider.com",
                    caller_id=phone_number,
                    is_active=True
                )
            else:
                trunk.caller_id = phone_number
                trunk.save(update_fields=['caller_id'])

            return JsonResponse({
                "status": "success",
                "message": f"Caller ID {phone_number} linked to outbound trunk {trunk.name}",
                "client_id": client_id,
                "trunk": trunk.to_dict()
            }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# =========================================================================
# Headless Trunk Detail & Deletion API
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_telephony_detail(request, client_id, trunk_type, trunk_id):
    """
    GET & DELETE /api/partner/v1/clients/<int:client_id>/telephony/<str:trunk_type>/<int:trunk_id>/
    GET: Get trunk details and Issabel PBX config.
    DELETE: Remove trunk for client.
    """
    model = InboundPBXTrunk if trunk_type == 'inbound' else OutboundSIPTrunk
    trunk = model.objects.filter(id=trunk_id, user=request.client_user).first()

    if not trunk:
        return JsonResponse({"status": "error", "message": f"{trunk_type.capitalize()} trunk not found"}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "trunk_type": trunk_type,
            "trunk": trunk.to_dict()
        })
    elif request.method == 'DELETE':
        trunk_name = trunk.name
        trunk.delete()
        return JsonResponse({
            "status": "success",
            "message": f"{trunk_type.capitalize()} trunk '{trunk_name}' deleted successfully.",
            "client_id": client_id
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


# =========================================================================
# Client FastMCP Server Management & Live Tool Synchronization
# =========================================================================

@csrf_exempt
@partner_client_access_required
def api_partner_client_mcp(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<int:client_id>/mcp/
    Manage external FastMCP SSE tool servers for this specific sub-client.
    """
    if request.method == 'GET':
        servers = list(UserMCPServer.objects.filter(user=request.client_user).order_by('-updated_at'))
        
        shared_server = None
        if request.partner.shared_mcp_server:
            shared_server = request.partner.shared_mcp_server.to_dict()

        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "total_servers": len(servers),
            "partner_shared_server": shared_server,
            "servers": [s.to_dict() for s in servers]
        })

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        name = data.get('name', 'خادم أدوات العميل (FastMCP)').strip()
        server_url = data.get('server_url', '').strip()
        auth_token = data.get('auth_token', '').strip()
        is_active = bool(data.get('is_active', True))
        sync_now = bool(data.get('sync_now', True))

        if not server_url:
            return JsonResponse({"status": "error", "message": "server_url is required"}, status=400)

        server = UserMCPServer.objects.create(
            user=request.client_user,
            name=name,
            server_url=server_url,
            auth_token=auth_token,
            is_active=is_active
        )

        tools_count = 0
        sync_error = None
        if sync_now and is_active:
            try:
                tools = fetch_mcp_tools_sync(server.server_url, server.auth_token, timeout=5.0)
                from django.utils import timezone
                server.cached_tools = tools
                server.last_synced_at = timezone.now()
                server.save(update_fields=['cached_tools', 'last_synced_at'])
                tools_count = len(tools)
            except Exception as e:
                sync_error = str(e)
                logger.warning(f"Initial sync failed for client {client_id} MCP {server.id}: {e}")

        s_dict = server.to_dict()
        s_dict['initial_sync_error'] = sync_error

        return JsonResponse({
            "status": "success",
            "message": f"Client FastMCP server created successfully. Synced {tools_count} live tools.",
            "client_id": client_id,
            "server": s_dict
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_mcp_detail(request, client_id, mcp_id):
    """
    GET, PATCH, DELETE /api/partner/v1/clients/<int:client_id>/mcp/<int:mcp_id>/
    Retrieve, update, or remove a client's FastMCP server.
    """
    server = UserMCPServer.objects.filter(user=request.client_user, id=mcp_id).first()
    if not server:
        return JsonResponse({"status": "error", "message": "Client FastMCP server not found"}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            "status": "success",
            "client_id": client_id,
            "server": server.to_dict()
        })

    if request.method in ('PATCH', 'PUT'):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        if 'name' in data:
            server.name = data['name'].strip() or server.name
        if 'server_url' in data:
            server.server_url = data['server_url'].strip() or server.server_url
        if 'auth_token' in data:
            server.auth_token = data['auth_token'].strip()
        if 'is_active' in data:
            server.is_active = bool(data['is_active'])

        server.save()
        return JsonResponse({
            "status": "success",
            "message": "Client FastMCP server updated successfully",
            "client_id": client_id,
            "server": server.to_dict()
        })

    if request.method == 'DELETE':
        srv_name = server.name
        server.delete()
        return JsonResponse({
            "status": "success",
            "message": f"Client FastMCP server '{srv_name}' deleted successfully",
            "client_id": client_id
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@partner_client_access_required
def api_partner_client_mcp_sync(request, client_id, mcp_id):
    """
    POST /api/partner/v1/clients/<int:client_id>/mcp/<int:mcp_id>/sync/
    Perform real-time SSE discovery handshake to fetch latest tool signatures for this client.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    server = UserMCPServer.objects.filter(user=request.client_user, id=mcp_id).first()
    if not server:
        return JsonResponse({"status": "error", "message": "Client FastMCP server not found"}, status=404)

    try:
        from django.utils import timezone
        tools = fetch_mcp_tools_sync(server.server_url, server.auth_token, timeout=8.0)
        server.cached_tools = tools
        server.last_synced_at = timezone.now()
        server.save(update_fields=['cached_tools', 'last_synced_at'])

        return JsonResponse({
            "status": "success",
            "message": f"Successfully synchronized {len(tools)} tools from FastMCP server via SSE.",
            "client_id": client_id,
            "mcp_id": server.id,
            "server_name": server.name,
            "tools_count": len(tools),
            "tools": tools,
            "synced_at": server.last_synced_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        logger.exception(f"Client MCP sync error for server {mcp_id}: {e}")
        return JsonResponse({
            "status": "error",
            "message": f"Failed to connect to FastMCP server: {str(e)}",
            "client_id": client_id,
            "mcp_id": server.id
        }, status=502)


# =========================================================================
# Partner API Documentation Portal View
# =========================================================================

def api_partner_docs(request):
    """
    GET /api/partner/v1/docs/
    Official Interactive Scalar API Reference for Partners & SaaS Integrations (Burgundy & Off-White Theme).
    Supports bilingual Arabic & English switching (?lang=ar | ?lang=en).
    """
    partner = None
    if request.user.is_authenticated:
        partner = PartnerProfile.objects.filter(user=request.user, status='approved').first()

    lang = request.GET.get('lang', 'ar').lower().strip()
    if lang not in ('ar', 'en'):
        lang = 'ar'

    return render(request, 'partners/scalar_docs.html', {
        'partner': partner,
        'partner_api_key': partner.api_key if partner else '',
        'base_url': request.build_absolute_uri('/')[:-1],
        'current_lang': lang,
        'is_ar': (lang == 'ar'),
    })


class PartnerSpectacularSchemaView(SpectacularAPIView):
    """
    OpenAPI 3.1 Schema generator powered by drf-spectacular for Partner SaaS API.
    Provides isolated schema for /api/partner/v1/ endpoints and feeds Partner Scalar Docs directly.
    """
    custom_settings = {
        'TITLE': 'بوابة وحلول الشركاء - Partner SaaS API (v1)',
        'DESCRIPTION': 'توثيق واجهات برمجة التطبيقات لمنظومة الشركاء وإدارة العملاء المستقلين (Multi-Tenant SaaS) والربط مع السنترالات.',
        'VERSION': '1.0.0',
        'PREPROCESSING_HOOKS': ['partners.openapi_hooks.filter_partner_endpoints'],
    }

    def get(self, request, *args, **kwargs):
        lang = request.GET.get('lang', 'ar').lower().strip()
        if lang not in ('ar', 'en'):
            lang = 'ar'

        resp = super().get(request, *args, **kwargs)
        spec = resp.data if hasattr(resp, 'data') else {}

        # 1. Normalize paths: Django's root URLconf has '/api/partner/v1/', but the OpenAPI server base URL
        # is already '/api/partner/v1'. Stripping '/api/partner/v1' prevents duplicate '/api/partner/v1/api/partner/v1/...' in Scalar.
        cleaned_paths = {}
        for path_key, path_data in spec.get('paths', {}).items():
            clean_path = path_key
            if clean_path.startswith('/api/partner/v1/'):
                clean_path = clean_path[15:]  # strips '/api/partner/v1' while keeping leading '/'
            elif clean_path == '/api/partner/v1':
                clean_path = '/'
            cleaned_paths[clean_path] = path_data
        spec['paths'] = cleaned_paths

        legacy_spec = get_partner_openapi_spec(server_url='/api/partner/v1', lang=lang)
        if not spec.get('paths'):
            spec['paths'] = legacy_spec.get('paths', {})
        else:
            for path_key, path_data in legacy_spec.get('paths', {}).items():
                if path_key not in spec['paths']:
                    spec['paths'][path_key] = path_data

        for k in ('info', 'servers', 'components'):
            if k not in spec or not spec[k]:
                spec[k] = legacy_spec.get(k, {})

        # Use curated ordered tags from partner openapi_spec
        spec['tags'] = legacy_spec.get('tags', [])

        if lang == 'en':
            if 'info' in spec:
                spec['info']['title'] = 'Partner SaaS Multi-Tenant REST API (v1)'
                spec['info']['description'] = 'B2B Partner API for multi-tenant customer management, voice AI personas, and WebRTC telephony.'
            # Translate campaign tag on paths if English
            for p_key, p_methods in spec.get('paths', {}).items():
                for m_verb, m_data in p_methods.items():
                    if isinstance(m_data, dict) and 'tags' in m_data:
                        m_data['tags'] = [
                            "13. Client Outbound Campaigns" if t == "13. حملات اتصال العملاء (Client Campaigns)" else t
                            for t in m_data['tags']
                        ]

        return JsonResponse(spec, json_dumps_params={'ensure_ascii': False, 'indent': 2})


api_partner_openapi_spec = PartnerSpectacularSchemaView.as_view()


def api_partner_docs_scalar(request):
    """
    GET /api/partner/v1/docs/scalar/
    Alias redirecting or rendering the primary documentation.
    """
    return api_partner_docs(request)


# =========================================================================
# Partner SaaS Client Campaigns API (Inngest Powered)
# =========================================================================

@extend_schema(
    methods=['GET'],
    operation_id="list_partner_client_campaigns",
    summary="استعراض حملات الاتصال الآلي للعميل التابع (Client Campaigns)",
    description="استعراض قائمة حملات الاتصال الصادرة الخاصة بعميل الشريك وإحصائياتها.",
    responses={200: PartnerClientCampaignsListResponseSerializer},
    tags=["13. حملات اتصال العملاء (Client Campaigns)"]
)
@extend_schema(
    methods=['POST'],
    operation_id="create_partner_client_campaign",
    summary="إنشاء حملة اتصال آلي جديدة للعميل التابع",
    description="إطلاق حملة اتصال جديدة وتزويدها بجهات الاتصال والسيناريو المخصص.",
    request=PartnerClientCampaignCreateRequestSerializer,
    responses={201: BaseSuccessResponseSerializer},
    tags=["13. حملات اتصال العملاء (Client Campaigns)"]
)
@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
@partner_client_access_required
def api_partner_client_campaigns(request, client_id):
    """
    GET & POST /api/partner/v1/clients/<client_id>/campaigns/
    List all outbound campaigns or create a new campaign with target contacts (via file upload or JSON array).
    """
    client_user = request.client_user
    if request.method == 'GET':
        qs = OutboundCampaign.objects.filter(user=client_user).order_by('-created_at')
        return JsonResponse({
            "status": "success",
            "total": qs.count(),
            "campaigns": [c.to_dict() for c in qs]
        })

    elif request.method == 'POST':
        data = request.data if hasattr(request, 'data') and request.data else {}
        if not data and request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except Exception:
                pass

        file_obj = request.FILES.get('file')
        contacts_to_create = []

        if file_obj:
            file_bytes = file_obj.read()
            parse_res = parse_leads_file(file_bytes, file_obj.name)
            if parse_res.get("status") != "success":
                return JsonResponse({"status": "error", "message": parse_res.get("message", "فشل تحليل الملف")}, status=400)
            valid_contacts = parse_res.get("valid_contacts", [])
            if not valid_contacts:
                return JsonResponse({
                    "status": "error",
                    "message": "لم يتم العثور على أي أرقام هواتف صالحة داخل الملف المرفوع. يرجى التأكد من محتوى الملف."
                }, status=400)
            contacts_to_create = valid_contacts
        else:
            raw_contacts = data.get('contacts')
            if isinstance(raw_contacts, str):
                try:
                    raw_contacts = json.loads(raw_contacts)
                except Exception:
                    raw_contacts = []
            if isinstance(raw_contacts, list) and raw_contacts:
                for item in raw_contacts:
                    if not isinstance(item, dict):
                        continue
                    phone = normalize_phone(item.get('phone_number') or item.get('phone') or '')
                    if not is_valid_phone(phone):
                        phone = str(item.get('phone_number') or item.get('phone') or '').strip()
                    if not phone:
                        continue
                    name_val = str(item.get('name') or item.get('customer_name') or '').strip()
                    contacts_to_create.append({
                        "customer_name": name_val or f"عميل ({phone})",
                        "phone_number": phone,
                        "attributes": item.get('attributes') or {}
                    })

        if not contacts_to_create:
            return JsonResponse({
                "status": "error",
                "message": "يجب تزويد ملف جهات الاتصال (file) أو مصفوفة جهات الاتصال (contacts) تحتوي على أرقام هواتف صالحة."
            }, status=400)

        name = str(data.get('name') or '').strip()
        if not name:
            if file_obj:
                name = f"حملة {file_obj.name} - {timezone.now().strftime('%Y/%m/%d %H:%M')}"
            else:
                name = f"حملة جهات اتصال - {timezone.now().strftime('%Y/%m/%d %H:%M')}"

        call_prompt = str(data.get('call_prompt') or '').strip()
        profile_id = data.get('agent_profile_id')
        agent_profile = AgentProfile.objects.filter(id=profile_id, user=client_user).first() if profile_id else None

        gateway_type = str(data.get('gateway_type') or 'auto').strip()
        gateway_id = data.get('gateway_id')
        gateway_id_int = int(gateway_id) if gateway_id and str(gateway_id).isdigit() else None

        try:
            max_retries = max(0, min(5, int(data.get('max_retries', 1))))
        except (ValueError, TypeError):
            max_retries = 1

        try:
            retry_delay_minutes = max(1, min(1440, int(data.get('retry_delay_minutes', 15))))
        except (ValueError, TypeError):
            retry_delay_minutes = 15

        campaign = OutboundCampaign.objects.create(
            user=client_user,
            name=name,
            agent_profile=agent_profile,
            call_prompt=call_prompt,
            max_retries=max_retries,
            retry_delay_minutes=retry_delay_minutes,
            gateway_type=gateway_type,
            gateway_id=gateway_id_int,
            status='draft'
        )

        contact_objs = [
            CampaignContact(
                campaign=campaign,
                customer_name=c.get("customer_name") or f"عميل ({c.get('phone_number')})",
                phone_number=c.get("phone_number"),
                attributes=c.get("attributes", {}),
                call_status='pending',
                interest_level='uncontacted'
            )
            for c in contacts_to_create
        ]
        CampaignContact.objects.bulk_create(contact_objs)
        campaign.update_metrics()

        return JsonResponse({
            "status": "success",
            "message": "تم إنشاء حملة الاتصال للعميل بنجاح",
            "campaign": campaign.to_dict()
        }, status=201)


@extend_schema(
    methods=['GET'],
    operation_id="get_partner_client_campaign_detail",
    summary="تفاصيل حملة اتصال للعميل التابع",
    description="استرجاع بيانات الحملة التفصيلية وقائمة العملاء المستهدفين وتصنيفات AI.",
    responses={200: PartnerClientCampaignDetailResponseSerializer},
    tags=["13. حملات اتصال العملاء (Client Campaigns)"]
)
@extend_schema(
    methods=['DELETE'],
    operation_id="delete_partner_client_campaign",
    summary="حذف حملة اتصال للعميل التابع",
    description="حذف الحملة وكافة جهات الاتصال التابعة لها.",
    responses={200: BaseSuccessResponseSerializer},
    tags=["13. حملات اتصال العملاء (Client Campaigns)"]
)
@api_view(['GET', 'DELETE'])
@partner_client_access_required
def api_partner_client_campaign_detail(request, client_id, campaign_id):
    """
    GET & DELETE /api/partner/v1/clients/<client_id>/campaigns/<campaign_id>/
    """
    client_user = request.client_user
    campaign = get_object_or_404(OutboundCampaign, id=campaign_id, user=client_user)

    if request.method == 'GET':
        contacts = campaign.contacts.all().order_by('id')
        return JsonResponse({
            "status": "success",
            "campaign": campaign.to_dict(),
            "contacts": [c.to_dict() for c in contacts],
            "total_contacts_count": contacts.count()
        })

    elif request.method == 'DELETE':
        campaign.delete()
        return JsonResponse({
            "status": "success",
            "message": "تم حذف الحملة بنجاح"
        })


@extend_schema(
    operation_id="start_partner_client_campaign",
    summary="بدء إطلاق الاتصال الآلي لحملة العميل عبر Inngest",
    description="تفعيل الحملة وبدء محرك الاتصال الآلي المتوازي للعميل بحسب حد المكالمات المتزامنة المخصص له.",
    request=None,
    responses={200: BaseSuccessResponseSerializer},
    tags=["13. حملات اتصال العملاء (Client Campaigns)"]
)
@api_view(['POST'])
@partner_client_access_required
def api_partner_client_campaign_start(request, client_id, campaign_id):
    """
    POST /api/partner/v1/clients/<client_id>/campaigns/<campaign_id>/start/
    """
    client_user = request.client_user
    campaign = get_object_or_404(OutboundCampaign, id=campaign_id, user=client_user)

    has_gw = OutboundSIPTrunk.objects.filter(user=campaign.user, is_active=True).exists()
    if not has_gw and not getattr(settings, 'DEBUG', False):
        return JsonResponse({
            "status": "error",
            "code": "no_outbound_gateway",
            "message": "لا يمكن بدء الحملة: لا يوجد خط اتصال صادر (SIP Trunk) مفعل لحساب العميل."
        }, status=422)

    limit = getattr(request.client_rel, 'concurrent_call_limit', 1) or 1
    campaign.status = 'running'
    campaign.save(update_fields=['status', 'updated_at'])

    pending_contacts = list(campaign.contacts.filter(call_status='pending').values_list('id', flat=True))
    if pending_contacts:
        try:
            events = [
                inngest.Event(
                    name="campaign/contact.dial",
                    data={
                        "campaign_id": campaign.id,
                        "contact_id": cid,
                        "user_id": campaign.user_id,
                        "concurrency_limit": limit
                    }
                )
                for cid in pending_contacts
            ]
            async_to_sync(inngest_client.send)(events)
        except Exception as e:
            logger.warning(f"Inngest dispatch notice for partner campaign {campaign.id}: {e}")

        broadcast_campaign_update(campaign.id, "campaign_started", {
            "queued": len(pending_contacts),
            "concurrency_limit": limit
        })

    return JsonResponse({
        "status": "success",
        "message": "تم بدء تشغيل الحملة والاتصال الآلي بنجاح",
        "campaign": campaign.to_dict()
    })


@extend_schema(
    operation_id="pause_partner_client_campaign",
    summary="إيقاف حملة العميل مؤقتاً",
    description="إيقاف الاتصال الآلي لحملة العميل مؤقتاً مع الحفاظ على تقدم المكالمات السابقة.",
    request=None,
    responses={200: BaseSuccessResponseSerializer},
    tags=["13. حملات اتصال العملاء (Client Campaigns)"]
)
@api_view(['POST'])
@partner_client_access_required
def api_partner_client_campaign_pause(request, client_id, campaign_id):
    """
    POST /api/partner/v1/clients/<client_id>/campaigns/<campaign_id>/pause/
    """
    client_user = request.client_user
    campaign = get_object_or_404(OutboundCampaign, id=campaign_id, user=client_user)
    campaign.status = 'paused'
    campaign.save(update_fields=['status', 'updated_at'])
    broadcast_campaign_update(campaign.id, "campaign_paused", {})

    return JsonResponse({
        "status": "success",
        "message": "تم إيقاف الحملة مؤقتاً بنجاح",
        "campaign": campaign.to_dict()
    })

