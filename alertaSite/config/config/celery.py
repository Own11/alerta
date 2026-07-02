import os
from celery import Celery
from celery.schedules import crontab

# Устанавливаем дефолтное значение для переменной окружения настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Используем строку конфигурации, начинающуюся с CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим задачи во всех зарегистрированных приложениях Django
app.autodiscover_tasks()

# Периодические задачи (Celery Beat)
app.conf.beat_schedule = {
    'schedule_checks_every_minute': {
        'task': 'monitors.tasks.schedule_checks',
        'schedule': 60.0, # Каждую минуту
    },
    'reset_ai_limits_daily': {
        'task': 'accounts.tasks.reset_ai_limits',
        'schedule': crontab(hour=0, minute=0), # В полночь
    },
    'daily_report_pro_business': {
        'task': 'notifications.tasks.daily_report',
        'schedule': crontab(hour=9, minute=0),
    },
    'weekly_report_pro_business': {
        'task': 'notifications.tasks.weekly_report',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    'schedule_ssl_checks_every_6_hours': {
        'task': 'monitors.tasks.schedule_ssl_checks',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}
