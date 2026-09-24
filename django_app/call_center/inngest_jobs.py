import os
import json
import time
import uuid
import logging
import datetime
from django.conf import settings
from asgiref.sync import sync_to_async
from livekit import api
import redis
import requests
import inngest

logger = logging.getLogger(__name__)

# Use shared Inngest client pointing to local dev container
inngest_client = inngest.Inngest(
    app_id="voice-ai-call-center",
    api_base_url="http://inngest:8288",
    event_api_base_url="http://inngest:8288",
    is_production=False,
)

def _get_redis():
    return redis.Redis.from_url(settings.REDIS_URL)

def publish_to_centrifugo(channel: str, data: dict):
    """Publish real-time notification to Centrifugo channel."""
    try:
        url = f"{settings.CENTRIFUGO_HTTP_API_URL}/publish"
        headers = {
            "Authorization": f"apikey {settings.CENTRIFUGO_API_KEY}",
            "Content-Type": "application/json",
        }
        res = requests.post(url, json={"channel": channel, "data": data}, headers=headers, timeout=2)
        if res.status_code != 200:
            logger.error(f"Centrifugo publish error ({res.status_code}): {res.text}")
    except Exception as e:
        logger.error(f"Failed to publish to Centrifugo: {e}")

async def delete_livekit_room(room_name: str):
    """Cleanly delete and close LiveKit room on server."""
    if not room_name:
        return
    try:
        lk = api.LiveKitAPI(settings.LIVEKIT_INTERNAL_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        await lk.room.delete_room(api.DeleteRoomRequest(room=room_name))
        await lk.aclose()
        logger.info(f"LiveKit room {room_name} deleted successfully.")
    except Exception as e:
        logger.debug(f"LiveKit room deletion note for {room_name}: {e}")

def generate_livekit_token(room_name: str, identity: str, name: str, metadata: dict = None) -> str:
    """Generate secure LiveKit token for a room."""
    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET) \
        .with_identity(identity) \
        .with_name(name)
    if metadata:
        token = token.with_metadata(json.dumps(metadata))
    token = token.with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
    return token.to_jwt()


def _get_employee_sync(emp_id: int):
    from call_center.models import EmployeeProfile
    return EmployeeProfile.objects.filter(id=emp_id, is_active=True).first()

def _update_employee_status_sync(emp_id: int, status: str):
    from call_center.models import EmployeeProfile
    emp = EmployeeProfile.objects.filter(id=emp_id).first()
    if emp:
        emp.status = status
        emp.save(update_fields=['status'])
        publish_to_centrifugo("employees:presence", {
            "event": "status_change",
            "employee": emp.to_dict()
        })
        return emp.to_dict()
    return None

def _create_call_log_sync(emp_id: int, other_party: str, extension: str, room_name: str, call_type: str):
    from call_center.models import EmployeeProfile, EmployeeCallLog
    emp = EmployeeProfile.objects.filter(id=emp_id).first()
    if emp:
        return EmployeeCallLog.objects.create(
            employee=emp,
            other_party=other_party,
            extension=extension,
            room_name=room_name,
            call_type=call_type
        )
    return None


