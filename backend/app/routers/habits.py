"""
HabitFlow AI — Habit Routes
CRUD, today's view, templates, calendar heatmap, reorder.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.dependencies import get_current_user, check_habit_limit
from app.database import get_supabase_admin
from app.models.habit import (
    HabitCreate, HabitUpdate, HabitResponse,
    HabitReorderRequest, HabitTemplate,
)

router = APIRouter(prefix="/habits", tags=["Habits"])


# ============================================================
# Habit Templates (pre-built for onboarding)
# ============================================================

HABIT_TEMPLATES = [
    {
        "name": "Drink Water",
        "description": "Drink a glass of water to stay hydrated",
        "icon": "💧",
        "color": "#2196F3",
        "category": "health",
        "duration_minutes": 1,
        "suggested_time": "08:00",
    },
    {
        "name": "Meditate 2 min",
        "description": "Take 2 minutes for mindful breathing",
        "icon": "🧘",
        "color": "#9C27B0",
        "category": "mindfulness",
        "duration_minutes": 2,
        "suggested_time": "07:30",
    },
    {
        "name": "Read 5 Pages",
        "description": "Read at least 5 pages of any book",
        "icon": "📖",
        "color": "#FF9800",
        "category": "learning",
        "duration_minutes": 10,
        "suggested_time": "21:00",
    },
    {
        "name": "Stretch",
        "description": "Do a quick 2-minute stretch routine",
        "icon": "🤸",
        "color": "#4CAF50",
        "category": "fitness",
        "duration_minutes": 2,
        "suggested_time": "07:00",
    },
    {
        "name": "Gratitude Journal",
        "description": "Write down 3 things you're grateful for",
        "icon": "🙏",
        "color": "#E91E63",
        "category": "mindfulness",
        "duration_minutes": 3,
        "suggested_time": "22:00",
    },
    {
        "name": "No Phone First Hour",
        "description": "Avoid checking your phone for the first hour after waking",
        "icon": "📵",
        "color": "#607D8B",
        "category": "productivity",
        "duration_minutes": 60,
        "suggested_time": "07:00",
    },
    {
        "name": "Walk 10 Minutes",
        "description": "Take a short walk outside",
        "icon": "🚶",
        "color": "#8BC34A",
        "category": "fitness",
        "duration_minutes": 10,
        "suggested_time": "12:30",
    },
    {
        "name": "Deep Breathing",
        "description": "4-7-8 breathing: inhale 4s, hold 7s, exhale 8s",
        "icon": "🌬️",
        "color": "#00BCD4",
        "category": "mindfulness",
        "duration_minutes": 2,
        "suggested_time": "15:00",
    },
    {
        "name": "Learn a New Word",
        "description": "Look up and memorize one new vocabulary word",
        "icon": "🔤",
        "color": "#3F51B5",
        "category": "learning",
        "duration_minutes": 2,
        "suggested_time": "09:00",
    },
    {
        "name": "Tidy Up 5 Min",
        "description": "Spend 5 minutes tidying your space",
        "icon": "🧹",
        "color": "#795548",
        "category": "productivity",
        "duration_minutes": 5,
        "suggested_time": "19:00",
    },
]


# ============================================================
# Routes
# ============================================================

@router.get("/templates", response_model=list[HabitTemplate])
async def get_habit_templates():
    """Get pre-built habit templates for onboarding."""
    return HABIT_TEMPLATES


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=HabitResponse)
async def create_habit(
    body: HabitCreate,
    profile: dict = Depends(check_habit_limit),
):
    """Create a new habit. Checks subscription limits."""
    admin = get_supabase_admin()

    # Get current max sort_order
    existing = (
        admin.table("habits")
        .select("sort_order")
        .eq("user_id", profile["id"])
        .order("sort_order", desc=True)
        .limit(1)
        .execute()
    )
    next_order = (existing.data[0]["sort_order"] + 1) if existing.data else 0

    insert_data = body.model_dump(exclude_none=True)
    insert_data["user_id"] = profile["id"]
    insert_data["sort_order"] = next_order

    result = admin.table("habits").insert(insert_data).execute()
    if not result.data:
        raise HTTPException(500, "Failed to create habit")

    return result.data[0]


@router.get("/", response_model=list[HabitResponse])
async def list_habits(
    active: Optional[bool] = Query(None),
    category: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    """List all habits for the current user."""
    admin = get_supabase_admin()
    query = admin.table("habits").select("*").eq("user_id", user["id"])

    if active is not None:
        query = query.eq("is_active", active)
    if category:
        query = query.eq("category", category)

    query = query.eq("is_archived", False).order("sort_order")
    result = query.execute()
    return result.data or []


@router.get("/today")
async def get_today_habits(user: dict = Depends(get_current_user)):
    """
    PRIMARY HOME SCREEN ENDPOINT.
    Returns all habits scheduled for today with completion status
    and AI-computed optimal times.
    """
    admin = get_supabase_admin()
    today = date.today()
    today_dow = today.isoweekday()  # 1=Mon, 7=Sun

    # Get all active habits
    habits_result = (
        admin.table("habits")
        .select("*")
        .eq("user_id", user["id"])
        .eq("is_active", True)
        .eq("is_archived", False)
        .order("sort_order")
        .execute()
    )
    habits = habits_result.data or []

    # Filter by frequency (daily = all, weekly = check day)
    scheduled_habits = []
    for h in habits:
        if h["frequency_type"] == "daily":
            scheduled_habits.append(h)
        elif today_dow in (h.get("frequency_days") or []):
            scheduled_habits.append(h)

    # Get today's completions
    completions_result = (
        admin.table("habit_completions")
        .select("*")
        .eq("user_id", user["id"])
        .eq("completed_date", today.isoformat())
        .execute()
    )
    completions = {c["habit_id"]: c for c in (completions_result.data or [])}

    # Build combined response
    result = []
    for habit in scheduled_habits:
        completion = completions.get(habit["id"])
        scheduled_time = (
            habit.get("ai_optimal_time")
            if habit.get("ai_scheduling_enabled") and habit.get("ai_optimal_time")
            else habit.get("preferred_time")
        )
        result.append({
            "habit": habit,
            "is_completed_today": completion is not None,
            "completion": completion,
            "scheduled_time": scheduled_time,
        })

    # Sort: incomplete first, then by scheduled time
    result.sort(key=lambda x: (
        x["is_completed_today"],  # False (0) before True (1)
        x["scheduled_time"] or "99:99",
    ))

    return result


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a single habit by ID."""
    admin = get_supabase_admin()
    result = (
        admin.table("habits")
        .select("*")
        .eq("id", habit_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Habit not found")
    return result.data


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: str,
    body: HabitUpdate,
    user: dict = Depends(get_current_user),
):
    """Update a habit."""
    admin = get_supabase_admin()
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(400, "No fields to update")

    result = (
        admin.table("habits")
        .update(update_data)
        .eq("id", habit_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Habit not found")
    return result.data[0]


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a habit and all its completions (cascade)."""
    admin = get_supabase_admin()
    result = (
        admin.table("habits")
        .delete()
        .eq("id", habit_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Habit not found")
    return None


@router.post("/{habit_id}/archive", response_model=HabitResponse)
async def archive_habit(
    habit_id: str,
    user: dict = Depends(get_current_user),
):
    """Archive a habit (soft delete)."""
    admin = get_supabase_admin()
    result = (
        admin.table("habits")
        .update({"is_archived": True, "is_active": False})
        .eq("id", habit_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Habit not found")
    return result.data[0]


@router.post("/{habit_id}/unarchive", response_model=HabitResponse)
async def unarchive_habit(
    habit_id: str,
    user: dict = Depends(get_current_user),
):
    """Unarchive a habit."""
    admin = get_supabase_admin()
    result = (
        admin.table("habits")
        .update({"is_archived": False, "is_active": True})
        .eq("id", habit_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Habit not found")
    return result.data[0]


@router.post("/reorder")
async def reorder_habits(
    body: HabitReorderRequest,
    user: dict = Depends(get_current_user),
):
    """Reorder habits by providing ordered list of IDs."""
    admin = get_supabase_admin()
    for idx, habit_id in enumerate(body.habit_ids):
        admin.table("habits").update({
            "sort_order": idx,
        }).eq("id", habit_id).eq("user_id", user["id"]).execute()

    return {"reordered": len(body.habit_ids)}


@router.get("/{habit_id}/calendar")
async def get_habit_calendar(
    habit_id: str,
    month: str = Query(..., description="YYYY-MM format, e.g. 2026-03"),
    user: dict = Depends(get_current_user),
):
    """Get calendar heatmap data for a habit in a given month."""
    admin = get_supabase_admin()

    # Validate month format
    try:
        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"
        # Calculate end of month
        if int(mon) == 12:
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{int(mon)+1:02d}-01"
    except ValueError:
        raise HTTPException(400, "Invalid month format. Use YYYY-MM")

    # Verify habit belongs to user
    habit_check = (
        admin.table("habits")
        .select("id")
        .eq("id", habit_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not habit_check.data:
        raise HTTPException(404, "Habit not found")

    # Get completions for the month
    result = (
        admin.table("habit_completions")
        .select("completed_date, mood_score, energy_score")
        .eq("habit_id", habit_id)
        .gte("completed_date", start_date)
        .lt("completed_date", end_date)
        .order("completed_date")
        .execute()
    )

    days = []
    for row in (result.data or []):
        days.append({
            "date": row["completed_date"],
            "completed": True,
            "mood_score": row.get("mood_score"),
            "energy_score": row.get("energy_score"),
        })

    return {"habit_id": habit_id, "month": month, "days": days}
