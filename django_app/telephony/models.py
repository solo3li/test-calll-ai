from django.db import models
from django.contrib.auth.models import User
from common.crypto import encrypt_secret, decrypt_secret

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
    auth_password = models.CharField(max_length=255, blank=True, null=True, help_text='كلمة المرور المشفرة للمزود')
    caller_id = models.CharField(max_length=64, blank=True, null=True, help_text='الرقم المعتمد الذي يظهر للمتصل به بصيغة E.164')
    livekit_outbound_trunk_id = models.CharField(max_length=128, blank=True, default='', help_text='معرف الجذع الصادر في LiveKit (ST_...)')
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'voice_assistant_outboundsiptrunk'
        ordering = ['-is_default', '-created_at']

    def set_auth_password(self, raw_password: str):
        """Encrypt and store plain password."""
        self.auth_password = encrypt_secret(raw_password) if raw_password else ""

    def get_auth_password(self) -> str:
        """Decrypt and return plain password for LiveKit connection."""
        return decrypt_secret(self.auth_password or "")

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


class InboundPBXTrunk(models.Model):
    AUTH_MODE_CHOICES = [
        ('ip', 'IP Whitelisting (عنوان IP ثابت)'),
        ('credentials', 'SIP Credentials (اسم مستخدم وكلمة مرور)'),
    ]

    DESTINATION_CHOICES = [
        ('ai_assistant', 'المساعد الصوتي الذكي (Smart IVR)'),
        ('call_queue', 'طابور انتظار محدد (Call Queue)'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inbound_pbx_trunks')
    name = models.CharField(max_length=100, default='سنترال الشركة (Issabel PBX)')
    auth_mode = models.CharField(max_length=20, choices=AUTH_MODE_CHOICES, default='ip')
    pbx_ip = models.CharField(max_length=255, blank=True, null=True, help_text='عنوان IP العام أو المحلي لسنترال Issabel')
    auth_username = models.CharField(max_length=128, blank=True, null=True, help_text='اسم المستخدم الذي يسجل به سنترال Issabel لدينا')
    auth_password = models.CharField(max_length=255, blank=True, null=True, help_text='كلمة المرور المشفرة لسنترال Issabel')
    inbound_numbers = models.CharField(max_length=255, blank=True, default='', help_text='أرقام الاستقبال/DIDs المسموحة مفصولة بفواصل (اختياري)')
    destination_type = models.CharField(max_length=32, choices=DESTINATION_CHOICES, default='ai_assistant')
    target_queue = models.ForeignKey('call_center.CallQueue', on_delete=models.SET_NULL, null=True, blank=True, related_name='pbx_trunks')
    target_profile = models.ForeignKey('agents.AgentProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='pbx_trunks')
    livekit_trunk_id = models.CharField(max_length=128, blank=True, default='', help_text='معرف الجذع الوارد في LiveKit')
    livekit_rule_id = models.CharField(max_length=128, blank=True, default='', help_text='معرف قاعدة التوجيه في LiveKit')
    enable_outbound = models.BooleanField(default=True, help_text='تمكين إجراء مكالمات صادرة عبر هذا السنترال')
    outbound_port = models.IntegerField(default=5060, help_text='منفذ SIP الصادر للسنترال')
    outbound_transport = models.CharField(max_length=10, default='UDP', choices=[('UDP', 'UDP'), ('TCP', 'TCP'), ('TLS', 'TLS')])
    livekit_outbound_trunk_id = models.CharField(max_length=128, blank=True, default='', help_text='معرف الجذع الصادر في LiveKit')
    is_default_outbound = models.BooleanField(default=False, help_text='تعيين كجذع صادر افتراضي')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'voice_assistant_inboundpbxtrunk'
        ordering = ['-created_at']

    def set_auth_password(self, raw_password: str):
        """Encrypt and store plain password for PBX trunk."""
        self.auth_password = encrypt_secret(raw_password) if raw_password else ""

    def get_auth_password(self) -> str:
        """Decrypt and return plain password for PBX connection."""
        return decrypt_secret(self.auth_password or "")

    def __str__(self):
        status = " [نشط]" if self.is_active else " [معطل]"
        outbound_info = " (ثنائي الاتجاه)" if self.enable_outbound else " (وارد فقط)"
        return f"{self.name} ({self.get_auth_mode_display()}){outbound_info}{status}"

    def generate_issabel_config(self, host_domain="app.localhost", sip_port=5060):
        trunk_name = f"livekit-ai-{self.id}"
        lines = [
            f"; ===========================================================",
            f"; 1. اعدادات الطرفية الصادرة (PEER Details) في Issabel",
            f"; ضع هذا النص في: PBX -> Trunks -> Add SIP Trunk -> PEER Details",
            f"; Trunk Name: {trunk_name}",
            f"; ===========================================================",
            f"[PEER Details]",
            f"host={host_domain}",
            f"port={sip_port}",
            f"type=peer",
            f"qualify=yes",
            f"disallow=all",
            f"allow=alaw,ulaw,opus",
            f"insecure=port,invite",
            f"context=from-internal",
            f"canreinvite=yes",
            f"promiscredir=yes",
        ]
        if self.auth_mode == 'credentials' and self.auth_username:
            lines.extend([
                f"username={self.auth_username}",
                f"secret={self.auth_password or ''}",
                f"fromuser={self.auth_username}",
            ])
        else:
            lines.append(f"; المصادقة: موثوق عبر الـ IP ({self.pbx_ip or 'Any'})")

        peer_text = "\n".join(lines)

        # USER Details (For incoming calls sent from LiveKit into Issabel)
        user_lines = [
            f"; ===========================================================",
            f"; 2. إعدادات استقبال مكالمات الـ AI (USER Details) في Issabel",
            f"; ضع هذا النص في قسم: USER Details / USER Context",
            f"; ===========================================================",
            f"[USER Details]",
            f"type=user",
            f"context=from-internal",
            f"insecure=port,invite",
            f"disallow=all",
            f"allow=alaw,ulaw,opus",
        ]
        if self.auth_mode == 'credentials' and self.auth_username:
            user_lines.extend([
                f"secret={self.auth_password or ''}",
                f"context=from-internal",
            ])
        else:
            user_lines.append(f"; يقبل المكالمات الصادرة من خادمنا ({host_domain})")

        user_text = "\n".join(user_lines)

        register_string = ""
        if self.auth_mode == 'credentials' and self.auth_username and self.auth_password:
            register_string = f"{self.auth_username}:{self.auth_password}@{host_domain}:{sip_port}/{self.auth_username}"

        return {
            "trunk_name": trunk_name,
            "peer_details": peer_text,
            "user_details": user_text,
            "register_string": register_string,
            "host": host_domain,
            "port": sip_port,
        }

    def to_dict(self, host_domain="app.localhost"):
        config = self.generate_issabel_config(host_domain)
        return {
            "id": self.id,
            "name": self.name,
            "auth_mode": self.auth_mode,
            "auth_mode_display": self.get_auth_mode_display(),
            "pbx_ip": self.pbx_ip or "",
            "auth_username": self.auth_username or "",
            "has_password": bool(self.auth_password),
            "inbound_numbers": self.inbound_numbers or "",
            "destination_type": self.destination_type,
            "destination_type_display": self.get_destination_type_display(),
            "target_queue_id": self.target_queue_id,
            "target_queue_name": self.target_queue.name if self.target_queue else "",
            "target_queue_code": self.target_queue.code if self.target_queue else "",
            "target_profile_id": self.target_profile_id,
            "target_profile_name": self.target_profile.name if self.target_profile else "",
            "livekit_trunk_id": self.livekit_trunk_id,
            "livekit_rule_id": self.livekit_rule_id,
            "enable_outbound": self.enable_outbound,
            "outbound_port": self.outbound_port,
            "outbound_transport": self.outbound_transport,
            "livekit_outbound_trunk_id": self.livekit_outbound_trunk_id,
            "is_default_outbound": self.is_default_outbound,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "issabel_config": config,
        }
