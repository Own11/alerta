"""
Синхронизация Django User ↔ Supabase auth.users + profiles.

Django подключён к той же PostgreSQL, что и Supabase — auth.users и profiles
создаются напрямую через SQL (без Admin API), если нет service_role ключа.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection, transaction

logger = logging.getLogger(__name__)
User = get_user_model()

SUPABASE_INSTANCE_ID = '00000000-0000-0000-0000-000000000000'


class SupabaseSyncError(Exception):
    """Ошибка синхронизации с Supabase."""


def is_supabase_configured() -> bool:
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        return True
    return _profiles_table_accessible()


def _profiles_table_accessible() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'profiles'
                LIMIT 1
                """
            )
            return cursor.fetchone() is not None
    except Exception:
        return False


def _admin_headers() -> dict[str, str]:
    return {
        'apikey': settings.SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}',
        'Content-Type': 'application/json',
    }


def _admin_url(path: str) -> str:
    return f'{settings.SUPABASE_URL.rstrip("/")}/auth/v1/admin{path}'


def _find_auth_user_id_by_email(email: str) -> uuid.UUID | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id
            FROM auth.users
            WHERE lower(email) = lower(%s)
              AND deleted_at IS NULL
            LIMIT 1
            """,
            [email],
        )
        row = cursor.fetchone()
        if row:
            return uuid.UUID(str(row[0]))
    return None


def create_auth_user_via_sql(
    *,
    email: str,
    password: str,
    username: str,
) -> uuid.UUID:
    existing_id = _find_auth_user_id_by_email(email)
    if existing_id:
        return existing_id

    auth_user_id = uuid.uuid4()
    metadata = json.dumps({'username': username})

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO auth.users (
                instance_id,
                id,
                aud,
                role,
                email,
                encrypted_password,
                email_confirmed_at,
                raw_user_meta_data,
                created_at,
                updated_at
            )
            VALUES (
                %s::uuid,
                %s::uuid,
                'authenticated',
                'authenticated',
                lower(%s),
                crypt(%s, gen_salt('bf')),
                now(),
                %s::jsonb,
                now(),
                now()
            )
            RETURNING id
            """,
            [SUPABASE_INSTANCE_ID, str(auth_user_id), email, password, metadata],
        )
        row = cursor.fetchone()
        if not row:
            raise SupabaseSyncError(f'Failed to insert auth.users for {email}')
        auth_user_id = uuid.UUID(str(row[0]))

        identity_data = json.dumps({
            'sub': str(auth_user_id),
            'email': email.lower(),
            'username': username,
            'email_verified': True,
            'phone_verified': False,
        })
        cursor.execute(
            """
            INSERT INTO auth.identities (
                id,
                user_id,
                provider_id,
                identity_data,
                provider,
                last_sign_in_at,
                created_at,
                updated_at
            )
            VALUES (
                gen_random_uuid(),
                %s::uuid,
                %s,
                %s::jsonb,
                'email',
                now(),
                now(),
                now()
            )
            ON CONFLICT DO NOTHING
            """,
            [str(auth_user_id), str(auth_user_id), identity_data],
        )

    return auth_user_id


def _find_auth_user_by_email_api(email: str) -> dict[str, Any] | None:
    response = requests.get(
        _admin_url('/users'),
        headers=_admin_headers(),
        params={'page': 1, 'per_page': 200},
        timeout=15,
    )
    response.raise_for_status()
    users = response.json().get('users', response.json())
    if not isinstance(users, list):
        return None
    email_lower = email.lower()
    for user in users:
        if (user.get('email') or '').lower() == email_lower:
            return user
    return None


def create_supabase_auth_user_api(
    *,
    email: str,
    password: str,
    username: str,
) -> uuid.UUID:
    payload = {
        'email': email,
        'password': password,
        'email_confirm': True,
        'user_metadata': {'username': username},
    }
    response = requests.post(
        _admin_url('/users'),
        headers=_admin_headers(),
        json=payload,
        timeout=15,
    )

    if response.status_code == 422:
        existing = _find_auth_user_by_email_api(email)
        if existing and existing.get('id'):
            return uuid.UUID(existing['id'])
        response.raise_for_status()

    response.raise_for_status()
    data = response.json()
    auth_user_id = data.get('id') or data.get('user', {}).get('id')
    if not auth_user_id:
        raise SupabaseSyncError(f'Supabase did not return user id: {data}')
    return uuid.UUID(str(auth_user_id))


