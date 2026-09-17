import json
import logging
import time
import uuid
import jwt
import requests
import redis
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from livekit import api

from agents.models import AgentProfile
from call_center.models import CallQueue
from telephony.models import OutboundSIPTrunk
from crm.models import CallSession
from telephony.views import _async_dial_sip_participant

# Re-export views from domain apps for backward compatibility
from knowledge.views import (
    list_documents,
    upload_document,
    delete_document,
)
from agents.views import (
    list_profiles,
    create_profile,
    activate_profile,
    update_profile,
    delete_profile,
    get_mcp_server,
    save_mcp_server,
    sync_mcp_server,
    toggle_mcp_server,
    delete_mcp_server,
)
from crm.views import (
    list_customers_memory,
    get_customer_memory,
    reset_customer_memory,
)
from telephony.views import (
    normalize_phone_number,
    get_outbound_trunk,
    save_outbound_trunk,
    delete_outbound_trunk,
    trigger_ai_outbound_call,
    list_pbx_trunks,
    save_pbx_trunk,
    delete_pbx_trunk,
)
from telephony.models import InboundPBXTrunk
from call_center.views import (
    api_employee_login,
    api_employee_me,
    api_list_employees,
    api_create_employee,
    api_delete_employee,
    api_update_employee_status,
    list_call_queues,
    create_call_queue,
    delete_call_queue,
    api_dial_call,
    api_get_call_token,
    api_hangup_call,
)

logger = logging.getLogger(__name__)

def publish_to_centrifugo(channel: str, data: dict):
    """Publish real-time notification to Centrifugo channel."""
    try:
        url = f"{settings.CENTRIFUGO_HTTP_API_URL}/publish"
        headers = {
            "Authorization": f"apikey {settings.CENTRIFUGO_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "channel": channel,
            "data": data,
        }
        res = requests.post(url, json=payload, headers=headers, timeout=2)
        if res.status_code != 200:
            logger.error(f"Centrifugo publish error ({res.status_code}): {res.text}")
    except Exception as e:
        logger.error(f"Failed to publish to Centrifugo: {e}")

# ==================== Authentication Views ====================

def login_view(request):
    """Render and process login."""
    if request.user.is_authenticated:
        return redirect('voice_assistant:room')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            error = "يرجى إدخال اسم المستخدم وكلمة المرور."
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next') or request.POST.get('next') or '/'
                return redirect(next_url)
            else:
                error = "اسم المستخدم أو كلمة المرور غير صحيحة."

    return render(request, 'voice_assistant/login.html', {'error': error})

def register_view(request):
    """Render and process user registration."""
    if request.user.is_authenticated:
        return redirect('voice_assistant:room')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not username or not password:
            error = "اسم المستخدم وكلمة المرور مطلوبان."
        elif len(password) < 6:
            error = "يجب أن تتكون كلمة المرور من 6 أحرف على الأقل."
        elif password != password_confirm:
            error = "كلمتا المرور غير متطابقتين."
        elif User.objects.filter(username=username).exists():
            error = "اسم المستخدم هذا مسجل بالفعل، يرجى اختيار اسم آخر."
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect('voice_assistant:room')

    return render(request, 'voice_assistant/register.html', {'error': error})

def logout_view(request):
    """Log out user and redirect to login page."""
    logout(request)
    return redirect('voice_assistant:login')

# ==================== Voice Room & WebRTC ====================

@never_cache
@login_required(login_url='/login/')
def room_view(request):
    """Render the main Voice Assistant page."""
    context = {
        'centrifugo_ws_url': settings.CENTRIFUGO_WS_URL,
        'livekit_url': settings.LIVEKIT_URL,
        'username': request.user.username,
        'user_id': request.user.id,
    }
    return render(request, 'voice_assistant/room.html', context)

@login_required(login_url='/login/')
def get_tokens(request):
    """
    Generate authentication tokens for LiveKit and Centrifugo for the authenticated user.
    """
    room_name = request.GET.get('room') or f"room_user_{request.user.id}_{uuid.uuid4().hex[:6]}"
    user_identity = f"user_{request.user.id}_{request.user.username}"
    channel_name = f"rooms:{room_name}"

    active_profile = AgentProfile.objects.filter(user=request.user, is_active=True).first()
    if not active_profile:
        active_profile = AgentProfile.objects.create(
            user=request.user,
            name="نورهان - خدمة عملاء مصرية",
            voice_name="Aoede",
            gender="female",
            dialect="egyptian",
            persona_role="customer_support",
            speaking_style="friendly",
            is_active=True
        )

    metadata = json.dumps({
        "user_id": request.user.id,
        "username": request.user.username,
        "profile": active_profile.to_dict()
    })

    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
        .with_identity(user_identity) \
        .with_name(request.user.username) \
        .with_metadata(metadata) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    livekit_jwt = token.to_jwt()

    centrifugo_payload = {
        "sub": user_identity,
        "exp": int(time.time()) + (24 * 3600),
        "subs": {
            channel_name: {}
        }
    }
    centrifugo_jwt = jwt.encode(
        centrifugo_payload,
        settings.CENTRIFUGO_SECRET,
        algorithm="HS256"
    )

    return JsonResponse({
        "status": "success",
        "room_name": room_name,
        "channel": channel_name,
        "user_identity": user_identity,
        "livekit_url": settings.LIVEKIT_URL,
        "livekit_token": livekit_jwt,
        "centrifugo_ws_url": settings.CENTRIFUGO_WS_URL,
        "centrifugo_token": centrifugo_jwt,
        "active_profile": active_profile.to_dict(),
    })

