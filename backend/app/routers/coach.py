"""
HabitFlow AI — AI Coach Routes
Chat with AI coach, weekly summaries, habit suggestions, BYOK key management.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.dependencies import get_current_user, get_user_profile
from app.database import get_supabase_admin
from app.models.schemas import (
    CoachChatRequest, CoachMessageResponse,
    CoachConversationResponse, WeeklySummaryResponse,
)
from app.services.ai_coach import (
    chat as ai_chat,
    generate_weekly_summary,
    validate_api_key,
    QuotaExceededError,
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
    preferred_ai_provider: str  # "gemini", "openrouter", or "anthropic"
    preferred_model: str | None = None  # OpenRouter model ID (e.g. "google/gemini-2.0-flash-exp:free")


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
    All users get unlimited messages via Gemini (free).
    Users can optionally bring their own Anthropic key for Claude.
    """
    try:
        result = await ai_chat(
            user_id=user["id"],
            conversation_id=body.conversation_id,
            user_message=body.message,
            profile=profile,
        )
        return result
    except QuotaExceededError as e:
        raise HTTPException(429, str(e))
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
    if body.provider not in ("anthropic", "openai", "openrouter"):
        raise HTTPException(400, "Provider must be 'anthropic', 'openai', or 'openrouter'")

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

    # Auto-set preferred provider when adding a BYOK key
    if body.provider in ("anthropic", "openrouter"):
        admin.table("profiles").update({
            "preferred_ai_provider": body.provider
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
    if body.preferred_ai_provider not in ("gemini", "anthropic", "openrouter"):
        raise HTTPException(400, "Must be 'gemini', 'anthropic', or 'openrouter'")

    admin = get_supabase_admin()

    # If switching to a BYOK provider, verify they have a valid key
    if body.preferred_ai_provider in ("anthropic", "openrouter"):
        key = (
            admin.table("user_api_keys")
            .select("id")
            .eq("user_id", user["id"])
            .eq("provider", body.preferred_ai_provider)
            .eq("is_valid", True)
            .limit(1)
            .execute()
        )
        if not key.data:
            provider_name = "Anthropic" if body.preferred_ai_provider == "anthropic" else "OpenRouter"
            raise HTTPException(400, f"Add your {provider_name} API key first.")

    update_data = {"preferred_ai_provider": body.preferred_ai_provider}
    if body.preferred_model:
        update_data["preferred_model"] = body.preferred_model

    admin.table("profiles").update(update_data).eq("id", user["id"]).execute()

    return {"preferred_ai_provider": body.preferred_ai_provider, "preferred_model": body.preferred_model}


# ============================================================
# DAILY INSIGHT
# ============================================================

@router.get("/daily-insight")
async def get_daily_insight(
    user: dict = Depends(get_current_user),
    profile: dict = Depends(get_user_profile),
):
    """
    Generate a short, personalized AI insight for the home screen.
    Cached per day — only generates once, then returns cached version.
    """
    admin = get_supabase_admin()
    from datetime import date, timedelta
    today = date.today()

    # Check cache (stored in daily_logs.ai_insight)
    log = (
        admin.table("daily_logs")
        .select("id, ai_insight")
        .eq("user_id", user["id"])
        .eq("log_date", today.isoformat())
        .execute()
    )
    if log.data and log.data[0].get("ai_insight"):
        return {"insight": log.data[0]["ai_insight"], "cached": True}

    # Gather quick stats
    week_ago = (today - timedelta(days=7)).isoformat()
    completions = (
        admin.table("habit_completions")
        .select("habit_id, completed_date, mood_score, completed_time")
        .eq("user_id", user["id"])
        .gte("completed_date", week_ago)
        .execute()
    ).data or []

    habits = (
        admin.table("habits")
        .select("id, name, current_streak, completion_rate")
        .eq("user_id", user["id"])
        .eq("is_active", True)
        .execute()
    ).data or []

    # Build data for AI
    habit_summary = ", ".join([
        f"{h['name']} (streak:{h.get('current_streak',0)}, rate:{round((h.get('completion_rate',0) or 0)*100)}%)"
        for h in habits
    ])

    total_week = len(completions)
    moods = [c["mood_score"] for c in completions if c.get("mood_score")]
    avg_mood = round(sum(moods)/len(moods), 1) if moods else "unknown"

    data_prompt = f"Habits: {habit_summary}. This week: {total_week} completions, avg mood: {avg_mood}/5."

    from app.services.ai_coach import _resolve_provider, _call_provider
    provider_info = _resolve_provider(user["id"], profile)

    system = """You are a habit coach. Generate ONE short insight (max 100 characters) based on the user's data.
Be specific and data-driven. Examples:
- "You complete 40% more habits on mornings you meditate first."
- "Your reading streak peaks on weekdays — try a weekend session!"
- "Mood jumps to 4.2/5 on days you exercise. Keep it up!"
Return ONLY the insight text, nothing else."""

    try:
        result = _call_provider(provider_info, system, [
            {"role": "user", "content": data_prompt}
        ], 100)
        insight = result["content"].strip().strip('"')
    except Exception:
        # Fallback to a generic but data-informed insight
        if habits:
            best = max(habits, key=lambda h: h.get("current_streak", 0))
            insight = f"Your {best['name']} streak is at {best.get('current_streak', 0)} days — keep it going!"
        else:
            insight = "Start your first habit today and build momentum!"

    # Cache in daily_logs
    admin.table("daily_logs").upsert({
        "user_id": user["id"],
        "log_date": today.isoformat(),
        "ai_insight": insight,
    }, on_conflict="user_id,log_date").execute()

    return {"insight": insight, "cached": False}
