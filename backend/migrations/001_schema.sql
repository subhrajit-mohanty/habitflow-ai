-- ============================================================
-- HabitFlow AI — Database Schema (Supabase / PostgreSQL)
-- Version: 1.0.0
-- Date: 2026-03-15
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. USERS & PROFILES
-- ============================================================

-- Supabase Auth handles auth.users — this is our public profile
CREATE TABLE public.profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username        TEXT UNIQUE,
    display_name    TEXT,
    avatar_url      TEXT,
    timezone        TEXT DEFAULT 'UTC',
    
    -- Onboarding
    onboarding_completed BOOLEAN DEFAULT FALSE,
    goals           TEXT[] DEFAULT '{}',          -- e.g. ['health', 'productivity', 'mindfulness']
    wake_time       TIME DEFAULT '07:00',
    sleep_time      TIME DEFAULT '23:00',
    
    -- Subscription
    subscription_tier   TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free', 'pro', 'lifetime')),
    subscription_expires_at TIMESTAMPTZ,
    
    -- Gamification
    total_xp        INTEGER DEFAULT 0,
    level           INTEGER DEFAULT 1,
    longest_streak  INTEGER DEFAULT 0,
    
    -- Metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for leaderboard queries
CREATE INDEX idx_profiles_total_xp ON public.profiles(total_xp DESC);
CREATE INDEX idx_profiles_username ON public.profiles(username);

-- ============================================================
-- 2. HABITS
-- ============================================================

CREATE TABLE public.habits (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    -- Habit definition
    name            TEXT NOT NULL,
    description     TEXT,
    icon            TEXT DEFAULT '✨',           -- emoji or icon key
    color           TEXT DEFAULT '#6C63FF',       -- hex color for UI
    category        TEXT DEFAULT 'general' CHECK (category IN (
                        'health', 'fitness', 'mindfulness', 'productivity',
                        'learning', 'social', 'nutrition', 'sleep', 'general'
                    )),
    
    -- Scheduling
    frequency_type  TEXT DEFAULT 'daily' CHECK (frequency_type IN ('daily', 'weekly', 'custom')),
    frequency_days  INTEGER[] DEFAULT '{1,2,3,4,5,6,7}',  -- 1=Mon, 7=Sun
    preferred_time  TIME,                        -- user's preferred time (nullable = AI decides)
    duration_minutes INTEGER DEFAULT 2,          -- how long the habit takes
    
    -- AI Scheduling
    ai_scheduling_enabled BOOLEAN DEFAULT TRUE,  -- let AI pick optimal time
    ai_optimal_time       TIME,                  -- AI-computed best time
    ai_confidence_score   FLOAT DEFAULT 0.0,     -- 0.0 to 1.0
    
    -- Habit stacking
    stack_after_habit_id  UUID REFERENCES public.habits(id) ON DELETE SET NULL,
    
    -- Verification
    verification_type TEXT DEFAULT 'tap' CHECK (verification_type IN ('tap', 'photo', 'timer', 'gps')),
    
    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    is_archived     BOOLEAN DEFAULT FALSE,
    sort_order      INTEGER DEFAULT 0,
    
    -- Stats (denormalized for fast reads)
    current_streak  INTEGER DEFAULT 0,
    best_streak     INTEGER DEFAULT 0,
    total_completions INTEGER DEFAULT 0,
    completion_rate FLOAT DEFAULT 0.0,           -- 0.0 to 1.0
    
    -- Metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_habits_user_id ON public.habits(user_id);
CREATE INDEX idx_habits_user_active ON public.habits(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_habits_category ON public.habits(category);

-- ============================================================
-- 3. HABIT COMPLETIONS (check-ins)
-- ============================================================

CREATE TABLE public.habit_completions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id        UUID NOT NULL REFERENCES public.habits(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    -- Completion details
    completed_at    TIMESTAMPTZ DEFAULT NOW(),
    completed_date  DATE NOT NULL DEFAULT CURRENT_DATE,  -- for easy daily lookups
    
    -- Verification
    verification_type TEXT DEFAULT 'tap',
    photo_url       TEXT,                        -- for photo check-ins
    photo_verified  BOOLEAN DEFAULT FALSE,       -- AI verification result
    
    -- Context (for ML model training)
    completed_time  TIME NOT NULL,               -- actual time of completion
    day_of_week     INTEGER,                     -- 1-7
    was_on_time     BOOLEAN DEFAULT TRUE,        -- within scheduled window?
    
    -- Mood/energy snapshot at completion
    mood_score      SMALLINT CHECK (mood_score BETWEEN 1 AND 5),
    energy_score    SMALLINT CHECK (energy_score BETWEEN 1 AND 5),
    note            TEXT,                         -- optional journal note
    
    -- Gamification
    xp_earned       INTEGER DEFAULT 10,
    streak_day      INTEGER,                     -- which day of the streak this was
    
    -- Prevent duplicate check-ins per day per habit
    UNIQUE(habit_id, completed_date)
);

CREATE INDEX idx_completions_habit_date ON public.habit_completions(habit_id, completed_date DESC);
CREATE INDEX idx_completions_user_date ON public.habit_completions(user_id, completed_date DESC);
CREATE INDEX idx_completions_user_mood ON public.habit_completions(user_id, mood_score) WHERE mood_score IS NOT NULL;

-- ============================================================
-- 4. DAILY MOOD / ENERGY LOGS
-- ============================================================

CREATE TABLE public.daily_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    log_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Mood & energy (morning, afternoon, evening)
    morning_mood    SMALLINT CHECK (morning_mood BETWEEN 1 AND 5),
    morning_energy  SMALLINT CHECK (morning_energy BETWEEN 1 AND 5),
    afternoon_mood  SMALLINT CHECK (afternoon_mood BETWEEN 1 AND 5),
    afternoon_energy SMALLINT CHECK (afternoon_energy BETWEEN 1 AND 5),
    evening_mood    SMALLINT CHECK (evening_mood BETWEEN 1 AND 5),
    evening_energy  SMALLINT CHECK (evening_energy BETWEEN 1 AND 5),
    
    -- Daily journal
    journal_entry   TEXT,
    gratitude       TEXT[],                      -- up to 3 gratitude items
    
    -- Sleep data (optional)
    sleep_hours     FLOAT,
    sleep_quality   SMALLINT CHECK (sleep_quality BETWEEN 1 AND 5),
    
    -- Computed
    avg_mood        FLOAT,
    avg_energy      FLOAT,
    habits_completed INTEGER DEFAULT 0,
    habits_total    INTEGER DEFAULT 0,
    completion_pct  FLOAT DEFAULT 0.0,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, log_date)
);

