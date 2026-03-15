-- ============================================================
-- HabitFlow AI — RPC Functions Migration
-- Run after 002_notifications.sql
-- Adds helper RPC functions used by the application services.
-- ============================================================

-- Atomically increment XP and recalculate level for a user
CREATE OR REPLACE FUNCTION increment_xp(p_user_id UUID, p_xp INTEGER)
RETURNS TABLE(new_total_xp INTEGER, new_level INTEGER) AS $$
DECLARE
    xp_per_level CONSTANT INTEGER := 100;
BEGIN
    UPDATE public.profiles
    SET total_xp = total_xp + p_xp,
        level = ((total_xp + p_xp) / xp_per_level) + 1
    WHERE id = p_user_id
    RETURNING profiles.total_xp, profiles.level INTO new_total_xp, new_level;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Atomically increment the token count on a conversation
CREATE OR REPLACE FUNCTION increment_tokens(p_conv_id UUID, p_tokens INTEGER)
RETURNS INTEGER AS $$
DECLARE
    new_total INTEGER;
BEGIN
    UPDATE public.coach_conversations
    SET total_tokens = total_tokens + p_tokens
    WHERE id = p_conv_id
    RETURNING total_tokens INTO new_total;

    RETURN new_total;
END;
$$ LANGUAGE plpgsql;
