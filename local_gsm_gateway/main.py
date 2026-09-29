"""Local GSM USB Dongle AI Voice Gateway Flet Application Entrypoint.

Starts the Flet application in a modern mobile form factor (400x800).
Loads saved session for automatic login, or shows the Owner Login screen.
"""
import sys
import os

# Ensure package path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import flet as ft
from theme import COLOR_CREAM, COLOR_BURGUNDY, FONT_FAMILY
from controllers.api_client import DongleApiClient
from views.login_view import LoginView
from views.dashboard_view import DashboardView


def main(page: ft.Page):
    page.title = "بوابة الاتصال الخلوي الذكية"
    page.width = 410
    page.height = 820
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = COLOR_CREAM
    page.padding = 0

    # API Client instance
    api_client = DongleApiClient()

    def show_dashboard():
        page.clean()
        dashboard = DashboardView(page, api_client, on_logout=show_login)
        page.add(dashboard.build())
        page.update()

    def show_login():
        page.clean()
        login = LoginView(page, api_client, on_login_success=show_dashboard)
        page.add(login.build())
        page.update()

    # Check for Auto-Login (Remember Me session)
    if api_client.token and api_client.user_data:
        # Validate token with cloud backend
        status = api_client.get_status()
        if status.get("success"):
            show_dashboard()
            return

    # If no session or expired token, show login screen
    show_login()


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main)
    elif hasattr(ft, "app"):
        ft.app(target=main)
    else:
        raise RuntimeError("No app runner found in flet module")
