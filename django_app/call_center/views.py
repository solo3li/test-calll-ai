import re
import time
import json
import uuid
import logging
import requests
import jwt
import redis
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from livekit import api

from .models import EmployeeProfile, CallQueue, QueueMembership

logger = logging.getLogger(__name__)

JWT_SECRET = getattr(settings, 'SECRET_KEY', 'default_secret_key')

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

# ==================== Auth & Profile APIs ====================

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
    """Return profile and Centrifugo credentials for the authenticated employee."""
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

# ==================== Employee Directory APIs ====================

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
    """Update employee status (ready, break, busy, offline)."""
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

# ==================== Call Queues Management ====================

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
    """List all call queues for authenticated user with waiting metrics."""
    queues = CallQueue.objects.filter(user=request.user).prefetch_related('memberships__employee')
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
        results.append(q_dict)

    return JsonResponse({
        "status": "success",
        "queues": results
    })

@login_required(login_url='/login/')
def create_call_queue(request):
    """Create a new CallQueue and assign members."""
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
            fallback_action=fallback_action,
            hold_music=hold_music_file,
            livekit_trunk_id=trunk_id or '',
            livekit_rule_id=rule_id or '',
            is_active=True
        )

        member_ids = request.POST.getlist('member_ids')
        for order_idx, emp_id in enumerate(member_ids):
            emp = EmployeeProfile.objects.filter(id=emp_id).first()
            if emp:
                QueueMembership.objects.create(
                    queue=queue,
                    employee=emp,
                    order=order_idx,
                    is_active=True
                )

        return JsonResponse({
            "status": "success",
            "message": f"تم إنشاء طابور '{name}' بنجاح وتفعيل الكود {code}.",
            "queue": queue.to_dict()
        }, status=201)

    except Exception as e:
        logger.error(f"Error creating call queue: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"حدث خطأ أثناء إنشاء الطابور: {str(e)}"}, status=400)

@login_required(login_url='/login/')
def delete_call_queue(request, queue_id):
    """Delete a call queue."""
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "طريقة الطلب غير مسموحة"}, status=405)

    queue = get_object_or_404(CallQueue, id=queue_id, user=request.user)
    name = queue.name
    queue.delete()
    return JsonResponse({"status": "success", "message": f"تم حذف الطابور '{name}' بنجاح."})

# ==================== Call Dialing & WebRTC APIs ====================

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

            token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
                .with_identity(f"employee_{caller.id}_{caller.extension}") \
                .with_name(caller.display_name) \
                .with_metadata(json.dumps({"role": "caller", "employee_id": caller.id})) \
                .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            caller_jwt = token.to_jwt()

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

        # 3. Check if target is an External Phone Number (PSTN via telephony app)
        cleaned_phone = re.sub(r'[^\d+]', '', target)
        if len(cleaned_phone) >= 7:
            from telephony.models import OutboundSIPTrunk
            from crm.models import CallSession
            trunk = OutboundSIPTrunk.objects.filter(is_active=True).first()
            if not trunk or not trunk.livekit_outbound_trunk_id:
                return JsonResponse({
                    "status": "error",
                    "message": "لا يوجد خط SIP Trunk خارجي مفعل. يرجى إعداد بيانات المزود الخارجي أولاً."
                }, status=400)

            room_name = f"pstn_out_{caller.extension}_{uuid.uuid4().hex[:6]}"

            token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
                .with_identity(f"employee_{caller.id}_{caller.extension}") \
                .with_name(caller.display_name) \
                .with_metadata(json.dumps({"role": "caller", "employee_id": caller.id, "phone": cleaned_phone})) \
                .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
            caller_jwt = token.to_jwt()

            CallSession.objects.create(
                user=caller.user,
                room_name=room_name,
                direction='outbound_agent',
                destination_phone=cleaned_phone,
                call_goal=f"مكالمة موظف ({caller.display_name}) لرقم العميل {cleaned_phone}"
            )

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

@csrf_exempt
def api_transfer_call(request):
    """
    Handle Call Transfer from an active WebRTC session to another employee or call queue.
    Does NOT terminate the room or drop the customer.
    Pushes transfer job to Redis for agent hold music and rings the target employee.
    """
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    employee = get_employee_from_token(request)
    if not employee:
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
        room_name = data.get('room_name')
        target = str(data.get('target', '')).strip()

        if not room_name or not target:
            return JsonResponse({"status": "error", "message": "room_name و target مطلوبان"}, status=400)

        # Check if target is an employee (search globally across all active employees)
        target_emp = EmployeeProfile.objects.filter(
            extension=target,
            is_active=True
        ).exclude(id=employee.id).first()

        # Or check if target is a call queue (search globally across all active queues)
        target_queue = None
        if not target_emp:
            target_queue = CallQueue.objects.filter(
                code=target,
                is_active=True
            ).first()

        if not target_emp and not target_queue:
            return JsonResponse({"status": "error", "message": f"التحويلة أو الطابور '{target}' غير موجود"}, status=404)

        target_name = target_emp.display_name if target_emp else target_queue.name
        target_type = "employee" if target_emp else "queue"
        target_id = target_emp.id if target_emp else target_queue.id

        # Push to Redis transfer_events queue for the agent service
        r = redis.Redis.from_url(settings.REDIS_URL)
        transfer_payload = {
            "event": "transfer_request",
            "room_name": room_name,
            "from_user": employee.extension,
            "from_name": employee.display_name,
            "from_employee_id": employee.id,
            "target": target,
            "target_type": target_type,
            "target_id": target_id,
            "target_name": target_name,
            "real_target_user": str(target_emp.id) if target_emp else str(target),
            "timestamp": time.time()
        }
        r.rpush("transfer_events", json.dumps(transfer_payload))

        logger.info(f"Initiated call transfer from {employee.extension} to {target} in room {room_name}")

        return JsonResponse({
            "status": "success",
            "message": f"جاري تحويل المكالمة إلى {target_name} ({target})",
            "room_name": room_name,
            "target": target,
            "target_name": target_name,
            "target_type": target_type
        })

    except Exception as e:
        logger.error(f"Error in api_transfer_call: {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

