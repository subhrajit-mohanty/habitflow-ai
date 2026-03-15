-- Migration 005: Add OpenRouter support
-- Adds 'openrouter' as a valid AI provider and preferred_model column

-- Update user_api_keys provider constraint to include 'openrouter'
ALTER TABLE public.user_api_keys DROP CONSTRAINT IF EXISTS user_api_keys_provider_check;
ALTER TABLE public.user_api_keys ADD CONSTRAINT user_api_keys_provider_check
    CHECK (provider IN ('anthropic', 'openai', 'openrouter'));

-- Update profiles preferred_ai_provider constraint to include 'openrouter'
ALTER TABLE public.profiles DROP CONSTRAINT IF EXISTS profiles_preferred_ai_provider_check;
ALTER TABLE public.profiles ADD CONSTRAINT profiles_preferred_ai_provider_check
    CHECK (preferred_ai_provider IN ('gemini', 'anthropic', 'openai', 'openrouter'));

-- Add preferred_model column for OpenRouter model selection
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS preferred_model TEXT DEFAULT NULL;
