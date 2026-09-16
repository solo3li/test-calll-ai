import re
import json
import uuid
import logging
import asyncio
import redis
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from livekit import api

from .models import OutboundSIPTrunk
from agents.models import AgentProfile
from crm.models import CallSession

logger = logging.getLogger(__name__)

def normalize_phone_number(raw_phone: str) -> str:
    """
    Normalize phone numbers into standard E.164 format.
    - Egyptian mobile (01xxxxxxxxx, 11 digits) -> +201xxxxxxxxx
    - Egyptian mobile with 20 prefix (201xxxxxxxxx) -> +201xxxxxxxxx
    - International with 00 prefix (00...) -> +...
    - International standard (+...) -> preserved
    - Clean digits starting with non-zero country code -> +...
    """
    cleaned = re.sub(r'[\s\-\(\)\.]', '', str(raw_phone or '').strip())
    if not cleaned:
        return ""
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    elif cleaned.startswith('01') and len(cleaned) == 11 and cleaned.isdigit():
        cleaned = '+20' + cleaned[1:]
    elif cleaned.startswith('201') and len(cleaned) == 12 and cleaned.isdigit():
        cleaned = '+' + cleaned
    elif not cleaned.startswith('+') and re.match(r'^[1-9]\d{6,14}$', cleaned):
        cleaned = '+' + cleaned
    return cleaned


async def _async_create_or_update_outbound_trunk(name, address, port, transport_str, auth_username, auth_password, caller_id, existing_trunk_id=None):
    lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        trans_map = {
            'UDP': api.SIPTransport.SIP_TRANSPORT_UDP,
            'TCP': api.SIPTransport.SIP_TRANSPORT_TCP,
            'TLS': api.SIPTransport.SIP_TRANSPORT_TLS,
        }
        trans_enum = trans_map.get(str(transport_str).upper(), api.SIPTransport.SIP_TRANSPORT_UDP)

        full_address = address.strip()
        if ":" not in full_address and port:
            full_address = f"{full_address}:{port}"

        numbers = [caller_id.strip()] if caller_id and caller_id.strip() else []

        if existing_trunk_id:
            try:
                await lk.sip.delete_sip_trunk(api.DeleteSIPTrunkRequest(sip_trunk_id=existing_trunk_id))
            except Exception as e:
                logger.warning(f"Failed to delete prior outbound trunk {existing_trunk_id}: {e}")

        trunk_info = api.SIPOutboundTrunkInfo(
            name=name,
            address=full_address,
            transport=trans_enum,
            numbers=numbers,
            auth_username=auth_username.strip() if auth_username else "",
            auth_password=auth_password.strip() if auth_password else "",
        )
        req = api.CreateSIPOutboundTrunkRequest(trunk=trunk_info)
        created = await lk.sip.create_sip_outbound_trunk(req)
        return created.sip_trunk_id
    finally:
        await lk.aclose()


async def _async_delete_outbound_trunk(trunk_id):
    if not trunk_id:
        return
    lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        await lk.sip.delete_sip_trunk(api.DeleteSIPTrunkRequest(sip_trunk_id=trunk_id))
    except Exception as e:
        logger.warning(f"Error deleting LiveKit outbound trunk {trunk_id}: {e}")
    finally:
        await lk.aclose()


async def _async_dial_sip_participant(trunk_id, destination_phone, room_name, caller_id=None):
    lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        req = api.CreateSIPParticipantRequest(
            sip_trunk_id=trunk_id,
            sip_call_to=destination_phone,
            room_name=room_name,
            sip_number=caller_id or "",
            participant_identity=f"customer_{destination_phone}",
            participant_name=f"عميل ({destination_phone})",
            play_dialtone=True,
        )
        return await lk.sip.create_sip_participant(req)
    finally:
        await lk.aclose()


