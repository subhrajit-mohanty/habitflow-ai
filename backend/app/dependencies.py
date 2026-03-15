"""
HabitFlow AI — Dependencies (Auth, Rate Limiting, Subscription Guards)
"""

from fastapi import Depends, HTTPException, Header, status
from jose import jwt, JWTError
from typing import Optional
from app.config import get_settings, Settings
from app.database import get_supabase_client, get_supabase_admin
from supabase import Client


# ============================================================
# Auth — Extract & verify Supabase JWT
# ============================================================

async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Extract user from Supabase JWT. Returns {id, email, ...}."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        return {
            "id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role", "authenticated"),
        }
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
        )


# ============================================================
# Authenticated Supabase Client — passes user JWT for RLS
# ============================================================

async def get_auth_client(
    authorization: str = Header(...),
) -> Client:
    """Returns a Supabase client with the user's JWT set for RLS."""
    token = authorization.removeprefix("Bearer ").strip()
    client = get_supabase_client()
    client.postgrest.auth(token)
    return client


# ============================================================
# Subscription Guard
# ============================================================

async def get_user_profile(
    user: dict = Depends(get_current_user),
) -> dict:
    """Fetch the full profile with subscription info."""
    admin = get_supabase_admin()
    result = admin.table("profiles").select("*").eq("id", user["id"]).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result.data


def require_pro(profile: dict = Depends(get_user_profile)) -> dict:
    """Guard: requires Pro or Lifetime subscription."""
    if profile.get("subscription_tier") not in ("pro", "lifetime"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a Pro subscription",
        )
    return profile


# ============================================================
# Habit Limit Check
# ============================================================

async def check_habit_limit(
    profile: dict = Depends(get_user_profile),
    settings: Settings = Depends(get_settings),
):
    """Check if user can create more habits based on subscription tier."""
    tier = profile.get("subscription_tier", "free")
    max_habits = settings.free_max_habits if tier == "free" else settings.pro_max_habits

    admin = get_supabase_admin()
    result = (
        admin.table("habits")
        .select("id", count="exact")
        .eq("user_id", profile["id"])
        .eq("is_active", True)
        .eq("is_archived", False)
        .execute()
    )
    current_count = result.count or 0

    if current_count >= max_habits:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Habit limit reached ({max_habits}). Upgrade to Pro for unlimited habits.",
        )
    return profile
