import os
import sys
import subprocess
import logging
from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=1)
def start_pipecat_agent(self, room_name: str):
    """
    Celery task to launch the Pipecat Voice Agent as an isolated subprocess.
    """
    logger.info(f"[Celery] Triggered Agent task for room: {room_name}")
    script_path = os.path.join(os.path.dirname(__file__), "pipecat_agent.py")

    # Launch subprocess running the voice agent
    process = subprocess.Popen(
        [sys.executable, script_path, room_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    logger.info(f"[Celery] Agent subprocess started with PID {process.pid} for room {room_name}")

    # Stream logs from the subprocess
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if line:
                logger.info(f"[Agent-{room_name}] {line.strip()}")

    process.wait()
    logger.info(f"[Celery] Agent subprocess for room {room_name} ended with code: {process.returncode}")
    return process.returncode
