import uuid
from django.db import models
from projects.models import Project

class Monitor(models.Model):
    """
    Модель монитора для проверки доступности сайтов и сервисов.
    """
    TYPE_CHOICES = [
        ('http', 'HTTP/HTTPS'),
        ('icmp', 'ICMP Ping'),
        ('port', 'TCP Port'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='monitors')
    name = models.CharField(max_length=255)
    url = models.CharField(max_length=2000) # Может быть IP, URL или домен
    monitor_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='http')
    
    check_interval = models.IntegerField(default=300) # Интервал проверки в секундах
    timeout = models.IntegerField(default=10) # Таймаут ожидания ответа
    retries = models.IntegerField(default=3) # Количество попыток при ошибке
    
    # Настройки SSL
    ssl_enabled = models.BooleanField(default=False)
    ssl_expiry_threshold = models.IntegerField(default=7) # Дней до истечения
    
    # Статус монитора
    is_active = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    
    last_status = models.CharField(max_length=50, default='unknown') # up, down, degraded, unknown
    last_check_at = models.DateTimeField(blank=True, null=True)
    uptime_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    response_time_ms = models.IntegerField(blank=True, null=True)

    # SSL status
    ssl_expires_at = models.DateTimeField(blank=True, null=True)
    ssl_days_left = models.IntegerField(blank=True, null=True)
    ssl_last_checked_at = models.DateTimeField(blank=True, null=True)
    ssl_status = models.CharField(max_length=20, default='unknown')  # ok, warning, expired, error, disabled

    class Meta:
        db_table = 'monitors_monitor'

    def __str__(self):
        return f"{self.name} ({self.url})"


class MonitorCheck(models.Model):
    """History of individual monitor checks for uptime calculation."""
    STATUS_CHOICES = [
        ('up', 'Up'),
        ('down', 'Down'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, related_name='checks')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    response_time_ms = models.IntegerField(blank=True, null=True)
    reason = models.TextField(blank=True, default='')
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'monitors_monitorcheck'
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['monitor', '-checked_at']),
        ]

    def __str__(self):
        return f"{self.monitor.name} @ {self.checked_at}: {self.status}"
