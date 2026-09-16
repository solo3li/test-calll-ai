import json
import logging
import datetime
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .models import CustomerMemory, CallSession

logger = logging.getLogger(__name__)

def verify_internal_api_key(request) -> bool:
    api_key = request.headers.get('X-Internal-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    expected_key = getattr(settings, 'INTERNAL_API_KEY', 'voice-internal-secret-token-key-12345')
    return bool(api_key and api_key == expected_key)


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


# ==================== Internal Agent Call Completion & Memory API ====================

@csrf_exempt
def api_internal_save_call_session_and_memory(request):
    """
    Internal API called by Voice Agent upon call completion to persist
    the CallSession details and update CustomerMemory using Django ORM.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    if not verify_internal_api_key(request):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        user_id = data.get('user_id')
        room_name = data.get('room_name')
        if not user_id or not room_name:
            return JsonResponse({"status": "error", "message": "user_id and room_name are required"}, status=400)

        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"status": "error", "message": f"User {user_id} not found"}, status=404)

        duration_seconds = int(data.get('duration_seconds', 0))
        direction = data.get('direction', 'inbound')
        destination_phone = str(data.get('destination_phone') or '')
        call_goal = str(data.get('call_goal') or '')
        transcript_text = str(data.get('transcript_text') or '')
        summary = str(data.get('summary') or '')
        permanent_profile = data.get('permanent_profile')

        now_dt = datetime.datetime.now(datetime.timezone.utc)

        # 1. Update existing CallSession (e.g. created by outbound dialer) or create a new record
        session = CallSession.objects.filter(room_name=room_name).first()
        if session:
            session.ended_at = now_dt
            session.duration_seconds = duration_seconds
            session.transcript_text = transcript_text
            session.summary = summary
            session.save(update_fields=['ended_at', 'duration_seconds', 'transcript_text', 'summary'])
        else:
            session = CallSession.objects.create(
                user=user,
                room_name=room_name,
                direction=direction,
                destination_phone=destination_phone,
                call_goal=call_goal,
                ended_at=now_dt,
                duration_seconds=duration_seconds,
                transcript_text=transcript_text,
                summary=summary
            )

        # 2. Upsert CustomerMemory
        memory, _ = CustomerMemory.objects.get_or_create(user=user)
        if permanent_profile is not None:
            if isinstance(permanent_profile, dict):
                memory.permanent_profile = permanent_profile
            elif isinstance(permanent_profile, str):
                try:
                    memory.permanent_profile = json.loads(permanent_profile)
                except Exception:
                    pass
        if summary:
            memory.last_interaction_summary = summary
        memory.last_interaction_at = now_dt
        memory.total_calls_count = (memory.total_calls_count or 0) + 1
        memory.save()

        logger.info(f"Successfully saved CallSession #{session.id} and updated CustomerMemory for user #{user.id}")

        return JsonResponse({
            "status": "success",
            "session_id": session.id,
            "total_calls_count": memory.total_calls_count
        })

    except Exception as e:
        logger.error(f"Error saving CallSession and memory: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
