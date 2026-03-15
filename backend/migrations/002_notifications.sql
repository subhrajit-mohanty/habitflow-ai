-- ============================================================
-- HabitFlow AI — Push Notifications Schema Migration
-- Run after the main schema.sql
-- ============================================================

-- Push token storage (one per user, updated on each app open)
CREATE TABLE IF NOT EXISTS public.push_tokens (
    user_id     UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    token       TEXT NOT NULL,
    platform    TEXT NOT NULL CHECK (platform IN ('ios', 'android')),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER update_push_tokens_updated_at
    BEFORE UPDATE ON public.push_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Notification preferences per user
CREATE TABLE IF NOT EXISTS public.notification_preferences (
    user_id             UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    habit_reminders     BOOLEAN DEFAULT TRUE,
    streak_alerts       BOOLEAN DEFAULT TRUE,
    nudges              BOOLEAN DEFAULT TRUE,
    weekly_summary      BOOLEAN DEFAULT TRUE,
    badge_earned        BOOLEAN DEFAULT TRUE,
    challenge_updates   BOOLEAN DEFAULT TRUE,
    -- Quiet hours (no notifications during this window)
    quiet_start         TIME DEFAULT '23:00',
    quiet_end           TIME DEFAULT '07:00',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER update_notification_prefs_updated_at
    BEFORE UPDATE ON public.notification_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE public.push_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own push tokens"
    ON public.push_tokens FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users manage own notification prefs"
    ON public.notification_preferences FOR ALL USING (auth.uid() = user_id);

-- Index for scheduler queries (find all users with tokens)
CREATE INDEX idx_push_tokens_platform ON public.push_tokens(platform);
