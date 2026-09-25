import json
import logging
import secrets
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from livekit import api
from google import genai
from google.genai import types
from pgvector.django import CosineDistance

from .models import UserApiKey
from .decorators import user_api_key_required
from .user_openapi_spec import get_user_openapi_spec

from agents.models import AgentProfile, UserMCPServer, SystemSetting
from agents.views import fetch_mcp_tools_sync
from billing.models import UserWallet
from call_center.models import EmployeeProfile, CallQueue, QueueMembership
from crm.models import CustomerMemory, CallSession
from knowledge.models import Document, DocumentChunk
from telephony.models import OutboundSIPTrunk, InboundPBXTrunk
from telephony.services import initiate_outbound_call

logger = logging.getLogger(__name__)


# =========================================================================
# Web UI Dashboard Endpoints for Managing User API Keys
# =========================================================================

@login_required(login_url='/login/')
def get_developer_keys(request):
    """
    GET /api/v1/developer/keys/
    Returns active API keys for the logged-in user, generating a default one if none exists.
    """
    keys = UserApiKey.objects.filter(user=request.user, is_active=True).order_by('-created_at')
    if not keys.exists():
        default_key = UserApiKey.generate_for_user(user=request.user, name="مفتاح التطبيق الرئيسي")
        keys = [default_key]

    return JsonResponse({
        "status": "success",
        "keys": [k.to_dict() for k in keys]
    })


