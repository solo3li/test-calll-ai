import json
import logging
import time
import uuid
import jwt
import requests
import redis
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from livekit import api

from django.views.decorators.cache import never_cache

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

@never_cache
def room_view(request):
    """Render the main Voice Assistant page."""
    context = {
        'centrifugo_ws_url': settings.CENTRIFUGO_WS_URL,
        'livekit_url': settings.LIVEKIT_URL,
    }
    return render(request, 'voice_assistant/room.html', context)

def get_tokens(request):
    """
    Generate authentication tokens for:
    1. LiveKit (WebRTC Audio Room)
    2. Centrifugo (Real-time WebSockets Notifications)
    """
    room_name = request.GET.get('room', f"room_{uuid.uuid4().hex[:6]}")
    user_identity = f"user_{uuid.uuid4().hex[:6]}"
    channel_name = f"rooms:{room_name}"

    # 1. Generate LiveKit Token
    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
        .with_identity(user_identity) \
        .with_name(user_identity) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    livekit_jwt = token.to_jwt()

    # 2. Generate Centrifugo Connection & Subscription Token (Centrifugo v5 requires subs to be map[string]SubscribeOptions)
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
    })

@csrf_exempt
def livekit_webhook(request):
    """
    Handle LiveKit Webhooks.
    When a human participant enters the room, trigger Pipecat Agent via Celery.
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
        # CRITICAL: Prevent infinite loop when the bot itself joins!
        if participant_identity == "pipecat-agent":
            logger.info(f"pipecat-agent joined room {room_name}. No action needed.")
            publish_to_centrifugo(channel, {
                "event": "agent_connected",
                "message": "المساعد الصوتي متصل وجاهز للاستماع الآن",
                "timestamp": time.time(),
            })
        else:
            logger.info(f"Human participant '{participant_identity}' joined room {room_name}. Queuing Pipecat Agent...")
            publish_to_centrifugo(channel, {
                "event": "agent_queued",
                "message": "تم رصد انضمام المستخدم. جاري استدعاء المساعد الصوتي...",
                "timestamp": time.time(),
            })
            # Dispatch to standalone Agent service via Redis queue
            try:
                r = redis.Redis.from_url(settings.REDIS_URL)
                r.rpush("agent_jobs", room_name)
                logger.info(f"Dispatched room '{room_name}' to standalone agent service via Redis queue.")
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

    elif event_type == "room_finished":
        logger.info(f"Room {room_name} finished.")

    return HttpResponse("ok")
