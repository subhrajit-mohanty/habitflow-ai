"""
HabitFlow AI — User / Profile Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user, get_user_profile
from app.database import get_supabase_admin
from app.models.user import ProfileUpdate, ProfileResponse, OnboardingRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(user: dict = Depends(get_current_user)):
    """Get the current user's profile."""
    admin = get_supabase_admin()
    result = admin.table("profiles").select("*").eq("id", user["id"]).single().execute()
    if not result.data:
        raise HTTPException(404, "Profile not found")
    return result.data


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update the current user's profile."""
    admin = get_supabase_admin()
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(400, "No fields to update")

    result = (
        admin.table("profiles")
        .update(update_data)
        .eq("id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Profile not found")
    return result.data[0]


@router.post("/me/onboarding", response_model=ProfileResponse)
async def complete_onboarding(
    body: OnboardingRequest,
    user: dict = Depends(get_current_user),
):
    """Complete the onboarding flow — sets profile and optionally creates initial habits."""
    admin = get_supabase_admin()

    # Update profile
    profile_result = (
        admin.table("profiles")
        .update({
            "display_name": body.display_name,
            "timezone": body.timezone,
            "goals": body.goals,
            "wake_time": body.wake_time,
            "sleep_time": body.sleep_time,
            "onboarding_completed": True,
        })
        .eq("id", user["id"])
        .execute()
    )

    # Create initial habits from templates if provided
    if body.initial_habits:
        from app.routers.habits import HABIT_TEMPLATES
        for template_name in body.initial_habits:
            template = next((t for t in HABIT_TEMPLATES if t["name"] == template_name), None)
            if template:
                admin.table("habits").insert({
                    "user_id": user["id"],
                    "name": template["name"],
                    "description": template["description"],
                    "icon": template["icon"],
                    "color": template["color"],
                    "category": template["category"],
                    "duration_minutes": template["duration_minutes"],
                    "ai_scheduling_enabled": True,
                }).execute()

    return profile_result.data[0]


@router.get("/search")
async def search_users(
    q: str,
    user: dict = Depends(get_current_user),
):
    """Search users by username (for buddy invites)."""
    if len(q) < 2:
        raise HTTPException(400, "Search query must be at least 2 characters")

    admin = get_supabase_admin()
    result = (
        admin.table("profiles")
        .select("id, username, display_name, avatar_url")
        .ilike("username", f"%{q}%")
        .neq("id", user["id"])  # Exclude self
        .limit(10)
        .execute()
    )
    return result.data or []


@router.get("/{username}")
async def get_user_by_username(
    username: str,
    user: dict = Depends(get_current_user),
):
    """Get a user's public profile by username."""
    admin = get_supabase_admin()
    result = (
        admin.table("profiles")
        .select("id, username, display_name, avatar_url, total_xp, level, longest_streak")
        .eq("username", username)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "User not found")
    return result.data
