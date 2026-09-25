"""
Serializers for Developer RESTful API (v1).
Used by Django REST Framework and drf-spectacular for auto-generated OpenAPI documentation.
"""
from rest_framework import serializers


class BaseSuccessResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    message = serializers.CharField(required=False)


class BaseErrorResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="error")
    message = serializers.CharField()


# ============================================================================
# Account & Stats
# ============================================================================

class UserAccountResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    wallet_balance = serializers.FloatField(help_text="Current wallet balance in USD")
    active_profile = serializers.DictField(allow_null=True)
    total_calls = serializers.IntegerField()
    total_documents = serializers.IntegerField()
    total_employees = serializers.IntegerField()
    total_mcp_servers = serializers.IntegerField()


# ============================================================================
# Voice Personas & Profiles
# ============================================================================

class AgentProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(help_text="اسم الشخصية (مثال: نورهان - خدمة عملاء)")
    voice_name = serializers.CharField(default="Aoede", help_text="صوت Google المعتمد (مثال: Aoede, Puck, Charon)")
    gender = serializers.ChoiceField(choices=[('female', 'أنثى'), ('male', 'ذكر')])
    language = serializers.CharField(default="arabic")
    dialect = serializers.CharField(default="egyptian", help_text="اللهجة الإقليمية")
    persona_role = serializers.CharField(required=False, allow_blank=True)
    speaking_style = serializers.CharField(required=False, allow_blank=True)
    verbosity = serializers.ChoiceField(choices=[('concise', 'موجز'), ('balanced', 'متوازن'), ('detailed', 'مفصل')])
    custom_instructions = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AgentProfileCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, help_text="اسم الشخصية")
    voice_name = serializers.CharField(default="Aoede")
    gender = serializers.ChoiceField(choices=[('female', 'أنثى'), ('male', 'ذكر')], default='female')
    language = serializers.CharField(default="arabic")
    dialect = serializers.CharField(default="egyptian")
    persona_role = serializers.CharField(required=False, default="خدمة عملاء ومبيعات المتجر")
    speaking_style = serializers.CharField(required=False, default="ودود ولطيف ومرح")
    verbosity = serializers.ChoiceField(choices=[('concise', 'موجز'), ('balanced', 'متوازن'), ('detailed', 'مفصل')], default='balanced')
    custom_instructions = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)


class AgentProfilesListResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    total = serializers.IntegerField()
    count = serializers.IntegerField()
    active_profile = AgentProfileSerializer(allow_null=True)
    profiles = AgentProfileSerializer(many=True)


class AgentStudioMetadataResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    google_voices = serializers.ListField(child=serializers.DictField())
    languages = serializers.ListField(child=serializers.DictField())
    language_dialects_map = serializers.DictField()
    genders = serializers.ListField(child=serializers.DictField())
    verbosities = serializers.ListField(child=serializers.DictField())
    sample_roles = serializers.ListField(child=serializers.CharField())
    sample_styles = serializers.ListField(child=serializers.CharField())


# ============================================================================
# Customer Memory & CRM
# ============================================================================

class CustomerMemorySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    phone_number = serializers.CharField(help_text="رقم هاتف العميل بالصيغة الدولية")
    customer_name = serializers.CharField(required=False, allow_blank=True)
    permanent_facts = serializers.CharField(required=False, allow_blank=True, help_text="الحقائق الدائمة والمستقرة عن العميل")
    immediate_context = serializers.CharField(required=False, allow_blank=True, help_text="السياق اللحظي لآخر محادثة")
    last_call_at = serializers.DateTimeField(read_only=True, allow_null=True)
    call_count = serializers.IntegerField(read_only=True)


class CustomerMemoryCreateRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    permanent_facts = serializers.CharField(required=False, allow_blank=True)
    immediate_context = serializers.CharField(required=False, allow_blank=True)


# ============================================================================
# RAG Knowledge Base & Documents
# ============================================================================

class DocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    file_name = serializers.CharField()
    file_type = serializers.CharField()
    file_size = serializers.IntegerField()
    chunk_count = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)


class RAGQueryRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, help_text="النص أو السؤال المراد البحث عنه دلالياً")
    limit = serializers.IntegerField(default=4, required=False, help_text="عدد المقاطع المطابقة")


class RAGQueryResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    query = serializers.CharField()
    matches_count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


# ============================================================================
# FastMCP External Tools
# ============================================================================

class MCPServerSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    url = serializers.URLField(help_text="SSE endpoint URL for FastMCP server")
    is_active = serializers.BooleanField()
    last_synced_at = serializers.DateTimeField(allow_null=True, read_only=True)
    tools = serializers.ListField(child=serializers.DictField(), read_only=True)


class MCPServerCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    url = serializers.URLField(required=True)
    is_active = serializers.BooleanField(default=True)


# ============================================================================
# Telephony & Trunks
# ============================================================================

class SIPTrunkSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    trunk_type = serializers.ChoiceField(choices=[('sip_trunk', 'SIP Trunk'), ('webrtc', 'WebRTC'), ('custom', 'Custom')])
    host = serializers.CharField()
    port = serializers.IntegerField()
    username = serializers.CharField()
    is_active = serializers.BooleanField()


class TelephonyNumberSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    phone_number = serializers.CharField()
    trunk_id = serializers.IntegerField(allow_null=True)
    route_to = serializers.CharField()
    is_active = serializers.BooleanField()


# ============================================================================
# Call Center: Employees & Queues
# ============================================================================

class EmployeeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    extension = serializers.CharField(help_text="رقم التحويلة الداخلية (مثال: 101)")
    department = serializers.CharField(required=False, allow_blank=True)
    protocol = serializers.CharField(default="webrtc_livekit")
    status = serializers.CharField(default="ready")
    is_available = serializers.BooleanField(default=True)


class EmployeeCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    extension = serializers.CharField(required=True)
    department = serializers.CharField(required=False, default="الدعم الفني")
    protocol = serializers.CharField(default="webrtc_livekit")
    is_available = serializers.BooleanField(default=True)


class QueueSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    queue_number = serializers.CharField(help_text="رقم الطابور المباشر (مثال: 800)")
    strategy = serializers.CharField(default="round_robin")
    timeout = serializers.IntegerField(default=30)
    members_count = serializers.IntegerField(read_only=True)


class QueueCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    queue_number = serializers.CharField(required=True)
    strategy = serializers.ChoiceField(choices=[('round_robin', 'دائري بالتناوب'), ('ring_all', 'رنين للجميع'), ('least_recent', 'الأقل استقبالاً')], default='round_robin')
    timeout = serializers.IntegerField(default=30)


# ============================================================================
# WebRTC Calls, CDR & Dialing
# ============================================================================

class WebRTCTokenResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    token = serializers.CharField(help_text="LiveKit JWT Token for WebRTC browser connection")
    room = serializers.CharField(help_text="LiveKit Room Name")
    identity = serializers.CharField(help_text="Participant Identity")
    livekit_url = serializers.CharField(help_text="LiveKit Server URL")


class DialCallRequestSerializer(serializers.Serializer):
    to_number = serializers.CharField(required=True, help_text="الرقم المراد الاتصال به أو التحويلة الداخلية")
    from_number = serializers.CharField(required=False, allow_blank=True, help_text="الرقم الصادر المسجل في السنترال")
    persona_id = serializers.IntegerField(required=False, allow_null=True, help_text="معرف شخصية الذكاء الاصطناعي")
    scenario_prompt = serializers.CharField(required=False, allow_blank=True, help_text="توجيهات وسيناريو خاص للمكالمة")


class DialCallResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    call_id = serializers.CharField()
    room_name = serializers.CharField()
    to_number = serializers.CharField()
    direction = serializers.CharField(default="outbound")


class HangupCallRequestSerializer(serializers.Serializer):
    call_id = serializers.CharField(required=True, help_text="معرف جلسة المكالمة المراد إنهاؤها")


class CallSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    call_id = serializers.CharField()
    from_number = serializers.CharField()
    to_number = serializers.CharField()
    status = serializers.CharField()
    duration = serializers.IntegerField()
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField(allow_null=True)
    recording_url = serializers.URLField(allow_null=True)
    summary = serializers.CharField(allow_blank=True)


class WebhookEventSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    event_type = serializers.CharField()
    payload = serializers.DictField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
