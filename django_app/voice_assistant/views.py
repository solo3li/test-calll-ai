import json
import logging
import time
import uuid
import re
import jwt
import requests
import redis
import os
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from livekit import api
from google import genai

from .models import Document, DocumentChunk, UserAction, AgentProfile, UserMCPServer, CustomerMemory, CallSession, CallQueue, QueueMembership, OutboundSIPTrunk, EmployeeProfile
from .rag_utils import extract_text_from_file, chunk_text, get_embeddings_batch

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
    # Use session or requested room, prefixing with user ID for tracking
    room_name = request.GET.get('room') or f"room_user_{request.user.id}_{uuid.uuid4().hex[:6]}"
    user_identity = f"user_{request.user.id}_{request.user.username}"
    channel_name = f"rooms:{room_name}"

    # 1. Fetch or create active AgentProfile for user
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

    # 2. Generate LiveKit Token with user metadata
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

    # 2. Generate Centrifugo Connection & Subscription Token
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
        # Prevent loop when agent joins
        if participant_identity == "pipecat-agent":
            logger.info(f"pipecat-agent joined room {room_name}.")
            publish_to_centrifugo(channel, {
                "event": "agent_connected",
                "message": "المساعد الصوتي متصل وجاهز للاستماع الآن",
                "timestamp": time.time(),
            })
        else:
            # Extract user_id and profile from participant metadata or identity
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

            # Also resolve user_id from room_name if dispatched by SIP rule: room_user_{user_id}_sip_...
            if not user_id and room_name.startswith("room_user_"):
                parts = room_name.split("_")
                if len(parts) >= 3 and parts[2].isdigit():
                    user_id = int(parts[2])

            # Check if this room is a Call Queue: room_user_{user_id}_queue_{code}_...
            is_queue = False
            queue_code = None
            queue_data = None
            parts = room_name.split("_")
            if len(parts) >= 5 and parts[3] == "queue":
                is_queue = True
                queue_code = parts[4]
                try:
                    q_obj = CallQueue.objects.filter(user_id=user_id, code=queue_code, is_active=True).first()
                    if q_obj:
                        queue_data = q_obj.to_dict()
                except Exception as e:
                    logger.error(f"Error loading queue {queue_code} for user {user_id}: {e}")

            # Resolve active profile if not provided in metadata
            if user_id and not profile:
                active_prof = AgentProfile.objects.filter(user_id=user_id, is_active=True).first()
                if active_prof:
                    profile = active_prof.to_dict()

            # Check if this participant is an agent making a direct outbound call to an external phone number
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
                # Direct Outbound Call initiated from MicroSIP!
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

            # Check if this room is an outbound AI room (dispatched via trigger_ai_outbound_call)
            if "_ai_out_" in room_name or "_agent_out_" in room_name:
                logger.info(f"Participant joined outbound room {room_name}. Already dispatched.")
                return HttpResponse("ok")

            logger.info(f"Human participant '{participant_identity}' (user_id={user_id}, is_queue={is_queue}) joined room {room_name}. Queuing Voice Agent...")
            publish_to_centrifugo(channel, {
                "event": "agent_queued",
                "message": f"تم رصد انضمام متصل لطابور الانتظار (كود: {queue_code})..." if is_queue else "تم رصد انضمام المستخدم. جاري استدعاء المساعد الصوتي وتجهيز قاعدة المستندات...",
                "timestamp": time.time(),
            })

            # Dispatch to standalone Agent service via Redis queue with user_id, profile, and queue info
            try:
                r = redis.Redis.from_url(settings.REDIS_URL)
                job_payload = json.dumps({
                    "room_name": room_name,
                    "user_id": user_id,
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
            # If a SIP agent left, reset their status to AVAILABLE in Redis and publish presence
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

# ==================== Document Ingestion & RAG Management ====================

@login_required(login_url='/login/')
def list_documents(request):
    """List all documents uploaded by the current user."""
    docs = Document.objects.filter(user=request.user).order_by('-created_at')
    data = []
    for d in docs:
        data.append({
            "id": d.id,
            "title": d.title,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "chunks_count": d.chunks.count(),
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return JsonResponse({"status": "success", "documents": data})

@login_required(login_url='/login/')
def upload_document(request):
    """Handle document upload, text extraction, chunking, and Gemini embedding generation."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    file_obj = request.FILES.get('file')
    if not file_obj:
        return JsonResponse({"status": "error", "message": "لم يتم تحديد أي ملف للرفع"}, status=400)

    filename = file_obj.name
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = ['.pdf', '.docx', '.doc', '.txt', '.md']
    if ext not in allowed_exts:
        return JsonResponse({
            "status": "error",
            "message": f"صيغة الملف غير مدعومة ({ext}). الصيغ المدعومة هي: PDF, DOCX, TXT, MD"
        }, status=400)

    try:
        # 1. Extract text from uploaded file
        text = extract_text_from_file(file_obj, filename)
        if not text:
            return JsonResponse({"status": "error", "message": "الملف فارغ أو يتعذر استخراج نص منه."}, status=400)

        # 2. Chunk text
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        if not chunks:
            return JsonResponse({"status": "error", "message": "لم يتم العثور على محتوى صالح للتقطيع."}, status=400)

        # 3. Create Document DB record
        doc = Document.objects.create(
            user=request.user,
            title=filename,
            file=file_obj,
            file_type=ext.lstrip('.'),
            file_size=file_obj.size
        )

        # 4. Generate embeddings with Gemini text-embedding-004
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        embeddings = get_embeddings_batch(client, chunks, batch_size=50)

        # 5. Bulk create DocumentChunks in PostgreSQL pgvector
        chunk_objects = []
        for i, (chunk_text_content, emb) in enumerate(zip(chunks, embeddings)):
            chunk_objects.append(DocumentChunk(
                document=doc,
                user=request.user,
                chunk_index=i,
                content=chunk_text_content,
                embedding=emb,
            ))
        DocumentChunk.objects.bulk_create(chunk_objects)

        logger.info(f"Successfully processed document '{filename}' for user {request.user.username}: {len(chunks)} chunks embedded.")

        return JsonResponse({
            "status": "success",
            "message": f"تمت معالجة المستند '{filename}' بنجاح وفهرسة {len(chunks)} مقطعاً دلالياً.",
            "document": {
                "id": doc.id,
                "title": doc.title,
                "chunks_count": len(chunks),
                "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        })

    except Exception as e:
        logger.error(f"Error processing document upload: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"حدث خطأ أثناء معالجة المستند: {str(e)}"}, status=500)

@login_required(login_url='/login/')
def delete_document(request, doc_id):
    """Delete a document and all its chunks for the authenticated user."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    doc = get_object_or_404(Document, id=doc_id, user=request.user)
    title = doc.title
    doc.delete()
    logger.info(f"Deleted document '{title}' (id={doc_id}) for user {request.user.username}")
    return JsonResponse({"status": "success", "message": f"تم حذف المستند '{title}' بنجاح."})

# ==================== User Custom Actions Management ====================

@login_required(login_url='/login/')
def list_actions(request):
    """List all custom HTTP actions defined by the current user."""
    actions = UserAction.objects.filter(user=request.user).order_by('-created_at')
    data = []
    for a in actions:
        data.append({
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "url": a.url,
            "method": a.method,
            "headers": a.headers,
            "parameters_schema": a.parameters_schema,
            "is_active": a.is_active,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return JsonResponse({"status": "success", "actions": data})

@login_required(login_url='/login/')
def create_action(request):
    """Create a new custom HTTP action for the current user."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        url = data.get('url', '').strip()
        method = data.get('method', 'GET').upper().strip()

        if not name or not description or not url:
            return JsonResponse({"status": "error", "message": "الاسم والوصف والرابط حقول مطلوبة."}, status=400)

        # Sanitize name to valid identifier
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name).lower().strip('_')
        if not clean_name:
            clean_name = "custom_action"

        headers = data.get('headers', {})
        if isinstance(headers, str):
            try:
                headers = json.loads(headers) if headers.strip() else {}
            except Exception:
                headers = {}

        parameters_schema = data.get('parameters_schema', {})
        if isinstance(parameters_schema, str):
            try:
                parameters_schema = json.loads(parameters_schema) if parameters_schema.strip() else {}
            except Exception:
                parameters_schema = {}

        action = UserAction.objects.create(
            user=request.user,
            name=clean_name,
            description=description,
            url=url,
            method=method,
            headers=headers,
            parameters_schema=parameters_schema,
            is_active=True
        )

        return JsonResponse({
            "status": "success",
            "message": f"تمت إضافة الإجراء '{clean_name}' بنجاح.",
            "action": {
                "id": action.id,
                "name": action.name,
                "description": action.description,
                "url": action.url,
                "method": action.method,
                "is_active": action.is_active,
                "created_at": action.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        }, status=201)

    except Exception as e:
        logger.error(f"Error creating user action: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"حدث خطأ أثناء حفظ الإجراء: {str(e)}"}, status=400)

@login_required(login_url='/login/')
def toggle_action(request, action_id):
    """Toggle the active state of an action."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    action = get_object_or_404(UserAction, id=action_id, user=request.user)
    action.is_active = not action.is_active
    action.save()
    status_text = "تفعيل" if action.is_active else "إيقاف"
    return JsonResponse({
        "status": "success",
        "is_active": action.is_active,
        "message": f"تم {status_text} الإجراء '{action.name}' بنجاح."
    })

@login_required(login_url='/login/')
def delete_action(request, action_id):
    """Delete an action owned by the current user."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    action = get_object_or_404(UserAction, id=action_id, user=request.user)
    name = action.name
    action.delete()
    return JsonResponse({"status": "success", "message": f"تم حذف الإجراء '{name}' بنجاح."})

# ==================== Agent Voice & Persona Profiles ====================

GOOGLE_VOICES = [
    # Feminine Voices
    {"name": "Aoede", "gender": "female", "style": "Breezy (نسيم هادئ ولطيف)", "tag": "طبيعي وهادئ"},
    {"name": "Kore", "gender": "female", "style": "Firm (واثق ورسمي)", "tag": "رسمي ومتمكن"},
    {"name": "Leda", "gender": "female", "style": "Youthful (شبابي ومشرق)", "tag": "شبابي وحيوي"},
    {"name": "Callirrhoe", "gender": "female", "style": "Easy-going (مسترخي ومريح)", "tag": "ودود ومسترخي"},
    {"name": "Autonoe", "gender": "female", "style": "Bright (مشرق ومتفاعل)", "tag": "مشرق"},
    {"name": "Despina", "gender": "female", "style": "Smooth (ناعم ورقيق)", "tag": "رقيق وناعم"},
    {"name": "Erinome", "gender": "female", "style": "Clear (نقي ومحدد)", "tag": "واضح جداً"},
    {"name": "Laomedeia", "gender": "female", "style": "Upbeat (مرح ومتفائل)", "tag": "مرح ومتفائل"},
    {"name": "Vindemiatrix", "gender": "female", "style": "Gentle (لطيف ودافئ)", "tag": "لطيف"},
    {"name": "Sulafat", "gender": "female", "style": "Warm (دافئ ومطمئن)", "tag": "دافئ"},
    {"name": "Pulcherrima", "gender": "female", "style": "Forward (مباشر وجريء)", "tag": "مباشر وحاسم"},

    # Masculine Voices
    {"name": "Puck", "gender": "male", "style": "Upbeat (مرح ومتحمس)", "tag": "حماسي وودود"},
    {"name": "Charon", "gender": "male", "style": "Informative (إخباري ورسمي)", "tag": "إخباري ومتقن"},
    {"name": "Fenrir", "gender": "male", "style": "Excitable (نشيط ومتحمس)", "tag": "حماسي جداً"},
    {"name": "Orus", "gender": "male", "style": "Firm (حازم ورصين)", "tag": "حازم وواثق"},
    {"name": "Algieba", "gender": "male", "style": "Smooth (انسيابي ورخيم)", "tag": "رخيم وهادئ"},
    {"name": "Algenib", "gender": "male", "style": "Gravelly (أجش وعميق)", "tag": "أجش ورجولي"},
    {"name": "Achird", "gender": "male", "style": "Friendly (ودود وأليف)", "tag": "ودود ومريح"},
    {"name": "Gacrux", "gender": "male", "style": "Mature (ناضج ووقور)", "tag": "ناضج ووقور"},
    {"name": "Sadaltager", "gender": "male", "style": "Knowledgeable (خبير ومتمكن)", "tag": "خبير ومقنع"},
    {"name": "Iapetus", "gender": "male", "style": "Clear (واضح وصريح)", "tag": "واضح"},
    {"name": "Umbriel", "gender": "male", "style": "Easy-going (عفوي ومرن)", "tag": "عفوي"},
    {"name": "Enceladus", "gender": "male", "style": "Breathy (نَفَسي وعميق)", "tag": "نَفَسي"},
    {"name": "Rasalgethi", "gender": "male", "style": "Informative (معلوماتي ورسمي)", "tag": "رسمي"},
    {"name": "Achernar", "gender": "male", "style": "Soft (ناعم وهادئ)", "tag": "ناعم وهادئ"},
    {"name": "Alnilam", "gender": "male", "style": "Firm (صلب وقوي)", "tag": "حازم"},
    {"name": "Schedar", "gender": "male", "style": "Even (متزن ومستقر)", "tag": "متزن"},
    {"name": "Zubenelgenubi", "gender": "male", "style": "Casual (تلقائي وعادي)", "tag": "تلقائي"},
    {"name": "Sadachbia", "gender": "male", "style": "Lively (حيوي ومتفاعل)", "tag": "حيوي"},
    {"name": "Zephyr", "gender": "male", "style": "Bright (منعش ومشرق)", "tag": "منعش"},
]

@login_required(login_url='/login/')
def list_profiles(request):
    """List all agent profiles for user, active profile, and options metadata."""
    profiles = list(AgentProfile.objects.filter(user=request.user))
    if not profiles:
        default_prof = AgentProfile.objects.create(
            user=request.user,
            name="نورهان - خدمة عملاء مصرية",
            voice_name="Aoede",
            gender="female",
            dialect="egyptian",
            persona_role="customer_support",
            speaking_style="friendly",
            is_active=True
        )
        profiles = [default_prof]

    active_p = next((p for p in profiles if p.is_active), profiles[0])

    return JsonResponse({
        "status": "success",
        "profiles": [p.to_dict() for p in profiles],
        "active_profile": active_p.to_dict(),
        "google_voices": GOOGLE_VOICES,
        "dialects": [{"id": d[0], "label": d[1]} for d in AgentProfile.DIALECT_CHOICES],
        "roles": [{"id": r[0], "label": r[1]} for r in AgentProfile.ROLE_CHOICES],
        "styles": [{"id": s[0], "label": s[1]} for s in AgentProfile.STYLE_CHOICES],
        "genders": [{"id": g[0], "label": g[1]} for g in AgentProfile.GENDER_CHOICES],
    })

@login_required(login_url='/login/')
def create_profile(request):
    """Create a new agent persona profile for user."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        name = data.get('name', '').strip() or 'بروفايل مخصص'
        voice_name = data.get('voice_name', 'Aoede').strip()
        gender = data.get('gender', 'female')
        dialect = data.get('dialect', 'egyptian')
        persona_role = data.get('persona_role', 'customer_support')
        speaking_style = data.get('speaking_style', 'friendly')
        custom_instructions = data.get('custom_instructions', '').strip()
        is_active = bool(data.get('is_active', True))

        profile = AgentProfile.objects.create(
            user=request.user,
            name=name,
            voice_name=voice_name,
            gender=gender,
            dialect=dialect,
            persona_role=persona_role,
            speaking_style=speaking_style,
            custom_instructions=custom_instructions,
            is_active=is_active
        )
        return JsonResponse({
            "status": "success",
            "message": f"تم حفظ البروفايل '{profile.name}' بنجاح.",
            "profile": profile.to_dict()
        }, status=201)
    except Exception as e:
        logger.error(f"Error creating agent profile: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required(login_url='/login/')
def update_profile(request, profile_id):
    """Update an existing agent persona profile."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        if 'name' in data and data['name'].strip():
            profile.name = data['name'].strip()
        if 'voice_name' in data and data['voice_name'].strip():
            profile.voice_name = data['voice_name'].strip()
        if 'gender' in data:
            profile.gender = data['gender']
        if 'dialect' in data:
            profile.dialect = data['dialect']
        if 'persona_role' in data:
            profile.persona_role = data['persona_role']
        if 'speaking_style' in data:
            profile.speaking_style = data['speaking_style']
        if 'custom_instructions' in data:
            profile.custom_instructions = data['custom_instructions'].strip()
        if 'is_active' in data:
            profile.is_active = bool(data['is_active'])

        profile.save()
        return JsonResponse({
            "status": "success",
            "message": f"تم تحديث البروفايل '{profile.name}' بنجاح.",
            "profile": profile.to_dict()
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required(login_url='/login/')
def activate_profile(request, profile_id):
    """Set a specific profile as the active one for future calls."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)
    profile.is_active = True
    profile.save()
    return JsonResponse({
        "status": "success",
        "message": f"تم تفعيل البروفايل '{profile.name}' للمكالمات القادمة.",
        "profile": profile.to_dict()
    })

@login_required(login_url='/login/')
def delete_profile(request, profile_id):
    """Delete an agent persona profile."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    profile = get_object_or_404(AgentProfile, id=profile_id, user=request.user)
    was_active = profile.is_active
    name = profile.name
    profile.delete()

    if was_active:
        fallback = AgentProfile.objects.filter(user=request.user).first()
        if fallback:
            fallback.is_active = True
            fallback.save()

    return JsonResponse({"status": "success", "message": f"تم حذف البروفايل '{name}' بنجاح."})

# ==================== User External MCP Server Handling ====================
import asyncio
from django.utils import timezone

async def _fetch_mcp_tools_async(url: str, auth_token: str = ""):
    """Connect to MCP SSE server, perform handshake, and list tools."""
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with sse_client(url, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_list = await session.list_tools()
            tools = []
            for t in tool_list.tools:
                schema = getattr(t, 'input_schema', None) or getattr(t, 'inputSchema', None) or {}
                tools.append({
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": schema
                })
            return tools

def fetch_mcp_tools_sync(url: str, auth_token: str = "", timeout: float = 6.0):
    """Fetch tool list from an external MCP SSE server synchronously with timeout."""
    async def _run():
        return await asyncio.wait_for(_fetch_mcp_tools_async(url, auth_token), timeout=timeout)
    return asyncio.run(_run())

@login_required(login_url='/login/')
def get_mcp_server(request):
    """Retrieve the user's active MCP server and cached tools."""
    server = UserMCPServer.objects.filter(user=request.user).first()
    if not server:
        return JsonResponse({
            "status": "success",
            "has_server": False,
            "server": None
        })
    return JsonResponse({
        "status": "success",
        "has_server": True,
        "server": server.to_dict()
    })

@login_required(login_url='/login/')
def save_mcp_server(request):
    """Save or update external MCP server configuration."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
        server = UserMCPServer.objects.filter(user=request.user).first()
        if not server:
            server = UserMCPServer(user=request.user)

        if 'name' in data and data['name'].strip():
            server.name = data['name'].strip()
        if 'server_url' in data and data['server_url'].strip():
            server.server_url = data['server_url'].strip()
        if 'auth_token' in data:
            server.auth_token = data['auth_token'].strip()
        if 'is_active' in data:
            server.is_active = bool(data['is_active'])

        server.save()
        return JsonResponse({
            "status": "success",
            "message": "تم حفظ بيانات خادم MCP بنجاح.",
            "server": server.to_dict()
        })
    except Exception as e:
        logger.error(f"Error saving MCP server: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=400)

@login_required(login_url='/login/')
def sync_mcp_server(request):
    """Test connection to MCP SSE server, fetch tools/list, and update cache."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    server = UserMCPServer.objects.filter(user=request.user).first()
    if not server:
        return JsonResponse({"status": "error", "message": "لا يوجد خادم MCP مسجل للفحص. يرجى إضافة خادم أولاً."}, status=404)

    try:
        tools = fetch_mcp_tools_sync(server.server_url, server.auth_token, timeout=6.0)
        server.cached_tools = tools
        server.last_synced_at = timezone.now()
        server.is_active = True
        server.save()

        return JsonResponse({
            "status": "success",
            "message": f"تم الاتصال بنجاح بخادم FastMCP! تم اكتشاف {len(tools)} أداة.",
            "tools": tools,
            "server": server.to_dict()
        })
    except Exception as e:
        logger.error(f"Error syncing MCP server {server.server_url}: {e}")
        return JsonResponse({
            "status": "error",
            "message": f"فشل الاتصال بخادم MCP على '{server.server_url}': {str(e)}"
        }, status=400)

@login_required(login_url='/login/')
def toggle_mcp_server(request):
    """Toggle active state of the user's MCP server."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    server = UserMCPServer.objects.filter(user=request.user).first()
    if not server:
        return JsonResponse({"status": "error", "message": "لا يوجد خادم MCP مسجل."}, status=404)

    server.is_active = not server.is_active
    server.save()
    status_text = "تفعيل" if server.is_active else "تعطيل"
    return JsonResponse({
        "status": "success",
        "is_active": server.is_active,
        "message": f"تم {status_text} خادم MCP بنجاح."
    })

@login_required(login_url='/login/')
def delete_mcp_server(request):
    """Delete external MCP server configuration for the user."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    count, _ = UserMCPServer.objects.filter(user=request.user).delete()
    if count == 0:
        return JsonResponse({"status": "error", "message": "لا يوجد خادم MCP لحذفه."}, status=404)

    return JsonResponse({
        "status": "success",
        "message": "تم حذف خادم MCP وجميع أدواته بنجاح."
    })

@login_required(login_url='/login/')
def get_customer_memory(request):
    """Retrieve the current customer memory card and recent call history."""
    memory, _ = CustomerMemory.objects.get_or_create(user=request.user)
    recent_calls = CallSession.objects.filter(user=request.user)[:5]
    return JsonResponse({
        "status": "success",
        "memory": memory.to_dict(),
        "recent_calls": [c.to_dict() for c in recent_calls]
    })

@login_required(login_url='/login/')
def reset_customer_memory(request):
    """Reset customer memory (both permanent profile and working memory)."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    memory, _ = CustomerMemory.objects.get_or_create(user=request.user)
    memory.permanent_profile = {}
    memory.last_interaction_summary = ""
    memory.last_interaction_at = None
    memory.save()
    return JsonResponse({
        "status": "success",
        "message": "تمت إعادة تعيين ذاكرة العميل بنجاح.",
        "memory": memory.to_dict()
    })


# ==================== Call Queues & Routing Management ====================

async def _async_create_queue_trunk_and_rule(queue_name, queue_code, user_id):
    lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        trunk_req = api.CreateSIPInboundTrunkRequest(
            trunk=api.SIPInboundTrunkInfo(
                name=f"Queue {queue_code} - {queue_name} (User {user_id})",
                numbers=[str(queue_code)],
                allowed_numbers=[str(queue_code)],
            )
        )
        created_trunk = await lk.sip.create_sip_inbound_trunk(trunk_req)
        trunk_id = created_trunk.sip_trunk_id

        rule_req = api.CreateSIPDispatchRuleRequest(
            name=f"Rule for Queue {queue_code} - User {user_id}",
            trunk_ids=[trunk_id],
            rule=api.SIPDispatchRule(
                dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                    room_prefix=f"room_user_{user_id}_queue_{queue_code}_"
                )
            )
        )
        created_rule = await lk.sip.create_sip_dispatch_rule(rule_req)
        rule_id = created_rule.sip_dispatch_rule_id
        return trunk_id, rule_id
    finally:
        await lk.aclose()

@login_required(login_url='/login/')
def list_call_queues(request):
    """List all call queues for authenticated user with live presence and waiting metrics."""
    queues = CallQueue.objects.filter(user=request.user).prefetch_related('memberships__sip_account')
    r = None
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
    except Exception:
        pass

    results = []
    for q in queues:
        q_dict = q.to_dict()
        waiting_count = 0
        if r:
            try:
                waiting_count = r.llen(f"queue:{q.code}:waiting")
            except Exception:
                pass
        q_dict["waiting_calls_count"] = waiting_count

        for m in q_dict["members"]:
            state = "AVAILABLE"
            if r:
                try:
                    s = r.get(f"agent_state:{m['sip_username']}")
                    if s:
                        state = s.decode() if isinstance(s, bytes) else str(s)
                except Exception:
                    pass
            m["presence_state"] = state
        results.append(q_dict)

    return JsonResponse({
        "status": "success",
        "queues": results
    })

@login_required(login_url='/login/')
def create_call_queue(request):
    """Create a new CallQueue, assign members, upload hold music, and register with LiveKit."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    try:
        name = request.POST.get('name', '').strip() or "طابور المبيعات"
        code = request.POST.get('code', '').strip()
        strategy = request.POST.get('strategy', 'round_robin').strip()
        ring_timeout = int(request.POST.get('ring_timeout_seconds', 15))
        total_timeout = int(request.POST.get('total_timeout_seconds', 60))
        fallback_action = request.POST.get('fallback_action', 'ai_assistant')

        if not code or not code.isdigit():
            return JsonResponse({"status": "error", "message": "يجب إدخال كود رقمي صحيح للطابور (مثل 200 أو 300)"}, status=400)

        if CallQueue.objects.filter(user=request.user, code=code).exists():
            return JsonResponse({"status": "error", "message": f"كود الطابور {code} مستخدم بالفعل لهذا الحساب"}, status=400)

        hold_music_file = request.FILES.get('hold_music')

        import asyncio
        trunk_id, rule_id = asyncio.run(_async_create_queue_trunk_and_rule(
            queue_name=name,
            queue_code=code,
            user_id=request.user.id
        ))

        queue = CallQueue.objects.create(
            user=request.user,
            name=name,
            code=code,
            strategy=strategy,
            ring_timeout_seconds=ring_timeout,
            total_timeout_seconds=total_timeout,
            hold_music=hold_music_file,
            fallback_action=fallback_action,
            livekit_trunk_id=trunk_id,
            livekit_rule_id=rule_id,
            is_active=True
        )

        member_ids_raw = request.POST.getlist('member_ids') or request.POST.get('member_ids', '')
        if isinstance(member_ids_raw, str) and member_ids_raw:
            try:
                member_ids = json.loads(member_ids_raw)
            except Exception:
                member_ids = [int(x.strip()) for x in member_ids_raw.split(',') if x.strip().isdigit()]
        else:
            member_ids = [int(x) for x in member_ids_raw if str(x).isdigit()]

        valid_employees = EmployeeProfile.objects.filter(id__in=member_ids, is_active=True)
        for idx, emp in enumerate(valid_employees):
            QueueMembership.objects.create(
                queue=queue,
                employee=emp,
                order=idx,
                is_active=True
            )

        return JsonResponse({
            "status": "success",
            "message": f"تم إنشاء الطابور '{name}' (كود: {code}) بنجاح.",
            "queue": queue.to_dict()
        }, status=201)

    except Exception as e:
        logger.error(f"Error creating CallQueue: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"فشل إنشاء الطابور: {str(e)}"}, status=500)

@login_required(login_url='/login/')
def delete_call_queue(request, queue_id):
    """Delete a CallQueue from DB and LiveKit."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    queue = get_object_or_404(CallQueue, id=queue_id, user=request.user)
    try:
        import asyncio
        asyncio.run(_async_delete_sip_trunk_and_rule(queue.livekit_trunk_id, queue.livekit_rule_id))
    except Exception as e:
        logger.warning(f"Error deleting queue LiveKit trunk/rule: {e}")

    if queue.hold_music:
        try:
            queue.hold_music.delete(save=False)
        except Exception:
            pass

    queue_name = queue.name
    queue_code = queue.code
    queue.delete()
    return JsonResponse({
        "status": "success",
        "message": f"تم حذف الطابور '{queue_name}' (كود: {queue_code}) بنجاح."
    })


# ==================== Outbound SIP Trunk & Calling Engine ====================

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

        import asyncio
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
        import asyncio
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
        import asyncio
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




# ==================== Employee WebRTC & Auth APIs ====================

JWT_SECRET = getattr(settings, 'SECRET_KEY', 'default_secret_key')

def generate_employee_jwt(employee: EmployeeProfile):
    payload = {
        "user_id": employee.user_id,
        "username": employee.user.username,
        "employee_id": employee.id,
        "extension": employee.extension,
        "exp": int(time.time()) + (30 * 24 * 3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def get_employee_from_token(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        # Check query param for fallback
        token_str = request.GET.get("token")
        if not token_str:
            return None
    else:
        token_str = auth_header.split("Bearer ")[1].strip()

    try:
        payload = jwt.decode(token_str, JWT_SECRET, algorithms=["HS256"])
        return EmployeeProfile.objects.select_related('user').filter(id=payload.get("employee_id"), is_active=True).first()
    except Exception as e:
        logger.warning(f"Invalid employee JWT: {e}")
        return None

def generate_centrifugo_token_for_employee(employee: EmployeeProfile):
    centrifugo_payload = {
        "sub": f"employee_{employee.id}_{employee.extension}",
        "exp": int(time.time()) + (30 * 24 * 3600),
        "info": {
            "id": employee.id,
            "name": employee.display_name,
            "extension": employee.extension,
            "department": employee.department,
        }
    }
    return jwt.encode(centrifugo_payload, settings.CENTRIFUGO_SECRET, algorithm="HS256")


@csrf_exempt
def api_employee_login(request):
    """Authenticate employee by username or extension and return JWT & Centrifugo tokens."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        identifier = str(data.get('identifier') or data.get('username') or data.get('extension') or '').strip()
        password = str(data.get('password') or '').strip()

        if not identifier or not password:
            return JsonResponse({"status": "error", "message": "يرجى إدخال اسم المستخدم أو التحويلة وكلمة المرور"}, status=400)

        # 1. Try to find user by extension first
        emp = EmployeeProfile.objects.select_related('user').filter(extension=identifier).first()
        username = emp.user.username if emp else identifier

        # 2. Authenticate
        user = authenticate(request, username=username, password=password)
        if not user:
            return JsonResponse({"status": "error", "message": "بيانات الدخول غير صحيحة (اسم المستخدم/التحويلة أو كلمة المرور خطأ)"}, status=401)

        # 3. Fetch or auto-create EmployeeProfile
        employee = EmployeeProfile.objects.filter(user=user).first()
        if not employee:
            ext = str(100 + user.id)
            employee = EmployeeProfile.objects.create(
                user=user,
                extension=ext,
                display_name=user.get_full_name() or user.username,
                department="المبيعات" if user.id % 2 != 0 else "خدمة العملاء",
                status="ready"
            )
        else:
            employee.status = "ready"
            employee.save(update_fields=['status'])

        # 4. Generate Tokens
        app_token = generate_employee_jwt(employee)
        centrifugo_token = generate_centrifugo_token_for_employee(employee)

        # Broadcast status change
        publish_to_centrifugo("employees:presence", {
            "event": "status_change",
            "employee": employee.to_dict()
        })

        return JsonResponse({
            "status": "success",
            "token": app_token,
            "employee": employee.to_dict(),
            "centrifugo": {
                "ws_url": settings.CENTRIFUGO_WS_URL,
                "token": centrifugo_token,
                "channel": f"employee:{employee.id}"
            }
        })

    except Exception as e:
        logger.error(f"Error in api_employee_login: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def api_employee_me(request):
    """Get current authenticated employee profile."""
    employee = get_employee_from_token(request)
    if not employee:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    centrifugo_token = generate_centrifugo_token_for_employee(employee)
    return JsonResponse({
        "status": "success",
        "employee": employee.to_dict(),
        "centrifugo": {
            "ws_url": settings.CENTRIFUGO_WS_URL,
            "token": centrifugo_token,
            "channel": f"employee:{employee.id}"
        }
    })


@csrf_exempt
def api_list_employees(request):
    """List all employees and active call queues for the internal directory."""
    employee = get_employee_from_token(request)
    if not employee and not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    if employee:
        employees = EmployeeProfile.objects.filter(is_active=True).exclude(id=employee.id).order_by('extension')
        current_emp_data = employee.to_dict()
    else:
        employees = EmployeeProfile.objects.filter(is_active=True).order_by('extension')
        current_emp_data = None

    queues = CallQueue.objects.filter(is_active=True).order_by('code')

    return JsonResponse({
        "status": "success",
        "current_employee": current_emp_data,
        "employees": [e.to_dict() for e in employees],
        "queues": [q.to_dict() for q in queues]
    })


@csrf_exempt
def api_create_employee(request):
    """Create a new employee profile and user account from dashboard or API."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    if not request.user.is_authenticated and not get_employee_from_token(request):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        display_name = str(data.get('display_name') or '').strip()
        username = str(data.get('username') or '').strip()
        extension = str(data.get('extension') or '').strip()
        department = str(data.get('department') or 'المبيعات').strip()
        password = str(data.get('password') or 'password123').strip()

        if not display_name or not username or not extension:
            return JsonResponse({"status": "error", "message": "الاسم واسم المستخدم ورقم التحويلة حقول مطلوبة"}, status=400)

        if EmployeeProfile.objects.filter(extension=extension).exists():
            return JsonResponse({"status": "error", "message": f"رقم التحويلة '{extension}' مسجل بالفعل لموظف آخر"}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({"status": "error", "message": f"اسم المستخدم '{username}' مسجل بالفعل"}, status=400)

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=display_name
        )

        employee = EmployeeProfile.objects.create(
            user=user,
            extension=extension,
            display_name=display_name,
            department=department,
            status='ready',
            avatar_url=f"https://api.dicebear.com/7.x/bottts/png?seed={extension}"
        )

        publish_to_centrifugo("employees:presence", {
            "event": "employee_created",
            "employee": employee.to_dict()
        })

        return JsonResponse({
            "status": "success",
            "message": f"تم إنشاء حساب الموظف '{display_name}' (تحويلة {extension}) بنجاح",
            "employee": employee.to_dict()
        }, status=201)

    except Exception as e:
        logger.error(f"Error creating employee: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def api_delete_employee(request, employee_id):
    """Delete an employee and their associated user account."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    if not request.user.is_authenticated and not get_employee_from_token(request):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        employee = EmployeeProfile.objects.filter(id=employee_id).first()
        if not employee:
            return JsonResponse({"status": "error", "message": "الموظف غير موجود"}, status=404)

        name = employee.display_name
        ext = employee.extension
        user = employee.user

        user.delete()

        publish_to_centrifugo("employees:presence", {
            "event": "employee_deleted",
            "employee_id": employee_id,
            "extension": ext
        })

        return JsonResponse({
            "status": "success",
            "message": f"تم حذف الموظف '{name}' (تحويلة {ext}) بنجاح"
        })

    except Exception as e:
        logger.error(f"Error deleting employee: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def api_update_employee_status(request):
    """Update employee status (ready, break, busy)."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    employee = get_employee_from_token(request)
    if not employee:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        new_status = data.get('status', 'ready')
        if new_status in ['ready', 'break', 'busy', 'offline']:
            employee.status = new_status
            employee.save(update_fields=['status'])

            publish_to_centrifugo("employees:presence", {
                "event": "status_change",
                "employee": employee.to_dict()
            })

            return JsonResponse({"status": "success", "employee": employee.to_dict()})
        else:
            return JsonResponse({"status": "error", "message": "Invalid status value"}, status=400)

    except Exception as e:
        logger.error(f"Error in api_update_employee_status: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def api_dial_call(request):
    """Initiate an internal WebRTC call to an employee extension or a Call Queue."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    caller = get_employee_from_token(request)
    if not caller:
        if request.user.is_authenticated:
            caller = EmployeeProfile.objects.filter(user=request.user).first()
            if not caller:
                caller = EmployeeProfile.objects.create(
                    user=request.user,
                    extension=f"99{request.user.id}",
                    display_name=request.user.get_full_name() or request.user.username or "المشرف (لوحة التحكم)",
                    department="الإدارة",
                    status="ready"
                )
        else:
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        target = str(data.get('target', '')).strip()

        if not target:
            return JsonResponse({"status": "error", "message": "يرجى تحديد رقم التحويلة أو كود الطابور للاتصال"}, status=400)

        # 1. Check if target is a CallQueue
        queue = CallQueue.objects.filter(code=target, is_active=True).first()
        if queue:
            room_name = f"queue_{queue.code}_{uuid.uuid4().hex[:6]}"

            # Generate caller LiveKit Token
            token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
                .with_identity(f"employee_{caller.id}_{caller.extension}") \
                .with_name(caller.display_name) \
                .with_metadata(json.dumps({"role": "caller", "employee_id": caller.id})) \
                .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            caller_jwt = token.to_jwt()

            # Broadcast incoming call to queue members
            members = queue.memberships.filter(is_active=True).select_related('employee')
            notified_count = 0
            for m in members:
                if m.employee and m.employee.id != caller.id and m.employee.status == 'ready':
                    publish_to_centrifugo(f"employee:{m.employee.id}", {
                        "event": "incoming_call",
                        "room_name": room_name,
                        "caller_name": caller.display_name,
                        "caller_extension": caller.extension,
                        "caller_department": caller.department,
                        "queue_name": queue.name,
                        "queue_code": queue.code,
                        "call_type": "queue"
                    })
                    notified_count += 1

            return JsonResponse({
                "status": "success",
                "call_type": "queue",
                "room_name": room_name,
                "target_name": queue.name,
                "target_number": queue.code,
                "livekit_url": settings.LIVEKIT_URL,
                "livekit_token": caller_jwt,
                "notified_agents": notified_count
            })

        # 2. Check if target is an Employee Extension
        callee = EmployeeProfile.objects.filter(extension=target, is_active=True).first()
        if callee:
            if callee.id == caller.id:
                return JsonResponse({"status": "error", "message": "لا يمكنك الاتصال بتحويلتك الشخصية"}, status=400)

            room_name = f"call_ext_{caller.extension}_{callee.extension}_{uuid.uuid4().hex[:6]}"

            # Generate caller LiveKit Token
            token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
                .with_identity(f"employee_{caller.id}_{caller.extension}") \
                .with_name(caller.display_name) \
                .with_metadata(json.dumps({"role": "caller", "employee_id": caller.id})) \
                .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            caller_jwt = token.to_jwt()

            # Send incoming call event to callee via Centrifugo
            publish_to_centrifugo(f"employee:{callee.id}", {
                "event": "incoming_call",
                "room_name": room_name,
                "caller_name": caller.display_name,
                "caller_extension": caller.extension,
                "caller_department": caller.department,
                "call_type": "direct_internal"
            })

            return JsonResponse({
                "status": "success",
                "call_type": "direct_internal",
                "room_name": room_name,
                "target_name": callee.display_name,
                "target_number": callee.extension,
                "target_status": callee.status,
                "livekit_url": settings.LIVEKIT_URL,
                "livekit_token": caller_jwt
            })

        # 3. Check if target is an External Phone Number (PSTN via OutboundSIPTrunk)
        cleaned_phone = re.sub(r'[^\d+]', '', target)
        if len(cleaned_phone) >= 7:
            trunk = OutboundSIPTrunk.objects.filter(is_active=True).first()
            if not trunk or not trunk.livekit_outbound_trunk_id:
                return JsonResponse({
                    "status": "error",
                    "message": "لا يوجد خط SIP Trunk خارجي مفعل. يرجى إعداد بيانات المزود الخارجي أولاً."
                }, status=400)

            room_name = f"pstn_out_{caller.extension}_{uuid.uuid4().hex[:6]}"

            # Generate caller WebRTC token
            token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
                .with_identity(f"employee_{caller.id}_{caller.extension}") \
                .with_name(caller.display_name) \
                .with_metadata(json.dumps({"role": "caller", "employee_id": caller.id, "phone": cleaned_phone})) \
                .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            caller_jwt = token.to_jwt()

            # Record call session
            CallSession.objects.create(
                user=caller.user,
                room_name=room_name,
                direction='outbound_agent',
                destination_phone=cleaned_phone,
                call_goal=f"مكالمة موظف ({caller.display_name}) لرقم العميل {cleaned_phone}"
            )

            # Dial customer via LiveKit Outbound Trunk
            import asyncio
            async def _dial_external_customer():
                lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
                try:
                    dial_req = api.CreateSIPParticipantRequest(
                        sip_trunk_id=trunk.livekit_outbound_trunk_id,
                        sip_call_to=cleaned_phone,
                        room_name=room_name,
                        participant_identity=f"customer_{cleaned_phone}",
                        participant_name=f"Customer {cleaned_phone}",
                        play_ringtone=True,
                    )
                    await lk.sip.create_sip_participant(dial_req)
                finally:
                    await lk.aclose()

            try:
                asyncio.run(_dial_external_customer())
            except Exception as e:
                logger.error(f"Failed to dial external customer via SIP trunk: {e}")

            return JsonResponse({
                "status": "success",
                "call_type": "external_pstn",
                "room_name": room_name,
                "target_name": f"عميل خارجي ({cleaned_phone})",
                "target_number": cleaned_phone,
                "livekit_url": settings.LIVEKIT_URL,
                "livekit_token": caller_jwt
            })

        return JsonResponse({"status": "error", "message": f"التحويلة أو كود الطابور '{target}' غير موجود"}, status=404)

    except Exception as e:
        logger.error(f"Error in api_dial_call: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def api_get_call_token(request):
    """Generate LiveKit token for callee to answer and join an active WebRTC room."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    employee = get_employee_from_token(request)
    if not employee:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        room_name = data.get('room_name')
        if not room_name:
            return JsonResponse({"status": "error", "message": "room_name مطلوب"}, status=400)

        token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
            .with_identity(f"employee_{employee.id}_{employee.extension}") \
            .with_name(employee.display_name) \
            .with_metadata(json.dumps({"role": "callee", "employee_id": employee.id})) \
            .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
        callee_jwt = token.to_jwt()

        # Notify room or caller that call was accepted
        publish_to_centrifugo("queues:broadcast", {
            "event": "call_accepted",
            "room_name": room_name,
            "accepted_by": employee.to_dict()
        })

        return JsonResponse({
            "status": "success",
            "room_name": room_name,
            "livekit_url": settings.LIVEKIT_URL,
            "livekit_token": callee_jwt
        })

    except Exception as e:
        logger.error(f"Error in api_get_call_token: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def api_hangup_call(request):
    """Signal call hangup/end to room participants and delete LiveKit room."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    employee = get_employee_from_token(request)
    caller_name = "المشرف"
    if not employee:
        if request.user.is_authenticated:
            caller_name = request.user.get_full_name() or request.user.username or "المشرف (لوحة التحكم)"
        else:
            return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)
    else:
        caller_name = employee.display_name

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        room_name = data.get('room_name')
        target_employee_id = data.get('target_employee_id')

        # 1. Direct peer employee channel notification if explicitly provided
        if target_employee_id:
            publish_to_centrifugo(f"employee:{target_employee_id}", {
                "event": "call_ended",
                "room_name": room_name,
                "ended_by": caller_name
            })

        # 2. Extract peers for internal employee-to-employee calls (call_ext_{ext1}_{ext2}_{uuid})
        if room_name and room_name.startswith("call_ext_"):
            parts = room_name.split("_")
            if len(parts) >= 4:
                ext1, ext2 = parts[2], parts[3]
                peers = EmployeeProfile.objects.filter(extension__in=[ext1, ext2], is_active=True)
                for peer in peers:
                    publish_to_centrifugo(f"employee:{peer.id}", {
                        "event": "call_ended",
                        "room_name": room_name,
                        "ended_by": caller_name
                    })

        # 3. Extract queue members if queue call (queue_{code}_{uuid})
        if room_name and room_name.startswith("queue_"):
            parts = room_name.split("_")
            if len(parts) >= 2:
                q_code = parts[1]
                queue = CallQueue.objects.filter(code=q_code, is_active=True).first()
                if queue:
                    for m in queue.memberships.filter(is_active=True).select_related('employee'):
                        if m.employee:
                            publish_to_centrifugo(f"employee:{m.employee.id}", {
                                "event": "call_ended",
                                "room_name": room_name,
                                "ended_by": caller_name
                            })

        # 4. Broadcast on global queues channel
        publish_to_centrifugo("queues:broadcast", {
            "event": "call_ended",
            "room_name": room_name,
            "ended_by": caller_name
        })

        # 5. Clean up and delete room on LiveKit server
        if room_name:
            import asyncio
            async def _delete_livekit_room():
                try:
                    lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
                    await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
                    await lk.aclose()
                except Exception as lk_err:
                    logger.debug(f"LiveKit room deletion note: {lk_err}")

            try:
                asyncio.run(_delete_livekit_room())
            except Exception as e:
                logger.warning(f"Failed to delete LiveKit room {room_name}: {e}")

        return JsonResponse({"status": "success", "message": "Call hung up and room cleaned up"})

    except Exception as e:
        logger.error(f"Error in api_hangup_call: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)




