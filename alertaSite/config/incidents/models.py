import uuid
from django.db import models
from monitors.models import Monitor

class Incident(models.Model):
    """
    Модель инцидента для регистрации падения доступности мониторов.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name='incidents')
    started_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True) # Длительность инцидента в секундах
    reason = models.TextField(blank=True, null=True)
    is_acknowledged = models.BooleanField(default=False)

    class Meta:
        db_table = 'incidents_incident'
        ordering = ['-started_at']

    def __str__(self):
        status = "Resolved" if self.resolved_at else "Active"
        return f"Incident for {self.monitor.name} ({status})"
