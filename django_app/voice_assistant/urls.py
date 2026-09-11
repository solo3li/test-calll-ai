from django.urls import path
from . import views

app_name = 'voice_assistant'

urlpatterns = [
    path('', views.room_view, name='room'),
    path('api/token/', views.get_tokens, name='get_tokens'),
    path('api/livekit/webhook/', views.livekit_webhook, name='livekit_webhook'),
]
