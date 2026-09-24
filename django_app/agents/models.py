import os
from django.db import models
from django.contrib.auth.models import User

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
        db_table = 'voice_assistant_agentprofile'
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
    name = models.CharField(max_length=100, default='خادم أدوات خارجي (FastMCP)')
    server_url = models.CharField(max_length=500, blank=True, default='')
    auth_token = models.CharField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    cached_tools = models.JSONField(default=list, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'voice_assistant_usermcpserver'
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


class SystemSetting(models.Model):
    gemini_api_key = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Google Gemini API Key",
        help_text="المفتاح المركزي لخدمات Google Gemini Live ونظام الـ RAG الصوتي"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'voice_assistant_systemsetting'
        verbose_name = "إعدادات النظام العامة"
        verbose_name_plural = "إعدادات النظام العامة"

    def __str__(self):
        status = "مُفعّل" if (self.gemini_api_key and self.gemini_api_key.strip()) else "غير محدد"
        return f"إعدادات النظام (Google Gemini API Key: {status})"

    @classmethod
    def get_settings(cls):
        setting, _ = cls.objects.get_or_create(id=1)
        return setting

    @classmethod
    def get_gemini_api_key(cls):
        setting = cls.objects.filter(id=1).first()
        if setting and setting.gemini_api_key and setting.gemini_api_key.strip():
            return setting.gemini_api_key.strip()
        from django.conf import settings
        return getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')

