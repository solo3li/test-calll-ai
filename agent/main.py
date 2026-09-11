import asyncio
import os
import sys
import time
import logging
import signal
import requests
import redis.asyncio as aioredis
from dotenv import load_dotenv
from google import genai
from google.genai import types
from livekit import api, rtc

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("VoiceAgentDaemon")

LIVEKIT_INTERNAL_URL = os.getenv("LIVEKIT_INTERNAL_URL", "ws://livekit:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secretkey1234567890abcdef")
CENTRIFUGO_HTTP_API_URL = os.getenv("CENTRIFUGO_HTTP_API_URL", "http://centrifugo:8000/api")
CENTRIFUGO_API_KEY = os.getenv("CENTRIFUGO_API_KEY", "centrifugo_api_key_1234567890")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

def notify_centrifugo(channel: str, event: str, message: str, extra: dict = None):
    """Notify web client via Centrifugo WebSocket channel."""
    try:
        url = f"{CENTRIFUGO_HTTP_API_URL}/publish"
        payload = {
            "channel": channel,
            "data": {
                "event": event,
                "message": message,
                "timestamp": time.time(),
                **(extra or {})
            }
        }
        headers = {
            "Authorization": f"apikey {CENTRIFUGO_API_KEY}",
            "Content-Type": "application/json"
        }
        requests.post(url, json=payload, headers=headers, timeout=2)
    except Exception as e:
        logger.warning(f"Could not notify Centrifugo: {e}")

