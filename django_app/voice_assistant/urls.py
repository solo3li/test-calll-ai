from django.urls import path
from . import views

app_name = 'voice_assistant'

urlpatterns = [
    # Auth Views
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Voice Assistant Main Room
    path('', views.room_view, name='room'),

    # Real-Time & WebRTC APIs
    path('api/token/', views.get_tokens, name='get_tokens'),
    path('api/livekit/webhook/', views.livekit_webhook, name='livekit_webhook'),

    # Document Management & RAG APIs
    path('api/documents/', views.list_documents, name='list_documents'),
    path('api/documents/upload/', views.upload_document, name='upload_document'),
    path('api/documents/<int:doc_id>/delete/', views.delete_document, name='delete_document'),

    # Actions Management APIs
    path('api/actions/', views.list_actions, name='list_actions'),
    path('api/actions/create/', views.create_action, name='create_action'),
    path('api/actions/<int:action_id>/toggle/', views.toggle_action, name='toggle_action'),
    path('api/actions/<int:action_id>/delete/', views.delete_action, name='delete_action'),

    # Voice, Dialect & Persona Profiles APIs
    path('api/profiles/', views.list_profiles, name='list_profiles'),
    path('api/profiles/create/', views.create_profile, name='create_profile'),
    path('api/profiles/<int:profile_id>/activate/', views.activate_profile, name='activate_profile'),
    path('api/profiles/<int:profile_id>/update/', views.update_profile, name='update_profile'),
    path('api/profiles/<int:profile_id>/delete/', views.delete_profile, name='delete_profile'),

    # External MCP Server APIs
    path('api/mcp/', views.get_mcp_server, name='get_mcp_server'),
    path('api/mcp/save/', views.save_mcp_server, name='save_mcp_server'),
    path('api/mcp/sync/', views.sync_mcp_server, name='sync_mcp_server'),
    path('api/mcp/toggle/', views.toggle_mcp_server, name='toggle_mcp_server'),
    path('api/mcp/delete/', views.delete_mcp_server, name='delete_mcp_server'),

    # Customer Memory & Call History APIs
    path('api/memory/', views.get_customer_memory, name='get_customer_memory'),
    path('api/memory/reset/', views.reset_customer_memory, name='reset_customer_memory'),

    # MicroSIP & VoIP Lines APIs
    path('api/sip/', views.list_sip_accounts, name='list_sip_accounts'),
    path('api/sip/create/', views.create_sip_account, name='create_sip_account'),
    path('api/sip/<int:account_id>/delete/', views.delete_sip_account, name='delete_sip_account'),

    # Call Queues & Routing APIs
    path('api/queues/', views.list_call_queues, name='list_call_queues'),
    path('api/queues/create/', views.create_call_queue, name='create_call_queue'),
    path('api/queues/<int:queue_id>/delete/', views.delete_call_queue, name='delete_call_queue'),
]


