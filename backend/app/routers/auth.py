"""
HabitFlow AI — Auth Routes
Wraps Supabase Auth for signup, login, OAuth, token refresh.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.database import get_supabase_client, get_supabase_admin
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class OAuthRequest(BaseModel):
    id_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str


# ============================================================
# Email / Password Auth
# ============================================================

@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def signup(body: SignupRequest):
    """Register a new user with email/password."""
    client = get_supabase_client()
    try:
        result = client.auth.sign_up({
            "email": body.email,
            "password": body.password,
        })
        if not result.user:
            raise HTTPException(400, "Signup failed")

        # Create profile record using admin client to bypass RLS
        admin = get_supabase_admin()
        try:
            admin.table("profiles").insert({
                "id": result.user.id,
                "username": body.email.split("@")[0],
            }).execute()
        except Exception as profile_err:
            logger.error("Profile creation failed for user %s: %s", result.user.id, profile_err)
            # Auth succeeded but profile failed — still return tokens
            # so the user can retry profile creation on next login

        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, "Signup failed")


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Login with email/password."""
    client = get_supabase_client()
    try:
        result = client.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password,
        })
        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except Exception:
        raise HTTPException(401, "Invalid email or password")


# ============================================================
# OAuth (Google / Apple)
# ============================================================

@router.post("/login/google", response_model=AuthResponse)
async def login_google(body: OAuthRequest):
    """Login with Google ID token."""
    client = get_supabase_client()
    try:
        result = client.auth.sign_in_with_id_token({
            "provider": "google",
            "token": body.id_token,
        })
        # Ensure profile exists — safely access user_metadata
        metadata = getattr(result.user, "user_metadata", None) or {}
        admin = get_supabase_admin()
        admin.table("profiles").upsert({
            "id": result.user.id,
            "display_name": metadata.get("full_name"),
            "avatar_url": metadata.get("avatar_url"),
        }).execute()

        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except Exception:
        raise HTTPException(401, "Google login failed")


@router.post("/login/apple", response_model=AuthResponse)
async def login_apple(body: OAuthRequest):
    """Login with Apple ID token."""
    client = get_supabase_client()
    try:
        result = client.auth.sign_in_with_id_token({
            "provider": "apple",
            "token": body.id_token,
        })
        admin = get_supabase_admin()
        admin.table("profiles").upsert({
            "id": result.user.id,
        }).execute()

        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except Exception:
        raise HTTPException(401, "Apple login failed")


# ============================================================
# Token Refresh & Logout
# ============================================================

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(body: RefreshRequest):
    """Refresh an expired access token."""
    client = get_supabase_client()
    try:
        result = client.auth.refresh_session(body.refresh_token)
        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except Exception:
        raise HTTPException(401, "Invalid refresh token")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Invalidate the current session."""
    client = get_supabase_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass  # Best effort
    return None


@router.post("/forgot-password")
async def forgot_password(body: dict):
    """Send a password reset email."""
    email = body.get("email")
    if not email:
        raise HTTPException(400, "Email is required")
    client = get_supabase_client()
    try:
        client.auth.reset_password_email(email)
    except Exception:
        pass  # Don't reveal if email exists
    return {"message": "If the email exists, a reset link has been sent"}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(user: dict = Depends(get_current_user)):
    """GDPR-compliant account deletion. Cascades via FK constraints."""
    admin = get_supabase_admin()
    try:
        # Delete profile (cascades to all user data via FK constraints)
        admin.table("profiles").delete().eq("id", user["id"]).execute()
        # Delete auth user via Supabase Admin API
        admin.auth.admin.delete_user(user["id"])
    except Exception as e:
        logger.error("Account deletion failed for user %s: %s", user["id"], e)
        raise HTTPException(500, "Account deletion failed. Please contact support.")
    return None
