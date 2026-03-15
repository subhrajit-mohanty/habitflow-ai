"""
HabitFlow AI — Gamification Routes
Badges, leaderboard, level progression.
"""

from fastapi import APIRouter, Depends, Query
from app.dependencies import get_current_user, get_user_profile
from app.database import get_supabase_admin
from app.config import get_settings
from app.models.schemas import BadgeResponse, LeaderboardEntry, LevelInfo

router = APIRouter(prefix="/gamification", tags=["Gamification"])


@router.get("/badges", response_model=list[BadgeResponse])
async def get_all_badges(user: dict = Depends(get_current_user)):
    """Get all badges with earned status for the current user."""
    admin = get_supabase_admin()

    all_badges = (
        admin.table("badges")
        .select("*")
        .order("sort_order")
        .execute()
    ).data or []

    earned = (
        admin.table("user_badges")
        .select("badge_id, earned_at")
        .eq("user_id", user["id"])
        .execute()
    ).data or []
    earned_map = {e["badge_id"]: e["earned_at"] for e in earned}

    return [
        BadgeResponse(
            id=b["id"],
            name=b["name"],
            description=b["description"],
            icon=b["icon"],
            category=b.get("category", "general"),
            xp_reward=b.get("xp_reward", 0),
            earned=b["id"] in earned_map,
            earned_at=earned_map.get(b["id"]),
        )
        for b in all_badges
    ]


@router.get("/badges/earned")
async def get_earned_badges(user: dict = Depends(get_current_user)):
    """Get only earned badges."""
    admin = get_supabase_admin()
    result = (
        admin.table("user_badges")
        .select("*, badges(*)")
        .eq("user_id", user["id"])
        .order("earned_at", desc=True)
        .execute()
    )
    return result.data or []


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    period: str = Query("weekly", description="weekly, monthly, alltime"),
    limit: int = Query(20, ge=5, le=50),
    user: dict = Depends(get_current_user),
):
    """XP leaderboard."""
    admin = get_supabase_admin()
    result = (
        admin.table("profiles")
        .select("id, username, display_name, avatar_url, total_xp, longest_streak")
        .order("total_xp", desc=True)
        .limit(limit)
        .execute()
    )

    return [
        LeaderboardEntry(
            rank=i + 1,
            user_id=p["id"],
            username=p.get("username"),
            display_name=p.get("display_name"),
            avatar_url=p.get("avatar_url"),
            total_xp=p.get("total_xp", 0),
            longest_streak=p.get("longest_streak", 0),
        )
        for i, p in enumerate(result.data or [])
    ]


@router.get("/level-info", response_model=LevelInfo)
async def get_level_info(profile: dict = Depends(get_user_profile)):
    """Get current level, XP, and progress to next level."""
    settings = get_settings()
    total_xp = profile.get("total_xp", 0)
    level = profile.get("level", 1)
    xp_per_level = settings.xp_per_level
    xp_in_current_level = total_xp % xp_per_level
    xp_to_next = xp_per_level - xp_in_current_level

    return LevelInfo(
        current_level=level,
        current_xp=xp_in_current_level,
        xp_to_next_level=xp_to_next,
        total_xp=total_xp,
        progress_pct=round(xp_in_current_level / xp_per_level, 3),
    )
