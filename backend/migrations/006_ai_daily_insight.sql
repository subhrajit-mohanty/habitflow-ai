-- Migration 006: AI Daily Insight cache column
ALTER TABLE public.daily_logs
    ADD COLUMN IF NOT EXISTS ai_insight TEXT;
