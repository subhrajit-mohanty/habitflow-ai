-- Migration 004: User API Keys (BYOK — Bring Your Own Key)
-- Stores user-provided API keys for AI providers (encrypted at rest via Supabase vault)

CREATE TABLE IF NOT EXISTS public.user_api_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('anthropic', 'openai')),
    api_key_encrypted TEXT NOT NULL,
    is_valid BOOLEAN DEFAULT TRUE,
    last_validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, provider)
);

-- RLS: users can only access their own keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own API keys"
    ON public.user_api_keys FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own API keys"
    ON public.user_api_keys FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own API keys"
    ON public.user_api_keys FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own API keys"
    ON public.user_api_keys FOR DELETE
    USING (auth.uid() = user_id);

-- Add ai_provider preference to profiles
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS preferred_ai_provider TEXT DEFAULT 'gemini'
    CHECK (preferred_ai_provider IN ('gemini', 'anthropic', 'openai'));

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_provider
    ON public.user_api_keys(user_id, provider);
