from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.list_products, name='list_products'),
    path('orders/<str:order_id>/', views.get_order, name='get_order'),
    path('orders/', views.create_order, name='create_order'),
]
