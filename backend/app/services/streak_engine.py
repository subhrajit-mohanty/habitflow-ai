"""
HabitFlow AI — Streak & XP Engine
Handles streak calculation, XP awards, level-ups.
"""

from datetime import date, timedelta
from app.database import get_supabase_admin
from app.config import get_settings


async def calculate_streak(habit_id: str) -> int:
    """Calculate current streak for a habit by walking backwards from today."""
    admin = get_supabase_admin()
    streak = 0
    check_date = date.today()

    while True:
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
        else:
            break

    # Update the habit record; fetch current best_streak to compute new best
    habit_result = (
        admin.table("habits")
        .select("best_streak")
        .eq("id", habit_id)
        .single()
        .execute()
    )
    best_streak = max(streak, (habit_result.data or {}).get("best_streak", 0))

    admin.table("habits").update({
        "current_streak": streak,
        "best_streak": best_streak,
    }).eq("id", habit_id).execute()

    return streak


async def update_habit_stats(habit_id: str, user_id: str) -> dict:
    """Recalculate streak, best_streak, total_completions, completion_rate."""
    admin = get_supabase_admin()

    # Get current streak
    streak = 0
    check_date = date.today()
    while True:
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
        else:
            break

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
        # Also update longest_streak if needed
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
