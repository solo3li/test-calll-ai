from django.contrib import admin
from .models import CustomerMemory, CallSession

@admin.register(CustomerMemory)
class CustomerMemoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone_number', 'customer_name', 'total_calls_count', 'last_interaction_at', 'updated_at')
    list_filter = ('updated_at', 'user')
    search_fields = ('user__username', 'phone_number', 'customer_name', 'last_interaction_summary')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'room_name', 'user', 'direction', 'caller_phone', 'destination_phone', 'duration_seconds', 'started_at', 'ended_at')
    list_filter = ('direction', 'started_at', 'user')
    search_fields = ('room_name', 'caller_phone', 'destination_phone', 'call_goal', 'summary', 'user__username')
    readonly_fields = ('started_at',)
