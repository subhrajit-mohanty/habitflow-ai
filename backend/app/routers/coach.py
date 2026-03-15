"""
HabitFlow AI — AI Coach Routes
Chat with AI coach, weekly summaries, habit suggestions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user, get_user_profile
from app.database import get_supabase_admin
from app.config import get_settings
from app.models.schemas import (
    CoachChatRequest, CoachMessageResponse,
    CoachConversationResponse, WeeklySummaryResponse,
)
from app.services.ai_coach import chat as ai_chat, generate_weekly_summary

router = APIRouter(prefix="/coach", tags=["AI Coach"])


@router.post("/chat", response_model=CoachMessageResponse)
async def chat_with_coach(
    body: CoachChatRequest,
    user: dict = Depends(get_current_user),
    profile: dict = Depends(get_user_profile),
):
    """
    Chat with the AI habit coach.
    Free tier: 3 messages/week. Pro: unlimited.
    """
    settings = get_settings()
    admin = get_supabase_admin()
    tier = profile.get("subscription_tier", "free")

    # Rate limit for free users
    if tier == "free":
        from datetime import date, timedelta
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

        # Count messages this week
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
                detail=f"Free tier limit: {settings.free_ai_messages_per_week} AI messages/week. Upgrade to Pro for unlimited.",
            )

    try:
        result = await ai_chat(
            user_id=user["id"],
            conversation_id=body.conversation_id,
            user_message=body.message,
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"AI Coach error: {str(e)}")


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

    # Verify ownership
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


@router.get("/weekly-summary", response_model=WeeklySummaryResponse)
async def get_weekly_summary(user: dict = Depends(get_current_user)):
    """Generate an AI-powered weekly review with insights and suggestions."""
    try:
        summary = await generate_weekly_summary(user["id"])
        return summary
    except Exception as e:
        raise HTTPException(500, f"Failed to generate summary: {str(e)}")


@router.post("/habit-suggestions")
async def get_habit_suggestions(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """AI-powered habit suggestions based on user goals and patterns."""
    goals = body.get("goals", [])
    if not goals:
        # Fall back to profile goals
        admin = get_supabase_admin()
        profile = (
            admin.table("profiles")
            .select("goals")
            .eq("id", user["id"])
            .single()
            .execute()
        ).data
        goals = profile.get("goals", [])

    # Use AI to suggest habits
    import anthropic
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    response = client.messages.create(
        model=settings.ai_model,
        max_tokens=500,
        system="""You are a habit coach. Given the user's goals, suggest 5 micro-habits (2 minutes or less each).
Respond in JSON format only: [{"name": "...", "description": "...", "category": "...", "duration_minutes": N, "icon": "emoji"}]
Categories: health, fitness, mindfulness, productivity, learning, social, nutrition, sleep, general.""",
        messages=[{"role": "user", "content": f"My goals: {', '.join(goals)}"}],
    )

    import json
    try:
        suggestions = json.loads(response.content[0].text)
    except json.JSONDecodeError:
        suggestions = []

    return suggestions
