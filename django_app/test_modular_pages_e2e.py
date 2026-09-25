"""
End-to-End Test for Modular Multi-Page Architecture:
- Verifies /calls/ renders dedicated page extending base.html.
- Verifies /billing/ renders dedicated page extending base.html.
- Verifies / renders room.html with navigation links and ?tab= query parameter support.
- Verifies static JS files (/static/js/common.js, /static/js/calls.js, /static/js/billing.js).
- Verifies unauthenticated users are redirected to /login/.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse


def test_modular_pages():
    print("\n========================================================")
    print("🚀 Running Modular Pages Multi-Page Architecture Test")
    print("========================================================")
    
    client = Client()
    test_user, _ = User.objects.get_or_create(username="test_pages_user", defaults={"email": "pages@example.com"})
    test_user.set_password("pass123")
    test_user.save()

    # 1. Unauthenticated redirects
    print("\n[TEST 1] Testing unauthenticated redirects to /login/...")
    r_calls = client.get('/calls/')
    assert r_calls.status_code == 302
    assert '/login/' in r_calls.url
    
    r_billing = client.get('/billing/')
    assert r_billing.status_code == 302
    assert '/login/' in r_billing.url
    print("✅ Unauthenticated protection verified on /calls/ and /billing/")

    # 2. Authenticated access to /calls/
    print("\n[TEST 2] Testing dedicated /calls/ page...")
    client.force_login(test_user)
    resp_calls = client.get('/calls/')
    assert resp_calls.status_code == 200, f"Expected 200, got {resp_calls.status_code}"
    content_calls = resp_calls.content.decode('utf-8')
    assert 'سجل كافة المكالمات (CDR)' in content_calls
    assert 'calls-table-tbody' in content_calls
    assert 'call-detail-modal' in content_calls
    assert 'cdm-recording-section' in content_calls
    assert 'js/calls.js' in content_calls
    assert 'js/common.js' in content_calls
    print("✅ /calls/ page successfully rendered with base layout, CDR table, audio player modal, and calls.js!")

    # 3. Authenticated access to /billing/
    print("\n[TEST 3] Testing dedicated /billing/ page...")
    resp_billing = client.get('/billing/')
    assert resp_billing.status_code == 200, f"Expected 200, got {resp_billing.status_code}"
    content_billing = resp_billing.content.decode('utf-8')
    assert 'حساب الاستخدام والرصيد' in content_billing
    assert 'billing-wallet-balance' in content_billing
    assert 'billing-transactions-tbody' in content_billing
    assert 'topup-modal' in content_billing
    assert 'js/billing.js' in content_billing
    assert 'js/common.js' in content_billing
    print("✅ /billing/ page successfully rendered with base layout, balance cards, top-up modal, and billing.js!")

    # 4. Main room.html navigation integration
    print("\n[TEST 4] Testing main / (room.html) links and tab param...")
    resp_room = client.get('/')
    assert resp_room.status_code == 200
    content_room = resp_room.content.decode('utf-8')
    assert '/calls/' in content_room
    assert '/billing/' in content_room
    assert 'URLSearchParams(window.location.search).get(\'tab\')' in content_room
    print("✅ / (room.html) contains direct links to /calls/ and /billing/ and handles ?tab= parameter!")

    # 5. Static files verification
    print("\n[TEST 5] Testing static files delivery...")
    resp_common = client.get('/static/js/common.js')
    assert resp_common.status_code in [200, 304], f"common.js status: {resp_common.status_code}"
    body_common = b''.join(resp_common.streaming_content) if hasattr(resp_common, 'streaming_content') else resp_common.content
    assert len(body_common) > 100
    
    resp_c_js = client.get('/static/js/calls.js')
    assert resp_c_js.status_code in [200, 304], f"calls.js status: {resp_c_js.status_code}"
    body_c = b''.join(resp_c_js.streaming_content) if hasattr(resp_c_js, 'streaming_content') else resp_c_js.content
    assert len(body_c) > 100

    resp_b_js = client.get('/static/js/billing.js')
    assert resp_b_js.status_code in [200, 304], f"billing.js status: {resp_b_js.status_code}"
    body_b = b''.join(resp_b_js.streaming_content) if hasattr(resp_b_js, 'streaming_content') else resp_b_js.content
    assert len(body_b) > 100
    print("✅ Static JS files (common.js, calls.js, billing.js) are properly served by Django static engine!")

    print("\n========================================================")
    print("🎉 ALL PHASE 1 MODULAR PAGES TESTS PASSED SUCCESSFULLY!")
    print("========================================================\n")


if __name__ == '__main__':
    test_modular_pages()
