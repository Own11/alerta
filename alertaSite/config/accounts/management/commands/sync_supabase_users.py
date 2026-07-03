from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from accounts.supabase_sync import is_supabase_configured, sync_django_user_to_supabase

User = get_user_model()


class Command(BaseCommand):
    help = 'Синхронизирует существующих Django-пользователей с Supabase (нужен пароль).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            help='Общий временный пароль для всех пользователей без profile_id (только для dev/staging)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать пользователей без синхронизации, не создавая записи',
        )

    def handle(self, *args, **options):
        if not is_supabase_configured():
            self.stderr.write(self.style.ERROR('SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY не заданы'))
            return

        password = options.get('password')
        dry_run = options['dry_run']
        users = User.objects.filter(profile_id__isnull=True)

        if not users.exists():
            self.stdout.write(self.style.SUCCESS('Все пользователи уже синхронизированы.'))
            return

        for user in users:
            if dry_run:
                self.stdout.write(f'[dry-run] {user.username} <{user.email}> — profile_id IS NULL')
                continue

            if not password:
                self.stderr.write(
                    f'Пропуск {user.username}: укажите --password или создайте пользователя заново через форму'
                )
                continue

            auth_id = sync_django_user_to_supabase(user, password=password)
            if auth_id:
                self.stdout.write(self.style.SUCCESS(f'{user.username} → {auth_id}'))
            else:
                self.stderr.write(self.style.ERROR(f'Не удалось синхронизировать {user.username}'))