CREATE INDEX idx_daily_logs_user_date ON public.daily_logs(user_id, log_date DESC);

-- ============================================================
-- 5. AI COACH CONVERSATIONS
-- ============================================================

CREATE TABLE public.coach_conversations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    title           TEXT,
    conversation_type TEXT DEFAULT 'chat' CHECK (conversation_type IN (
                        'chat', 'weekly_review', 'habit_suggestion', 'motivation'
                    )),
    
    -- Token tracking (for cost management)
    total_tokens    INTEGER DEFAULT 0,
    
    is_archived     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON public.coach_conversations(user_id, created_at DESC);

CREATE TABLE public.coach_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES public.coach_conversations(id) ON DELETE CASCADE,
    
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    
    -- Token tracking
    tokens_used     INTEGER DEFAULT 0,
    model           TEXT DEFAULT 'claude-sonnet-4-20250514',
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON public.coach_messages(conversation_id, created_at ASC);

-- ============================================================
-- 6. GAMIFICATION — BADGES & ACHIEVEMENTS
-- ============================================================

CREATE TABLE public.badges (
    id              TEXT PRIMARY KEY,             -- e.g. 'streak_7', 'early_bird', 'centurion'
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    icon            TEXT NOT NULL,
    category        TEXT DEFAULT 'general',
    xp_reward       INTEGER DEFAULT 50,
    requirement     JSONB NOT NULL,              -- e.g. {"type": "streak", "value": 7}
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.user_badges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    badge_id        TEXT NOT NULL REFERENCES public.badges(id),
    
    earned_at       TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, badge_id)
);

