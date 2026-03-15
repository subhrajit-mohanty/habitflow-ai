"""
HabitFlow AI — Auth Routes
Wraps Supabase Auth for signup, login, OAuth, token refresh.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from app.database import get_supabase_client

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

        # Create profile record
        client.table("profiles").insert({
            "id": result.user.id,
            "username": body.email.split("@")[0],  # default username
        }).execute()

        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except Exception as e:
        raise HTTPException(400, f"Signup failed: {str(e)}")


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
    except Exception as e:
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
        # Ensure profile exists
        client.table("profiles").upsert({
            "id": result.user.id,
            "display_name": result.user.user_metadata.get("full_name"),
            "avatar_url": result.user.user_metadata.get("avatar_url"),
        }).execute()

        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except Exception as e:
        raise HTTPException(401, f"Google login failed: {str(e)}")


@router.post("/login/apple", response_model=AuthResponse)
async def login_apple(body: OAuthRequest):
    """Login with Apple ID token."""
    client = get_supabase_client()
    try:
        result = client.auth.sign_in_with_id_token({
            "provider": "apple",
            "token": body.id_token,
        })
        client.table("profiles").upsert({
            "id": result.user.id,
        }).execute()

        return AuthResponse(
            user_id=result.user.id,
            access_token=result.session.access_token,
            refresh_token=result.session.refresh_token,
        )
    except Exception as e:
        raise HTTPException(401, f"Apple login failed: {str(e)}")


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
    except Exception as e:
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
        return {"message": "Password reset email sent"}
    except Exception as e:
        # Don't reveal if email exists
        return {"message": "If the email exists, a reset link has been sent"}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account():
    """GDPR-compliant account deletion. Cascades via FK constraints."""
    # In production, this would be handled via Supabase Admin API
    # with proper authorization checks
    raise HTTPException(501, "Account deletion requires admin verification. Contact support.")
