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

from .models import Document, DocumentChunk, UserAction
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

    # 1. Generate LiveKit Token with user metadata
    metadata = json.dumps({
        "user_id": request.user.id,
        "username": request.user.username
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
            # Extract user_id from participant metadata or identity
            user_id = None
            if event.participant.metadata:
                try:
                    meta = json.loads(event.participant.metadata)
                    user_id = meta.get("user_id")
                except Exception:
                    pass

            if not user_id and participant_identity.startswith("user_"):
                parts = participant_identity.split("_")
                if len(parts) >= 2 and parts[1].isdigit():
                    user_id = int(parts[1])

            logger.info(f"Human participant '{participant_identity}' (user_id={user_id}) joined room {room_name}. Queuing Voice Agent...")
            publish_to_centrifugo(channel, {
                "event": "agent_queued",
                "message": "تم رصد انضمام المستخدم. جاري استدعاء المساعد الصوتي وتجهيز قاعدة المستندات...",
                "timestamp": time.time(),
            })

            # Dispatch to standalone Agent service via Redis queue with user_id
            try:
                r = redis.Redis.from_url(settings.REDIS_URL)
                job_payload = json.dumps({
                    "room_name": room_name,
                    "user_id": user_id
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
