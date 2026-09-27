from django.contrib import admin
from .models import AgentProfile, UserMCPServer, SystemSetting

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'masked_api_key', 'updated_at')
    readonly_fields = ('updated_at',)

    def masked_api_key(self, obj):
        key = (obj.gemini_api_key or "").strip()
        if len(key) > 8:
            return f"{key[:4]}...{key[-4:]}"
        return "غير محدد" if not key else "******"
    masked_api_key.short_description = "Google Gemini API Key"

    def has_add_permission(self, request):
        return not SystemSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'voice_name', 'gender', 'dialect', 'persona_role', 'speaking_style', 'is_active', 'updated_at')
    list_filter = ('is_active', 'gender', 'dialect', 'persona_role', 'user')
    search_fields = ('name', 'custom_instructions', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserMCPServer)
class UserMCPServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'server_url', 'is_active', 'tools_count', 'last_synced_at')
    list_filter = ('is_active', 'user')
    search_fields = ('name', 'server_url', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'last_synced_at')

    def tools_count(self, obj):
        tools = obj.cached_tools
        if isinstance(tools, list):
            return len(tools)
        return 0
    tools_count.short_description = "الأدوات المتوفرة"


import json
from django.utils.html import format_html, mark_safe
from django.db.models import Avg, Count
from .models import AgentToolCallLog


