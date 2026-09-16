from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/knowledge/', include('knowledge.urls')),
    path('api/agents/', include('agents.urls')),
    path('api/call-center/', include('call_center.urls')),
    path('api/telephony/', include('telephony.urls')),
    path('api/crm/', include('crm.urls')),
    path('', include('voice_assistant.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
