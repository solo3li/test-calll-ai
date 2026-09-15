import json
import logging
import time
import uuid
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

from .models import Document, DocumentChunk, UserAction, AgentProfile, UserMCPServer, CustomerMemory, CallSession, UserSIPAccount
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

            # Resolve active profile if not provided in metadata
            if user_id and not profile:
                active_prof = AgentProfile.objects.filter(user_id=user_id, is_active=True).first()
                if active_prof:
                    profile = active_prof.to_dict()

            logger.info(f"Human participant '{participant_identity}' (user_id={user_id}) joined room {room_name}. Queuing Voice Agent...")
            publish_to_centrifugo(channel, {
                "event": "agent_queued",
                "message": "تم رصد انضمام المستخدم. جاري استدعاء المساعد الصوتي وتجهيز قاعدة المستندات...",
                "timestamp": time.time(),
            })

            # Dispatch to standalone Agent service via Redis queue with user_id and profile
            try:
                r = redis.Redis.from_url(settings.REDIS_URL)
                job_payload = json.dumps({
                    "room_name": room_name,
                    "user_id": user_id,
                    "profile": profile
                })
                r.rpush("agent_jobs", job_payload)
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

# ==================== LiveKit SIP & MicroSIP Management ====================

async def _async_create_sip_trunk_and_rule(username, password, user_id, line_name, extension):
    lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        trunk_info = api.SIPInboundTrunkInfo(
            name=f"{line_name} (User {user_id})",
            auth_username=username,
            auth_password=password,
            numbers=[str(extension), str(username)]
        )
        created_trunk = await lk.sip.create_sip_inbound_trunk(api.CreateSIPInboundTrunkRequest(trunk=trunk_info))
        trunk_id = created_trunk.sip_trunk_id

        rule_individual = api.SIPDispatchRuleIndividual(room_prefix=f"room_user_{user_id}_sip_")
        rule = api.SIPDispatchRule(dispatch_rule_individual=rule_individual)
        rule_req = api.CreateSIPDispatchRuleRequest(
            name=f"Rule for User {user_id} - {username}",
            rule=rule,
            trunk_ids=[trunk_id]
        )
        created_rule = await lk.sip.create_sip_dispatch_rule(rule_req)
        rule_id = created_rule.sip_dispatch_rule_id
        return trunk_id, rule_id
    finally:
        await lk.aclose()

async def _async_delete_sip_trunk_and_rule(trunk_id, rule_id):
    lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        if rule_id:
            try:
                await lk.sip.delete_sip_dispatch_rule(api.DeleteSIPDispatchRuleRequest(sip_dispatch_rule_id=rule_id))
            except Exception as e:
                logger.warning(f"Error deleting LiveKit SIP dispatch rule {rule_id}: {e}")
        if trunk_id:
            try:
                await lk.sip.delete_sip_trunk(api.DeleteSIPTrunkRequest(sip_trunk_id=trunk_id))
            except Exception as e:
                logger.warning(f"Error deleting LiveKit SIP trunk {trunk_id}: {e}")
    finally:
        await lk.aclose()

@login_required(login_url='/login/')
def list_sip_accounts(request):
    """List all SIP lines for the authenticated user."""
    accounts = UserSIPAccount.objects.filter(user=request.user)
    return JsonResponse({
        "status": "success",
        "accounts": [a.to_dict() for a in accounts],
        "server_info": {
            "sip_server": "127.0.0.1:5060",
            "sip_domain": "127.0.0.1",
            "sip_port": 5060,
        }
    })

@login_required(login_url='/login/')
def create_sip_account(request):
    """Create a new SIP trunk and dispatch rule in LiveKit and save to DB."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        name = data.get('name', '').strip() or f"خط MicroSIP #{UserSIPAccount.objects.filter(user=request.user).count() + 1}"
        
        # Generate unique SIP username and password
        unique_suffix = uuid.uuid4().hex[:6]
        sip_username = f"sip_u{request.user.id}_{unique_suffix}"
        sip_password = f"Pass_{uuid.uuid4().hex[:10]}"

        # Auto-assign clean extension number starting from 1001
        last_acc = UserSIPAccount.objects.order_by('-id').first()
        next_ext = (1000 + (last_acc.id if last_acc else 0) + 1)
        extension = str(next_ext)

        import asyncio
        trunk_id, rule_id = asyncio.run(_async_create_sip_trunk_and_rule(
            username=sip_username,
            password=sip_password,
            user_id=request.user.id,
            line_name=name,
            extension=extension
        ))

        account = UserSIPAccount.objects.create(
            user=request.user,
            name=name,
            sip_username=sip_username,
            sip_password=sip_password,
            livekit_trunk_id=trunk_id,
            livekit_rule_id=rule_id,
            is_active=True
        )

        return JsonResponse({
            "status": "success",
            "message": f"تم إنشاء خط SIP بنجاح: {name}",
            "account": account.to_dict(),
            "config": {
                "account_name": name,
                "sip_server": "127.0.0.1:5060",
                "sip_proxy": "127.0.0.1:5060",
                "username": sip_username,
                "domain": "127.0.0.1",
                "login": sip_username,
                "password": sip_password,
                "extension": extension,
                "instructions": f"في MicroSIP: اضغط Add Account وأدخل البيانات، ثم ألغِ تحديد خيار (Register with domain) و (Publish Presence) واضغط Save. يمكنك الاتصال بطلب الرقم {extension} أو {sip_username} للحديث مع الـ AI."
            }
        }, status=201)

    except Exception as e:
        logger.error(f"Error creating SIP account: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"فشل إنشاء خط SIP: {str(e)}"}, status=500)

@login_required(login_url='/login/')
def delete_sip_account(request, account_id):
    """Delete SIP line from LiveKit and database."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    account = get_object_or_404(UserSIPAccount, id=account_id, user=request.user)
    try:
        import asyncio
        asyncio.run(_async_delete_sip_trunk_and_rule(account.livekit_trunk_id, account.livekit_rule_id))
    except Exception as e:
        logger.warning(f"Failed to delete LiveKit trunk/rule: {e}")

    account.delete()
    return JsonResponse({
        "status": "success",
        "message": f"تم حذف خط SIP '{account.name}' بنجاح."
    })

