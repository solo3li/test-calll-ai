from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
import inngest.django
from crm.inngest_jobs import inngest_client, all_inngest_functions

urlpatterns = [
    inngest.django.serve(inngest_client, all_inngest_functions, serve_path="/api/inngest/"),
    path('admin/', admin.site.urls),
    path('api/knowledge/', include('knowledge.urls')),
    path('api/agents/', include('agents.urls')),
    path('api/call-center/', include('call_center.urls')),
    path('api/telephony/', include('telephony.urls')),
    path('api/crm/', include('crm.urls')),
    path('api/billing/', include('billing.urls')),
    path('api/partner/v1/', include('partners.urls')),
    path('api/v1/', include('developer.urls')),
    path('', include('voice_assistant.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