@admin.register(AgentToolCallLog)
class AgentToolCallLogAdmin(admin.ModelAdmin):
    change_list_template = "admin/agents/agenttoolcalllog/change_list.html"
    list_display = (
        'id',
        'status_badge',
        'tool_badge',
        'user',
        'caller_display',
        'execution_time_badge',
        'short_error_message',
        'created_at_formatted'
    )
    list_filter = ('status', 'tool_type', 'tool_name', 'created_at', 'user')
    search_fields = (
        'tool_name',
        'room_name',
        'caller_phone',
        'error_message',
        'server_name',
        'user__username'
    )
    date_hierarchy = 'created_at'
    list_per_page = 30

    readonly_fields = (
        'id',
        'user',
        'call_session',
        'room_name',
        'caller_phone',
        'tool_name',
        'tool_type',
        'server_name',
        'server_url',
        'status',
        'error_type',
        'error_message',
        'execution_time_ms',
        'formatted_arguments',
        'response_preview',
        'formatted_raw_response',
        'created_at'
    )

    fieldsets = (
        ('معلومات الاستدعاء والحالة', {
            'fields': (
                ('status', 'error_type'),
                ('tool_name', 'tool_type'),
                ('user', 'caller_phone'),
                ('room_name', 'call_session'),
                ('server_name', 'server_url'),
                ('execution_time_ms', 'created_at'),
            )
        }),
        ('تفاصيل الخطأ (إن وُجد)', {
            'fields': ('error_message',),
        }),
        ('المدخلات والردود البرمجية', {
            'fields': ('formatted_arguments', 'response_preview', 'formatted_raw_response')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def changelist_view(self, request, extra_context=None):
        # Calculate high-level KPIs for superadmin banner
        qs = self.get_queryset(request)
        total_count = qs.count()
        success_count = qs.filter(status='success').count()
        failed_count = qs.exclude(status='success').count()
        success_rate = round((success_count / total_count * 100), 1) if total_count > 0 else 0
        avg_ms = qs.aggregate(avg=Avg('execution_time_ms'))['avg'] or 0

        # Most failing tool
        failing_tool = (
            qs.exclude(status='success')
            .values('tool_name')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
            .first()
        )
        failing_tool_name = failing_tool['tool_name'] if failing_tool else "لا توجد أخطاء"
        failing_tool_count = failing_tool['cnt'] if failing_tool else 0

        kpi_html = f"""
        <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;font-family:sans-serif;">
            <div style="flex:1;min-width:180px;background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:4px solid #3b82f6;">
                <div style="font-size:12px;color:#6b7280;font-weight:600;margin-bottom:4px;">إجمالي الاستدعاءات</div>
                <div style="font-size:24px;font-weight:700;color:#111827;">{total_count:,}</div>
                <div style="font-size:11px;color:#9ca3af;margin-top:2px;">كافة الأدوات المسجلة</div>
            </div>
            <div style="flex:1;min-width:180px;background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:4px solid #10b981;">
                <div style="font-size:12px;color:#047857;font-weight:600;margin-bottom:4px;">الاستدعاءات الناجحة</div>
                <div style="font-size:24px;font-weight:700;color:#065f46;">{success_count:,} <span style="font-size:14px;font-weight:600;color:#10b981;">({success_rate}%)</span></div>
                <div style="font-size:11px;color:#059669;margin-top:2px;">معدل النجاح الإجمالي</div>
            </div>
            <div style="flex:1;min-width:180px;background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:4px solid #ef4444;">
                <div style="font-size:12px;color:#b91c1c;font-weight:600;margin-bottom:4px;">الاستدعاءات الفاشلة</div>
                <div style="font-size:24px;font-weight:700;color:#991b1b;">{failed_count:,}</div>
                <div style="font-size:11px;color:#dc2626;margin-top:2px;">أكثر أداة بها أخطاء: {failing_tool_name} ({failing_tool_count})</div>
            </div>
            <div style="flex:1;min-width:180px;background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;box-shadow:0 1px 3px rgba(0,0,0,0.05);border-top:4px solid #8b5cf6;">
                <div style="font-size:12px;color:#6d28d9;font-weight:600;margin-bottom:4px;">متوسط سرعة الاستجابة</div>
                <div style="font-size:24px;font-weight:700;color:#5b21b6;">{int(avg_ms)} <span style="font-size:13px;font-weight:500;">ms</span></div>
                <div style="font-size:11px;color:#7c3aed;margin-top:2px;">زمن المعالجة الفعلي</div>
            </div>
        </div>
        """

        extra_context = extra_context or {}
        extra_context['kpi_banner'] = mark_safe(kpi_html)
        return super().changelist_view(request, extra_context=extra_context)

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
            '<span style="background:{};color:{};font-weight:600;padding:3px 9px;border-radius:12px;font-size:11px;display:inline-block;white-space:nowrap;">{}</span>',
            bg, text_color, label
        )
    status_badge.short_description = "الحالة"

    def tool_badge(self, obj):
        type_colors = {
            'mcp': ('#e1effe', '#1e429f', 'FastMCP'),
            'rag': ('#fef9c3', '#854d0e', 'RAG'),
            'memory': ('#dcfce7', '#166534', 'ذاكرة CRM'),
            'transfer': ('#e0e7ff', '#3730a3', 'تحويل طابور'),
        }
        bg, text_color, type_label = type_colors.get(obj.tool_type, ('#f3f4f6', '#374151', obj.tool_type))
        return format_html(
            '<div style="font-weight:700;font-size:12px;color:#111827;">{}</div>'
            '<span style="background:{};color:{};font-size:10px;font-weight:600;padding:1px 6px;border-radius:6px;display:inline-block;margin-top:2px;">{}</span>',
            obj.tool_name, bg, text_color, type_label
        )
    tool_badge.short_description = "الأداة والنوع"

    def caller_display(self, obj):
        phone = obj.caller_phone or "لوحة التحكم"
        return format_html(
            '<div style="font-size:12px;font-weight:600;color:#1f2937;">{}</div>'
            '<div style="font-size:10px;color:#6b7280;font-family:monospace;">{}</div>',
            phone, obj.room_name[:22]
        )
    caller_display.short_description = "المتصل / الغرفة"

    def execution_time_badge(self, obj):
        ms = obj.execution_time_ms
        if ms < 500:
            color = "#057a55"
        elif ms < 1500:
            color = "#d97706"
        else:
            color = "#e02424"
        return format_html('<span style="color:{};font-weight:700;font-size:11px;">{} ms</span>', color, ms)
    execution_time_badge.short_description = "زمن التنفيذ"

    def short_error_message(self, obj):
        if not obj.error_message:
            return format_html('<span style="color:#9ca3af;font-size:11px;">—</span>')
        return format_html(
            '<div style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;color:#b91c1c;" title="{}">{}</div>',
            obj.error_message, obj.error_message[:45] + ("..." if len(obj.error_message) > 45 else "")
        )
    short_error_message.short_description = "سبب الخطأ"

    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    created_at_formatted.short_description = "التوقيت"

    def formatted_arguments(self, obj):
        content = json.dumps(obj.arguments or {}, ensure_ascii=False, indent=2)
        return format_html('<pre style="background:#1e293b;color:#f8fafc;padding:12px;border-radius:8px;font-size:12px;max-height:300px;overflow:auto;">{}</pre>', content)
    formatted_arguments.short_description = "المدخلات (JSON)"

    def formatted_raw_response(self, obj):
        raw = obj.raw_response
        if isinstance(raw, (dict, list)):
            content = json.dumps(raw, ensure_ascii=False, indent=2)
        else:
            content = str(raw or "")
        return format_html('<pre style="background:#0f172a;color:#38bdf8;padding:12px;border-radius:8px;font-size:12px;max-height:400px;overflow:auto;">{}</pre>', content)
    formatted_raw_response.short_description = "الرد الكامل (JSON/Raw)"
