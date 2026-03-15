"""
HabitFlow AI — AI Coach Routes
Chat with AI coach, weekly summaries, habit suggestions, BYOK key management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.dependencies import get_current_user, get_user_profile
from app.database import get_supabase_admin
from app.config import get_settings
from app.models.schemas import (
    CoachChatRequest, CoachMessageResponse,
    CoachConversationResponse, WeeklySummaryResponse,
)
from app.services.ai_coach import (
    chat as ai_chat,
    generate_weekly_summary,
    validate_api_key,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coach", tags=["AI Coach"])


# ─── Request/Response models for BYOK ───

class APIKeyRequest(BaseModel):
    provider: str  # "anthropic" or "openai"
    api_key: str

class APIKeyResponse(BaseModel):
    provider: str
    is_valid: bool
    created_at: str | None = None

class ProviderPreferenceRequest(BaseModel):
    preferred_ai_provider: str  # "gemini" or "anthropic"


# ============================================================
# CHAT
# ============================================================

@router.post("/chat", response_model=CoachMessageResponse)
async def chat_with_coach(
    body: CoachChatRequest,
    user: dict = Depends(get_current_user),
    profile: dict = Depends(get_user_profile),
):
    """
    Chat with the AI habit coach.
    - Free tier (Gemini): unlimited messages
    - BYOK (user's own key): unlimited messages
    - Pro (app's Claude key): unlimited messages
    Rate limit only applies to free users using the app's Claude key (legacy).
    """
    settings = get_settings()
    admin = get_supabase_admin()
    tier = profile.get("subscription_tier", "free")
    preferred = profile.get("preferred_ai_provider", "gemini")

    # Rate limit only if free user WITHOUT their own key and NOT using Gemini
    # (This is a safety net — _resolve_provider would route them to Gemini anyway)
    if tier == "free" and preferred == "anthropic":
        # Check if they have a valid BYOK key
        byok = (
            admin.table("user_api_keys")
            .select("id")
            .eq("user_id", user["id"])
            .eq("provider", "anthropic")
            .eq("is_valid", True)
            .limit(1)
            .execute()
        )
        if not byok.data:
            # No BYOK key — they'll use Gemini, which is free and unlimited
            # But if somehow Gemini is not configured, apply rate limit
            if not settings.google_gemini_api_key:
                from datetime import date, timedelta
                week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
                msg_count = (
                    admin.table("coach_messages")
                    .select("id", count="exact")
                    .eq("role", "user")
                    .gte("created_at", week_start)
                    .in_(
                        "conversation_id",
                        [c["id"] for c in (
                            admin.table("coach_conversations")
                            .select("id")
                            .eq("user_id", user["id"])
                            .execute()
                        ).data or []]
                    )
                    .execute()
                )
                if (msg_count.count or 0) >= settings.free_ai_messages_per_week:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Free tier limit: {settings.free_ai_messages_per_week} AI messages/week. Add your own API key or upgrade to Pro for unlimited.",
                    )

    try:
        result = await ai_chat(
            user_id=user["id"],
            conversation_id=body.conversation_id,
            user_message=body.message,
            profile=profile,
        )
        return result
    except Exception as e:
        logger.error(f"AI Coach error: {e}")
        raise HTTPException(500, "AI Coach is temporarily unavailable. Please try again.")


# ============================================================
# CONVERSATIONS
# ============================================================

@router.get("/conversations", response_model=list[CoachConversationResponse])
async def list_conversations(user: dict = Depends(get_current_user)):
    """List all coach conversations."""
    admin = get_supabase_admin()
    result = (
        admin.table("coach_conversations")
        .select("*")
        .eq("user_id", user["id"])
        .eq("is_archived", False)
        .order("updated_at", desc=True)
        .limit(20)
        .execute()
    )
    return result.data or []


@router.get("/conversations/{conversation_id}/messages", response_model=list[CoachMessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """Get all messages in a conversation."""
    admin = get_supabase_admin()
    conv = (
        admin.table("coach_conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not conv.data:
        raise HTTPException(404, "Conversation not found")

    result = (
        admin.table("coach_messages")
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a conversation and all its messages."""
    admin = get_supabase_admin()
    result = (
        admin.table("coach_conversations")
        .delete()
        .eq("id", conversation_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Conversation not found")
    return None


# ============================================================
# WEEKLY SUMMARY
# ============================================================

@router.get("/weekly-summary", response_model=WeeklySummaryResponse)
async def get_weekly_summary(
    user: dict = Depends(get_current_user),
    profile: dict = Depends(get_user_profile),
):
    """Generate an AI-powered weekly review with insights and suggestions."""
    try:
        summary = await generate_weekly_summary(user["id"], profile=profile)
        return summary
    except Exception as e:
        logger.error(f"Weekly summary error: {e}")
        raise HTTPException(500, "Failed to generate summary. Please try again.")


# ============================================================
# HABIT SUGGESTIONS
# ============================================================

@router.post("/habit-suggestions")
async def get_habit_suggestions(
    body: dict,
    user: dict = Depends(get_current_user),
    profile: dict = Depends(get_user_profile),
):
    """AI-powered habit suggestions based on user goals and patterns."""
    from app.services.ai_coach import _resolve_provider, _call_provider

    goals = body.get("goals", [])
    if not goals:
        admin = get_supabase_admin()
        prof = (
            admin.table("profiles")
            .select("goals")
            .eq("id", user["id"])
            .single()
            .execute()
        ).data
        goals = prof.get("goals", [])

    provider_info = _resolve_provider(user["id"], profile)

    system = """You are a habit coach. Given the user's goals, suggest 5 micro-habits (2 minutes or less each).
Respond in JSON format only: [{"name": "...", "description": "...", "category": "...", "duration_minutes": N, "icon": "emoji"}]
Categories: health, fitness, mindfulness, productivity, learning, social, nutrition, sleep, general."""

    messages = [{"role": "user", "content": f"My goals: {', '.join(goals)}"}]

    result = _call_provider(provider_info, system, messages, 500)

    import json
    try:
        suggestions = json.loads(result["content"])
    except json.JSONDecodeError:
        suggestions = []

    return suggestions


# ============================================================
# BYOK — API Key Management
# ============================================================

@router.post("/api-keys", response_model=APIKeyResponse)
async def save_api_key(
    body: APIKeyRequest,
    user: dict = Depends(get_current_user),
):
    """Save a user-provided API key (BYOK). Validates it first."""
    if body.provider not in ("anthropic", "openai"):
        raise HTTPException(400, "Provider must be 'anthropic' or 'openai'")

    # Validate the key
    is_valid = validate_api_key(body.provider, body.api_key)
    if not is_valid:
        raise HTTPException(400, f"Invalid {body.provider} API key. Please check and try again.")

    admin = get_supabase_admin()

    # Upsert the key
    result = (
        admin.table("user_api_keys")
        .upsert({
            "user_id": user["id"],
            "provider": body.provider,
            "api_key_encrypted": body.api_key,
            "is_valid": True,
            "last_validated_at": "now()",
        }, on_conflict="user_id,provider")
        .execute()
    )

    # Auto-set preferred provider to anthropic if they just added an Anthropic key
    if body.provider == "anthropic":
        admin.table("profiles").update({
            "preferred_ai_provider": "anthropic"
        }).eq("id", user["id"]).execute()

    row = result.data[0] if result.data else {}
    return APIKeyResponse(
        provider=body.provider,
        is_valid=True,
        created_at=row.get("created_at"),
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(user: dict = Depends(get_current_user)):
    """List user's saved API keys (without exposing the actual key)."""
    admin = get_supabase_admin()
    result = (
        admin.table("user_api_keys")
        .select("provider, is_valid, created_at")
        .eq("user_id", user["id"])
        .execute()
    )
    return [
        APIKeyResponse(provider=r["provider"], is_valid=r["is_valid"], created_at=r.get("created_at"))
        for r in (result.data or [])
    ]


@router.delete("/api-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    provider: str,
    user: dict = Depends(get_current_user),
):
    """Remove a saved API key."""
    admin = get_supabase_admin()
    result = (
        admin.table("user_api_keys")
        .delete()
        .eq("user_id", user["id"])
        .eq("provider", provider)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "API key not found")

    # Reset provider preference to gemini
    admin.table("profiles").update({
        "preferred_ai_provider": "gemini"
    }).eq("id", user["id"]).execute()
    return None


@router.put("/provider-preference")
async def set_provider_preference(
    body: ProviderPreferenceRequest,
    user: dict = Depends(get_current_user),
):
    """Set preferred AI provider (gemini or anthropic)."""
    if body.preferred_ai_provider not in ("gemini", "anthropic"):
        raise HTTPException(400, "Must be 'gemini' or 'anthropic'")

    admin = get_supabase_admin()

    # If switching to anthropic, verify they have a valid key or are pro
    if body.preferred_ai_provider == "anthropic":
        profile = (
            admin.table("profiles")
            .select("subscription_tier")
            .eq("id", user["id"])
            .single()
            .execute()
        ).data
        tier = profile.get("subscription_tier", "free")

        if tier not in ("pro", "lifetime"):
            key = (
                admin.table("user_api_keys")
                .select("id")
                .eq("user_id", user["id"])
                .eq("provider", "anthropic")
                .eq("is_valid", True)
                .limit(1)
                .execute()
            )
            if not key.data:
                raise HTTPException(400, "Add your Anthropic API key first, or upgrade to Pro.")

    admin.table("profiles").update({
        "preferred_ai_provider": body.preferred_ai_provider,
    }).eq("id", user["id"]).execute()

    return {"preferred_ai_provider": body.preferred_ai_provider}