@login_required(login_url='/login/')
def get_outbound_trunk(request):
    """Retrieve default/active Outbound SIP Trunk for current user."""
    trunk = OutboundSIPTrunk.objects.filter(user=request.user, is_default=True).first()
    if not trunk:
        trunk = OutboundSIPTrunk.objects.filter(user=request.user).first()

    return JsonResponse({
        "status": "success",
        "has_trunk": trunk is not None,
        "trunk": trunk.to_dict() if trunk else None,
        "providers_guide": [
            {
                "name": "Telnyx",
                "host": "sip.telnyx.com",
                "port": 5060,
                "transport": "UDP",
                "docs": "أنشئ Outbound SIP Connection وضع بيانات الـ SIP Credentials هنا ورقم هاتفك في Caller ID."
            },
            {
                "name": "Twilio Elastic SIP Trunking",
                "host": "{your-trunk}.pstn.twilio.com",
                "port": 5060,
                "transport": "UDP",
                "docs": "أنشئ Elastic SIP Trunk وضع Termination SIP URI وبيانات المصادقة ورقم هاتفك المشترى."
            },
            {
                "name": "Generic / Any SIP Provider",
                "host": "sip.provider.com",
                "port": 5060,
                "transport": "UDP",
                "docs": "يدعم النظام أي خادم SIP خارجي متوافق مع معايير RFC 3261."
            }
        ]
    })


@login_required(login_url='/login/')
def save_outbound_trunk(request):
    """Save or update Outbound SIP Trunk and provision in LiveKit."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        name = (data.get('name') or 'حساب المزود الخارجي (Generic SIP Trunk)').strip()
        sip_host = (data.get('sip_host') or '').strip()
        sip_port = int(data.get('sip_port') or 5060)
        transport = (data.get('transport') or 'UDP').strip().upper()
        auth_username = (data.get('auth_username') or '').strip()
        auth_password = (data.get('auth_password') or '').strip()
        caller_id_raw = (data.get('caller_id') or '').strip()

        if not sip_host:
            return JsonResponse({"status": "error", "message": "عنوان الخادم (SIP Host) مطلوب"}, status=400)

        caller_id = normalize_phone_number(caller_id_raw) if caller_id_raw else ""

        # Find existing default trunk or create new
        existing_trunk = OutboundSIPTrunk.objects.filter(user=request.user).first()
        existing_trunk_id = existing_trunk.livekit_outbound_trunk_id if existing_trunk else None

        # If user didn't enter password on update, keep existing password
        if not auth_password and existing_trunk and existing_trunk.auth_password:
            auth_password = existing_trunk.auth_password

        lk_trunk_id = asyncio.run(_async_create_or_update_outbound_trunk(
            name=name,
            address=sip_host,
            port=sip_port,
            transport_str=transport,
            auth_username=auth_username,
            auth_password=auth_password,
            caller_id=caller_id,
            existing_trunk_id=existing_trunk_id
        ))

        if existing_trunk:
            existing_trunk.name = name
            existing_trunk.sip_host = sip_host
            existing_trunk.sip_port = sip_port
            existing_trunk.transport = transport
            existing_trunk.auth_username = auth_username
            existing_trunk.auth_password = auth_password
            existing_trunk.caller_id = caller_id
            existing_trunk.livekit_outbound_trunk_id = lk_trunk_id
            existing_trunk.is_active = True
            existing_trunk.is_default = True
            existing_trunk.save()
            trunk_obj = existing_trunk
        else:
            trunk_obj = OutboundSIPTrunk.objects.create(
                user=request.user,
                name=name,
                sip_host=sip_host,
                sip_port=sip_port,
                transport=transport,
                auth_username=auth_username,
                auth_password=auth_password,
                caller_id=caller_id,
                livekit_outbound_trunk_id=lk_trunk_id,
                is_active=True,
                is_default=True
            )

        # Cache default outbound trunk in Redis for fast access by sip_proxy and workers
        try:
            r = redis.Redis.from_url(settings.REDIS_URL)
            r.set(f"user_outbound_trunk:{request.user.id}", json.dumps({
                "trunk_id": lk_trunk_id,
                "caller_id": caller_id,
                "sip_host": sip_host
            }))
        except Exception:
            pass

        return JsonResponse({
            "status": "success",
            "message": f"تم تسجيل الجذع الخارجي '{name}' بنجاح وربطه بخادم LiveKit (معرف الجذع: {lk_trunk_id})",
            "trunk": trunk_obj.to_dict()
        })

    except Exception as e:
        logger.error(f"Error saving outbound trunk: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"فشل تسجيل الجذع الخارجي: {str(e)}"}, status=500)


@login_required(login_url='/login/')
def delete_outbound_trunk(request, trunk_id):
    """Delete an Outbound SIP Trunk."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    trunk = get_object_or_404(OutboundSIPTrunk, id=trunk_id, user=request.user)
    try:
        asyncio.run(_async_delete_outbound_trunk(trunk.livekit_outbound_trunk_id))
    except Exception as e:
        logger.warning(f"Error deleting trunk {trunk.livekit_outbound_trunk_id}: {e}")

    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.delete(f"user_outbound_trunk:{request.user.id}")
    except Exception:
        pass

    name = trunk.name
    trunk.delete()
    return JsonResponse({
        "status": "success",
        "message": f"تم حذف الجذع الخارجي '{name}' بنجاح."
    })


