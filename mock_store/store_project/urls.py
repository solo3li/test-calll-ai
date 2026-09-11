from django.contrib import admin
from django.urls import path, include
from store_api import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.store_home, name='store_home'),
    path('api/', include('store_api.urls')),
]

