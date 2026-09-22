import json
import hmac
import hashlib
import logging
import threading
import requests

logger = logging.getLogger(__name__)


def _send_webhook_async(url: str, secret: str, payload: dict):
    try:
        data_bytes = json.dumps(payload, separators=(',', ':'), default=str).encode('utf-8')
        signature = hmac.new(secret.encode('utf-8'), data_bytes, hashlib.sha256).hexdigest()
        headers = {
            'Content-Type': 'application/json',
            'X-Signature': f"sha256={signature}",
            'User-Agent': 'Voice-AI-Partner-Platform/1.0',
        }
        res = requests.post(url, data=data_bytes, headers=headers, timeout=6)
        logger.info(f"Webhook dispatched to {url} [Event: {payload.get('event')}] - Status: {res.status_code}")
    except Exception as e:
        logger.warning(f"Failed to dispatch webhook to {url}: {e}")


def dispatch_partner_webhook(partner, event: str, data: dict):
    """
    Asynchronously dispatches a signed webhook to the partner's configured webhook_url.
    Does not block the calling thread.
    """
    if not partner or not partner.webhook_url:
        return

    payload = {
        "event": event,
        "partner_code": partner.partner_code,
        "timestamp": data.get("timestamp") or "",
        "data": data,
    }

    t = threading.Thread(
        target=_send_webhook_async,
        args=(partner.webhook_url, partner.webhook_secret or partner.api_key, payload),
        daemon=True
    )
    t.start()
