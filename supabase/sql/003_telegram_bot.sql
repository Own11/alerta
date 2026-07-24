-- 1. Add telegram_id to profiles table
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE;

CREATE INDEX IF NOT EXISTS idx_profiles_telegram_id
    ON public.profiles (telegram_id);

-- 2. Create table for generating unique links (Option A)
CREATE TABLE IF NOT EXISTS public.bot_auth_tokens (
    token UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 hour',
    used BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_bot_auth_tokens_token
    ON public.bot_auth_tokens (token);

-- RLS policies for bot_auth_tokens
ALTER TABLE public.bot_auth_tokens ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to create their own tokens via the web frontend
CREATE POLICY "Users can create their own tokens"
    ON public.bot_auth_tokens FOR INSERT WITH CHECK (auth.uid() = profile_id);

CREATE POLICY "Users can view their own tokens"
    ON public.bot_auth_tokens FOR SELECT USING (auth.uid() = profile_id);

-- Note: The bot will use the SUPABASE_SERVICE_ROLE_KEY to bypass RLS 
-- when it needs to validate the token and link the account.
