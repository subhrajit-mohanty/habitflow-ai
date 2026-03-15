"""
HabitFlow AI — AI Coach Service (Multi-Provider)
Supports:
  1. Google Gemini (free tier — no cost)
  2. Anthropic Claude via BYOK (user's own API key)
  3. Anthropic Claude via app key (Pro subscribers)
"""

import logging
from datetime import date, timedelta
from app.config import get_settings
from app.database import get_supabase_admin

logger = logging.getLogger(__name__)


# ============================================================
# PROVIDER ABSTRACTION
# ============================================================

def _call_gemini(system_prompt: str, messages: list[dict], max_tokens: int, model: str) -> dict:
    """Call Google Gemini API (free tier)."""
    import google.generativeai as genai

    settings = get_settings()
    genai.configure(api_key=settings.google_gemini_api_key)

    gmodel = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt,
    )

    # Convert messages to Gemini format
    gemini_history = []
    for m in messages[:-1]:  # all but last message
        role = "user" if m["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [m["content"]]})

    chat = gmodel.start_chat(history=gemini_history)
    last_msg = messages[-1]["content"] if messages else ""

    response = chat.send_message(
        last_msg,
        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
    )

    # Estimate token usage (Gemini provides usage metadata)
    usage = getattr(response, "usage_metadata", None)
    tokens_used = 0
    if usage:
        tokens_used = (getattr(usage, "prompt_token_count", 0) or 0) + (getattr(usage, "candidates_token_count", 0) or 0)

    return {
        "content": response.text,
        "tokens_used": tokens_used,
        "model": model,
        "provider": "gemini",
    }


def _call_anthropic(system_prompt: str, messages: list[dict], max_tokens: int, model: str, api_key: str) -> dict:
    """Call Anthropic Claude API (BYOK or app key)."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )

    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    return {
        "content": response.content[0].text,
        "tokens_used": tokens_used,
        "model": model,
        "provider": "anthropic",
    }


def _resolve_provider(user_id: str, profile: dict) -> dict:
    """
    Determine which AI provider to use based on user preference.
    Returns: {"provider": str, "model": str, "api_key": str | None}
    """
    settings = get_settings()
    admin = get_supabase_admin()
    preferred = profile.get("preferred_ai_provider", "gemini")

    # Check if user has their own API key (BYOK) and prefers Claude
    if preferred == "anthropic":
        key_result = (
            admin.table("user_api_keys")
            .select("api_key_encrypted, is_valid")
            .eq("user_id", user_id)
            .eq("provider", "anthropic")
            .eq("is_valid", True)
            .limit(1)
            .execute()
        )
        if key_result.data:
            return {
                "provider": "anthropic",
                "model": settings.ai_model,
                "api_key": key_result.data[0]["api_key_encrypted"],
            }

    # Default: free Gemini (unlimited for all users)
    return {
        "provider": "gemini",
        "model": settings.free_ai_model,
        "api_key": None,
    }


def _call_provider(provider_info: dict, system_prompt: str, messages: list[dict], max_tokens: int) -> dict:
    """Route to the correct provider."""
    if provider_info["provider"] == "gemini":
        return _call_gemini(system_prompt, messages, max_tokens, provider_info["model"])
    else:
        return _call_anthropic(system_prompt, messages, max_tokens, provider_info["model"], provider_info["api_key"])


# ============================================================
# SYSTEM PROMPT BUILDER
# ============================================================

async def build_system_prompt(user_id: str) -> str:
    """Build a context-rich system prompt with user's habit data."""
    admin = get_supabase_admin()

    # Fetch user profile
    profile = (
        admin.table("profiles")
        .select("display_name, goals, total_xp, level, longest_streak")
        .eq("id", user_id)
        .single()
        .execute()
    ).data

    # Fetch active habits with streaks
    habits = (
        admin.table("habits")
        .select("name, category, current_streak, best_streak, completion_rate, ai_optimal_time")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    ).data or []

    # Fetch recent mood data (last 7 days)
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    mood_logs = (
        admin.table("daily_logs")
        .select("log_date, avg_mood, avg_energy, habits_completed, habits_total")
        .eq("user_id", user_id)
        .gte("log_date", week_ago)
        .order("log_date", desc=True)
        .execute()
    ).data or []

    # Build habit summary
    habit_lines = []
    for h in habits:
        rate_pct = round((h.get("completion_rate", 0) or 0) * 100)
        habit_lines.append(
            f"- {h['name']} ({h['category']}): "
            f"streak={h.get('current_streak', 0)}, "
            f"best={h.get('best_streak', 0)}, "
            f"rate={rate_pct}%"
        )
    habit_summary = "\n".join(habit_lines) if habit_lines else "No active habits yet."

    # Build mood summary
    mood_lines = []
    for m in mood_logs:
        mood_lines.append(
            f"- {m['log_date']}: mood={m.get('avg_mood', '?')}, "
            f"energy={m.get('avg_energy', '?')}, "
            f"completed={m.get('habits_completed', 0)}/{m.get('habits_total', 0)}"
        )
    mood_summary = "\n".join(mood_lines) if mood_lines else "No mood data this week."

    return f"""You are HabitFlow AI Coach — a warm, encouraging, and insightful personal habit coach.

USER PROFILE:
- Name: {profile.get('display_name', 'Friend')}
- Goals: {', '.join(profile.get('goals', []) or ['general wellness'])}
- Level: {profile.get('level', 1)} | XP: {profile.get('total_xp', 0)}
- Longest streak: {profile.get('longest_streak', 0)} days

CURRENT HABITS:
{habit_summary}

MOOD/ENERGY THIS WEEK:
{mood_summary}

COACHING GUIDELINES:
1. Be warm, specific, and actionable — never generic.
2. Reference their actual habit data (streaks, completion rates, mood patterns).
3. Celebrate wins enthusiastically but naturally.
4. When habits are struggling, be compassionate — suggest small adjustments, not overhauls.
5. Recommend "habit stacking" (attaching a new habit to an existing one) when relevant.
6. Keep responses concise (2-4 paragraphs max) unless they ask for details.
7. Use their name occasionally.
8. If they share emotions, acknowledge them before offering advice.
9. Never be preachy or condescending.
10. End with one specific, actionable suggestion when appropriate."""


# ============================================================
# CHAT
# ============================================================

async def chat(
    user_id: str,
    conversation_id: str | None,
    user_message: str,
    profile: dict = None,
) -> dict:
    """Send a message to the AI coach and get a response."""
    settings = get_settings()
    admin = get_supabase_admin()

    # Load profile if not passed
    if profile is None:
        profile = (
            admin.table("profiles")
            .select("preferred_ai_provider")
            .eq("id", user_id)
            .single()
            .execute()
        ).data or {}

    # Resolve provider
    provider_info = _resolve_provider(user_id, profile)

    # Create or fetch conversation
    if conversation_id is None:
        conv_result = admin.table("coach_conversations").insert({
            "user_id": user_id,
            "conversation_type": "chat",
            "title": user_message[:50],
        }).execute()
        conversation_id = conv_result.data[0]["id"]

    # Save user message
    admin.table("coach_messages").insert({
        "conversation_id": conversation_id,
        "role": "user",
        "content": user_message,
    }).execute()

    # Fetch conversation history
    history_result = (
        admin.table("coach_messages")
        .select("role, content")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .limit(20)
        .execute()
    )
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (history_result.data or [])
        if m["role"] in ("user", "assistant")
    ]

    # Build system prompt with user context
    system_prompt = await build_system_prompt(user_id)

    # Call the resolved provider
    try:
        result = _call_provider(provider_info, system_prompt, messages, settings.ai_max_tokens)
    except Exception as e:
        logger.error(f"AI provider error ({provider_info['provider']}): {e}")
        # If BYOK key fails, mark it invalid and fallback to Gemini
        if provider_info["provider"] == "anthropic" and provider_info.get("api_key") != settings.anthropic_api_key:
            logger.warning(f"BYOK key failed for user {user_id}, falling back to Gemini")
            admin.table("user_api_keys").update({"is_valid": False}).eq("user_id", user_id).eq("provider", "anthropic").execute()
            fallback = {"provider": "gemini", "model": settings.free_ai_model, "api_key": None}
            result = _call_provider(fallback, system_prompt, messages, settings.ai_max_tokens)
        else:
            raise

    # Save assistant message
    msg_result = admin.table("coach_messages").insert({
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": result["content"],
        "tokens_used": result["tokens_used"],
        "model": result["model"],
    }).execute()

    # Atomically increment conversation token count
    if result["tokens_used"] > 0:
        admin.rpc("increment_tokens", {
            "p_conv_id": conversation_id,
            "p_tokens": result["tokens_used"],
        }).execute()

    return {
        "conversation_id": conversation_id,
        "message_id": msg_result.data[0]["id"],
        "role": "assistant",
        "content": result["content"],
        "tokens_used": result["tokens_used"],
        "provider": result["provider"],
        "created_at": msg_result.data[0].get("created_at"),
    }


