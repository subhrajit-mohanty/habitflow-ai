"""
HabitFlow AI — Dependencies (Auth, Profile)
"""

import logging
from fastapi import Depends, HTTPException, Header, status
from typing import Optional
from app.config import get_settings, Settings
from app.database import get_supabase_client, get_supabase_admin
from supabase import Client

logger = logging.getLogger(__name__)


# ============================================================
# Auth — Extract & verify Supabase JWT
# ============================================================

async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Extract user from Supabase JWT. Validates via Supabase Auth API."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    token = authorization.removeprefix("Bearer ").strip()

    try:
        # Validate token via Supabase Auth API (supports both HS256 and ES256)
        client = get_supabase_client()
        user_response = client.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return {
            "id": user.id,
            "email": user.email,
            "role": "authenticated",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.debug("Token validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
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
# User Profile
# ============================================================

async def get_user_profile(
    user: dict = Depends(get_current_user),
) -> dict:
    """Fetch the full user profile."""
    admin = get_supabase_admin()
    result = admin.table("profiles").select("*").eq("id", user["id"]).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result.data


