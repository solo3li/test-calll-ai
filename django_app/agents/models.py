import os
from django.db import models
from django.contrib.auth.models import User

class AgentProfile(models.Model):
    GENDER_CHOICES = [
        ('female', 'أنثى'),
        ('male', 'ذكر'),
    ]

    LANGUAGE_CHOICES = [
        ('arabic', 'العربية (Arabic)'),
        ('english', 'English'),
        ('french', 'Français (French)'),
        ('spanish', 'Español (Spanish)'),
        ('german', 'Deutsch (German)'),
        ('italian', 'Italiano (Italian)'),
        ('turkish', 'Türkçe (Turkish)'),
        ('russian', 'Русский (Russian)'),
        ('urdu', 'اردو (Urdu)'),
        ('hindi', 'हिन्दी (Hindi)'),
        ('chinese', '中文 (Mandarin Chinese)'),
    ]

    DIALECT_CHOICES = [
        # Arabic dialects
        ('egyptian', 'لهجة مصرية عامية (مصر)'),
        ('saudi', 'لهجة سعودية / نجدية وحجازية (السعودية)'),
        ('emirati', 'لهجة إماراتية / خليجية (الإمارات)'),
        ('kuwaiti', 'لهجة كويتية (الكويت)'),
        ('levantine', 'لهجة شامية (سوريا ولبنان)'),
        ('jordanian_palestinian', 'لهجة أردنية وفلسطينية (الأردن وفلسطين)'),
        ('moroccan', 'لهجة مغربية / دارجة (المغرب)'),
        ('algerian', 'لهجة جزائرية (الجزائر)'),
        ('tunisian', 'لهجة تونسية (تونس)'),
        ('iraqi', 'لهجة عراقية (العراق)'),
        ('sudanese', 'لهجة سودانية (السودان)'),
        ('yemeni', 'لهجة يمنية (اليمن)'),
        ('fusha', 'عربية فصحى معاصرة (رسمية)'),

        # English dialects
        ('english_us', 'American English (US)'),
        ('english_uk', 'British English (UK)'),
        ('english_aus', 'Australian English (Australia)'),
        ('english_ind', 'Indian English (India)'),
        ('english', 'General English'),

        # French dialects
        ('french_fr', 'Français Métropolitain (France)'),
        ('french_ca', 'Français Canadien (Canada)'),

        # Spanish dialects
        ('spanish_es', 'Español de España (Spain)'),
        ('spanish_latam', 'Español Latinoamericano'),

        # Global languages
        ('german_de', 'Standarddeutsch (Germany & Austria)'),
        ('italian_it', 'Italiano Standard (Italy)'),
        ('turkish_tr', 'Türkçe (Turkey)'),
        ('russian_ru', 'Русский язык (Russia)'),
        ('urdu_pk', 'اردو (Pakistan & India)'),
        ('hindi_in', 'हिन्दी (India)'),
        ('chinese_zh', '普通话 (Mandarin Chinese)'),
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

    VERBOSITY_CHOICES = [
        ('concise', 'مختصر (ردود سريعة ومباشرة في 1-2 جملة)'),
        ('balanced', 'متوازن (طبيعي ومهذب في 2-3 جمل)'),
        ('detailed', 'مفصل (شرح وافٍ واستشاري)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_profiles')
    name = models.CharField(max_length=100, default='البروفايل الافتراضي')
    voice_name = models.CharField(max_length=50, default='Aoede')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='female')
    language = models.CharField(max_length=50, choices=LANGUAGE_CHOICES, default='arabic')
    dialect = models.CharField(max_length=50, choices=DIALECT_CHOICES, default='egyptian')
    persona_role = models.TextField(blank=True, default='خدمة عملاء ومبيعات المتجر')
    speaking_style = models.TextField(blank=True, default='ودود ولطيف ومرح')
    verbosity = models.CharField(max_length=20, choices=VERBOSITY_CHOICES, default='balanced')
    custom_instructions = models.TextField(blank=True, default='')
    welcome_message = models.TextField(
        blank=True,
        default='',
        verbose_name="رسالة الترحيب الافتتاحية",
        help_text="الرسالة الترحيبية التي يبدأ بها المساعد فور فتح المكالمة (مثال: أهلاً بك، معك أحمد، كيف أقدر أساعدك؟)"
    )
    is_welcome_message_enabled = models.BooleanField(
        default=True,
        verbose_name="تفعيل رسالة الترحيب الافتتاحية",
        help_text="تفعيل أو إيقاف الترحيب التلقائي عند بدء المكالمة. عند التعطيل، ينتظر المساعد حتى يتحدث المتصل أولاً."
    )
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
        # Auto-deduce language from dialect if dialect belongs to a specific language
        if self.dialect in ['english', 'english_us', 'english_uk', 'english_aus', 'english_ind']:
            self.language = 'english'
        elif self.dialect in ['french_fr', 'french_ca']:
            self.language = 'french'
        elif self.dialect in ['spanish_es', 'spanish_latam']:
            self.language = 'spanish'
        elif self.dialect == 'german_de':
            self.language = 'german'
        elif self.dialect == 'italian_it':
            self.language = 'italian'
        elif self.dialect == 'turkish_tr':
            self.language = 'turkish'
        elif self.dialect == 'russian_ru':
            self.language = 'russian'
        elif self.dialect == 'urdu_pk':
            self.language = 'urdu'
        elif self.dialect == 'hindi_in':
            self.language = 'hindi'
        elif self.dialect == 'chinese_zh':
            self.language = 'chinese'
        elif not self.language:
            self.language = 'arabic'

        if self.is_active:
            # Ensure only one active profile per user
            AgentProfile.objects.filter(user=self.user, is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "language_display": self.get_language_display(),
            "voice_name": self.voice_name,
            "gender": self.gender,
            "gender_display": self.get_gender_display(),
            "dialect": self.dialect,
            "dialect_display": self.get_dialect_display(),
            "persona_role": self.persona_role,
            "persona_role_display": self.persona_role,
            "speaking_style": self.speaking_style,
            "speaking_style_display": self.speaking_style,
            "verbosity": self.verbosity or "balanced",
            "verbosity_display": self.get_verbosity_display(),
            "custom_instructions": self.custom_instructions,
            "welcome_message": self.welcome_message or "",
            "is_welcome_message_enabled": self.is_welcome_message_enabled,
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

