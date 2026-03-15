"""
HabitFlow AI — AI Coach Service
Uses Claude API for personalized habit coaching conversations.
"""

import anthropic
from datetime import date, timedelta
from app.config import get_settings
from app.database import get_supabase_admin


def _get_client() -> anthropic.Anthropic:
    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


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


async def chat(
    user_id: str,
    conversation_id: str | None,
    user_message: str,
) -> dict:
    """Send a message to the AI coach and get a response."""
    settings = get_settings()
    admin = get_supabase_admin()
    client = _get_client()

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
        .limit(20)  # Last 20 messages for context
        .execute()
    )
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (history_result.data or [])
        if m["role"] in ("user", "assistant")
    ]

    # Build system prompt with user context
    system_prompt = await build_system_prompt(user_id)

    # Call Claude API
    response = client.messages.create(
        model=settings.ai_model,
        max_tokens=settings.ai_max_tokens,
        system=system_prompt,
        messages=messages,
    )

    assistant_content = response.content[0].text
    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    # Save assistant message
    msg_result = admin.table("coach_messages").insert({
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": assistant_content,
        "tokens_used": tokens_used,
        "model": settings.ai_model,
    }).execute()

    # Atomically increment conversation token count
    admin.rpc("increment_tokens", {
        "p_conv_id": conversation_id,
        "p_tokens": tokens_used,
    }).execute()

    return {
        "conversation_id": conversation_id,
        "message_id": msg_result.data[0]["id"],
        "role": "assistant",
        "content": assistant_content,
        "tokens_used": tokens_used,
        "created_at": msg_result.data[0].get("created_at"),
    }


async def generate_weekly_summary(user_id: str) -> dict:
    """Generate an AI-powered weekly summary with insights."""
    settings = get_settings()
    admin = get_supabase_admin()
    client = _get_client()

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

    response = client.messages.create(
        model=settings.ai_model,
        max_tokens=500,
        system="You are a concise habit coach. Write a 2-3 paragraph weekly review that celebrates wins, identifies patterns, and gives 2-3 specific suggestions. Be warm and encouraging.",
        messages=[{"role": "user", "content": f"Here's my week:\n{data_summary}"}],
    )

    ai_summary = response.content[0].text

    return {
        "week_start": week_start.isoformat(),
        "week_end": today.isoformat(),
        "total_completions": total_completions,
        "completion_rate": round(completion_rate, 3),
        "best_habit": best_habit,
        "worst_habit": worst_habit,
        "avg_mood": avg_mood,
        "avg_energy": avg_energy,
        "mood_habit_correlations": [],  # TODO: compute via analytics engine
        "ai_summary": ai_summary,
        "suggestions": [],  # Extracted from ai_summary
    }