CREATE INDEX idx_user_badges_user ON public.user_badges(user_id);

-- ============================================================
-- 7. SOCIAL — BUDDIES & CHALLENGES
-- ============================================================

CREATE TABLE public.buddy_pairs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_a_id       UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    user_b_id       UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'declined', 'removed')),
    invited_by      UUID NOT NULL REFERENCES public.profiles(id),
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_a_id, user_b_id),
    CHECK (user_a_id <> user_b_id)
);

CREATE INDEX idx_buddy_pairs_user_a ON public.buddy_pairs(user_a_id, status);
CREATE INDEX idx_buddy_pairs_user_b ON public.buddy_pairs(user_b_id, status);

CREATE TABLE public.nudges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_user_id    UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    to_user_id      UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    message         TEXT DEFAULT '💪 Time to do your habit!',
    habit_id        UUID REFERENCES public.habits(id) ON DELETE SET NULL,
    
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nudges_to_user ON public.nudges(to_user_id, is_read, created_at DESC);

CREATE TABLE public.challenges (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creator_id      UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    title           TEXT NOT NULL,
    description     TEXT,
    habit_category  TEXT,
    
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    
    is_public       BOOLEAN DEFAULT TRUE,
    max_participants INTEGER DEFAULT 50,
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.challenge_participants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    challenge_id    UUID NOT NULL REFERENCES public.challenges(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    total_completions INTEGER DEFAULT 0,
    current_streak  INTEGER DEFAULT 0,
    
    UNIQUE(challenge_id, user_id)
);

CREATE INDEX idx_challenge_participants ON public.challenge_participants(challenge_id, total_completions DESC);

-- ============================================================
-- 8. AI BEHAVIOR DATA (for ML model training)
-- ============================================================

CREATE TABLE public.user_behavior_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    
    event_type      TEXT NOT NULL,               -- 'app_open', 'notification_tap', 'notification_dismiss', 'habit_skip', 'habit_snooze'
    event_data      JSONB DEFAULT '{}',
    
    -- Context for ML
    local_time      TIME,
    day_of_week     INTEGER,
    device_state    TEXT,                         -- 'active', 'idle', 'locked'
    
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Partitioned by month for performance (behavior data grows fast)
CREATE INDEX idx_behavior_user_type ON public.user_behavior_events(user_id, event_type, created_at DESC);

-- ============================================================
-- 9. NOTIFICATIONS LOG
-- ============================================================

CREATE TABLE public.notification_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    habit_id        UUID REFERENCES public.habits(id) ON DELETE SET NULL,
    
    notification_type TEXT NOT NULL,              -- 'habit_reminder', 'streak_alert', 'nudge', 'weekly_summary', 'badge_earned'
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    opened_at       TIMESTAMPTZ,
    acted_on        BOOLEAN DEFAULT FALSE,
    
    -- Push token tracking
    push_token      TEXT,
    delivery_status TEXT DEFAULT 'sent'
);

CREATE INDEX idx_notifications_user ON public.notification_log(user_id, sent_at DESC);

-- ============================================================
-- 10. HELPER FUNCTIONS
-- ============================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_habits_updated_at BEFORE UPDATE ON public.habits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_logs_updated_at BEFORE UPDATE ON public.daily_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON public.coach_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to recalculate habit streaks
CREATE OR REPLACE FUNCTION recalculate_streak(p_habit_id UUID)
RETURNS INTEGER AS $$
DECLARE
    streak INTEGER := 0;
    check_date DATE := CURRENT_DATE;
    found BOOLEAN;
BEGIN
    LOOP
        SELECT EXISTS(
            SELECT 1 FROM public.habit_completions
            WHERE habit_id = p_habit_id AND completed_date = check_date
        ) INTO found;
        
        IF found THEN
            streak := streak + 1;
            check_date := check_date - INTERVAL '1 day';
        ELSE
            EXIT;
        END IF;
    END LOOP;
    
    -- Update the habit record
    UPDATE public.habits
    SET current_streak = streak,
        best_streak = GREATEST(best_streak, streak)
    WHERE id = p_habit_id;
    
    RETURN streak;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 11. ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.habit_completions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coach_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.coach_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nudges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_behavior_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_log ENABLE ROW LEVEL SECURITY;

