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