@csrf_exempt
@login_required(login_url='/login/')
def trigger_ai_outbound_call(request):
    """Initiate an autonomous outbound AI call to a destination phone number."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        raw_phone = (data.get('phone_number') or '').strip()
        call_goal = (data.get('call_goal') or '').strip()
        profile_id = data.get('profile_id')

        if not raw_phone:
            return JsonResponse({"status": "error", "message": "رقم الهاتف مطلوب للاتصال"}, status=400)

        normalized_phone = normalize_phone_number(raw_phone)
        if not normalized_phone or len(normalized_phone) < 8:
            return JsonResponse({"status": "error", "message": f"رقم الهاتف غير صالح ({raw_phone}). يرجى التأكد من كتابة الرقم بصيغة صحيحة."}, status=400)

        # Get user's active outbound trunk
        trunk = OutboundSIPTrunk.objects.filter(user=request.user, is_active=True, is_default=True).first()
        if not trunk:
            trunk = OutboundSIPTrunk.objects.filter(user=request.user, is_active=True).first()

        if not trunk or not trunk.livekit_outbound_trunk_id:
            return JsonResponse({
                "status": "error",
                "message": "لا يوجد جذع SIP خارجي مفعل. يرجى أولاً إدخال بيانات المزود (Telnyx أو Twilio) في قسم 'إعدادات الجذع الخارجي' وحفظها."
            }, status=400)

        # Resolve voice profile
        profile = None
        if profile_id:
            profile = AgentProfile.objects.filter(id=profile_id, user=request.user).first()
        if not profile:
            profile = AgentProfile.objects.filter(user=request.user, is_active=True).first()

        room_name = f"room_user_{request.user.id}_ai_out_{uuid.uuid4().hex[:8]}"

        # Create CallSession record
        session = CallSession.objects.create(
            user=request.user,
            room_name=room_name,
            direction='outbound_ai',
            destination_phone=normalized_phone,
            call_goal=call_goal or "مكالمة ذكاء اصطناعي صادرة للعميل"
        )

        # Dial external customer via LiveKit Outbound Trunk
        participant_info = asyncio.run(_async_dial_sip_participant(
            trunk_id=trunk.livekit_outbound_trunk_id,
            destination_phone=normalized_phone,
            room_name=room_name,
            caller_id=trunk.caller_id
        ))

        # Push dispatch job to Redis for Voice Assistant agent
        r = redis.Redis.from_url(settings.REDIS_URL)
        job_payload = {
            "room_name": room_name,
            "user_id": request.user.id,
            "is_outbound_ai": True,
            "call_goal": call_goal,
            "destination_phone": normalized_phone,
            "profile": profile.to_dict() if profile else None,
            "session_id": session.id
        }
        r.lpush("agent_jobs", json.dumps(job_payload, ensure_ascii=False))

        logger.info(f"Triggered AI Outbound Call to {normalized_phone} in room {room_name} (Session {session.id})")

        return JsonResponse({
            "status": "success",
            "message": f"تم بدء الاتصال الصادر بالرقم {normalized_phone} بنجاح عبر المساعد الذكي",
            "room_name": room_name,
            "session_id": session.id,
            "destination_phone": normalized_phone,
            "trunk_name": trunk.name,
            "caller_id": trunk.caller_id or "غير محدد"
        })

    except Exception as e:
        logger.error(f"Error triggering AI outbound call: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"فشل بدء المكالمة الصادرة: {str(e)}"}, status=500)
