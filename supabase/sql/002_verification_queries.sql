-- =============================================================================
-- Проверочные SQL-запросы (Supabase SQL Editor)
-- =============================================================================

-- 1. Пользователи auth без профиля (должно быть 0 строк)
SELECT u.id, u.email, u.created_at
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE p.id IS NULL;

-- 2. Профили без auth-пользователя (orphan profiles)
SELECT p.id, p.username, p.django_user_id
FROM public.profiles p
LEFT JOIN auth.users u ON u.id = p.id
WHERE u.id IS NULL;

-- 3. Django-пользователи без profile_id (запускать в Django БД, если она отдельная)
-- SELECT id, username, email, profile_id
-- FROM accounts_user
-- WHERE profile_id IS NULL;

-- 4. Связка Django ↔ Supabase через django_user_id
SELECT
    p.id          AS supabase_auth_id,
    p.username    AS profile_username,
    p.django_user_id,
    p.urls
FROM public.profiles p
WHERE p.django_user_id IS NOT NULL
ORDER BY p.django_user_id;

-- 5. Конкретный пользователь по email
SELECT
    u.id   AS auth_user_id,
    u.email,
    p.id   AS profile_id,
    p.username,
    p.urls,
    p.django_user_id
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE u.email = 'user@example.com';

-- 6. Ручной backfill profile для существующего auth-пользователя
-- INSERT INTO public.profiles (id, username, urls, api)
-- VALUES ('00000000-0000-0000-0000-000000000000', 'username', '[]'::jsonb, '{}'::jsonb)
-- ON CONFLICT (id) DO NOTHING;
