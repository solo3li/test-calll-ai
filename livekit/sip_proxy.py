import asyncio
import os
import socket
import logging
import json
import re
import redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SIPProxy")

SIP_UPSTREAM_HOST = os.environ.get("SIP_UPSTREAM_HOST", "sip")
SIP_UPSTREAM_PORT = int(os.environ.get("SIP_UPSTREAM_PORT", "5061"))
LISTEN_PORT = int(os.environ.get("SIP_LISTEN_PORT", "5060"))
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

class SIPProxyProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.client_sessions = {}
        self.upstream_ip = None
        self.redis_client = None

    def connection_made(self, transport):
        self.transport = transport
        self.resolve_upstream()
        self.init_redis()
        logger.info(f"SIP Proxy & Registrar listening on 0.0.0.0:{LISTEN_PORT} UDP (upstream={SIP_UPSTREAM_HOST}:{SIP_UPSTREAM_PORT})")

    def init_redis(self):
        try:
            self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Presence tracking may be impaired.")

    def resolve_upstream(self):
        try:
            infos = socket.getaddrinfo(SIP_UPSTREAM_HOST, SIP_UPSTREAM_PORT, socket.AF_INET, socket.SOCK_DGRAM)
            if infos:
                self.upstream_ip = infos[0][4][0]
                logger.info(f"Resolved upstream '{SIP_UPSTREAM_HOST}' to IP {self.upstream_ip}")
        except Exception as e:
            logger.warning(f"Failed to resolve upstream host '{SIP_UPSTREAM_HOST}': {e}. Will retry on demand.")

    def extract_header(self, text: str, name: str) -> str:
        target = name.lower() + ":"
        for line in text.splitlines():
            line_str = line.strip()
            if line_str.lower().startswith(target):
                return line_str[len(target):].strip()
        return ""

    def extract_user(self, uri_or_header: str) -> str:
        match = re.search(r'sip:([^@>:\s]+)', uri_or_header)
        if match:
            return match.group(1)
        return ""

    def build_register_200_ok(self, text: str) -> str:
        via = self.extract_header(text, "via")
        from_h = self.extract_header(text, "from")
        to_h = self.extract_header(text, "to")
        call_id = self.extract_header(text, "call-id")
        cseq = self.extract_header(text, "cseq")
        contact = self.extract_header(text, "contact") or from_h

        if ";tag=" not in to_h.lower():
            to_h = f"{to_h};tag=reg-{abs(hash(call_id)) % 100000}"

        return (
            "SIP/2.0 200 OK\r\n"
            f"Via: {via}\r\n"
            f"From: {from_h}\r\n"
            f"To: {to_h}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq}\r\n"
            f"Contact: {contact}\r\n"
            "Expires: 300\r\n"
            "User-Agent: LiveKit-SIP-Proxy\r\n"
            "Content-Length: 0\r\n\r\n"
        )

    def build_refer_202_accepted(self, text: str) -> str:
        via = self.extract_header(text, "via")
        from_h = self.extract_header(text, "from")
        to_h = self.extract_header(text, "to")
        call_id = self.extract_header(text, "call-id")
        cseq = self.extract_header(text, "cseq")

        if ";tag=" not in to_h.lower():
            to_h = f"{to_h};tag=ref-{abs(hash(call_id)) % 100000}"

        return (
            "SIP/2.0 202 Accepted\r\n"
            f"Via: {via}\r\n"
            f"From: {from_h}\r\n"
            f"To: {to_h}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: {cseq}\r\n"
            "Expires: 60\r\n"
            "Content-Length: 0\r\n\r\n"
        )

    def build_refer_notify(self, text: str, addr: tuple) -> str:
        from_h = self.extract_header(text, "to")
        to_h = self.extract_header(text, "from")
        call_id = self.extract_header(text, "call-id")

        body = "SIP/2.0 200 OK\r\n"
        return (
            f"NOTIFY sip:{addr[0]}:{addr[1]} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP 127.0.0.1:{LISTEN_PORT};branch=z9hG4bKnotify-{abs(hash(call_id)) % 100000}\r\n"
            f"From: {from_h}\r\n"
            f"To: {to_h}\r\n"
            f"Call-ID: {call_id}\r\n"
            f"CSeq: 101 NOTIFY\r\n"
            "Event: refer\r\n"
            "Subscription-State: terminated;reason=noresource\r\n"
            "Content-Type: message/sipfrag\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
            f"{body}"
        )

    def datagram_received(self, data: bytes, addr: tuple):
        try:
            text = data.decode(errors="ignore")
            first_line = text.split("\r\n", 1)[0] if "\r\n" in text else text.split("\n", 1)[0]
        except Exception:
            return

        call_id = self.extract_header(text, "call-id")

        # 1. REGISTER -> Save presence in Redis and return 200 OK
        if first_line.startswith("REGISTER "):
            logger.info(f"[REGISTER] Intercepted from {addr} (Call-ID: {call_id})")
            from_user = self.extract_user(self.extract_header(text, "from")) or self.extract_user(self.extract_header(text, "to"))
            if from_user and self.redis_client:
                try:
                    self.redis_client.set(f"agent_endpoint:{from_user}", f"{addr[0]}:{addr[1]}", ex=360)
                    self.redis_client.set(f"agent_state:{from_user}", "AVAILABLE", ex=360)
                    logger.info(f"[PRESENCE] Registered agent '{from_user}' endpoint as {addr[0]}:{addr[1]}")
                except Exception as ex:
                    logger.warning(f"Error caching agent presence in Redis: {ex}")

            resp = self.build_register_200_ok(text)
            self.transport.sendto(resp.encode(), addr)
            logger.info(f"[REGISTER] Responded 200 OK to {addr}")
            return

        # 2. REFER -> Intercept transfer request, notify Redis, respond 202 Accepted + NOTIFY
        if first_line.startswith("REFER "):
            refer_to = self.extract_header(text, "refer-to")
            target = self.extract_user(refer_to)
            from_user = self.extract_user(self.extract_header(text, "from"))
            logger.info(f"[REFER] Intercepted transfer from {from_user} ({addr}) to target '{target}' (Call-ID: {call_id})")

            resp = self.build_refer_202_accepted(text)
            self.transport.sendto(resp.encode(), addr)

            notify = self.build_refer_notify(text, addr)
            self.transport.sendto(notify.encode(), addr)

            if self.redis_client:
                try:
                    payload = json.dumps({
                        "event": "call_transfer",
                        "call_id": call_id,
                        "from_user": from_user,
                        "target": target,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                    self.redis_client.rpush("transfer_events", payload)
                    logger.info(f"[REFER] Dispatched transfer event to Redis: {payload}")
                except Exception as ex:
                    logger.error(f"Error publishing transfer to Redis: {ex}")
            return

        if not self.upstream_ip:
            self.resolve_upstream()

        is_from_upstream = (
            addr[1] == SIP_UPSTREAM_PORT or
            (self.upstream_ip and addr[0] == self.upstream_ip) or
            first_line.startswith("SIP/2.0 ")
        )

        # 3. Traffic coming from LiveKit SIP -> Route to client
        if is_from_upstream:
            client_addr = self.client_sessions.get(call_id)

            if not client_addr and first_line.startswith("INVITE "):
                req_uri = first_line.split()[1]
                target_user = self.extract_user(req_uri)
                if target_user and self.redis_client:
                    ep = self.redis_client.get(f"agent_endpoint:{target_user}")
                    if ep and ":" in ep:
                        ip, port = ep.split(":", 1)
                        client_addr = (ip, int(port))
                        self.client_sessions[call_id] = client_addr
                        logger.info(f"[OUTBOUND INVITE] Routing call from LiveKit to agent '{target_user}' at {client_addr}")

            if client_addr:
                logger.info(f"[UPSTREAM -> CLIENT] {first_line} -> {client_addr}")
                self.transport.sendto(data, client_addr)
            else:
                logger.warning(f"[UPSTREAM] No active client mapping for Call-ID '{call_id}'. Dropping {first_line}")
            return

        # 4. Traffic coming from Client (MicroSIP) -> Route to LiveKit SIP
        if call_id:
            self.client_sessions[call_id] = addr

        target_host = self.upstream_ip or SIP_UPSTREAM_HOST
        logger.info(f"[CLIENT -> UPSTREAM] {first_line} from {addr} -> {target_host}:{SIP_UPSTREAM_PORT}")
        self.transport.sendto(data, (target_host, SIP_UPSTREAM_PORT))

        if first_line.startswith("BYE "):
            asyncio.get_event_loop().call_later(30.0, self.client_sessions.pop, call_id, None)

async def main():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SIPProxyProtocol(),
        local_addr=("0.0.0.0", LISTEN_PORT)
    )
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()

if __name__ == "__main__":
    asyncio.run(main())
