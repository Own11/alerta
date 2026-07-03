from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection

from accounts.supabase_sync import link_user_by_email, sync_django_user_to_supabase

User = get_user_model()
SQL_FILE = Path(__file__).resolve().parents[5] / 'supabase' / 'sql' / '001_profiles_sync.sql'


class Command(BaseCommand):
    help = 'Применяет SQL-триггер Supabase и синхронизирует Django-пользователей.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            help='Временный пароль для пользователей без auth.users (dev/staging)',
        )
        parser.add_argument(
            '--skip-sql',
            action='store_true',
            help='Не применять SQL-триггер, только синхронизировать пользователей',
        )
        parser.add_argument(
            '--link-only',
            action='store_true',
            help='Только привязать по email, не создавать новых auth.users',
        )

    def handle(self, *args, **options):
        if not options['skip_sql']:
            self._apply_sql()

        linked = 0
        created = 0
        skipped = 0

        for user in User.objects.all().order_by('id'):
            if user.profile_id:
                self.stdout.write(f'OK  {user.username} → {user.profile_id}')
                continue

            if options['link_only']:
                auth_id = link_user_by_email(user)
                if auth_id:
                    linked += 1
                    self.stdout.write(self.style.SUCCESS(f'LINK {user.username} → {auth_id}'))
                else:
                    skipped += 1
                    self.stdout.write(self.style.WARNING(f'SKIP {user.username} (нет auth.users)'))
                continue

            password = options.get('password')
            if not _find_auth_user_id_by_email(user.email) and not password:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'SKIP {user.username} — нет auth.users, укажите --password'
                    )
                )
                continue

            before = _find_auth_user_id_by_email(user.email)
            auth_id = sync_django_user_to_supabase(user, password=password)
            if auth_id:
                if before:
                    linked += 1
                    self.stdout.write(self.style.SUCCESS(f'LINK {user.username} → {auth_id}'))
                else:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f'NEW  {user.username} → {auth_id}'))
            else:
                skipped += 1
                self.stdout.write(self.style.ERROR(f'FAIL {user.username}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Готово: linked={linked}, created={created}, skipped={skipped}'))

    def _apply_sql(self):
        if not SQL_FILE.exists():
            self.stderr.write(self.style.ERROR(f'SQL file not found: {SQL_FILE}'))
            return

        sql = SQL_FILE.read_text(encoding='utf-8')
        with connection.cursor() as cursor:
            cursor.execute(sql)
        self.stdout.write(self.style.SUCCESS(f'Applied SQL: {SQL_FILE.name}'))


def _find_auth_user_id_by_email(email: str):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id FROM auth.users
            WHERE lower(email) = lower(%s) AND deleted_at IS NULL
            LIMIT 1
            """,
            [email],
        )
        row = cursor.fetchone()
        return row[0] if row else None
