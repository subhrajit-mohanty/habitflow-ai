-- Migration 005: Streak Freeze & Rest Days
-- Duolingo-style streak protection system

-- Streak freeze inventory per user
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS streak_freezes_available INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS streak_freezes_used_total INTEGER DEFAULT 0;

-- Log of streak freeze usage
CREATE TABLE IF NOT EXISTS public.streak_freeze_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    habit_id UUID REFERENCES public.habits(id) ON DELETE SET NULL,
    freeze_date DATE NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('earned', 'purchased', 'gift')),
    xp_cost INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.streak_freeze_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own freeze log"
    ON public.streak_freeze_log FOR ALL
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_streak_freeze_user_date
    ON public.streak_freeze_log(user_id, freeze_date);

-- Rest days configuration per habit
ALTER TABLE public.habits
    ADD COLUMN IF NOT EXISTS rest_days INTEGER[] DEFAULT '{}';