-- Profiles: users can read any profile, but only update their own
CREATE POLICY "Profiles are viewable by everyone" ON public.profiles
    FOR SELECT USING (true);
CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- Habits: users can only see/manage their own
CREATE POLICY "Users manage own habits" ON public.habits
    FOR ALL USING (auth.uid() = user_id);

-- Completions: users can only see/manage their own
CREATE POLICY "Users manage own completions" ON public.habit_completions
    FOR ALL USING (auth.uid() = user_id);

-- Daily logs: users can only see/manage their own
CREATE POLICY "Users manage own daily logs" ON public.daily_logs
    FOR ALL USING (auth.uid() = user_id);

-- Coach conversations: users can only see their own
CREATE POLICY "Users manage own conversations" ON public.coach_conversations
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users see own messages" ON public.coach_messages
    FOR ALL USING (
        conversation_id IN (
            SELECT id FROM public.coach_conversations WHERE user_id = auth.uid()
        )
    );

-- Badges: users see their own
CREATE POLICY "Users see own badges" ON public.user_badges
    FOR ALL USING (auth.uid() = user_id);

-- Nudges: users see nudges sent TO them
CREATE POLICY "Users see received nudges" ON public.nudges
    FOR SELECT USING (auth.uid() = to_user_id);
CREATE POLICY "Users send nudges" ON public.nudges
    FOR INSERT WITH CHECK (auth.uid() = from_user_id);

-- ============================================================
-- 12. SEED DATA — Default Badges
-- ============================================================

INSERT INTO public.badges (id, name, description, icon, category, xp_reward, requirement, sort_order) VALUES
    ('streak_3',      '3-Day Streak',       'Complete a habit for 3 days straight',        '🔥', 'streak',     25,  '{"type": "streak", "value": 3}', 1),
    ('streak_7',      'Week Warrior',       'Complete a habit for 7 days straight',         '⚡', 'streak',     50,  '{"type": "streak", "value": 7}', 2),
    ('streak_21',     'Habit Formed',        '21-day streak — science says it''s a habit!', '🧠', 'streak',     200, '{"type": "streak", "value": 21}', 3),
    ('streak_30',     'Monthly Master',      '30-day streak — you''re unstoppable',         '👑', 'streak',     300, '{"type": "streak", "value": 30}', 4),
    ('streak_100',    'Centurion',           '100-day streak — legendary dedication',       '🏆', 'streak',     1000,'{"type": "streak", "value": 100}', 5),
    ('early_bird',    'Early Bird',          'Complete a habit before 7 AM',                '🌅', 'time',       30,  '{"type": "time_before", "value": "07:00"}', 10),
    ('night_owl',     'Night Owl',           'Complete a habit after 10 PM',                '🌙', 'time',       30,  '{"type": "time_after", "value": "22:00"}', 11),
    ('first_habit',   'Fresh Start',         'Create your first habit',                     '🌱', 'milestone',  10,  '{"type": "habits_created", "value": 1}', 20),
    ('five_habits',   'Habit Collector',     'Have 5 active habits',                        '📚', 'milestone',  50,  '{"type": "habits_created", "value": 5}', 21),
    ('first_buddy',   'Better Together',     'Add your first accountability buddy',         '🤝', 'social',     25,  '{"type": "buddies", "value": 1}', 30),
    ('first_photo',   'Proof Positive',      'Complete your first photo-verified check-in', '📸', 'verification', 20, '{"type": "photo_checkins", "value": 1}', 40),
    ('mood_tracker',  'Self-Aware',          'Log your mood for 7 days straight',           '🎭', 'wellness',   50,  '{"type": "mood_logs", "value": 7}', 50),
    ('journal_entry', 'Dear Diary',          'Write your first journal entry',              '📝', 'wellness',   15,  '{"type": "journal_entries", "value": 1}', 51);
