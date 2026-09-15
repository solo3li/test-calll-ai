import asyncio
import os
import socket
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SIPProxy")

SIP_UPSTREAM_HOST = os.environ.get("SIP_UPSTREAM_HOST", "sip")
SIP_UPSTREAM_PORT = int(os.environ.get("SIP_UPSTREAM_PORT", "5061"))
LISTEN_PORT = int(os.environ.get("SIP_LISTEN_PORT", "5060"))

class SIPProxyProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.client_sessions = {}
        self.upstream_ip = None

    def connection_made(self, transport):
        self.transport = transport
        self.resolve_upstream()
        logger.info(f"SIP Proxy & Registrar listening on 0.0.0.0:{LISTEN_PORT} UDP (upstream={SIP_UPSTREAM_HOST}:{SIP_UPSTREAM_PORT})")

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

    def datagram_received(self, data: bytes, addr: tuple):
        try:
            text = data.decode(errors="ignore")
            first_line = text.split("\r\n", 1)[0] if "\r\n" in text else text.split("\n", 1)[0]
        except Exception:
            return

        call_id = self.extract_header(text, "call-id")

        # 1. REGISTER interceptor -> immediately 200 OK
        if first_line.startswith("REGISTER "):
            logger.info(f"[REGISTER] Intercepted from {addr} (Call-ID: {call_id})")
            resp = self.build_register_200_ok(text)
            self.transport.sendto(resp.encode(), addr)
            logger.info(f"[REGISTER] Responded 200 OK to {addr}")
            return

        if not self.upstream_ip:
            self.resolve_upstream()

        is_from_upstream = (
            addr[1] == SIP_UPSTREAM_PORT or
            (self.upstream_ip and addr[0] == self.upstream_ip) or
            first_line.startswith("SIP/2.0 ")
        )

        # 2. Traffic coming from LiveKit SIP -> Route to client
        if is_from_upstream:
            client_addr = self.client_sessions.get(call_id)
            if client_addr:
                logger.info(f"[UPSTREAM -> CLIENT] {first_line} -> {client_addr}")
                self.transport.sendto(data, client_addr)
            else:
                logger.warning(f"[UPSTREAM] No active client mapping for Call-ID '{call_id}'. Dropping {first_line}")
            return

        # 3. Traffic coming from Client (MicroSIP) -> Route to LiveKit SIP
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
