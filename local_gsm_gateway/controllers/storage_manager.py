"""Local SQLite Storage Manager for GSM Dongle Gateway.

Persists call records, SMS messages, USSD transaction history,
and device configurations offline-first with synchronization flags.
"""
import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gateway_local.db")


class StorageManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create necessary tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Call Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caller_phone TEXT NOT NULL,
                    destination_phone TEXT,
                    direction TEXT DEFAULT 'inbound',
                    duration INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed',
                    room_name TEXT,
                    dongle_port TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced INTEGER DEFAULT 0
                )
            """)

            # 2. SMS Messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sms_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    direction TEXT DEFAULT 'inbound',
                    dongle_port TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read INTEGER DEFAULT 0
                )
            """)

            # 3. USSD History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ussd_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ussd_code TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    dongle_port TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Dongle Device Configs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dongle_devices (
                    port TEXT PRIMARY KEY,
                    alias TEXT,
                    operator_name TEXT,
                    sim_number TEXT,
                    is_enabled INTEGER DEFAULT 1,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    # --- Call Logs ---
    def add_call_log(
        self,
        caller_phone: str,
        destination_phone: str = "",
        direction: str = "inbound",
        duration: int = 0,
        status: str = "completed",
        room_name: str = "",
        dongle_port: str = "SIMULATED",
        synced: bool = False
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO call_logs (caller_phone, destination_phone, direction, duration, status, room_name, dongle_port, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (caller_phone, destination_phone, direction, duration, status, room_name, dongle_port, 1 if synced else 0))
            conn.commit()
            return cursor.lastrowid

    def get_recent_calls(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, caller_phone, destination_phone, direction, duration, status, room_name, dongle_port, created_at, synced
                FROM call_logs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_total_calls_today(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as total FROM call_logs
                WHERE date(created_at) = date('now')
            """)
            row = cursor.fetchone()
            return row["total"] if row else 0

    # --- SMS Messages ---
    def add_sms(
        self,
        phone_number: str,
        message_text: str,
        direction: str = "inbound",
        dongle_port: str = "SIMULATED"
    ) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sms_messages (phone_number, message_text, direction, dongle_port, is_read)
                VALUES (?, ?, ?, ?, 1)
            """, (phone_number, message_text, direction, dongle_port))
            conn.commit()
            return cursor.lastrowid

    def get_sms_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, phone_number, message_text, direction, dongle_port, created_at, is_read
                FROM sms_messages
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # --- USSD History ---
    def add_ussd_record(self, ussd_code: str, response_text: str, dongle_port: str = "SIMULATED") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ussd_history (ussd_code, response_text, dongle_port)
                VALUES (?, ?, ?)
            """, (ussd_code, response_text, dongle_port))
            conn.commit()
            return cursor.lastrowid

    def get_recent_ussd(self, limit: int = 15) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ussd_code, response_text, dongle_port, created_at
                FROM ussd_history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Dongle Devices ---
    def upsert_dongle(
        self,
        port: str,
        alias: str = "",
        operator_name: str = "",
        sim_number: str = "",
        is_enabled: bool = True
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO dongle_devices (port, alias, operator_name, sim_number, is_enabled, last_seen)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(port) DO UPDATE SET
                    alias = excluded.alias,
                    operator_name = excluded.operator_name,
                    sim_number = excluded.sim_number,
                    is_enabled = excluded.is_enabled,
                    last_seen = CURRENT_TIMESTAMP
            """, (port, alias, operator_name, sim_number, 1 if is_enabled else 0))
            conn.commit()

    def get_all_dongles(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dongle_devices ORDER BY last_seen DESC")
            return [dict(row) for row in cursor.fetchall()]