# ============================================================
# WEEKLY SUMMARY
# ============================================================

async def generate_weekly_summary(user_id: str, profile: dict = None) -> dict:
    """Generate an AI-powered weekly summary with insights."""
    settings = get_settings()
    admin = get_supabase_admin()

    if profile is None:
        profile = (
            admin.table("profiles")
            .select("preferred_ai_provider")
            .eq("id", user_id)
            .single()
            .execute()
        ).data or {}

    provider_info = _resolve_provider(user_id, profile)

    today = date.today()
    week_start = today - timedelta(days=7)

    # Gather data
    completions = (
        admin.table("habit_completions")
        .select("habit_id, completed_date, mood_score, energy_score")
        .eq("user_id", user_id)
        .gte("completed_date", week_start.isoformat())
        .execute()
    ).data or []

    habits = (
        admin.table("habits")
        .select("id, name, current_streak, completion_rate")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    ).data or []

    mood_logs = (
        admin.table("daily_logs")
        .select("log_date, avg_mood, avg_energy")
        .eq("user_id", user_id)
        .gte("log_date", week_start.isoformat())
        .execute()
    ).data or []

    # Compute stats
    total_completions = len(completions)
    total_possible = len(habits) * 7
    completion_rate = total_completions / max(total_possible, 1)

    # Find best/worst habits
    habit_completions = {}
    for c in completions:
        hid = c["habit_id"]
        habit_completions[hid] = habit_completions.get(hid, 0) + 1

    best_habit = worst_habit = None
    if habits:
        sorted_habits = sorted(habits, key=lambda h: habit_completions.get(h["id"], 0), reverse=True)
        best_habit = sorted_habits[0]["name"]
        worst_habit = sorted_habits[-1]["name"]

    # Average mood/energy
    moods = [m["avg_mood"] for m in mood_logs if m.get("avg_mood")]
    energies = [m["avg_energy"] for m in mood_logs if m.get("avg_energy")]
    avg_mood = round(sum(moods) / len(moods), 1) if moods else None
    avg_energy = round(sum(energies) / len(energies), 1) if energies else None

    # Generate AI narrative
    data_summary = f"""Weekly stats: {total_completions} completions out of {total_possible} possible ({round(completion_rate*100)}%).
Best habit: {best_habit}. Needs work: {worst_habit}.
Average mood: {avg_mood}/5. Average energy: {avg_energy}/5.
Habits tracked: {len(habits)}."""

    system = "You are a concise habit coach. Write a 2-3 paragraph weekly review that celebrates wins, identifies patterns, and gives 2-3 specific suggestions. Be warm and encouraging."
    messages = [{"role": "user", "content": f"Here's my week:\n{data_summary}"}]

    result = _call_provider(provider_info, system, messages, 500)
    ai_summary = result["content"]

    return {
        "week_start": week_start.isoformat(),
        "week_end": today.isoformat(),
        "total_completions": total_completions,
        "completion_rate": round(completion_rate, 3),
        "best_habit": best_habit,
        "worst_habit": worst_habit,
        "avg_mood": avg_mood,
        "avg_energy": avg_energy,
        "mood_habit_correlations": [],
        "ai_summary": ai_summary,
        "suggestions": [],
    }


# ============================================================
# VALIDATE API KEY
# ============================================================

def validate_api_key(provider: str, api_key: str) -> bool:
    """Test if a user-provided API key is valid."""
    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        elif provider == "openai":
            import openai
            client = openai.OpenAI(api_key=api_key)
            client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        return False
    except Exception as e:
        logger.warning(f"API key validation failed for {provider}: {e}")
        return False