@login_required(login_url='/login/')
@csrf_exempt
def rotate_developer_key(request):
    """
    POST /api/v1/developer/keys/rotate/
    Deactivates existing keys and generates a fresh API key for the user.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    name = "مفتاح التطبيق (مُحدّث)"
    if request.body:
        try:
            data = json.loads(request.body.decode('utf-8'))
            name = data.get('name', name).strip() or name
        except Exception:
            pass

    # Deactivate older keys
    UserApiKey.objects.filter(user=request.user, is_active=True).update(is_active=False)

    # Generate brand new key
    new_key = UserApiKey.generate_for_user(user=request.user, name=name)

    return JsonResponse({
        "status": "success",
        "message": "تم توليد مفتاح API جديد بنجاح وإلغاء تفعيل المفاتيح السابقة.",
        "key": new_key.to_dict()
    })


# =========================================================================
# Documentation Portal Views (Scalar)
# =========================================================================

def api_user_docs(request):
    """
    GET /api/v1/docs/
    Interactive Scalar Reference for User Developer API (Burgundy & Warm Off-White Theme).
    Supports bilingual Arabic & English switching (?lang=ar | ?lang=en).
    """
    lang = request.GET.get('lang', 'ar').lower().strip()
    if lang not in ('ar', 'en'):
        lang = 'ar'

    user_api_key = ''
    if request.user.is_authenticated:
        key_obj = UserApiKey.objects.filter(user=request.user, is_active=True).first()
        if not key_obj:
            key_obj = UserApiKey.generate_for_user(user=request.user, name="مفتاح التطبيق الرئيسي")
        user_api_key = key_obj.key

    return render(request, 'developer/scalar_docs.html', {
        'user_api_key': user_api_key,
        'base_url': request.build_absolute_uri('/')[:-1],
        'current_lang': lang,
        'is_ar': (lang == 'ar'),
    })


def api_user_openapi_spec(request):
    """
    GET /api/v1/docs/openapi.json
    Dynamically serves OpenAPI 3.1 specification for User Developer API.
    Supports bilingual content (?lang=ar | ?lang=en).
    """
    lang = request.GET.get('lang', 'ar').lower().strip()
    if lang not in ('ar', 'en'):
        lang = 'ar'

    server_url = "/api/v1"
    spec = get_user_openapi_spec(server_url=server_url, lang=lang)
    return JsonResponse(spec, json_dumps_params={'ensure_ascii': False, 'indent': 2})


# =========================================================================
# User RESTful Developer API Endpoints (Authenticated via X-API-Key)
# =========================================================================

@csrf_exempt
@user_api_key_required
def api_user_account(request):
    """
    GET /api/v1/account/
    Returns current user profile, wallet balance, active voice persona, and account stats.
    """
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    wallet, _ = UserWallet.objects.get_or_create(user=request.user)
    active_profile = AgentProfile.objects.filter(user=request.user, is_active=True).first()

    return JsonResponse({
        "status": "success",
        "user_id": request.user.id,
        "username": request.user.username,
        "email": request.user.email,
        "wallet_balance": float(wallet.balance),
        "active_profile": active_profile.to_dict() if active_profile else None,
        "total_calls": CallSession.objects.filter(user=request.user).count(),
        "total_documents": Document.objects.filter(user=request.user).count(),
        "total_employees": EmployeeProfile.objects.filter(user=request.user).count(),
        "total_mcp_servers": UserMCPServer.objects.filter(user=request.user, is_active=True).count(),
    })


@csrf_exempt
@user_api_key_required
def api_user_profiles_studio(request):
    """
    GET /api/v1/profiles/studio/
    Returns full studio customization metadata:
    - 30 Google HD studio voices with styles and gender classifications
    - 11 Supported languages
    - 29 Regional dialects grouped hierarchically
    - Sample roles and styles for inspiration
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
@user_api_key_required
def api_user_profiles(request):
    """
    GET & POST /api/v1/profiles/
    List all voice agent profiles or create a new persona.
    """
    if request.method == 'GET':
        qs = AgentProfile.objects.filter(user=request.user).order_by('-updated_at')
        is_active_filter = request.GET.get('is_active')
        if is_active_filter is not None:
            qs = qs.filter(is_active=(is_active_filter.lower() in ('true', '1')))

        active_prof = AgentProfile.objects.filter(user=request.user, is_active=True).first()
        return JsonResponse({
            "status": "success",
            "total": qs.count(),
            "count": qs.count(),
            "active_profile": active_prof.to_dict() if active_prof else None,
            "profiles": [p.to_dict() for p in qs]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({"status": "error", "message": "name is required"}, status=400)

        profile = AgentProfile.objects.create(
            user=request.user,
            name=name,
            voice_name=data.get('voice_name', 'Aoede').strip(),
            gender=data.get('gender', 'female'),
            language=data.get('language', 'arabic').strip(),
            dialect=data.get('dialect', 'egyptian').strip(),
            persona_role=data.get('persona_role', 'خدمة عملاء ومبيعات المتجر').strip(),
            speaking_style=data.get('speaking_style', 'ودود ولطيف ومرح').strip(),
            custom_instructions=data.get('custom_instructions', '').strip(),
            is_active=bool(data.get('is_active', True))
        )
        return JsonResponse({
            "status": "success",
            "message": "Voice profile created successfully",
            "profile": profile.to_dict()
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_profile_detail(request, profile_id):
    """
    GET, PUT, PATCH, DELETE /api/v1/profiles/<int:profile_id>/
    Manage single voice persona.
    """
    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)

    if request.method == 'GET':
        return JsonResponse({"status": "success", "profile": profile.to_dict()})

    elif request.method in ('PUT', 'PATCH'):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        for field in ['name', 'voice_name', 'gender', 'language', 'dialect', 'persona_role', 'speaking_style', 'custom_instructions']:
            if field in data:
                setattr(profile, field, str(data[field]).strip())
        if 'is_active' in data:
            profile.is_active = bool(data['is_active'])

        profile.save()
        return JsonResponse({"status": "success", "message": "Profile updated successfully", "profile": profile.to_dict()})

    elif request.method == 'DELETE':
        profile.delete()
        return JsonResponse({"status": "success", "message": "Profile deleted successfully"})

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_profile_activate(request, profile_id):
    """
    POST /api/v1/profiles/<int:profile_id>/activate/
    Activates the target persona and deactivates all other profiles for this user.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)
    AgentProfile.objects.filter(user=request.user, is_active=True).exclude(pk=profile.pk).update(is_active=False)
    profile.is_active = True
    profile.save(update_fields=['is_active'])

    return JsonResponse({
        "status": "success",
        "message": f"Profile '{profile.name}' is now the active agent persona.",
        "active_profile": profile.to_dict(),
        "profile": profile.to_dict()
    })


@csrf_exempt
@user_api_key_required
def api_user_memory(request):
    """
    GET & POST /api/v1/memory/
    List, search, and paginate customer context memories or upsert by phone.
    """
    if request.method == 'GET':
        raw_phone = request.GET.get('phone') or request.GET.get('phone_number')
        if raw_phone:
            phone = str(raw_phone).strip()
            if not phone.startswith('+') and phone.isdigit() and len(phone) >= 9:
                phone = '+' + phone

            mem = CustomerMemory.objects.filter(user=request.user, phone_number=phone).first()
            if not mem:
                alt_phone = phone[1:] if phone.startswith('+') else ('+' + phone)
                mem = CustomerMemory.objects.filter(user=request.user, phone_number=alt_phone).first()

            if not mem:
                return JsonResponse({"status": "error", "message": "Customer memory not found for this phone"}, status=404)
            return JsonResponse({
                "status": "success",
                "memory": mem.to_dict(),
                "customer": mem.to_dict()
            })

        qs = CustomerMemory.objects.filter(user=request.user).order_by('-updated_at')
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(customer_name__icontains=q) | Q(phone_number__icontains=q))

        try:
            page_num = max(1, int(request.GET.get('page', 1)))
            limit = min(100, max(1, int(request.GET.get('limit', 20))))
        except Exception:
            page_num, limit = 1, 20

        paginator = Paginator(qs, limit)
        page_obj = paginator.get_page(page_num)

        return JsonResponse({
            "status": "success",
            "total": paginator.count,
            "page": page_num,
            "limit": limit,
            "total_pages": paginator.num_pages,
            "memories": [m.to_dict() for m in page_obj.object_list]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        phone = data.get('phone_number', '').strip()
        if not phone:
            return JsonResponse({"status": "error", "message": "phone_number is required"}, status=400)

        mem, created = CustomerMemory.objects.get_or_create(user=request.user, phone_number=phone)
        if 'customer_name' in data:
            mem.customer_name = data['customer_name']
        if 'permanent_profile' in data:
            mem.permanent_profile = data['permanent_profile']
        if 'immediate_notes' in data:
            mem.immediate_notes = data['immediate_notes']
        if 'total_calls_count' in data:
            mem.total_calls_count = int(data['total_calls_count'])

        mem.save()
        return JsonResponse({
            "status": "success",
            "message": "Memory created successfully" if created else "Memory updated successfully",
            "memory": mem.to_dict()
        }, status=201 if created else 200)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_memory_detail(request, memory_id):
    """
    GET, PUT, DELETE /api/v1/memory/<int:memory_id>/
    Manage single customer context memory record.
    """
    mem = get_object_or_404(CustomerMemory, id=memory_id, user=request.user)

    if request.method == 'GET':
        return JsonResponse({"status": "success", "memory": mem.to_dict()})

    elif request.method in ('PUT', 'PATCH'):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        for field in ['customer_name', 'permanent_profile', 'immediate_notes']:
            if field in data:
                setattr(mem, field, data[field])
        if 'total_calls_count' in data:
            mem.total_calls_count = int(data['total_calls_count'])

        mem.save()
        return JsonResponse({"status": "success", "message": "Memory updated successfully", "memory": mem.to_dict()})

    elif request.method == 'DELETE':
        mem.delete()
        return JsonResponse({"status": "success", "message": "Memory deleted successfully"})

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_documents(request):
    """
    GET & POST /api/v1/documents/
    List indexed documents or upload new knowledge content.
    """
    if request.method == 'GET':
        docs = Document.objects.filter(user=request.user).order_by('-created_at')
        return JsonResponse({
            "status": "success",
            "count": docs.count(),
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "file_type": d.file_type or "text",
                    "file_size": d.file_size,
                    "created_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else None,
                    "chunks_count": d.chunks.count()
                }
                for d in docs
            ]
        })

    elif request.method == 'POST':
        try:
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()
            if not content and request.body:
                body_data = json.loads(request.body.decode('utf-8'))
                title = body_data.get('title', '').strip()
                content = body_data.get('content', '').strip()

            if not content:
                return JsonResponse({"status": "error", "message": "content is required"}, status=400)

            title = title or "مستند معرفي جديد"
            doc = Document.objects.create(
                user=request.user,
                title=title,
                file_type="text/plain",
                file_size=len(content.encode('utf-8'))
            )

            # Generate Gemini embedding & store chunk
            chunks_created = 0
            try:
                client = genai.Client(api_key=SystemSetting.get_gemini_api_key())
                embed_res = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=content,
                    config=types.EmbedContentConfig(output_dimensionality=768)
                )
                if embed_res and embed_res.embeddings:
                    emb = embed_res.embeddings[0].values
                    DocumentChunk.objects.create(
                        document=doc,
                        user=request.user,
                        content=content,
                        chunk_index=0,
                        embedding=emb
                    )
                    chunks_created = 1
            except Exception as emb_err:
                logger.warning(f"Failed to generate embedding for document {doc.id}: {emb_err}")

            return JsonResponse({
                "status": "success",
                "message": "Document indexed successfully",
                "document": {
                    "id": doc.id,
                    "title": doc.title,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "chunks_count": chunks_created,
                    "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M") if doc.created_at else None
                }
            }, status=201)
        except Exception as e:
            logger.error(f"Error creating user document: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_rag_query(request):
    """
    POST /api/v1/rag/query/
    Semantic vector search against indexed documents using pgvector and Gemini.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        query = str(data.get('query', '')).strip()
        top_k = int(data.get('top_k', 3))

        if not query:
            return JsonResponse({"status": "error", "message": "query is required"}, status=400)

        client = genai.Client(api_key=SystemSetting.get_gemini_api_key())
        embed_res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        if not embed_res or not embed_res.embeddings:
            return JsonResponse({"status": "error", "message": "Failed to generate query embedding"}, status=500)

        query_vec = embed_res.embeddings[0].values
        chunks = DocumentChunk.objects.filter(user=request.user) \
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
            "query": query,
            "total_matches": len(results),
            "results": results
        })
    except Exception as e:
        logger.error(f"Error in user RAG query: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@user_api_key_required
def api_user_mcp(request):
    """
    GET & POST /api/v1/mcp/
    List or register FastMCP servers for the user.
    """
    if request.method == 'GET':
        servers = UserMCPServer.objects.filter(user=request.user).order_by('-updated_at')
        return JsonResponse({
            "status": "success",
            "count": servers.count(),
            "servers": [s.to_dict() for s in servers]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        name = data.get('name', 'خادم FastMCP الرئيسي').strip()
        server_url = data.get('server_url', '').strip()
        auth_token = data.get('auth_token', '').strip()

        if not server_url:
            return JsonResponse({"status": "error", "message": "server_url is required"}, status=400)

        server = UserMCPServer.objects.create(
            user=request.user,
            name=name,
            server_url=server_url,
            auth_token=auth_token,
            is_active=bool(data.get('is_active', True))
        )

        # Trigger initial handshake
        try:
            tools = fetch_mcp_tools_sync(server_url, auth_token, timeout=5.0)
            if tools:
                server.cached_tools = tools
                server.save(update_fields=['cached_tools'])
        except Exception as e:
            logger.warning(f"Initial tool sync failed for MCP {server.id}: {e}")

        return JsonResponse({
            "status": "success",
            "message": "MCP server registered successfully",
            "server": server.to_dict()
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_mcp_sync(request, mcp_id):
    """
    POST /api/v1/mcp/<int:mcp_id>/sync/
    Triggers on-demand tool synchronization for the designated MCP server.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    server = get_object_or_404(UserMCPServer, id=mcp_id, user=request.user)
    try:
        tools = fetch_mcp_tools_sync(server.server_url, server.auth_token, timeout=8.0)
        server.cached_tools = tools
        server.save(update_fields=['cached_tools'])
        return JsonResponse({
            "status": "success",
            "message": f"Successfully synchronized {len(tools)} tools from MCP server.",
            "server": server.to_dict(),
            "tools_count": len(tools),
            "tools": tools
        })
    except Exception as e:
        logger.error(f"Failed to sync user MCP server {server.id}: {e}")
        return JsonResponse({"status": "error", "message": f"MCP sync failed: {str(e)}"}, status=502)


@csrf_exempt
@user_api_key_required
def api_user_mcp_detail(request, mcp_id):
    """
    GET, PATCH, DELETE /api/v1/mcp/<int:mcp_id>/
    Inspect, update, or remove an MCP server.
    """
    server = get_object_or_404(UserMCPServer, id=mcp_id, user=request.user)

    if request.method == 'GET':
        return JsonResponse({"status": "success", "server": server.to_dict()})

    elif request.method in ('PUT', 'PATCH'):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        for field in ['name', 'server_url', 'auth_token']:
            if field in data:
                setattr(server, field, str(data[field]).strip())
        if 'is_active' in data:
            server.is_active = bool(data['is_active'])

        server.save()
        return JsonResponse({"status": "success", "message": "MCP server updated successfully", "server": server.to_dict()})

    elif request.method == 'DELETE':
        server.delete()
        return JsonResponse({"status": "success", "message": "MCP server deleted successfully"})

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_telephony(request):
    """
    GET & POST /api/v1/telephony/
    List or register PBX and SIP trunks for the user.
    """
    if request.method == 'GET':
        pbx = InboundPBXTrunk.objects.filter(user=request.user)
        sip = OutboundSIPTrunk.objects.filter(user=request.user)
        return JsonResponse({
            "status": "success",
            "pbx_trunks": [t.to_dict() for t in pbx],
            "sip_trunks": [t.to_dict() for t in sip]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        trunk_type = data.get('trunk_type', 'pbx').lower()
        name = data.get('name', '').strip()
        host = data.get('host', '').strip()

        if not name or not host:
            return JsonResponse({"status": "error", "message": "name and host are required"}, status=400)

        if trunk_type == 'pbx':
            trunk = InboundPBXTrunk.objects.create(
                user=request.user,
                name=name,
                host=host,
                port=int(data.get('port', 5060)),
                username=data.get('username', '').strip(),
                secret=data.get('secret', '').strip(),
                is_active=bool(data.get('is_active', True))
            )
        else:
            trunk = OutboundSIPTrunk.objects.create(
                user=request.user,
                name=name,
                host=host,
                port=int(data.get('port', 5060)),
                username=data.get('username', '').strip(),
                password=data.get('secret', '').strip(),
                is_active=bool(data.get('is_active', True))
            )

        return JsonResponse({
            "status": "success",
            "message": f"{trunk_type.upper()} trunk registered successfully",
            "trunk": trunk.to_dict()
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_numbers(request):
    """
    GET & POST /api/v1/telephony/numbers/
    List or assign phone numbers / DIDs for the user's PBX.
    """
    from call_center.models import PhoneNumber
    if request.method == 'GET':
        nums = PhoneNumber.objects.filter(user=request.user)
        return JsonResponse({
            "status": "success",
            "count": nums.count(),
            "numbers": [n.to_dict() for n in nums]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        phone_num = data.get('phone_number', '').strip()
        pbx_id = data.get('pbx_trunk_id')

        if not phone_num:
            return JsonResponse({"status": "error", "message": "phone_number is required"}, status=400)

        pbx = get_object_or_404(InboundPBXTrunk, id=pbx_id, user=request.user) if pbx_id else None
        num, created = PhoneNumber.objects.get_or_create(
            phone_number=phone_num,
            defaults={
                'user': request.user,
                'inbound_trunk': pbx,
                'description': data.get('description', '')
            }
        )
        if not created:
            num.user = request.user
            if pbx:
                num.inbound_trunk = pbx
            num.save()

        return JsonResponse({
            "status": "success",
            "message": "Phone number assigned successfully",
            "number": num.to_dict()
        }, status=201 if created else 200)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_employees(request):
    """
    GET & POST /api/v1/employees/
    List staff extensions or create an employee profile.
    """
    if request.method == 'GET':
        employees = EmployeeProfile.objects.filter(Q(employer=request.user) | Q(user=request.user)).order_by('extension')
        return JsonResponse({
            "status": "success",
            "count": employees.count(),
            "employees": [e.to_dict() for e in employees]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        name = (data.get('display_name') or data.get('name') or '').strip()
        extension = data.get('extension', '').strip()

        if not name or not extension:
            return JsonResponse({"status": "error", "message": "name and extension are required"}, status=400)

        # If an employee with this extension already exists for this employer, update and return
        emp = EmployeeProfile.objects.filter(employer=request.user, extension=extension).first()
        if emp:
            emp.display_name = name
            if 'department' in data:
                emp.department = str(data['department']).strip()
            if 'status' in data:
                emp.status = str(data['status']).strip()
            emp.save()
            return JsonResponse({
                "status": "success",
                "message": "Employee updated successfully",
                "employee": emp.to_dict()
            }, status=200)

        emp_username = f"emp_{request.user.id}_{extension}_{secrets.token_hex(3)}"
        emp_user = User.objects.create_user(
            username=emp_username,
            password=secrets.token_urlsafe(16),
            first_name=name
        )

        emp = EmployeeProfile.objects.create(
            employer=request.user,
            user=emp_user,
            display_name=name,
            extension=extension,
            department=data.get('department', 'المبيعات').strip(),
            status=data.get('status', 'ready'),
            avatar_url=f"https://api.dicebear.com/7.x/bottts/png?seed={extension}"
        )
        return JsonResponse({
            "status": "success",
            "message": "Employee created successfully",
            "employee": emp.to_dict()
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_employee_detail(request, employee_id):
    """
    GET, PATCH, DELETE /api/v1/employees/<int:employee_id>/
    Manage single employee record.
    """
    emp = EmployeeProfile.objects.filter(Q(employer=request.user) | Q(user=request.user), id=employee_id).first()
    if not emp:
        return JsonResponse({"status": "error", "message": "Employee not found"}, status=404)

    if request.method == 'GET':
        return JsonResponse({"status": "success", "employee": emp.to_dict()})

    elif request.method in ('PUT', 'PATCH'):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        for field in ['display_name', 'extension', 'department', 'status']:
            if field in data:
                setattr(emp, field, str(data[field]).strip())
        if 'name' in data:
            emp.display_name = str(data['name']).strip()
        emp.save()
        return JsonResponse({"status": "success", "message": "Employee updated successfully", "employee": emp.to_dict()})

    elif request.method == 'DELETE':
        emp.delete()
        return JsonResponse({"status": "success", "message": "Employee deleted successfully"})

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_queues(request):
    """
    GET & POST /api/v1/queues/
    List or create call center queues with strategy, timeouts, and fallback action.
    """
    if request.method == 'GET':
        queues = CallQueue.objects.filter(user=request.user).order_by('code')
        return JsonResponse({
            "status": "success",
            "count": queues.count(),
            "queues": [q.to_dict() for q in queues]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        name = data.get('name', '').strip() or 'طابور خدمة العملاء'
        code = str(data.get('code', '')).strip()
        if not code:
            existing_codes = set(CallQueue.objects.filter(user=request.user).values_list('code', flat=True))
            cand = 200
            while str(cand) in existing_codes:
                cand += 10
            code = str(cand)
        elif not code.isdigit():
            return JsonResponse({"status": "error", "message": "Queue code must be numeric (e.g. 200, 300)"}, status=400)
        elif CallQueue.objects.filter(user=request.user, code=code).exists():
            return JsonResponse({"status": "error", "message": f"Queue code '{code}' already exists for this account"}, status=400)

        description = str(data.get('description', '')).strip()
        strategy = str(data.get('strategy', 'round_robin')).strip()
        if strategy not in ('round_robin', 'ring_all'):
            strategy = 'round_robin'
        ring_timeout = int(data.get('ring_timeout_seconds', 15))
        total_timeout = int(data.get('total_timeout_seconds', 60))
        fallback_action = str(data.get('fallback_action', 'ai_assistant')).strip()
        if fallback_action not in ('ai_assistant', 'hangup'):
            fallback_action = 'ai_assistant'

        queue = CallQueue.objects.create(
            user=request.user,
            name=name,
            code=code,
            description=description,
            strategy=strategy,
            ring_timeout_seconds=ring_timeout,
            total_timeout_seconds=total_timeout,
            fallback_action=fallback_action,
            is_active=bool(data.get('is_active', True))
        )

        members = data.get('members') or data.get('member_ids')
        if isinstance(members, list):
            for idx, emp_id in enumerate(members):
                emp = EmployeeProfile.objects.filter(Q(employer=request.user) | Q(user=request.user), id=emp_id).first()
                if emp:
                    QueueMembership.objects.create(queue=queue, employee=emp, order=idx)

        return JsonResponse({
            "status": "success",
            "message": "Queue created successfully",
            "queue": queue.to_dict()
        }, status=201)

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_queue_detail(request, queue_id):
    """
    GET, PUT/PATCH, & DELETE /api/v1/queues/<int:queue_id>/
    Manage single call center queue.
    """
    queue = get_object_or_404(CallQueue, id=queue_id, user=request.user)

    if request.method == 'GET':
        return JsonResponse({"status": "success", "queue": queue.to_dict()})

    elif request.method in ('PUT', 'PATCH'):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        if 'name' in data:
            queue.name = str(data['name']).strip() or queue.name
        if 'code' in data:
            new_code = str(data['code']).strip()
            if new_code != queue.code:
                if not new_code.isdigit():
                    return JsonResponse({"status": "error", "message": "Queue code must be numeric"}, status=400)
                if CallQueue.objects.filter(user=request.user, code=new_code).exclude(id=queue.id).exists():
                    return JsonResponse({"status": "error", "message": f"Queue code '{new_code}' already exists"}, status=400)
                queue.code = new_code
        if 'description' in data:
            queue.description = str(data['description']).strip()
        if 'strategy' in data:
            strat = str(data['strategy']).strip()
            if strat in ('round_robin', 'ring_all'):
                queue.strategy = strat
        if 'ring_timeout_seconds' in data:
            queue.ring_timeout_seconds = int(data['ring_timeout_seconds'])
        if 'total_timeout_seconds' in data:
            queue.total_timeout_seconds = int(data['total_timeout_seconds'])
        if 'fallback_action' in data:
            fb = str(data['fallback_action']).strip()
            if fb in ('ai_assistant', 'hangup'):
                queue.fallback_action = fb
        if 'is_active' in data:
            queue.is_active = bool(data['is_active'])

        queue.save()

        members = data.get('members') or data.get('member_ids')
        if isinstance(members, list):
            queue.memberships.all().delete()
            for idx, emp_id in enumerate(members):
                emp = EmployeeProfile.objects.filter(Q(employer=request.user) | Q(user=request.user), id=emp_id).first()
                if emp:
                    QueueMembership.objects.create(queue=queue, employee=emp, order=idx)

        return JsonResponse({
            "status": "success",
            "message": "Queue updated successfully",
            "queue": queue.to_dict()
        })

    elif request.method == 'DELETE':
        queue.delete()
        return JsonResponse({"status": "success", "message": "Queue deleted successfully"})

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_queue_members(request, queue_id):
    """
    GET, POST, DELETE /api/v1/queues/<int:queue_id>/members/
    Manage employee memberships in a specific call queue.
    """
    queue = get_object_or_404(CallQueue, id=queue_id, user=request.user)

    if request.method == 'GET':
        members = queue.memberships.select_related('employee').all()
        return JsonResponse({
            "status": "success",
            "queue_id": queue.id,
            "queue_name": queue.name,
            "total_members": members.count(),
            "members": [m.to_dict() for m in members]
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        emp_id = data.get('employee_id')
        if not emp_id:
            return JsonResponse({"status": "error", "message": "employee_id is required"}, status=400)

        emp = EmployeeProfile.objects.filter(Q(employer=request.user) | Q(user=request.user), id=emp_id).first()
        if not emp:
            return JsonResponse({"status": "error", "message": "Employee not found"}, status=404)
        order = int(data.get('order', queue.memberships.count()))

        membership, created = QueueMembership.objects.get_or_create(
            queue=queue,
            employee=emp,
            defaults={'order': order, 'is_active': True}
        )
        if not created:
            membership.is_active = True
            membership.order = order
            membership.save()

        return JsonResponse({
            "status": "success",
            "message": f"Employee '{emp.name}' added to queue '{queue.name}'",
            "member": membership.to_dict()
        }, status=201 if created else 200)

    elif request.method == 'DELETE':
        emp_id = request.GET.get('employee_id')
        if not emp_id and request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
                emp_id = data.get('employee_id')
            except Exception:
                pass

        if not emp_id:
            return JsonResponse({"status": "error", "message": "employee_id is required"}, status=400)

        membership = queue.memberships.filter(employee_id=emp_id).first()
        if not membership:
            return JsonResponse({"status": "error", "message": "Membership not found in this queue"}, status=404)

        membership.delete()
        return JsonResponse({
            "status": "success",
            "message": f"Employee removed from queue '{queue.name}'"
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_token(request):
    """
    POST /api/v1/token/
    Generates an ephemeral JWT token for connecting a client (browser or mobile)
    directly to a LiveKit voice session with this user's active AI agent.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    wallet, _ = UserWallet.objects.get_or_create(user=request.user)
    if wallet.balance < 0.05:
        return JsonResponse({
            "status": "error",
            "code": "INSUFFICIENT_BALANCE",
            "message": "Insufficient wallet balance to start a voice call. Please recharge your balance."
        }, status=402)

    participant_name = "مستخدم التطبيق"
    if request.body:
        try:
            data = json.loads(request.body.decode('utf-8'))
            participant_name = data.get('participant_name', participant_name).strip() or participant_name
        except Exception:
            pass

    room_name = f"user_{request.user.id}_{secrets.token_hex(4)}"
    identity = f"usr_{request.user.id}_{secrets.token_hex(2)}"

    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
        .with_identity(identity) \
        .with_name(participant_name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))

    jwt_token = token.to_jwt()

    return JsonResponse({
        "status": "success",
        "room_name": room_name,
        "token": jwt_token,
        "livekit_url": getattr(settings, 'LIVEKIT_WS_URL', 'wss://app.localhost:7881'),
        "user_id": request.user.id
    })


@csrf_exempt
@user_api_key_required
def api_user_calls(request):
    """
    GET /api/v1/calls/
    Returns call logs, duration, cost, recordings, and AI conversation summaries.
    """
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    calls = CallSession.objects.filter(user=request.user).order_by('-started_at')[:100]
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
            "recording_url": call.recording_url or "",
            "dialogue_turns": call.dialogue_turns,
        })

    return JsonResponse({
        "status": "success",
        "total_calls": len(calls_list),
        "calls": calls_list
    })


@csrf_exempt
@user_api_key_required
def api_user_call_hangup(request):
    """
    POST /api/v1/calls/hangup/
    Terminate an active call session immediately (hang up caller and AI/employee, clean up LiveKit room).
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
        return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

    room_name = str(data.get('call_id') or data.get('room_name') or '').strip()
    if not room_name:
        return JsonResponse({"status": "error", "message": "call_id or room_name is required"}, status=400)

    from call_center.views import api_hangup_call
    return api_hangup_call(request)


@csrf_exempt
@user_api_key_required
def api_user_webhooks(request):
    """
    GET & POST /api/v1/webhooks/
    Get or set user webhook configuration.
    """
    from .models import UserWebhookEndpoint
    endpoint, _ = UserWebhookEndpoint.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        return JsonResponse({
            "status": "success",
            "webhook_url": endpoint.url,
            "has_secret": bool(endpoint.secret),
            "is_active": endpoint.is_active
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
        except Exception:
            return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

        url = data.get('webhook_url', '').strip()
        endpoint.url = url
        if 'webhook_secret' in data:
            endpoint.secret = data['webhook_secret'].strip()
        if 'is_active' in data:
            endpoint.is_active = bool(data['is_active'])
        endpoint.save()

        return JsonResponse({
            "status": "success",
            "message": "Webhook configuration saved successfully",
            "webhook_url": endpoint.url,
            "has_secret": bool(endpoint.secret),
            "is_active": endpoint.is_active
        })

    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)


@csrf_exempt
@user_api_key_required
def api_user_call_dial(request):
    """
    POST /api/v1/calls/dial/
    Trigger an autonomous AI outbound phone call to an external customer or internal PBX extension.
    Accepts:
    {
        "phone_number": "+201012345678",  // or PBX extension "101"
        "call_goal": "تأكيد الطلب رقم 1005",
        "profile_id": 1,                   // optional agent profile ID
        "gateway_type": "auto",            // "auto" | "pbx" | "cloud"
        "gateway_id": 2                    // optional PBX trunk ID
    }
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
            user=request.user,
            phone_number=phone_number,
            call_goal=call_goal,
            profile_id=profile_id,
            gateway_type=gateway_type,
            gateway_id=gateway_id,
        )
        http_status = res.pop('http_status', 201)
        return JsonResponse(res, status=http_status)
    except Exception as e:
        logger.exception(f"Error in api_user_call_dial for user {request.user.id}: {e}")
        return JsonResponse({"status": "error", "message": f"Outbound call initiation failed: {str(e)}"}, status=500)

