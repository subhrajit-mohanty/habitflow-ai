"""
HabitFlow AI — Badge / Achievement Engine
Checks if user has earned any new badges after a completion.
"""

from app.database import get_supabase_admin


async def check_and_award_badges(user_id: str, habit_id: str, streak: int) -> list[dict]:
    """Check all badge conditions and award any newly earned badges.
    Returns list of newly earned badges.
    """
    admin = get_supabase_admin()

    # Get all badges the user hasn't earned yet
    all_badges = admin.table("badges").select("*").execute().data or []
    earned_result = (
        admin.table("user_badges")
        .select("badge_id")
        .eq("user_id", user_id)
        .execute()
    )
    earned_ids = {b["badge_id"] for b in (earned_result.data or [])}
    unearned = [b for b in all_badges if b["id"] not in earned_ids]

    if not unearned:
        return []

    new_badges = []

    for badge in unearned:
        req = badge.get("requirement", {})
        req_type = req.get("type")
        req_value = req.get("value")

        earned = False

        if req_type == "streak":
            earned = streak >= req_value

        elif req_type == "habits_created":
            result = (
                admin.table("habits")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .execute()
            )
            earned = (result.count or 0) >= req_value

        elif req_type == "photo_checkins":
            result = (
                admin.table("habit_completions")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("verification_type", "photo")
                .execute()
            )
            earned = (result.count or 0) >= req_value

        elif req_type == "buddies":
            result = (
                admin.table("buddy_pairs")
                .select("id", count="exact")
                .or_(f"user_a_id.eq.{user_id},user_b_id.eq.{user_id}")
                .eq("status", "active")
                .execute()
            )
            earned = (result.count or 0) >= req_value

        elif req_type == "mood_logs":
            result = (
                admin.table("daily_logs")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .not_.is_("morning_mood", "null")
                .execute()
            )
            earned = (result.count or 0) >= req_value

        elif req_type == "journal_entries":
            result = (
                admin.table("daily_logs")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .not_.is_("journal_entry", "null")
                .execute()
            )
            earned = (result.count or 0) >= req_value

        elif req_type == "time_before":
            # Check if the latest completion was before the specified time
            result = (
                admin.table("habit_completions")
                .select("completed_time")
                .eq("habit_id", habit_id)
                .order("completed_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                completed_time = result.data[0]["completed_time"]
                earned = completed_time < req_value

        elif req_type == "time_after":
            result = (
                admin.table("habit_completions")
                .select("completed_time")
                .eq("habit_id", habit_id)
                .order("completed_at", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                completed_time = result.data[0]["completed_time"]
                earned = completed_time > req_value

        if earned:
            # Award badge
            admin.table("user_badges").insert({
                "user_id": user_id,
                "badge_id": badge["id"],
            }).execute()

            # Award badge XP
            xp_reward = badge.get("xp_reward", 0)
            if xp_reward > 0:
                admin.rpc("increment_xp", {
                    "p_user_id": user_id,
                    "p_xp": xp_reward,
                }).execute()

            new_badges.append({
                "id": badge["id"],
                "name": badge["name"],
                "description": badge["description"],
                "icon": badge["icon"],
                "xp_reward": xp_reward,
            })

    return new_badges
