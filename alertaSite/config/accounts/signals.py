import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from projects.models import Project

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User, dispatch_uid='accounts_create_default_project')
def create_default_project_for_user(sender, instance, created, **kwargs):
    """Создаёт дефолтный Project для каждого нового Django-пользователя."""
    if not created:
        return

    if Project.objects.filter(user=instance).exists():
        return

    try:
        with transaction.atomic():
            Project.objects.create(
                user=instance,
                name=f'Проект {instance.username}',
            )
    except Exception:
        logger.exception(
            'Failed to create default project for user %s (pk=%s)',
            instance.username,
            instance.pk,
        )
        raise
