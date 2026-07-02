import uuid
from django.db import models
from django.conf import settings
from monitors.models import Monitor

class AIChatSession(models.Model):
    """
    Сессия чата с ИИ-ассистентом для консультаций по доступности сайтов.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_chat_sessions')
    monitor = models.ForeignKey(Monitor, on_delete=models.SET_NULL, blank=True, null=True, related_name='ai_chat_sessions')
    title = models.CharField(max_length=255, default="New AI Chat")
    messages = models.JSONField(default=list, blank=True) # Хранит историю диалога в JSON [{role: "user"|"assistant", content: "text", timestamp: "..."}]
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_assistant_chatsession'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
