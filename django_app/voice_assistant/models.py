from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField, HnswIndex

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_chunks')
    chunk_index = models.IntegerField(default=0)
    content = models.TextField()
    embedding = VectorField(dimensions=768)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['chunk_index']
        indexes = [
            HnswIndex(
                name='docchunk_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            )
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"

class UserAction(models.Model):
    HTTP_METHODS = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actions')
    name = models.CharField(max_length=64)
    description = models.TextField()
    url = models.URLField(max_length=500)
    method = models.CharField(max_length=10, choices=HTTP_METHODS, default='GET')
    headers = models.JSONField(default=dict, blank=True)
    parameters_schema = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def to_gemini_declaration(self):
        """Convert this action to a Gemini FunctionDeclaration dictionary."""
        decl = {
            "name": self.name,
            "description": self.description,
        }
        if self.parameters_schema and isinstance(self.parameters_schema, dict) and self.parameters_schema.get("properties"):
            decl["parameters"] = self.parameters_schema
        return decl

class AgentProfile(models.Model):
    GENDER_CHOICES = [
        ('female', 'أنثى'),
        ('male', 'ذكر'),
    ]

    DIALECT_CHOICES = [
        ('egyptian', 'لهجة مصرية عامية'),
        ('saudi', 'لهجة خليجية / سعودية'),
        ('levantine', 'لهجة شامية'),
        ('fusha', 'عربية فصحى معاصرة'),
        ('english', 'English'),
    ]

    ROLE_CHOICES = [
        ('customer_support', 'خدمة عملاء ومبيعات المتجر'),
        ('sales_advisor', 'مستشار تسويق ومبيعات شاطر'),
        ('personal_assistant', 'مساعد شخصي ذكي وودود'),
        ('technical_consultant', 'مستشار فني ورسمي'),
    ]

    STYLE_CHOICES = [
        ('friendly', 'ودود ولطيف ومرح'),
        ('formal', 'رسمي وهادئ ورصين'),
        ('concise', 'مباشر وسريع وموجز'),
        ('enthusiastic', 'حماسي وتشجيعي'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_profiles')
    name = models.CharField(max_length=100, default='البروفايل الافتراضي')
    voice_name = models.CharField(max_length=50, default='Aoede')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='female')
    dialect = models.CharField(max_length=50, choices=DIALECT_CHOICES, default='egyptian')
    persona_role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='customer_support')
    speaking_style = models.CharField(max_length=50, choices=STYLE_CHOICES, default='friendly')
    custom_instructions = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        active_str = " [نشط]" if self.is_active else ""
        return f"{self.name} ({self.voice_name}/{self.dialect}){active_str}"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Ensure only one active profile per user
            AgentProfile.objects.filter(user=self.user, is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "voice_name": self.voice_name,
            "gender": self.gender,
            "gender_display": self.get_gender_display(),
            "dialect": self.dialect,
            "dialect_display": self.get_dialect_display(),
            "persona_role": self.persona_role,
            "persona_role_display": self.get_persona_role_display(),
            "speaking_style": self.speaking_style,
            "speaking_style_display": self.get_speaking_style_display(),
            "custom_instructions": self.custom_instructions,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

class UserMCPServer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mcp_servers')
    name = models.CharField(max_length=100, default='خادم المتجر الرئيسي (FastMCP)')
    server_url = models.CharField(max_length=500, default='http://mock-store:8002/sse')
    auth_token = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    cached_tools = models.JSONField(default=list, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        status = " [نشط]" if self.is_active else " [معطل]"
        return f"{self.name} ({self.server_url}){status}"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "server_url": self.server_url,
            "auth_token": self.auth_token,
            "is_active": self.is_active,
            "cached_tools": self.cached_tools or [],
            "tools_count": len(self.cached_tools or []),
            "last_synced_at": self.last_synced_at.strftime("%Y-%m-%d %H:%M") if self.last_synced_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }

class CustomerMemory(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_memory')
    permanent_profile = models.JSONField(default=dict, blank=True)
    last_interaction_summary = models.TextField(blank=True, default='')
    last_interaction_at = models.DateTimeField(null=True, blank=True)
    total_calls_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"ذاكرة العميل: {self.user.username}"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "permanent_profile": self.permanent_profile or {},
            "last_interaction_summary": self.last_interaction_summary or "",
            "last_interaction_at": self.last_interaction_at.strftime("%Y-%m-%d %H:%M") if self.last_interaction_at else None,
            "total_calls_count": self.total_calls_count,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

    def format_for_system_instruction(self) -> str:
        """Format the two-tier memory into a compact ~100-150 token block."""
        parts = []
        prof = self.permanent_profile or {}
        if prof:
            items = []
            if prof.get("customer_name"):
                items.append(f"اسم العميل: {prof['customer_name']}")
            if prof.get("phone"):
                items.append(f"الهاتف: {prof['phone']}")
            if prof.get("city") or prof.get("address"):
                items.append(f"العنوان/المدينة: {prof.get('city') or prof.get('address')}")
            if prof.get("preferences"):
                prefs = prof['preferences']
                if isinstance(prefs, list):
                    prefs = "، ".join(str(p) for p in prefs)
                items.append(f"الاهتمامات والتفضيلات: {prefs}")
            if prof.get("notes"):
                items.append(f"ملاحظات: {prof['notes']}")
            if items:
                parts.append("البيانات الدائمة للعميل:\n- " + "\n- ".join(items))

        if self.last_interaction_summary:
            time_str = self.last_interaction_at.strftime("%Y-%m-%d %H:%M") if self.last_interaction_at else "مكالمة سابقة"
            parts.append(f"الذاكرة اللحظية من آخر تواصل ({time_str}):\n{self.last_interaction_summary}")

        if not parts:
            return ""
        return "سياق وذاكرة العميل التراكمية (استخدمها بذكاء وعفوية للتذكر دون سردها للمستخدم كقائمة):\n" + "\n\n".join(parts)

class CallSession(models.Model):
    DIRECTION_CHOICES = [
        ('inbound', 'مكالمة واردة'),
        ('outbound_agent', 'صادرة (موظف)'),
        ('outbound_ai', 'صادرة (ذكاء اصطناعي)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_sessions')
    room_name = models.CharField(max_length=120)
    direction = models.CharField(max_length=32, choices=DIRECTION_CHOICES, default='inbound')
    destination_phone = models.CharField(max_length=64, blank=True, default='')
    call_goal = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    transcript_text = models.TextField(blank=True, default='')
    summary = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"جلسة مكالمة {self.room_name} ({self.get_direction_display()}) - {self.user.username}"

    def to_dict(self):
        return {
            "id": self.id,
            "room_name": self.room_name,
            "direction": self.direction,
            "direction_display": self.get_direction_display(),
            "destination_phone": self.destination_phone or "",
            "call_goal": self.call_goal or "",
            "started_at": self.started_at.strftime("%Y-%m-%d %H:%M"),
            "ended_at": self.ended_at.strftime("%Y-%m-%d %H:%M") if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary or "",
        }

class OutboundSIPTrunk(models.Model):
    TRANSPORT_CHOICES = [
        ('UDP', 'UDP'),
        ('TCP', 'TCP'),
        ('TLS', 'TLS'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outbound_sip_trunks')
    name = models.CharField(max_length=100, default='حساب المزود الخارجي (Generic SIP Trunk)')
    sip_host = models.CharField(max_length=255, help_text='عنوان خادم المزود مثل sip.telnyx.com أو mytrunk.pstn.twilio.com')
    sip_port = models.PositiveIntegerField(default=5060)
    transport = models.CharField(max_length=10, choices=TRANSPORT_CHOICES, default='UDP')
    auth_username = models.CharField(max_length=128, blank=True, null=True, help_text='اسم المستخدم للمصادقة في المزود')
    auth_password = models.CharField(max_length=128, blank=True, null=True, help_text='كلمة المرور في المزود')
    caller_id = models.CharField(max_length=64, blank=True, null=True, help_text='الرقم المعتمد الذي يظهر للمتصل به بصيغة E.164')
    livekit_outbound_trunk_id = models.CharField(max_length=128, blank=True, default='', help_text='معرف الجذع الصادر في LiveKit (ST_...)')
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        status = " [نشط]" if self.is_active else " [معطل]"
        default_str = " [افتراضي]" if self.is_default else ""
        return f"{self.name} ({self.sip_host}){default_str}{status}"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sip_host": self.sip_host,
            "sip_port": self.sip_port,
            "transport": self.transport,
            "auth_username": self.auth_username or "",
            "has_password": bool(self.auth_password),
            "caller_id": self.caller_id or "",
            "livekit_outbound_trunk_id": self.livekit_outbound_trunk_id,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }

class EmployeeProfile(models.Model):
    STATUS_CHOICES = [
        ('ready', 'متاح (Ready)'),
        ('break', 'استراحة (Break)'),
        ('busy', 'مشغول (Busy)'),
        ('offline', 'غير متصل (Offline)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    extension = models.CharField(max_length=32, unique=True, db_index=True, help_text='رقم التحويلة الداخلية مثل 101 أو 102')
    display_name = models.CharField(max_length=100, default='موظف')
    department = models.CharField(max_length=100, default='المبيعات')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ready')
    avatar_url = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['extension']

    def __str__(self):
        return f"{self.display_name} (تحويلة: {self.extension}) - {self.get_status_display()}"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username,
            "extension": self.extension,
            "display_name": self.display_name,
            "department": self.department,
            "status": self.status,
            "status_display": self.get_status_display(),
            "avatar_url": self.avatar_url or f"https://api.dicebear.com/7.x/bottts/png?seed={self.extension}",
            "is_active": self.is_active,
        }


class CallQueue(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_queues')
    name = models.CharField(max_length=100, default='طابور المبيعات')
    code = models.CharField(max_length=32, help_text='كود الطابور للاتصال والتحويل مثل 200 أو 300')
    strategy = models.CharField(max_length=32, default='round_robin', choices=[
        ('round_robin', 'رنين بالتناوب (Round-Robin)'),
        ('ring_all', 'رنين جماعي متزامن (Ring-All)')
    ])
    ring_timeout_seconds = models.PositiveIntegerField(default=15, help_text='مدة رنين الموظف قبل الانتقال للتالي')
    total_timeout_seconds = models.PositiveIntegerField(default=60, help_text='أقصى مدة انتظار للعميل قبل التحويل للذكاء الاصطناعي')
    hold_music = models.FileField(upload_to='hold_music/', null=True, blank=True, help_text='ملف صوتي لموسيقى الانتظار')
    fallback_action = models.CharField(max_length=32, default='ai_assistant', choices=[
        ('ai_assistant', 'مساعد الذكاء الاصطناعي (Gemini Live)'),
        ('hangup', 'إنهاء المكالمة')
    ])
    livekit_trunk_id = models.CharField(max_length=128, blank=True)
    livekit_rule_id = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        unique_together = ('user', 'code')

    def __str__(self):
        return f"{self.name} (كود: {self.code})"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "strategy": self.strategy,
            "ring_timeout_seconds": self.ring_timeout_seconds,
            "total_timeout_seconds": self.total_timeout_seconds,
            "hold_music_url": self.hold_music.url if self.hold_music else None,
            "fallback_action": self.fallback_action,
            "is_active": self.is_active,
            "members": [m.to_dict() for m in self.memberships.filter(is_active=True).select_related('employee')],
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }


class QueueMembership(models.Model):
    queue = models.ForeignKey(CallQueue, on_delete=models.CASCADE, related_name='memberships')
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='queue_memberships')
    order = models.PositiveIntegerField(default=0, help_text='ترتيب أولوية الموظف في التناوب')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.employee.display_name} في {self.queue.name}"

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.employee.display_name,
            "extension": self.employee.extension,
            "department": self.employee.department,
            "status": self.employee.status,
            "order": self.order,
            "is_active": self.is_active,
        }




