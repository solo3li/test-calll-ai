from django.db import models
from django.contrib.auth.models import User

class CustomerMemory(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_memory')
    permanent_profile = models.JSONField(default=dict, blank=True)
    last_interaction_summary = models.TextField(blank=True, default='')
    last_interaction_at = models.DateTimeField(null=True, blank=True)
    total_calls_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'voice_assistant_customermemory'
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
        db_table = 'voice_assistant_callsession'
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
