"""
HabitFlow AI — Streak & XP Engine
Handles streak calculation (with freeze + rest day support), XP awards, level-ups.
"""

from datetime import date, timedelta
from app.database import get_supabase_admin
from app.config import get_settings


def _is_rest_day(check_date: date, rest_days: list) -> bool:
    """Check if a date is a configured rest day for the habit."""
    if not rest_days:
        return False
    return check_date.isoweekday() in rest_days


def _has_freeze(user_id: str, check_date: date, admin) -> bool:
    """Check if user has an active streak freeze for a given date."""
    result = (
        admin.table("streak_freeze_log")
        .select("id")
        .eq("user_id", user_id)
        .eq("freeze_date", check_date.isoformat())
        .limit(1)
        .execute()
    )
    return bool(result.data)


async def calculate_streak(habit_id: str, user_id: str = None) -> int:
    """Calculate current streak for a habit, honoring freezes and rest days."""
    admin = get_supabase_admin()

    # Get habit info for rest_days
    habit_info = (
        admin.table("habits")
        .select("user_id, rest_days, best_streak")
        .eq("id", habit_id)
        .single()
        .execute()
    ).data
    if not habit_info:
        return 0

    uid = user_id or habit_info["user_id"]
    rest_days = habit_info.get("rest_days") or []

    streak = 0
    check_date = date.today()
    max_lookback = 400  # safety limit

    for _ in range(max_lookback):
        # Skip rest days — they don't count for or against the streak
        if _is_rest_day(check_date, rest_days):
            check_date -= timedelta(days=1)
            continue

        # Check for completion
        result = (
            admin.table("habit_completions")
            .select("id")
            .eq("habit_id", habit_id)
            .eq("completed_date", check_date.isoformat())
            .execute()
        )
        if result.data:
            streak += 1
            check_date -= timedelta(days=1)
            continue

        # Check for streak freeze
        if _has_freeze(uid, check_date, admin):
            # Freeze preserves streak but doesn't increment it
            check_date -= timedelta(days=1)
            continue

        # No completion, no freeze, not a rest day → streak broken
        break

    # Update the habit record
    best_streak = max(streak, habit_info.get("best_streak", 0))
    admin.table("habits").update({
        "current_streak": streak,
        "best_streak": best_streak,
    }).eq("id", habit_id).execute()

    return streak


async def update_habit_stats(habit_id: str, user_id: str) -> dict:
    """Recalculate streak, best_streak, total_completions, completion_rate."""
    admin = get_supabase_admin()

    # Get current streak (with freeze/rest day support)
    streak = await calculate_streak(habit_id, user_id)

    # Get total completions
    total_result = (
        admin.table("habit_completions")
        .select("id", count="exact")
        .eq("habit_id", habit_id)
        .execute()
    )
    total_completions = total_result.count or 0

    # Get habit creation date for completion rate
    habit_result = (
        admin.table("habits")
        .select("created_at, best_streak")
        .eq("id", habit_id)
        .single()
        .execute()
    )
    habit = habit_result.data
    created_date = date.fromisoformat(habit["created_at"][:10])
    days_since_creation = max((date.today() - created_date).days, 1)
    completion_rate = min(total_completions / days_since_creation, 1.0)

    best_streak = max(streak, habit.get("best_streak", 0))

    # Update habit
    admin.table("habits").update({
        "current_streak": streak,
        "best_streak": best_streak,
        "total_completions": total_completions,
        "completion_rate": round(completion_rate, 3),
    }).eq("id", habit_id).execute()

    return {
        "current_streak": streak,
        "best_streak": best_streak,
        "total_completions": total_completions,
        "completion_rate": completion_rate,
    }


async def award_xp(user_id: str, streak: int) -> dict:
    """Award XP for a completion. Bonus for streaks >= 7."""
    settings = get_settings()
    admin = get_supabase_admin()

    base_xp = settings.xp_per_completion
    xp = base_xp
    if streak >= 7:
        xp = int(base_xp * settings.xp_streak_bonus_multiplier)

    # Get current profile
    profile_result = (
        admin.table("profiles")
        .select("total_xp, level")
        .eq("id", user_id)
        .single()
        .execute()
    )
    profile = profile_result.data
    new_total_xp = profile["total_xp"] + xp
    new_level = (new_total_xp // settings.xp_per_level) + 1
    level_up = new_level > profile["level"]

    # Update profile
    update_data = {"total_xp": new_total_xp, "level": new_level}
    if streak > 0:
        update_data["longest_streak"] = max(
            profile.get("longest_streak", 0) if "longest_streak" in profile else 0,
            streak
        )

    admin.table("profiles").update(update_data).eq("id", user_id).execute()

    return {
        "xp_earned": xp,
        "total_xp": new_total_xp,
        "level": new_level,
        "level_up": level_up,
    }
