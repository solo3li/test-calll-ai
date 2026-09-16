from django.db import models
from django.contrib.auth.models import User

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
        db_table = 'voice_assistant_outboundsiptrunk'
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
