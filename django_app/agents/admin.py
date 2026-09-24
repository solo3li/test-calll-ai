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
