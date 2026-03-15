"""
HabitFlow AI — Analytics Routes
Overview stats, per-habit analytics, mood-habit correlations, trends.
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_current_user, require_pro
from app.database import get_supabase_admin
from app.models.schemas import OverallAnalytics, HabitAnalytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=OverallAnalytics)
async def get_overview(
    period: int = Query(30, ge=7, le=365, description="Period in days"),
    user: dict = Depends(get_current_user),
):
    """Overall analytics for the user over a given period."""
    admin = get_supabase_admin()
    start_date = (date.today() - timedelta(days=period)).isoformat()

    # Profile data
    profile = (
        admin.table("profiles")
        .select("total_xp, level")
        .eq("id", user["id"])
        .single()
        .execute()
    ).data

    # Active habits
    habits = (
        admin.table("habits")
        .select("id, name, category, current_streak, best_streak, completion_rate, is_active")
        .eq("user_id", user["id"])
        .eq("is_archived", False)
        .execute()
    ).data or []

    active_habits = [h for h in habits if h.get("is_active")]

    # Completions in period
    completions = (
        admin.table("habit_completions")
        .select("habit_id, completed_date, completed_time, mood_score, energy_score, day_of_week")
        .eq("user_id", user["id"])
        .gte("completed_date", start_date)
        .execute()
    ).data or []

    total_completions = len(completions)
    total_possible = len(active_habits) * period
    overall_rate = total_completions / max(total_possible, 1)

    # Badges earned
    badges = (
        admin.table("user_badges")
        .select("id", count="exact")
        .eq("user_id", user["id"])
        .execute()
    )

    # Mood/energy from daily logs
    mood_logs = (
        admin.table("daily_logs")
        .select("log_date, avg_mood, avg_energy")
        .eq("user_id", user["id"])
        .gte("log_date", start_date)
        .order("log_date")
        .execute()
    ).data or []

    moods = [m["avg_mood"] for m in mood_logs if m.get("avg_mood")]
    energies = [m["avg_energy"] for m in mood_logs if m.get("avg_energy")]

    # Per-habit analytics
    habit_analytics = []
    completions_by_habit = {}
    for c in completions:
        hid = c["habit_id"]
        completions_by_habit.setdefault(hid, []).append(c)

    for h in active_habits:
        h_completions = completions_by_habit.get(h["id"], [])
        h_count = len(h_completions)

        # Best/worst day of week
        day_counts = {}
        for c in h_completions:
            dow = c.get("day_of_week", 0)
            day_counts[dow] = day_counts.get(dow, 0) + 1

        best_day = max(day_counts, key=day_counts.get) if day_counts else None
        worst_day = min(day_counts, key=day_counts.get) if day_counts else None

        habit_analytics.append(HabitAnalytics(
            habit_id=h["id"],
            habit_name=h["name"],
            period_days=period,
            completions=h_count,
            completion_rate=round(h.get("completion_rate", 0) or 0, 3),
            current_streak=h.get("current_streak", 0),
            best_streak=h.get("best_streak", 0),
            best_day_of_week=best_day,
            worst_day_of_week=worst_day,
        ))

    # Find best day overall
    date_counts = {}
    for c in completions:
        d = c["completed_date"]
        date_counts[d] = date_counts.get(d, 0) + 1
    best_day_overall = max(date_counts, key=date_counts.get) if date_counts else None

    return OverallAnalytics(
        period_days=period,
        total_habits=len(habits),
        active_habits=len(active_habits),
        total_completions=total_completions,
        overall_completion_rate=round(overall_rate, 3),
        total_xp=profile.get("total_xp", 0),
        level=profile.get("level", 1),
        badges_earned=badges.count or 0,
        avg_mood=round(sum(moods) / len(moods), 2) if moods else None,
        avg_energy=round(sum(energies) / len(energies), 2) if energies else None,
        best_day=best_day_overall,
        habit_analytics=habit_analytics,
        mood_trend=[{"date": m["log_date"], "mood": m["avg_mood"]} for m in mood_logs if m.get("avg_mood")],
        energy_trend=[{"date": m["log_date"], "energy": m["avg_energy"]} for m in mood_logs if m.get("avg_energy")],
    )


@router.get("/habits/{habit_id}", response_model=HabitAnalytics)
async def get_habit_analytics(
    habit_id: str,
    period: int = Query(30, ge=7, le=365),
    user: dict = Depends(get_current_user),
):
    """Detailed analytics for a single habit."""
    admin = get_supabase_admin()
    start_date = (date.today() - timedelta(days=period)).isoformat()

    # Verify ownership
    habit = (
        admin.table("habits")
        .select("*")
        .eq("id", habit_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not habit.data:
        raise HTTPException(404, "Habit not found")
    h = habit.data

    # Completions
    completions = (
        admin.table("habit_completions")
        .select("completed_date, completed_time, mood_score, energy_score, day_of_week")
        .eq("habit_id", habit_id)
        .gte("completed_date", start_date)
        .execute()
    ).data or []

    day_counts = {}
    for c in completions:
        dow = c.get("day_of_week", 0)
        day_counts[dow] = day_counts.get(dow, 0) + 1

    return HabitAnalytics(
        habit_id=h["id"],
        habit_name=h["name"],
        period_days=period,
        completions=len(completions),
        completion_rate=round(h.get("completion_rate", 0) or 0, 3),
        current_streak=h.get("current_streak", 0),
        best_streak=h.get("best_streak", 0),
        best_day_of_week=max(day_counts, key=day_counts.get) if day_counts else None,
        worst_day_of_week=min(day_counts, key=day_counts.get) if day_counts else None,
    )


@router.get("/mood-correlations")
async def get_mood_correlations(
    period: int = Query(30, ge=7, le=365),
    profile: dict = Depends(require_pro),  # Pro-only feature
):
    """Show which habits have the strongest mood/energy correlation. PRO ONLY."""
    admin = get_supabase_admin()
    start_date = (date.today() - timedelta(days=period)).isoformat()
    user_id = profile["id"]

    # Get habits
    habits = (
        admin.table("habits")
        .select("id, name")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    ).data or []

    # Get completions with mood scores
    completions = (
        admin.table("habit_completions")
        .select("habit_id, mood_score, energy_score, completed_date")
        .eq("user_id", user_id)
        .gte("completed_date", start_date)
        .not_.is_("mood_score", "null")
        .execute()
    ).data or []

    # Get daily logs for days WITHOUT certain habits
    daily_logs = (
        admin.table("daily_logs")
        .select("log_date, avg_mood, avg_energy")
        .eq("user_id", user_id)
        .gte("log_date", start_date)
        .not_.is_("avg_mood", "null")
        .execute()
    ).data or []

    # Simple correlation: avg mood on days with habit vs without
    correlations = []
    daily_mood_map = {d["log_date"]: d for d in daily_logs}
    completion_dates_by_habit = {}
    for c in completions:
        completion_dates_by_habit.setdefault(c["habit_id"], set()).add(c["completed_date"])

    for h in habits:
        h_dates = completion_dates_by_habit.get(h["id"], set())
        moods_with = [daily_mood_map[d]["avg_mood"] for d in h_dates if d in daily_mood_map and daily_mood_map[d].get("avg_mood")]
        moods_without = [daily_mood_map[d]["avg_mood"] for d in daily_mood_map if d not in h_dates and daily_mood_map[d].get("avg_mood")]

        if moods_with and moods_without:
            impact = round(sum(moods_with) / len(moods_with) - sum(moods_without) / len(moods_without), 2)
        else:
            impact = 0.0

        correlations.append({
            "habit_name": h["name"],
            "habit_id": h["id"],
            "mood_impact": impact,
            "sample_days_with": len(moods_with),
            "sample_days_without": len(moods_without),
            "confidence": "high" if min(len(moods_with), len(moods_without)) >= 10 else "low",
        })

    # Sort by absolute impact
    correlations.sort(key=lambda x: abs(x["mood_impact"]), reverse=True)
    return correlations


@router.get("/best-times")
async def get_best_times(
    profile: dict = Depends(require_pro),  # Pro-only
):
    """AI-computed optimal times per habit. PRO ONLY."""
    admin = get_supabase_admin()

    habits = (
        admin.table("habits")
        .select("id, name, ai_optimal_time, ai_confidence_score, preferred_time")
        .eq("user_id", profile["id"])
        .eq("is_active", True)
        .order("sort_order")
        .execute()
    ).data or []

    return [
        {
            "habit_name": h["name"],
            "habit_id": h["id"],
            "optimal_time": h.get("ai_optimal_time") or h.get("preferred_time"),
            "confidence": h.get("ai_confidence_score", 0),
            "source": "ai" if h.get("ai_optimal_time") else "user_preference",
        }
        for h in habits
    ]


@router.get("/trends")
async def get_trends(
    metric: str = Query("completion_rate", description="completion_rate, mood, energy"),
    period: int = Query(30, ge=7, le=365),
    user: dict = Depends(get_current_user),
):
    """Time-series trend data for charts."""
    admin = get_supabase_admin()
    start_date = (date.today() - timedelta(days=period)).isoformat()

    if metric in ("mood", "energy"):
        field = "avg_mood" if metric == "mood" else "avg_energy"
        result = (
            admin.table("daily_logs")
            .select(f"log_date, {field}")
            .eq("user_id", user["id"])
            .gte("log_date", start_date)
            .not_.is_(field, "null")
            .order("log_date")
            .execute()
        )
        return [{"date": r["log_date"], "value": r[field]} for r in (result.data or [])]

    elif metric == "completion_rate":
        result = (
            admin.table("daily_logs")
            .select("log_date, completion_pct")
            .eq("user_id", user["id"])
            .gte("log_date", start_date)
            .order("log_date")
            .execute()
        )
        return [{"date": r["log_date"], "value": r.get("completion_pct", 0)} for r in (result.data or [])]

    else:
        raise HTTPException(400, "Invalid metric. Use: completion_rate, mood, energy")
