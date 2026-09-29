"""Dashboard View for Local GSM USB Dongle Gateway App.

Implements the approved 'Dynamic Cards' design:
- Top Burgundy Header (#680E23) with LiveKit Online Pill and 4G Signal
- Active Inbound Call Hero Card (NO Live Transcript bubbles for zero latency!)
- 2x2 Telemetry Cards Grid (4G Signal, SIM Card, WebRTC Latency, Total Calls)
- Hardware Port & Audio Selector with Test Simulation Call Trigger
- Recent Calls History Log
"""
import time
import flet as ft
from theme import (
    COLOR_BURGUNDY,
    COLOR_BURGUNDY_LIGHT,
    COLOR_BURGUNDY_BORDER,
    COLOR_CREAM,
    COLOR_WHITE,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_GREEN,
    COLOR_GREEN_BG,
    COLOR_GREEN_TEXT,
    COLOR_RED,
    COLOR_RED_HOVER,
    COLOR_RED_BG,
)
from controllers.api_client import DongleApiClient
from controllers.modem_controller import ModemController, list_available_ports


class DashboardView:
    def __init__(self, page: ft.Page, api_client: DongleApiClient, on_logout):
        self.page = page
        self.api_client = api_client
        self.on_logout = on_logout

        # State Variables
        self.is_in_call = False
        self.current_caller = ""
        self.current_room = ""
        self.current_session_id = None
        self.call_start_time = 0
        self.is_muted = False
        self.total_calls_today = 0
        self.recent_calls = []

        # Modem Controller
        self.modem = ModemController(
            port="SIMULATED",
            on_incoming_call=self._on_modem_incoming_call,
            on_call_ended=self._on_modem_call_ended
        )

        # UI Components
        self._build_components()

        # Connect modem automatically
        self.modem.connect()

    def _build_components(self):
        # 1. Header (Brand Burgundy)
        owner_name = (self.api_client.user_data or {}).get("name") or "المالك"
        self.header = ft.Container(
            bgcolor=COLOR_BURGUNDY,
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    # Title & Owner
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text("بوابة الاتصال الذكية", color=COLOR_WHITE, size=15, weight=ft.FontWeight.BOLD),
                            ft.Text(f"المالك: {owner_name}", color=COLOR_BURGUNDY_LIGHT, size=11),
                        ],
                    ),
                    # Badges
                    ft.Row(
                        spacing=8,
                        controls=[
                            # LiveKit Online Badge
                            ft.Container(
                                content=ft.Row(
                                    spacing=4,
                                    controls=[
                                        ft.Icon(ft.Icons.CIRCLE, color=COLOR_GREEN, size=8),
                                        ft.Text("متصل LiveKit", color=COLOR_WHITE, size=10, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                bgcolor="#FFFFFF22",
                                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                border_radius=12,
                            ),
                            # 4G Signal
                            ft.Row(
                                spacing=2,
                                controls=[
                                    ft.Icon(ft.Icons.SIGNAL_CELLULAR_ALT_ROUNDED, color=COLOR_WHITE, size=16),
                                    ft.Text("4G", color=COLOR_WHITE, size=10, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                            # Logout Button
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT_ROUNDED,
                                icon_color=COLOR_WHITE,
                                icon_size=18,
                                tooltip="تسجيل الخروج",
                                on_click=self._handle_logout,
                            ),
                        ],
                    ),
                ],
            ),
        )

        # 2. Active Call Hero Card (Hidden by default, shown during call)
        self.caller_number_text = ft.Text("+20 10 ...", size=20, weight=ft.FontWeight.BOLD, color=COLOR_BURGUNDY)
        self.call_timer_text = ft.Text("00:00", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXT_MUTED)

        # Audio Waveform Representation (Smooth animated bars)
        self.waveform_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=3,
            controls=[
                ft.Container(width=3, height=h, bgcolor=COLOR_BURGUNDY, border_radius=2)
                for h in [8, 14, 24, 32, 18, 28, 36, 20, 12, 26, 34, 16, 8]
            ],
        )

        self.mute_btn = ft.IconButton(
            icon=ft.Icons.MIC_ROUNDED,
            icon_color=COLOR_BURGUNDY,
            bgcolor=COLOR_BURGUNDY_LIGHT,
            icon_size=20,
            tooltip="كتم الصوت",
            on_click=self._toggle_mute,
        )

        self.hangup_btn = ft.IconButton(
            icon=ft.Icons.CALL_END_ROUNDED,
            icon_color=COLOR_WHITE,
            bgcolor=COLOR_RED,
            icon_size=22,
            tooltip="إنهاء المكالمة",
            on_click=lambda _: self._end_call(),
        )

        self.active_call_card = ft.Card(
            visible=False,
            elevation=3,
            bgcolor=COLOR_WHITE,
            shape=ft.RoundedRectangleBorder(radius=18),
            content=ft.Container(
                padding=16,
                border=ft.Border.all(1.5, COLOR_BURGUNDY_BORDER),
                border_radius=18,
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Container(
                                    content=ft.Text("📞 مكالمة واردة نشطة عبر الشريحة", size=11, color=COLOR_BURGUNDY, weight=ft.FontWeight.BOLD),
                                    bgcolor=COLOR_BURGUNDY_LIGHT,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=8,
                                ),
                                self.call_timer_text,
                            ],
                        ),
                        self.caller_number_text,
                        self.waveform_row,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=20,
                            controls=[self.mute_btn, self.hangup_btn],
                        ),
                    ],
                ),
            ),
        )

        # 3. 2x2 Telemetry Metric Cards
        self.signal_card = self._build_metric_card(
            icon=ft.Icons.SPEED_ROUNDED,
            title="إشارة الشبكة (4G)",
            value="95% ممتازة",
            subtitle="فودافون مصر",
        )

        self.sim_card = self._build_metric_card(
            icon=ft.Icons.SIM_CARD_OUTLINED,
            title="حالة الشريحة",
            value="جاهزة للاستقبال",
            subtitle="صوت وبيانات نشطة",
        )

        self.latency_card = self._build_metric_card(
            icon=ft.Icons.BOLT_ROUNDED,
            title="سرعة الاستجابة",
            value="24 ms",
            subtitle="WebRTC سحابي فائق",
        )

        self.calls_count_text = ft.Text("0 مكالمة", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY)
        self.calls_card = ft.Card(
            expand=True,
            elevation=1,
            bgcolor=COLOR_WHITE,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=12,
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("إجمالي المكالمات", size=11, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.W_600),
                                ft.Icon(ft.Icons.CALL_ROUNDED, color=COLOR_BURGUNDY, size=16),
                            ],
                        ),
                        self.calls_count_text,
                        ft.Text("تمت معالجتها بالـ AI اليوم", size=10, color=COLOR_TEXT_SECONDARY),
                    ],
                ),
            ),
        )

        # 4. Port & Hardware Drawer
        ports = list_available_ports()
        self.port_dropdown = ft.Dropdown(
            label="منفذ المودم (USB Port)",
            value="SIMULATED" if not ports else ports[0]["device"],
            options=[ft.dropdown.Option(p["device"], p["description"]) for p in ports],
            border_radius=10,
            text_size=12,
            border_color=COLOR_BORDER,
            focused_border_color=COLOR_BURGUNDY,
            dense=True,
            on_select=self._on_port_change,
        )

        self.sim_caller_input = ft.TextField(
            hint_text="+201012345678",
            value="+201012345678",
            dense=True,
            border_radius=10,
            text_size=12,
            border_color=COLOR_BORDER,
            focused_border_color=COLOR_BURGUNDY,
            width=160,
        )

        self.hardware_card = ft.Card(
            elevation=1,
            bgcolor=COLOR_WHITE,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=12,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("إعدادات الفلاشة والمحاكاة", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                                ft.Icon(ft.Icons.USB_ROUNDED, color=COLOR_BURGUNDY, size=16),
                            ],
                        ),
                        self.port_dropdown,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                self.sim_caller_input,
                                ft.FilledButton(
                                    content=ft.Text("تجربة اتصال وارد", size=11, weight=ft.FontWeight.BOLD, color=COLOR_WHITE),
                                    bgcolor=COLOR_BURGUNDY,
                                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                                    on_click=self._trigger_simulated_call,
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        )

        # 5. Recent Calls Log Table
        self.calls_list_column = ft.Column(spacing=6)
        self._render_recent_calls()

        self.calls_history_card = ft.Card(
            elevation=1,
            bgcolor=COLOR_WHITE,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=12,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text("سجل المكالمات الأخيرة", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        self.calls_list_column,
                    ],
                ),
            ),
        )

    def _build_metric_card(self, icon, title: str, value: str, subtitle: str) -> ft.Card:
        return ft.Card(
            expand=True,
            elevation=1,
            bgcolor=COLOR_WHITE,
            shape=ft.RoundedRectangleBorder(radius=14),
            content=ft.Container(
                padding=12,
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(title, size=11, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.W_600),
                                ft.Icon(icon, color=COLOR_BURGUNDY, size=16),
                            ],
                        ),
                        ft.Text(value, size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                        ft.Text(subtitle, size=10, color=COLOR_TEXT_SECONDARY),
                    ],
                ),
            ),
        )

    def _render_recent_calls(self):
        self.calls_list_column.controls.clear()
        if not self.recent_calls:
            self.calls_list_column.controls.append(
                ft.Text("لا توجد مكالمات مسجلة بعد، البوابة في وضع الاستعداد", size=11, color=COLOR_TEXT_MUTED, italic=True)
            )
            return

        for c in reversed(self.recent_calls[-5:]):
            self.calls_list_column.controls.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                    bgcolor=COLOR_BORDER_LIGHT,
                    border_radius=8,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.Icons.PHONE_IN_TALK_ROUNDED, size=14, color=COLOR_BURGUNDY),
                                    ft.Text(c["phone"], size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_PRIMARY),
                                ],
                            ),
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Text(f"{c['duration']} ثانية", size=11, color=COLOR_TEXT_MUTED),
                                    ft.Container(
                                        content=ft.Text("تمت بنجاح", size=9, color=COLOR_GREEN_TEXT, weight=ft.FontWeight.BOLD),
                                        bgcolor=COLOR_GREEN_BG,
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=6,
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )

    # ------------------ Event Handlers ------------------

    def _on_port_change(self, e):
        new_port = self.port_dropdown.value
        self.modem.connect(new_port)
        self.page.snack_bar = ft.SnackBar(ft.Text(f"تم التحويل إلى المنفذ: {new_port}"), bgcolor=COLOR_BURGUNDY)
        self.page.snack_bar.open = True
        self.page.update()

    def _handle_logout(self, e):
        self.modem.disconnect()
        self.api_client.clear_session()
        if self.on_logout:
            self.on_logout()

    def _trigger_simulated_call(self, e):
        phone = (self.sim_caller_input.value or "+201012345678").strip()
        self.modem.simulate_incoming_call(phone)

    def _on_modem_incoming_call(self, caller_number: str):
        """Called when modem detects RING from the SIM card."""
        if self.is_in_call:
            return

        self.is_in_call = True
        self.current_caller = caller_number
        self.call_start_time = time.time()

        # 1. Answer modem call via ATA
        self.modem.answer_call()

        # 2. Request LiveKit Room from Django Cloud API
        res = self.api_client.init_call(caller_phone=caller_number, dongle_id=self.modem.port)
        if res.get("success"):
            data = res.get("data", {})
            self.current_room = data.get("room_name", "")
            self.current_session_id = data.get("session_id")
        else:
            self.current_room = f"offline_room_{int(time.time())}"

        # 3. Update UI to Active Call State
        self.caller_number_text.value = self.current_caller
        self.call_timer_text.value = "00:01"
        self.active_call_card.visible = True
        self.page.update()

    def _end_call(self):
        """Terminate the call and report duration to cloud backend."""
        if not self.is_in_call:
            return

        duration = int(time.time() - self.call_start_time) if self.call_start_time else 0
        self.modem.hangup_call()

        # Report to Cloud API
        if self.current_room:
            self.api_client.hangup_call(
                room_name=self.current_room,
                duration_seconds=duration,
                session_id=self.current_session_id
            )

        # Update stats
        self.total_calls_today += 1
        self.calls_count_text.value = f"{self.total_calls_today} مكالمة"
        self.recent_calls.append({"phone": self.current_caller, "duration": max(duration, 1)})
        self._render_recent_calls()

        # Reset UI
        self.is_in_call = False
        self.current_caller = ""
        self.current_room = ""
        self.active_call_card.visible = False
        self.page.update()

    def _on_modem_call_ended(self):
        """Called when remote party closes connection."""
        self._end_call()

    def _toggle_mute(self, e):
        self.is_muted = not self.is_muted
        self.mute_btn.icon = ft.Icons.MIC_OFF_ROUNDED if self.is_muted else ft.Icons.MIC_ROUNDED
        self.mute_btn.icon_color = COLOR_RED if self.is_muted else COLOR_BURGUNDY
        self.page.update()

    def build(self) -> ft.Control:
        return ft.Container(
            expand=True,
            bgcolor=COLOR_CREAM,
            content=ft.Column(
                spacing=0,
                expand=True,
                controls=[
                    self.header,
                    ft.Container(
                        expand=True,
                        padding=14,
                        content=ft.ListView(
                            spacing=12,
                            controls=[
                                self.active_call_card,
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        self.signal_card,
                                        self.sim_card,
                                    ],
                                ),
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        self.latency_card,
                                        self.calls_card,
                                    ],
                                ),
                                self.hardware_card,
                                self.calls_history_card,
                            ],
                        ),
                    ),
                ],
            ),
        )
