from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def reset_ai_limits():
    """
    Каждую ночь сбрасывает счетчики использованных запросов ИИ
    для всех пользователей.
    """
    today = timezone.localdate()
    updated = User.objects.all().update(ai_used_today=0, last_ai_reset=today)
    return f"AI limits reset for {updated} users."