async def run_agent_session(room_name: str):
    channel_name = f"rooms:{room_name}"
    logger.info(f"Starting Gemini Live Voice Agent session for room: {room_name}")
    notify_centrifugo(channel_name, "agent_starting", "جاري تهيئة المساعد الصوتي والاتصال بـ Gemini...")

    # 1. Create LiveKit Access Token for Agent
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity("pipecat-agent") \
        .with_name("Gemini Voice Assistant") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    agent_jwt = token.to_jwt()

    # 2. Connect to LiveKit Room
    room = rtc.Room()
    try:
        await room.connect(LIVEKIT_INTERNAL_URL, agent_jwt)
        logger.info(f"Connected to LiveKit room '{room_name}'")
    except Exception as e:
        logger.error(f"Failed to connect to LiveKit: {e}")
        notify_centrifugo(channel_name, "agent_error", f"فشل الاتصال بخادم LiveKit: {e}")
        return

    # 3. Prepare Local Audio Track (Agent output: 24kHz mono)
    audio_source = rtc.AudioSource(sample_rate=24000, num_channels=1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent-audio", audio_source)
    publish_options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    await room.local_participant.publish_track(audio_track, publish_options)
    logger.info(f"Published agent audio track to room '{room_name}'")

    # 4. Prepare Gemini Live Client
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("your_"):
        err = "GEMINI_API_KEY is not configured properly in .env"
        logger.error(err)
        notify_centrifugo(channel_name, "agent_error", err)
        await room.disconnect()
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    live_config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        system_instruction=types.Content(
            parts=[types.Part(text="أنت مساعد صوتي ذكي وودود وسريع البديهة. تتحدث باللغة العربية بطلاقة وبشكل طبيعي وموجز دون إطالة غير ضرورية. تجيب دائماً على كل سؤال يطرحه المستخدم.")]
        )
    )

    in_audio_queue = asyncio.Queue()
    out_audio_queue = asyncio.Queue()
    stop_event = asyncio.Event()

    state = {
        "is_agent_speaking": False,
        "turn_complete": True,
        "agent_last_audio_time": 0.0,
    }

    subscribed_sids = set()

    def subscribe_track(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        sid = publication.sid or (track.sid if track else None)
        if not sid or sid in subscribed_sids:
            return
        if track and track.kind == rtc.TrackKind.KIND_AUDIO:
            subscribed_sids.add(sid)
            logger.info(f"Subscribing to audio track {sid} from participant {participant.identity}")
            audio_stream = rtc.AudioStream(track, sample_rate=16000, num_channels=1)
            asyncio.create_task(stream_user_audio_to_queue(audio_stream, in_audio_queue, stop_event, participant.identity))

    @room.on("track_published")
    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        publication.set_subscribed(True)
        if publication.track:
            subscribe_track(publication.track, publication, participant)

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        subscribe_track(track, publication, participant)

    for participant in room.remote_participants.values():
        for publication in participant.track_publications.values():
            publication.set_subscribed(True)
            if publication.track:
                subscribe_track(publication.track, publication, participant)

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant disconnected: {participant.identity} from room {room_name}")
        remaining_humans = [p for p in room.remote_participants.values() if p.identity != "pipecat-agent"]
        if not remaining_humans:
            logger.info(f"No human participants left in room '{room_name}'. Terminating agent session.")
            stop_event.set()

    # 5. Connect to Gemini Live Session
    try:
        logger.info(f"Connecting to Gemini Live API (gemini-3.1-flash-live-preview) for room {room_name}...")
        async with client.aio.live.connect(model="gemini-3.1-flash-live-preview", config=live_config) as session:
            logger.info(f"Gemini Live session connected for room '{room_name}'!")
            notify_centrifugo(channel_name, "agent_ready", "المساعد الصوتي متصل وجاهز للاستماع الآن!")

            # Worker 1: Stream user PCM audio frames to Gemini Live (continuous 40ms chunks with echo gating)
            async def send_audio_worker():
                buffer = bytearray()
                CHUNK_SIZE = 1280  # 40ms at 16kHz 16-bit mono

                while not stop_event.is_set():
                    try:
                        chunk = await asyncio.wait_for(in_audio_queue.get(), timeout=0.05)

                        # Echo suppression: if agent is currently speaking, discard mic audio
                        if state["is_agent_speaking"]:
                            buffer.clear()
                            continue

                        buffer.extend(chunk)

                        while len(buffer) >= CHUNK_SIZE:
                            to_send = bytes(buffer[:CHUNK_SIZE])
                            del buffer[:CHUNK_SIZE]
                            await session.send_realtime_input(
                                audio=types.Blob(data=to_send, mime_type="audio/pcm;rate=16000")
                            )

                    except asyncio.TimeoutError:
                        if buffer and not state["is_agent_speaking"]:
                            to_send = bytes(buffer)
                            buffer.clear()
                            try:
                                await session.send_realtime_input(
                                    audio=types.Blob(data=to_send, mime_type="audio/pcm;rate=16000")
                                )
                            except Exception:
                                pass
                    except Exception as ex:
                        if not stop_event.is_set():
                            logger.error(f"Error sending audio to Gemini: {ex}")
                            await asyncio.sleep(0.05)

            # Worker 2: Receive audio & transcripts from Gemini Live across multiple turns
            async def receive_audio_worker():
                while not stop_event.is_set():
                    try:
                        async for response in session.receive():
                            if stop_event.is_set():
                                break

                            content = response.server_content
                            if not content:
                                continue

                            # Interruption handling
                            if content.interrupted:
                                logger.info(f"Gemini playback interrupted by user in room {room_name}")
                                while not out_audio_queue.empty():
                                    try:
                                        out_audio_queue.get_nowait()
                                    except asyncio.QueueEmpty:
                                        break
                                state["is_agent_speaking"] = False
                                state["turn_complete"] = True
                                notify_centrifugo(channel_name, "agent_interrupted", "تمت المقاطعة...")
                                continue

                            # Transcriptions
                            if content.input_transcription and content.input_transcription.text:
                                user_text = content.input_transcription.text.strip()
                                logger.info(f"[{room_name}] User: {user_text}")
                                notify_centrifugo(channel_name, "transcription_user", user_text, {"speaker": "user"})

                            if content.output_transcription and content.output_transcription.text:
                                bot_text = content.output_transcription.text.strip()
                                logger.info(f"[{room_name}] Gemini: {bot_text}")
                                notify_centrifugo(channel_name, "transcription_agent", bot_text, {"speaker": "agent"})

                            # Audio response from Gemini
                            if content.model_turn:
                                if not state["is_agent_speaking"]:
                                    state["is_agent_speaking"] = True
                                    notify_centrifugo(channel_name, "agent_speaking", "المساعد يتحدث...")
                                state["turn_complete"] = False
                                state["agent_last_audio_time"] = time.time()
                                for part in content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        await out_audio_queue.put(part.inline_data.data)

                            if content.turn_complete:
                                logger.info(f"Gemini model turn complete for room {room_name}")
                                state["turn_complete"] = True

                    except asyncio.CancelledError:
                        break
                    except Exception as ex:
                        if not stop_event.is_set():
                            logger.error(f"Error receiving from Gemini Live in room {room_name}: {ex}")
                            await asyncio.sleep(0.1)

            # Worker 3: Audio Pacer (paces output to LiveKit track in smooth 20ms frames)
            async def audio_pacer_worker():
                FRAME_SAMPLES = 480  # 20ms at 24kHz
                FRAME_BYTES = 960
                buffer = bytearray()

                while not stop_event.is_set():
                    try:
                        while len(buffer) < FRAME_BYTES:
                            chunk = await asyncio.wait_for(out_audio_queue.get(), timeout=0.02)
                            buffer.extend(chunk)

                        frame_bytes = bytes(buffer[:FRAME_BYTES])
                        del buffer[:FRAME_BYTES]

                        frame = rtc.AudioFrame(
                            data=frame_bytes,
                            sample_rate=24000,
                            num_channels=1,
                            samples_per_channel=FRAME_SAMPLES
                        )
                        await audio_source.capture_frame(frame)
                        state["agent_last_audio_time"] = time.time()
                        await asyncio.sleep(0.019)
                    except asyncio.TimeoutError:
                        if buffer:
                            pad = FRAME_BYTES - len(buffer)
                            frame_bytes = bytes(buffer + b'\x00' * pad)
                            buffer.clear()
                            frame = rtc.AudioFrame(
                                data=frame_bytes,
                                sample_rate=24000,
                                num_channels=1,
                                samples_per_channel=FRAME_SAMPLES
                            )
                            await audio_source.capture_frame(frame)
                            state["agent_last_audio_time"] = time.time()
                        else:
                            # If queue and buffer are empty and turn is complete and 250ms have passed:
                            if state["is_agent_speaking"] and state.get("turn_complete", True) and (time.time() - state["agent_last_audio_time"] > 0.25):
                                # Drain any residual mic frames from queue before opening mic
                                while not in_audio_queue.empty():
                                    try:
                                        in_audio_queue.get_nowait()
                                    except asyncio.QueueEmpty:
                                        break
                                state["is_agent_speaking"] = False
                                logger.info(f"Agent playback finished for room {room_name}. Mic listening active.")
                                notify_centrifugo(channel_name, "agent_listening", "المساعد يستمع إليك الآن...")
                        continue
                    except Exception as ex:
                        if not stop_event.is_set():
                            logger.error(f"Error in audio pacer for room {room_name}: {ex}")
                        break

            sender_task = asyncio.create_task(send_audio_worker())
            receiver_task = asyncio.create_task(receive_audio_worker())
            pacer_task = asyncio.create_task(audio_pacer_worker())

            await stop_event.wait()
            sender_task.cancel()
            receiver_task.cancel()
            pacer_task.cancel()

    except Exception as e:
        logger.error(f"Gemini Live session error in room {room_name}: {e}")
        notify_centrifugo(channel_name, "agent_error", f"خطأ في جلسة Gemini Live: {e}")
    finally:
        logger.info(f"Cleaning up and disconnecting from room '{room_name}'...")
        await room.disconnect()
        notify_centrifugo(channel_name, "agent_disconnected", "تم إنهاء جلسة المساعد الصوتي.")

async def stream_user_audio_to_queue(audio_stream: rtc.AudioStream, queue: asyncio.Queue, stop_event: asyncio.Event, identity: str):
    """Read user audio frames from LiveKit stream and push to queue."""
    logger.info(f"Started reading audio frames from participant: {identity}")
    try:
        async for frame_event in audio_stream:
            if stop_event.is_set():
                break
            frame: rtc.AudioFrame = frame_event.frame
            queue.put_nowait(bytes(frame.data))
    except Exception as e:
        logger.debug(f"Audio stream for {identity} ended: {e}")

async def main():
    logger.info("Starting Standalone Voice Agent Service (Listening on Redis queue: agent_jobs)...")
    logger.info(f"LiveKit Internal URL: {LIVEKIT_INTERNAL_URL}")
    logger.info(f"Centrifugo API URL: {CENTRIFUGO_HTTP_API_URL}")
    logger.info(f"Redis URL: {REDIS_URL}")

    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    active_sessions: dict[str, asyncio.Task] = {}

    shutdown_event = asyncio.Event()

    def handle_signal():
        logger.info("Received termination signal. Shutting down agent daemon...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass  # Windows may not implement signal handlers for all signals

    while not shutdown_event.is_set():
        try:
            # Non-blocking pop with 1s timeout
            item = await r.brpop("agent_jobs", timeout=1.0)
            if item:
                _, room_name = item
                room_name = room_name.strip()
                if not room_name:
                    continue

                # Check if session is already running for this room
                if room_name in active_sessions and not active_sessions[room_name].done():
                    logger.info(f"Session for room '{room_name}' is already running. Skipping duplicate dispatch.")
                    continue

                logger.info(f"Received new agent dispatch for room: {room_name}")

                def make_cleanup(rm):
                    def _cleanup(fut):
                        logger.info(f"Agent session task finished for room: {rm}")
                        active_sessions.pop(rm, None)
                    return _cleanup

                task = asyncio.create_task(run_agent_session(room_name))
                task.add_done_callback(make_cleanup(room_name))
                active_sessions[room_name] = task

            # Periodically prune any finished tasks
            for rm, t in list(active_sessions.items()):
                if t.done():
                    active_sessions.pop(rm, None)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in agent dispatcher loop: {e}")
            await asyncio.sleep(1)

    logger.info("Stopping all active agent sessions...")
    for rm, t in active_sessions.items():
        t.cancel()
    if active_sessions:
        await asyncio.gather(*active_sessions.values(), return_exceptions=True)
    await r.aclose()
    logger.info("Agent service stopped gracefully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
