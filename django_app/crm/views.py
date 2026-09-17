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
def list_customers_memory(request):
    """List all customers (by phone number) for the authenticated user with search."""
    query = request.GET.get('q', '').strip()
    memories = CustomerMemory.objects.filter(user=request.user)
    if query:
        from django.db.models import Q
        memories = memories.filter(
            Q(phone_number__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(last_interaction_summary__icontains=query)
        )
    
    results = [m.to_dict() for m in memories]
    return JsonResponse({
        "status": "success",
        "customers": results,
        "count": len(results)
    })


@login_required(login_url='/login/')
def get_customer_memory(request):
    """Retrieve the customer memory card and recent call history for a specific phone number."""
    phone = request.GET.get('phone', '').strip()
    if not phone:
        # Default to web_dashboard or the most recently updated customer
        latest = CustomerMemory.objects.filter(user=request.user).first()
        phone = latest.phone_number if latest else 'web_dashboard'

    memory, _ = CustomerMemory.objects.get_or_create(user=request.user, phone_number=phone)
    recent_calls = CallSession.objects.filter(user=request.user)
    if phone != 'web_dashboard':
        from django.db.models import Q
        recent_calls = recent_calls.filter(Q(caller_phone=phone) | Q(destination_phone=phone))
    recent_calls = recent_calls[:5]

    return JsonResponse({
        "status": "success",
        "phone_number": phone,
        "memory": memory.to_dict(),
        "recent_calls": [c.to_dict() for c in recent_calls]
    })


@login_required(login_url='/login/')
def reset_customer_memory(request):
    """Reset customer memory for a specific phone number."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    data = json.loads(request.body.decode('utf-8')) if request.body else {}
    phone = (data.get('phone') or request.POST.get('phone') or '').strip()
    if not phone:
        phone = 'web_dashboard'

    memory = CustomerMemory.objects.filter(user=request.user, phone_number=phone).first()
    if memory:
        memory.permanent_profile = {}
        memory.customer_name = ""
        memory.last_interaction_summary = ""
        memory.last_interaction_at = None
        memory.save()
        res_dict = memory.to_dict()
    else:
        res_dict = {}

    return JsonResponse({
        "status": "success",
        "message": f"تمت إعادة تعيين ذاكرة العميل ({phone}) بنجاح.",
        "memory": res_dict
    })


# ==================== Internal Agent Call Completion & Memory API ====================

@csrf_exempt
def api_internal_get_customer_memory(request):
    """Internal API to get customer memory by user_id and caller_phone (supports GET and POST)."""
    if request.method not in ['GET', 'POST']:
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    if not verify_internal_api_key(request):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        user_id = None
        caller_phone = 'web_dashboard'
        if request.method == 'POST':
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            user_id = data.get('user_id') or request.POST.get('user_id')
            raw_phone = str(data.get('caller_phone') or request.POST.get('caller_phone') or 'web_dashboard')
        else:
            user_id = request.GET.get('user_id')
            raw_phone = str(request.GET.get('caller_phone') or 'web_dashboard')

        caller_phone = raw_phone.strip()
        if raw_phone.startswith(' ') and not caller_phone.startswith('+'):
            caller_phone = '+' + caller_phone

        if not user_id:
            return JsonResponse({"status": "error", "message": "user_id is required"}, status=400)

        memory = CustomerMemory.objects.filter(user_id=user_id, phone_number=caller_phone).first()
        if not memory and caller_phone != 'web_dashboard' and len(caller_phone) >= 7:
            suffix = caller_phone[-8:]
            memory = CustomerMemory.objects.filter(user_id=user_id, phone_number__endswith=suffix).first()

        card_text = memory.format_for_system_instruction() if memory else ""
        mem_dict = memory.to_dict() if memory else {
            "phone_number": caller_phone,
            "customer_name": "",
            "permanent_profile": {},
            "last_interaction_summary": "",
            "total_calls_count": 0
        }

        return JsonResponse({
            "status": "success",
            "phone_number": memory.phone_number if memory else caller_phone,
            "card_text": card_text,
            "memory": mem_dict
        })
    except Exception as e:
        logger.error(f"Error in api_internal_get_customer_memory: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def api_internal_save_call_session_and_memory(request):
    """
    Internal API called by Voice Agent upon call completion to persist
    the CallSession details and update CustomerMemory for (user, caller_phone).
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
        caller_phone = str(data.get('caller_phone') or 'web_dashboard').strip()
        destination_phone = str(data.get('destination_phone') or '').strip()
        customer_name = str(data.get('customer_name') or '').strip()
        call_goal = str(data.get('call_goal') or '')
        transcript_text = str(data.get('transcript_text') or '')
        summary = str(data.get('summary') or '')
        permanent_profile = data.get('permanent_profile') or data.get('distilled_profile')

        now_dt = datetime.datetime.now(datetime.timezone.utc)

        # Check if permanent_profile contains extracted phone or name
        if isinstance(permanent_profile, dict):
            extracted_phone = str(permanent_profile.get('phone') or '').strip()
            extracted_name = str(permanent_profile.get('customer_name') or '').strip()
            if extracted_name and not customer_name:
                customer_name = extracted_name
            if extracted_phone and caller_phone in ['web_dashboard', 'anonymous', 'unknown', '']:
                caller_phone = extracted_phone

        # 1. Update existing CallSession (e.g. created by outbound dialer) or create a new record
        session = CallSession.objects.filter(room_name=room_name).first()
        if session:
            session.ended_at = now_dt
            session.duration_seconds = duration_seconds
            session.transcript_text = transcript_text
            session.summary = summary
            if caller_phone:
                session.caller_phone = caller_phone
            if destination_phone:
                session.destination_phone = destination_phone
            session.save(update_fields=['ended_at', 'duration_seconds', 'transcript_text', 'summary', 'caller_phone', 'destination_phone'])
        else:
            session = CallSession.objects.create(
                user=user,
                room_name=room_name,
                direction=direction,
                caller_phone=caller_phone,
                destination_phone=destination_phone,
                call_goal=call_goal,
                ended_at=now_dt,
                duration_seconds=duration_seconds,
                transcript_text=transcript_text,
                summary=summary
            )

        # 2. Upsert CustomerMemory for (user, caller_phone)
        memory, _ = CustomerMemory.objects.get_or_create(user=user, phone_number=caller_phone)
        if customer_name:
            memory.customer_name = customer_name
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

        logger.info(f"Successfully saved CallSession #{session.id} and updated CustomerMemory for ({user.id}, {caller_phone})")

        return JsonResponse({
            "status": "success",
            "session_id": session.id,
            "caller_phone": caller_phone,
            "phone_number": caller_phone,
            "total_calls_count": memory.total_calls_count
        })

    except Exception as e:
        logger.error(f"Error saving CallSession and memory: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
