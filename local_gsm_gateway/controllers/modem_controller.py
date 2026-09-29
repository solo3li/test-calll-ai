"""Modem Controller for GSM USB Dongle.

Interfaces with USB Modem serial COM ports (e.g. Huawei E173, ZTE, etc.)
Handles AT commands for answering calls, detecting incoming rings with Caller ID,
and reading cellular network signal metrics.
Also provides a simulation mode for testing when no physical dongle is attached.
"""
import time
import logging
import sys
import threading
from typing import Callable, Optional, List, Dict

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

logger = logging.getLogger(__name__)


def list_available_ports() -> List[Dict[str, str]]:
    """Scan and list all detected USB Serial and COM ports."""
    ports = []
    # On Android, physical tty ports cannot be enumerated via standard posix scan
    if sys.platform != "android" and SERIAL_AVAILABLE:
        try:
            for p in serial.tools.list_ports.comports():
                desc = p.description or "Generic Serial Port"
                ports.append({
                    "device": p.device,
                    "description": f"{p.device} ({desc})",
                    "manufacturer": getattr(p, 'manufacturer', '') or 'Unknown'
                })
        except Exception as e:
            logger.warning(f"Error enumerating serial ports: {e}")
    if not ports:
        # Default virtual entries for simulation / testing
        ports.append({"device": "SIMULATED", "description": "مودم تجريبي افتراضي (Simulation Mode)", "manufacturer": "Virtual"})
    return ports


class ModemController:
    def __init__(
        self,
        port: str = "SIMULATED",
        baudrate: int = 115200,
        on_incoming_call: Optional[Callable[[str], None]] = None,
        on_call_ended: Optional[Callable[[], None]] = None,
        on_signal_update: Optional[Callable[[int], None]] = None
    ):
        self.port = port
        self.baudrate = baudrate
        self.on_incoming_call = on_incoming_call
        self.on_call_ended = on_call_ended
        self.on_signal_update = on_signal_update

        self.ser: Optional[serial.Serial] = None
        self.is_running = False
        self._listener_thread: Optional[threading.Thread] = None
        self.is_connected = False
        self.signal_strength = 85  # Default simulated signal %

    def connect(self, port: Optional[str] = None) -> bool:
        """Open serial connection to the USB dongle."""
        if port:
            self.port = port

        if self.port == "SIMULATED" or not SERIAL_AVAILABLE:
            self.is_connected = True
            self.is_running = True
            logger.info("ModemController running in SIMULATED mode.")
            return True

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_connected = True
            self.is_running = True

            # Send initialization AT commands
            self._send_at("AT")
            self._send_at("ATE0")       # Echo off
            self._send_at("AT+CLIP=1")  # Enable Caller ID presentation
            self._send_at("AT+CMGF=1")  # Text mode for SMS

            # Start listener thread
            self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listener_thread.start()
            logger.info(f"Connected to USB Dongle on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to modem on {self.port}: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Close connection and stop listener."""
        self.is_running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.is_connected = False
        logger.info("ModemController disconnected.")

    def _send_at(self, cmd: str) -> str:
        """Send AT command and read response."""
        if not self.ser or not self.ser.is_open:
            return ""
        try:
            self.ser.write((cmd + "\r\n").encode('utf-8'))
            time.sleep(0.1)
            resp = self.ser.read_all().decode('utf-8', errors='ignore')
            return resp
        except Exception as e:
            logger.warning(f"Error sending AT command '{cmd}': {e}")
            return ""

    def answer_call(self) -> bool:
        """Send ATA to pick up and answer incoming call."""
        logger.info("Modem answering call (ATA)...")
        if self.port == "SIMULATED":
            return True
        resp = self._send_at("ATA")
        return "OK" in resp or "CONNECT" in resp

    def hangup_call(self) -> bool:
        """Send ATH to terminate/hang up call."""
        logger.info("Modem hanging up call (ATH)...")
        if self.port == "SIMULATED":
            return True
        resp = self._send_at("ATH")
        return "OK" in resp

    def simulate_incoming_call(self, caller_number: str = "+201012345678"):
        """Trigger simulated incoming call for testing without a physical dongle."""
        logger.info(f"Simulating incoming call from {caller_number}")
        if self.on_incoming_call:
            threading.Thread(target=self.on_incoming_call, args=(caller_number,), daemon=True).start()

    def _listen_loop(self):
        """Background thread reading serial lines for incoming rings and status."""
        caller_id = "unknown"
        while self.is_running and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                logger.debug(f"Modem Rx: {line}")

                # 1. Incoming Call Ring
                if "RING" in line:
                    # Next line or recent line might have +CLIP: "..."
                    time.sleep(0.2)
                    extra = self.ser.read_all().decode('utf-8', errors='ignore')
                    for sub in extra.split("\n"):
                        if "+CLIP:" in sub:
                            parts = sub.split('"')
                            if len(parts) > 1:
                                caller_id = parts[1]

                    if self.on_incoming_call:
                        self.on_incoming_call(caller_id)

                # 2. Remote Hangup
                elif "NO CARRIER" in line or "BUSY" in line:
                    if self.on_call_ended:
                        self.on_call_ended()

            except Exception as e:
                logger.warning(f"Error in modem listener loop: {e}")
                time.sleep(1)
