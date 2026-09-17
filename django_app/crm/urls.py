from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    path('customers/', views.list_customers_memory, name='list_customers_memory'),
    path('memory/', views.get_customer_memory, name='get_customer_memory'),
    path('memory/reset/', views.reset_customer_memory, name='reset_customer_memory'),
    path('internal/memory/', views.api_internal_get_customer_memory, name='api_internal_get_customer_memory'),
    path('internal/complete-call/', views.api_internal_save_call_session_and_memory, name='api_internal_save_call_session_and_memory'),
    path('internal/save-session-and-memory/', views.api_internal_save_call_session_and_memory, name='api_internal_save_session_and_memory_alias'),
]
