from django.contrib import admin
from .models import Product, Order

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'stock', 'category')
    search_fields = ('name', 'category', 'description')
    list_filter = ('category',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'customer_name', 'product_name', 'quantity', 'total_price', 'status', 'created_at')
    search_fields = ('order_id', 'customer_name', 'customer_phone', 'product_name')
    list_filter = ('status', 'created_at')
