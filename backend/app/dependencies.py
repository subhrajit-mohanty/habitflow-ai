"""
HabitFlow AI — Dependencies (Auth, Profile)
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
    except JWTError:
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


