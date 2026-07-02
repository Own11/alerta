import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Кастомная модель пользователя, содержащая информацию о плане подписки,
    интеграциях и лимитах ИИ.
    """
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('business', 'Business'),
    ]

    email = models.EmailField(unique=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True)
    slack_webhook_url = models.URLField(max_length=500, blank=True, null=True)
    fcm_device_token = models.TextField(blank=True, null=True)

    REPORT_FREQUENCY_CHOICES = [
        ('off', 'Выключено'),
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
    ]

    report_frequency = models.CharField(max_length=10, choices=REPORT_FREQUENCY_CHOICES, default='daily')
    notify_telegram = models.BooleanField(default=True)
    notify_slack = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=True)
    notify_push = models.BooleanField(default=True)
    
    # Лимиты AI ассистента
    ai_daily_limit = models.IntegerField(default=0)  # Будет пересчитано в зависимости от тарифа
    ai_used_today = models.IntegerField(default=0)
    last_ai_reset = models.DateField(auto_now_add=True)

    # Связь с существующей Supabase таблицей profiles
    # В Django мы можем ссылаться на нее через внешнюю/существующую модель или хранить profile_id напрямую
    profile_id = models.UUIDField(blank=True, null=True, unique=True)

    class Meta:
        db_table = 'accounts_user'

    def save(self, *args, **kwargs):
        from billing.plan_limits import PLAN_LIMITS, get_effective_plan
        limits = PLAN_LIMITS.get(get_effective_plan(self), PLAN_LIMITS['free'])
        self.ai_daily_limit = limits['ai_daily_limit']
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.plan})"


class SupabaseProfile(models.Model):
    """
    Модель для интеграции с существующей Supabase таблицей profiles.
    OneToOne с локальной моделью User для полной интеграции.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supabase_profile')
    username = models.CharField(max_length=255, blank=True, null=True)
    auth_users_id = models.UUIDField(blank=True, null=True) # auth.users.id
    urls = models.JSONField(default=list, blank=True)
    api = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'profiles' # Маппинг на существующую таблицу в Supabase
        managed = False # Не создавать миграцию для изменения схемы этой таблицы, если она внешняя

    def __str__(self):
        return f"Profile for {self.username or self.user.username}"
