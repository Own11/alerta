import uuid
from django.db import models
from django.conf import settings

class Notification(models.Model):
    """
    Модель уведомления пользователя об инцидентах, еженедельных отчетах и SSL статусах.
    """
    TYPE_CHOICES = [
        ('alert', 'Alert (Incident)'),
        ('report', 'Daily/Weekly Report'),
        ('ssl', 'SSL Expiry Warning'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"