@csrf_exempt
def livekit_webhook(request):
    """
    Handle LiveKit Webhooks.
    When a human participant enters the room, trigger Voice Agent via Redis queue.
    """
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    auth_header = request.headers.get('Authorization')
    if not auth_header:
        logger.warning("LiveKit webhook missing Authorization header")
        return HttpResponse("Missing authorization header", status=401)

    try:
        token_verifier = api.TokenVerifier(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        receiver = api.WebhookReceiver(token_verifier)
        event = receiver.receive(request.body.decode('utf-8'), auth_header)
    except Exception as e:
        logger.error(f"Invalid webhook signature: {e}")
        return HttpResponse("Invalid signature", status=401)

    event_type = event.event
    room_name = event.room.name if event.room else "unknown"
    channel = f"rooms:{room_name}"

    logger.info(f"Received LiveKit Webhook: {event_type} in room {room_name}")

    if event_type == "participant_joined":
        participant_identity = event.participant.identity
        if participant_identity == "pipecat-agent":
            logger.info(f"pipecat-agent joined room {room_name}.")
            publish_to_centrifugo(channel, {
                "event": "agent_connected",
                "message": "المساعد الصوتي متصل وجاهز للاستماع الآن",
                "timestamp": time.time(),
            })
            return HttpResponse("ok")

        # Skip direct human-to-human calls (employee to employee or employee to external PSTN)
        if room_name.startswith("call_ext_") or room_name.startswith("pstn_out_"):
            logger.info(f"Direct human-to-human call room '{room_name}' (participant: {participant_identity}). Skipping AI agent dispatch.")
            return HttpResponse("ok")

        else:
            user_id = None
            profile = None
            if event.participant.metadata:
                try:
                    meta = json.loads(event.participant.metadata)
                    user_id = meta.get("user_id")
                    profile = meta.get("profile")
                except Exception:
                    pass

            if not user_id and participant_identity.startswith("user_"):
                parts = participant_identity.split("_")
                if len(parts) >= 2 and parts[1].isdigit():
                    user_id = int(parts[1])

            if not user_id and room_name.startswith("room_user_"):
                parts = room_name.split("_")
                if len(parts) >= 3 and parts[2].isdigit():
                    user_id = int(parts[2])

            is_queue = False
            queue_code = None
            queue_data = None
            parts = room_name.split("_")
            if len(parts) >= 5 and parts[3] == "queue":
                is_queue = True
                queue_code = parts[4]
            elif room_name.startswith("queue_") and len(parts) >= 2:
                is_queue = True
                queue_code = parts[1]

            if is_queue and queue_code:
                try:
                    q_filter = {"code": queue_code, "is_active": True}
                    if user_id:
                        q_filter["user_id"] = user_id
                    q_obj = CallQueue.objects.filter(**q_filter).first()
                    if q_obj:
                        queue_data = q_obj.to_dict()
                        if not user_id:
                            user_id = q_obj.user_id
                except Exception as e:
                    logger.error(f"Error loading queue {queue_code}: {e}")

            if user_id and not profile:
                if "_pbx_" in room_name:
                    try:
                        p_idx = parts.index("pbx")
                        if len(parts) > p_idx + 1 and parts[p_idx + 1].isdigit():
                            pbx_t = InboundPBXTrunk.objects.filter(id=int(parts[p_idx + 1])).select_related('target_profile').first()
                            if pbx_t and pbx_t.target_profile:
                                profile = pbx_t.target_profile.to_dict()
                    except Exception:
                        pass
                if not profile:
                    active_prof = AgentProfile.objects.filter(user_id=user_id, is_active=True).first()
                    if active_prof:
                        profile = active_prof.to_dict()

            pending_dest = None
            if participant_identity.startswith("sip_"):
                clean = participant_identity.replace("sip_sip_", "sip_")
                try:
                    r = redis.Redis.from_url(settings.REDIS_URL)
                    p_val = r.get(f"pending_outbound_dial:{clean}") or r.get(f"pending_outbound_dial:{participant_identity}")
                    if p_val:
                        pending_dest = p_val.decode() if isinstance(p_val, bytes) else str(p_val)
                        r.delete(f"pending_outbound_dial:{clean}")
                        r.delete(f"pending_outbound_dial:{participant_identity}")
                except Exception as ex:
                    logger.warning(f"Error checking pending outbound dial in Redis: {ex}")

            if pending_dest and user_id:
                trunk = OutboundSIPTrunk.objects.filter(user_id=user_id, is_active=True, is_default=True).first()
                if not trunk:
                    trunk = OutboundSIPTrunk.objects.filter(user_id=user_id, is_active=True).first()

                if trunk and trunk.livekit_outbound_trunk_id:
                    CallSession.objects.create(
                        user_id=user_id,
                        room_name=room_name,
                        direction='outbound_agent',
                        destination_phone=pending_dest,
                        call_goal=f"مكالمة موظف مباشرة عبر MicroSIP للرقم {pending_dest}"
                    )
                    import asyncio
                    try:
                        asyncio.run(_async_dial_sip_participant(
                            trunk_id=trunk.livekit_outbound_trunk_id,
                            destination_phone=pending_dest,
                            room_name=room_name,
                            caller_id=trunk.caller_id
                        ))
                        logger.info(f"Direct MicroSIP outbound call bridged to {pending_dest} in room {room_name}")
                    except Exception as de:
                        logger.error(f"Failed to bridge outbound participant: {de}")

                try:
                    r = redis.Redis.from_url(settings.REDIS_URL)
                    clean = participant_identity.replace("sip_sip_", "sip_")
                    r.set(f"agent_room:{participant_identity}", room_name, ex=7200)
                    r.set(f"agent_room:{clean}", room_name, ex=7200)
                except Exception:
                    pass
                return HttpResponse("ok")

            if "_ai_out_" in room_name or "_agent_out_" in room_name:
                logger.info(f"Participant joined outbound room {room_name}. Already dispatched.")
                return HttpResponse("ok")

            caller_phone = 'web_dashboard'
            if participant_identity.startswith("sip_"):
                raw_sip = participant_identity.replace("sip_sip_", "").replace("sip_", "")
                raw_sip = raw_sip.split("@")[0].replace("sip:", "")
                if raw_sip:
                    caller_phone = raw_sip
            elif participant_identity.startswith("customer_"):
                caller_phone = participant_identity.replace("customer_", "")

            logger.info(f"Human participant '{participant_identity}' (user_id={user_id}, caller_phone={caller_phone}, is_queue={is_queue}) joined room {room_name}. Queuing Voice Agent...")
            publish_to_centrifugo(channel, {
                "event": "agent_queued",
                "message": f"تم رصد انضمام متصل لطابور الانتظار (كود: {queue_code})..." if is_queue else "تم رصد انضمام المستخدم. جاري استدعاء المساعد الصوتي وتجهيز قاعدة المستندات...",
                "timestamp": time.time(),
            })

            try:
                r = redis.Redis.from_url(settings.REDIS_URL)
                job_payload = json.dumps({
                    "room_name": room_name,
                    "user_id": user_id,
                    "caller_phone": caller_phone,
                    "profile": profile,
                    "is_queue": is_queue,
                    "queue_code": queue_code,
                    "queue_data": queue_data,
                    "participant_identity": participant_identity
                })
                r.rpush("agent_jobs", job_payload)
                if participant_identity.startswith("sip_"):
                    clean = participant_identity.replace("sip_sip_", "sip_")
                    r.set(f"agent_room:{participant_identity}", room_name, ex=7200)
                    r.set(f"agent_room:{clean}", room_name, ex=7200)
                logger.info(f"Dispatched job {job_payload} to Redis 'agent_jobs' queue.")
            except Exception as ex:
                logger.error(f"Failed to dispatch room '{room_name}' to Redis: {ex}")

    elif event_type == "participant_left":
        participant_identity = event.participant.identity
        if participant_identity != "pipecat-agent":
            publish_to_centrifugo(channel, {
                "event": "user_left",
                "message": "المستخدم غادر الغرفة",
                "timestamp": time.time(),
            })
            if participant_identity.startswith("sip_"):
                try:
                    clean = participant_identity.replace("sip_sip_", "sip_")
                    r = redis.Redis.from_url(settings.REDIS_URL)
                    r.set(f"agent_state:{participant_identity}", "AVAILABLE")
                    r.set(f"agent_state:{clean}", "AVAILABLE")
                    r.delete(f"agent_room:{participant_identity}")
                    r.delete(f"agent_room:{clean}")
                    publish_to_centrifugo("presence_updates", {
                        "event": "agent_presence",
                        "sip_username": participant_identity,
                        "state": "AVAILABLE"
                    })
                except Exception:
                    pass

    elif event_type == "room_finished":
        logger.info(f"Room {room_name} finished.")

    return HttpResponse("ok")
