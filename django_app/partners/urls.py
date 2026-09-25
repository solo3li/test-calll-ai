from django.urls import path
from . import views

urlpatterns = [
    # Platform UI endpoints (for authenticated user dashboard in room.html)
    path('apply/', views.apply_partner, name='partner_apply'),
    path('dashboard/', views.get_partner_dashboard, name='partner_dashboard'),
    path('settings/', views.update_partner_settings, name='partner_settings'),
    path('settings/test-webhook/', views.test_partner_webhook, name='partner_test_webhook'),
    path('clients/cap/', views.update_client_cap, name='partner_client_cap'),

    path('docs/', views.api_partner_docs, name='partner_docs'),
    path('docs/openapi.json', views.api_partner_openapi_spec, name='partner_openapi_spec'),
    path('docs/scalar/', views.api_partner_docs_scalar, name='partner_docs_scalar'),

    # Headless REST API v1 for Partner SaaS Server-to-Server Integrations
    path('studio/', views.api_partner_studio, name='api_partner_studio'),
    path('clients/register/', views.api_partner_register_client, name='api_partner_register_client'),
    path('clients/', views.api_partner_list_clients, name='api_partner_list_clients'),
    path('clients/<int:client_id>/calls/', views.api_partner_client_calls, name='api_partner_client_calls'),
    path('clients/<int:client_id>/calls/dial/', views.api_partner_client_call_dial, name='api_partner_client_calls_dial'),
    path('clients/<int:client_id>/calls/hangup/', views.api_partner_client_call_hangup, name='api_partner_client_call_hangup'),
    path('clients/<int:client_id>/profiles/', views.api_partner_client_profile, name='api_partner_client_profile'),
    path('clients/<int:client_id>/profiles/studio/', views.api_partner_studio, name='api_partner_client_studio'),
    path('clients/<int:client_id>/profiles/<int:profile_id>/', views.api_partner_client_profile_detail, name='api_partner_client_profile_detail'),
    path('clients/<int:client_id>/profiles/<int:profile_id>/activate/', views.api_partner_client_profile_activate, name='api_partner_client_profile_activate'),
    path('clients/<int:client_id>/memory/', views.api_partner_client_memory, name='api_partner_client_memory'),
    path('clients/<int:client_id>/memory/<int:memory_id>/', views.api_partner_client_memory_detail, name='api_partner_client_memory_detail'),
    path('clients/<int:client_id>/documents/', views.api_partner_client_documents, name='api_partner_client_documents'),
    path('clients/<int:client_id>/rag/query/', views.api_partner_client_rag_query, name='api_partner_client_rag_query'),
    path('clients/<int:client_id>/telephony/', views.api_partner_client_telephony, name='api_partner_client_telephony'),
    path('clients/<int:client_id>/telephony/numbers/', views.api_partner_client_numbers, name='api_partner_client_numbers'),
    path('clients/<int:client_id>/telephony/<str:trunk_type>/<int:trunk_id>/', views.api_partner_client_telephony_detail, name='api_partner_client_telephony_detail'),
    path('clients/<int:client_id>/employees/', views.api_partner_client_employees, name='api_partner_client_employees'),
    path('clients/<int:client_id>/employees/<int:employee_id>/', views.api_partner_client_employee_detail, name='api_partner_client_employee_detail'),
    path('clients/<int:client_id>/queues/', views.api_partner_client_queues, name='api_partner_client_queues'),
    path('clients/<int:client_id>/queues/<int:queue_id>/', views.api_partner_client_queue_detail, name='api_partner_client_queue_detail'),
    path('clients/<int:client_id>/queues/<int:queue_id>/members/', views.api_partner_client_queue_members, name='api_partner_client_queue_members'),
    path('clients/<int:client_id>/mcp/', views.api_partner_client_mcp, name='api_partner_client_mcp'),
    path('clients/<int:client_id>/mcp/<int:mcp_id>/', views.api_partner_client_mcp_detail, name='api_partner_client_mcp_detail'),
    path('clients/<int:client_id>/mcp/<int:mcp_id>/sync/', views.api_partner_client_mcp_sync, name='api_partner_client_mcp_sync'),
    path('clients/<int:client_id>/token/', views.api_partner_client_token, name='api_partner_client_token'),

    # Managed Client Campaigns (Inngest Powered)
    path('clients/<int:client_id>/campaigns/', views.api_partner_client_campaigns, name='api_partner_client_campaigns'),
    path('clients/<int:client_id>/campaigns/<int:campaign_id>/', views.api_partner_client_campaign_detail, name='api_partner_client_campaign_detail'),
    path('clients/<int:client_id>/campaigns/<int:campaign_id>/start/', views.api_partner_client_campaign_start, name='api_partner_client_campaign_start'),
    path('clients/<int:client_id>/campaigns/<int:campaign_id>/pause/', views.api_partner_client_campaign_pause, name='api_partner_client_campaign_pause'),
]

