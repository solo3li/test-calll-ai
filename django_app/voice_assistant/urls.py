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
]