def create_supabase_auth_user(
    *,
    email: str,
    password: str,
    username: str,
) -> uuid.UUID:
    if _profiles_table_accessible():
        return create_auth_user_via_sql(email=email, password=password, username=username)
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        return create_supabase_auth_user_api(email=email, password=password, username=username)
    raise SupabaseSyncError('Supabase is not configured')


def ensure_profile_row(
    auth_user_id: uuid.UUID,
    *,
    username: str,
    django_user_id: int | None = None,
) -> None:
    if _profiles_table_accessible():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO public.profiles (id, username, urls, api, django_user_id)
                VALUES (%s::uuid, %s, ARRAY[]::text[], ARRAY[]::text[], %s)
                ON CONFLICT (id) DO UPDATE
                SET username = COALESCE(EXCLUDED.username, public.profiles.username),
                    django_user_id = COALESCE(EXCLUDED.django_user_id, public.profiles.django_user_id)
                """,
                [str(auth_user_id), username, django_user_id],
            )
        return

    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        raise SupabaseSyncError('Cannot upsert profile: Supabase API is not configured')

    rest_url = f'{settings.SUPABASE_URL.rstrip("/")}/rest/v1/profiles'
    headers = {**_admin_headers(), 'Prefer': 'resolution=merge-duplicates'}
    payload: dict[str, Any] = {
        'id': str(auth_user_id),
        'username': username,
        'urls': [],
        'api': [],
    }
    if django_user_id is not None:
        payload['django_user_id'] = django_user_id

    response = requests.post(rest_url, headers=headers, json=payload, timeout=15)
    if response.status_code not in (200, 201):
        raise SupabaseSyncError(
            f'Failed to upsert profile for {auth_user_id}: {response.status_code} {response.text}'
        )


def link_user_by_email(user, password: str | None = None) -> uuid.UUID | None:
    """Привязать Django-пользователя к уже существующему auth.users по email."""
    auth_user_id = _find_auth_user_id_by_email(user.email)
    if not auth_user_id:
        return None

    ensure_profile_row(auth_user_id, username=user.username, django_user_id=user.pk)
    User.objects.filter(pk=user.pk).update(profile_id=auth_user_id)
    user.profile_id = auth_user_id
    logger.info('Linked Django user %s to existing auth user %s', user.username, auth_user_id)
    return auth_user_id


@transaction.atomic
def sync_django_user_to_supabase(user, password: str | None = None) -> uuid.UUID | None:
    if user.profile_id:
        ensure_profile_row(
            user.profile_id,
            username=user.username,
            django_user_id=user.pk,
        )
        return user.profile_id

    if not is_supabase_configured():
        logger.warning('Supabase is not configured; skip sync for user %s', user.username)
        return None

    if not user.email:
        logger.warning('Cannot sync user %s without email', user.username)
        return None

    try:
        linked = link_user_by_email(user, password=password)
        if linked:
            return linked

        if not password:
            logger.warning(
                'Cannot create auth user for %s without password (profile_id stays NULL)',
                user.username,
            )
            return None

        auth_user_id = create_supabase_auth_user(
            email=user.email,
            password=password,
            username=user.username,
        )
        ensure_profile_row(
            auth_user_id,
            username=user.username,
            django_user_id=user.pk,
        )
        User.objects.filter(pk=user.pk).update(profile_id=auth_user_id)
        user.profile_id = auth_user_id
        logger.info(
            'Synced Django user %s (pk=%s) → Supabase auth %s',
            user.username,
            user.pk,
            auth_user_id,
        )
        return auth_user_id
    except Exception as exc:
        logger.exception('Supabase sync failed for user %s: %s', user.username, exc)
        return None
