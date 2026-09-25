"""
End-to-End Test for Modular Multi-Page Architecture:
- Verifies /calls/ renders dedicated page extending base.html.
- Verifies /billing/ renders dedicated page extending base.html.
- Verifies /crm/ renders dedicated page extending base.html.
- Verifies /documents/ renders dedicated page extending base.html.
- Verifies /personas/ renders dedicated page extending base.html.
- Verifies / renders room.html with updated sidebar navigation links and ?tab= query parameter support.
- Verifies static JS files (/static/js/common.js, /static/js/calls.js, /static/js/billing.js, /static/js/crm.js, /static/js/rag.js, /static/js/personas.js).
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
    for endpoint in ['/calls/', '/billing/', '/crm/', '/documents/', '/personas/']:
        resp = client.get(endpoint)
        assert resp.status_code == 302, f"Expected 302 redirect for {endpoint}, got {resp.status_code}"
        assert '/login/' in resp.url
    print("✅ Unauthenticated protection verified on all modular routes!")

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

    # 4. Authenticated access to /crm/
    print("\n[TEST 4] Testing dedicated /crm/ page...")
    resp_crm = client.get('/crm/')
    assert resp_crm.status_code == 200, f"Expected 200, got {resp_crm.status_code}"
    content_crm = resp_crm.content.decode('utf-8')
    assert 'Two-Tier Distilled Memory' in content_crm
    assert 'memory-permanent-content' in content_crm
    assert 'memory-immediate-content' in content_crm
    assert 'memory-recent-calls' in content_crm
    assert 'js/crm.js' in content_crm
    assert 'js/common.js' in content_crm
    print("✅ /crm/ page successfully rendered with customer memory cards, recent calls, and crm.js!")

    # 5. Authenticated access to /documents/ (RAG)
    print("\n[TEST 5] Testing dedicated /documents/ (RAG) page...")
    resp_rag = client.get('/documents/')
    assert resp_rag.status_code == 200, f"Expected 200, got {resp_rag.status_code}"
    content_rag = resp_rag.content.decode('utf-8')
    assert 'RAG Knowledge Base' in content_rag
    assert 'upload-form' in content_rag
    assert 'docs-tbody' in content_rag
    assert 'js/rag.js' in content_rag
    assert 'js/common.js' in content_rag
    print("✅ /documents/ page successfully rendered with upload form, docs table, and rag.js!")

    # 6. Authenticated access to /personas/
    print("\n[TEST 6] Testing dedicated /personas/ page...")
    resp_personas = client.get('/personas/')
    assert resp_personas.status_code == 200, f"Expected 200, got {resp_personas.status_code}"
    content_personas = resp_personas.content.decode('utf-8')
    assert 'الشخصيات المتاحة للمحادثات' in content_personas
    assert 'personas-cards-grid' in content_personas
    assert 'profile-editor-card' in content_personas
    assert 'profile-modal' in content_personas
    assert 'js/personas.js' in content_personas
    assert 'js/common.js' in content_personas
    print("✅ /personas/ page successfully rendered with studio editor, profile modal, and personas.js!")

    # 7. Main room.html navigation integration
    print("\n[TEST 7] Testing main / (room.html) links and tab param...")
    resp_room = client.get('/')
    assert resp_room.status_code == 200
    content_room = resp_room.content.decode('utf-8')
    assert '/calls/' in content_room
    assert '/billing/' in content_room
    assert '/crm/' in content_room
    assert '/documents/' in content_room
    assert '/personas/' in content_room
    assert 'URLSearchParams(window.location.search).get(\'tab\')' in content_room
    print("✅ / (room.html) contains direct links to /calls/, /billing/, /crm/, /documents/, and /personas/!")

    # 8. Static files delivery verification
    print("\n[TEST 8] Testing static JS files delivery...")
    static_files = [
        'common.js',
        'calls.js',
        'billing.js',
        'crm.js',
        'rag.js',
        'personas.js',
    ]
    for sf in static_files:
        resp_sf = client.get(f'/static/js/{sf}')
        assert resp_sf.status_code in [200, 304], f"{sf} status: {resp_sf.status_code}"
        body = b''.join(resp_sf.streaming_content) if hasattr(resp_sf, 'streaming_content') else resp_sf.content
        assert len(body) > 100, f"{sf} file content too short ({len(body)} bytes)"
    print(f"✅ All {len(static_files)} static JS files are properly served with non-empty content!")

    print("\n========================================================")
    print("🎉 ALL PHASE 1 & PHASE 2 MODULAR PAGES TESTS PASSED! (100%)")
    print("========================================================\n")


if __name__ == '__main__':
    test_modular_pages()
