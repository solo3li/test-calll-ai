from django.contrib import admin
from .models import OutboundSIPTrunk

@admin.register(OutboundSIPTrunk)
class OutboundSIPTrunkAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'sip_host', 'sip_port', 'transport', 'caller_id', 'livekit_outbound_trunk_id', 'is_default', 'is_active', 'created_at')
    list_filter = ('transport', 'is_active', 'is_default', 'user')
    search_fields = ('name', 'sip_host', 'caller_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
