from django.contrib import admin
from django.utils.html import format_html
from agents.models import AgentToolCallLog
from .models import CustomerMemory, CallSession, UserCampaignLimit, OutboundCampaign, CampaignContact

class AgentToolCallLogInline(admin.TabularInline):
    model = AgentToolCallLog
    extra = 0
    can_delete = False
    readonly_fields = (
        'status_badge',
        'tool_badge',
        'execution_time_badge',
        'short_error_message',
        'created_at_formatted',
    )
    fields = (
        'status_badge',
        'tool_badge',
        'execution_time_badge',
        'short_error_message',
        'created_at_formatted',
    )
    show_change_link = True
    verbose_name = "استدعاء أداة ذكاء اصطناعي"
    verbose_name_plural = "استدعاءات الأدوات أثناء هذه المكالمة (AI Tool Calls)"

    def has_add_permission(self, request, obj=None):
        return False

    def status_badge(self, obj):
        colors = {
            'success': ('#def7ec', '#03543f', '✓ ناجح'),
            'failed': ('#fde8e8', '#9b1c1c', '✕ فشل أداة'),
            'timeout': ('#fef08a', '#713f12', '⏱ انتهاء مهلة'),
            'connection_error': ('#f3e8ff', '#6b21a8', '⚡ فشل اتصال'),
            'validation_error': ('#ffedd5', '#9a3412', '⚠ خطأ مدخلات'),
        }
        bg, text_color, label = colors.get(obj.status, ('#f3f4f6', '#374151', obj.status))
        return format_html(
            '<span style="background:{};color:{};font-weight:600;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            bg, text_color, label
        )
    status_badge.short_description = "الحالة"

    def tool_badge(self, obj):
        return format_html(
            '<strong>{}</strong> <span style="color:#6b7280;font-size:11px;">({})</span>',
            obj.tool_name, obj.get_tool_type_display()
        )
    tool_badge.short_description = "الأداة"

    def execution_time_badge(self, obj):
        return format_html('<span>{} ms</span>', obj.execution_time_ms)
    execution_time_badge.short_description = "الزمن"

    def short_error_message(self, obj):
        if not obj.error_message:
            return "—"
        return obj.error_message[:50] + ("..." if len(obj.error_message) > 50 else "")
    short_error_message.short_description = "السبب / الخطأ"

    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%H:%M:%S") if obj.created_at else "—"
    created_at_formatted.short_description = "الوقت"


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'room_name', 'user', 'direction', 'caller_phone', 'destination_phone', 'duration_seconds', 'started_at', 'ended_at')
    list_filter = ('direction', 'started_at', 'user')
    search_fields = ('room_name', 'caller_phone', 'destination_phone', 'call_goal', 'summary', 'user__username')
    readonly_fields = ('started_at',)
    inlines = [AgentToolCallLogInline]

class CampaignContactInline(admin.TabularInline):
    model = CampaignContact
    extra = 0
    readonly_fields = ('phone_number', 'customer_name', 'call_status', 'interest_level', 'retries_count', 'duration_seconds')
    fields = ('phone_number', 'customer_name', 'call_status', 'interest_level', 'retries_count', 'duration_seconds')
    can_delete = True
    show_change_link = True

@admin.register(OutboundCampaign)
class OutboundCampaignAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'status', 'total_contacts', 'completed_contacts', 'answered_contacts', 'hot_leads_count', 'warm_leads_count', 'created_at')
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('name', 'call_prompt', 'user__username')
    readonly_fields = ('total_contacts', 'completed_contacts', 'answered_contacts', 'hot_leads_count', 'warm_leads_count', 'cold_leads_count', 'created_at', 'updated_at')
    inlines = [CampaignContactInline]

@admin.register(CampaignContact)
class CampaignContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'phone_number', 'campaign', 'call_status', 'interest_level', 'retries_count', 'duration_seconds', 'last_attempt_at')
    list_filter = ('call_status', 'interest_level', 'campaign')
    search_fields = ('customer_name', 'phone_number', 'call_summary', 'campaign__name')
    readonly_fields = ('created_at', 'updated_at')