@inngest_client.create_function(
    fn_id="transfer-call-queue",
    trigger=inngest.TriggerEvent(event="call_center/transfer.requested"),
)
async def fn_transfer_call_queue(ctx: inngest.Context) -> dict:
    """
    Durable, clean call transfer workflow.
    - Closes old room immediately.
    - Puts Caller on hold locally with hold tone.
    - Rings queue candidates one by one in priority order.
    - If answered: creates new room, connects both, and notifies transferrer.
    - If rejected/timeout: moves to next online candidate.
    - If cancelled: restores connection between Caller and Transferrer.
    - If expired: ends hold and notifies parties.
    """
    event_data = ctx.event.data
    transfer_id = event_data.get("transfer_id")
    old_room_name = event_data.get("old_room_name")
    from_emp_id = event_data.get("from_employee_id")
    from_emp_name = event_data.get("from_employee_name", "الزميل")
    from_emp_ext = event_data.get("from_employee_extension", "")
    caller_id = event_data.get("caller_id")
    caller_name = event_data.get("caller_name", "المتصل")
    caller_ext = event_data.get("caller_extension", "")
    candidate_ids = event_data.get("candidate_ids", [])
    ring_timeout_seconds = int(event_data.get("ring_timeout_seconds", 15))
    total_timeout_seconds = int(event_data.get("total_timeout_seconds", 60))

    logger.info(f"[Inngest Transfer {transfer_id}] Starting transfer for caller {caller_name} ({caller_ext}) -> candidates {candidate_ids}")

    # Step 1: Ensure old LiveKit room is cleanly deleted
    async def step_close_old_room():
        if old_room_name:
            await delete_livekit_room(old_room_name)
        return {"status": "room_closed", "room": old_room_name}

    await ctx.step.run("close-old-room", step_close_old_room)

    r = _get_redis()
    r.set(f"transfer:{transfer_id}:state", "ringing", ex=total_timeout_seconds + 30)

    # Step 3: Iterate through candidate employees in order
    transferred_success = False
    answered_emp_id = None

    for idx, cand_id in enumerate(candidate_ids):
        # Check current Redis state before attempting next candidate
        current_state = r.get(f"transfer:{transfer_id}:state")
        if current_state in [b"completed", b"cancelled"]:
            logger.info(f"[Inngest Transfer {transfer_id}] Stopped: state is already {current_state}")
            return {"status": current_state.decode()}

        # Verify candidate is still available in DB
        cand = await sync_to_async(_get_employee_sync, thread_sensitive=True)(cand_id)
        if not cand or cand.status not in ['ready', 'available']:
            logger.info(f"[Inngest Transfer {transfer_id}] Candidate {cand_id} not available (status={getattr(cand, 'status', None)}), skipping.")
            continue

        # Ring candidate
        async def step_ring_candidate():
            r.set(f"transfer:{transfer_id}:current_candidate", cand_id, ex=ring_timeout_seconds + 5)
            publish_to_centrifugo(f"employee:{cand_id}", {
                "event": "incoming_call",
                "call_type": "transfer",
                "transfer_id": transfer_id,
                "room_name": f"transfer_{transfer_id}",
                "caller_name": caller_name,
                "caller_extension": caller_ext,
                "transferred_by": from_emp_name,
                "ring_timeout_seconds": ring_timeout_seconds,
            })
            return {"status": "ringing", "candidate_id": cand_id}

        await ctx.step.run(f"ring-candidate-{cand_id}", step_ring_candidate)

        # Wait for action event from candidate (answer/reject) or from transferrer (cancel)
        action_event = await ctx.step.wait_for_event(
            f"wait-action-cand-{cand_id}",
            event="call_center/transfer.action",
            if_exp=f"async.data.transfer_id == '{transfer_id}'",
            timeout=datetime.timedelta(seconds=ring_timeout_seconds)
        )

        if action_event is None:
            # Timeout on this candidate
            logger.info(f"[Inngest Transfer {transfer_id}] Candidate {cand_id} timed out after {ring_timeout_seconds}s.")
            async def step_timeout_candidate():
                publish_to_centrifugo(f"employee:{cand_id}", {
                    "event": "call_ended",
                    "transfer_id": transfer_id,
                    "reason": "timeout"
                })
                return {"status": "candidate_timed_out", "candidate_id": cand_id}
            await ctx.step.run(f"timeout-candidate-{cand_id}", step_timeout_candidate)
            continue

        action_data = action_event.data
        action = action_data.get("action")
        action_emp_id = action_data.get("employee_id")

        # 3.1: Candidate Answered
        if action == "answer" and int(action_emp_id) == int(cand_id):
            logger.info(f"[Inngest Transfer {transfer_id}] Candidate {cand_id} answered call!")
            answered_emp_id = cand_id

            async def step_complete_transfer():
                new_room = f"call_tr_{caller_ext}_{cand.extension}_{uuid.uuid4().hex[:6]}"
                
                # Tokens
                caller_token = generate_livekit_token(
                    new_room,
                    f"employee_{caller_id}_{caller_ext}",
                    caller_name,
                    {"role": "caller", "employee_id": caller_id}
                )
                cand_token = generate_livekit_token(
                    new_room,
                    f"employee_{cand.id}_{cand.extension}",
                    cand.display_name,
                    {"role": "callee", "employee_id": cand.id}
                )

                # Set candidate busy
                await sync_to_async(_update_employee_status_sync, thread_sensitive=True)(cand.id, "busy")
                
                # Create call log for candidate
                await sync_to_async(_create_call_log_sync, thread_sensitive=True)(
                    cand.id, caller_name, caller_ext, new_room, "inbound"
                )

                # Send new room token to Caller on hold
                publish_to_centrifugo(f"employee:{caller_id}", {
                    "event": "transfer_room_ready",
                    "transfer_id": transfer_id,
                    "room_name": new_room,
                    "livekit_url": settings.LIVEKIT_URL,
                    "livekit_token": caller_token,
                    "partner_name": cand.display_name,
                    "partner_extension": cand.extension
                })

                # Send new room token to Answered Candidate
                publish_to_centrifugo(f"employee:{cand.id}", {
                    "event": "transfer_room_ready",
                    "transfer_id": transfer_id,
                    "room_name": new_room,
                    "livekit_url": settings.LIVEKIT_URL,
                    "livekit_token": cand_token,
                    "partner_name": caller_name,
                    "partner_extension": caller_ext
                })

                # Notify Transferrer of success and set them ready
                publish_to_centrifugo(f"employee:{from_emp_id}", {
                    "event": "transfer_success",
                    "transfer_id": transfer_id,
                    "transferred_to": cand.display_name,
                    "target_extension": cand.extension
                })
                await sync_to_async(_update_employee_status_sync, thread_sensitive=True)(from_emp_id, "ready")

                r.set(f"transfer:{transfer_id}:state", "completed", ex=300)
                return {"status": "completed", "room": new_room, "answered_by": cand.id}

            res = await ctx.step.run("complete-transfer", step_complete_transfer)
            transferred_success = True
            return res

        # 3.2: Transferrer Cancelled
        elif action == "cancel":
            logger.info(f"[Inngest Transfer {transfer_id}] Transfer cancelled by transferrer {from_emp_id}.")
            async def step_cancel_transfer():
                # Dismiss ringing on candidate
                publish_to_centrifugo(f"employee:{cand_id}", {
                    "event": "call_ended",
                    "transfer_id": transfer_id,
                    "reason": "cancelled"
                })

                # Reconnect Caller and Transferrer in a restored room
                restored_room = f"call_rst_{caller_ext}_{from_emp_ext}_{uuid.uuid4().hex[:6]}"
                caller_token = generate_livekit_token(
                    restored_room,
                    f"employee_{caller_id}_{caller_ext}",
                    caller_name,
                    {"role": "caller", "employee_id": caller_id}
                )
                from_token = generate_livekit_token(
                    restored_room,
                    f"employee_{from_emp_id}_{from_emp_ext}",
                    from_emp_name,
                    {"role": "transferrer", "employee_id": from_emp_id}
                )

                publish_to_centrifugo(f"employee:{caller_id}", {
                    "event": "transfer_cancelled",
                    "transfer_id": transfer_id,
                    "room_name": restored_room,
                    "livekit_url": settings.LIVEKIT_URL,
                    "livekit_token": caller_token,
                    "partner_name": from_emp_name
                })
                publish_to_centrifugo(f"employee:{from_emp_id}", {
                    "event": "transfer_cancelled",
                    "transfer_id": transfer_id,
                    "room_name": restored_room,
                    "livekit_url": settings.LIVEKIT_URL,
                    "livekit_token": from_token,
                    "partner_name": caller_name
                })

                r.set(f"transfer:{transfer_id}:state", "cancelled", ex=300)
                return {"status": "cancelled", "restored_room": restored_room}

            res = await ctx.step.run("cancel-transfer", step_cancel_transfer)
            return res

        # 3.3: Candidate Rejected
        elif action == "reject":
            logger.info(f"[Inngest Transfer {transfer_id}] Candidate {cand_id} rejected call.")
            async def step_reject_candidate():
                publish_to_centrifugo(f"employee:{cand_id}", {
                    "event": "call_ended",
                    "transfer_id": transfer_id,
                    "reason": "rejected"
                })
                return {"status": "rejected", "candidate_id": cand_id}
            await ctx.step.run(f"reject-candidate-{cand_id}", step_reject_candidate)
            continue

    # Step 4: If nobody answered or all rejected / timed out
    if not transferred_success:
        logger.info(f"[Inngest Transfer {transfer_id}] All candidates exhausted. Transfer failed.")
        async def step_finalize_failed():
            publish_to_centrifugo(f"employee:{caller_id}", {
                "event": "transfer_failed",
                "transfer_id": transfer_id,
                "message": "عذراً، لم يتسنَّ للموظفين الرد على المكالمة حالياً."
            })
            publish_to_centrifugo(f"employee:{from_emp_id}", {
                "event": "transfer_failed",
                "transfer_id": transfer_id,
                "message": "لم يتم الرد على التحويل من قبل الموظفين."
            })
            await sync_to_async(_update_employee_status_sync, thread_sensitive=True)(caller_id, "ready")
            await sync_to_async(_update_employee_status_sync, thread_sensitive=True)(from_emp_id, "ready")
            r.set(f"transfer:{transfer_id}:state", "failed", ex=300)
            return {"status": "failed", "reason": "all_candidates_exhausted"}

        res = await ctx.step.run("finalize-failed-transfer", step_finalize_failed)
        return res

    return {"status": "done"}

all_call_center_inngest_functions = [
    fn_transfer_call_queue,
]
