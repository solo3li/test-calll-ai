from django.contrib import admin
from .models import CustomerMemory, CallSession

@admin.register(CustomerMemory)
class CustomerMemoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'customer_name_preview', 'total_calls_count', 'last_interaction_at', 'updated_at')
    list_filter = ('updated_at', 'user')
    search_fields = ('user__username', 'last_interaction_summary')
    readonly_fields = ('created_at', 'updated_at')

    def customer_name_preview(self, obj):
        prof = obj.permanent_profile or {}
        if isinstance(prof, dict):
            return prof.get('customer_name', 'غير محدد')
        return 'غير محدد'
    customer_name_preview.short_description = "اسم العميل"

@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'room_name', 'user', 'direction', 'destination_phone', 'duration_seconds', 'started_at', 'ended_at')
    list_filter = ('direction', 'started_at', 'user')
    search_fields = ('room_name', 'destination_phone', 'call_goal', 'summary', 'user__username')
    readonly_fields = ('started_at',)
