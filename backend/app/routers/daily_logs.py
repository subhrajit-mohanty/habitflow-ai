"""
HabitFlow AI — Daily Log Routes
Mood, energy, journal, sleep tracking.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.dependencies import get_current_user
from app.database import get_supabase_admin
from app.models.schemas import DailyLogCreate, DailyLogResponse

router = APIRouter(prefix="/daily-logs", tags=["Daily Logs"])


@router.post("/", status_code=201, response_model=DailyLogResponse)
async def create_or_update_daily_log(
    body: DailyLogCreate,
    user: dict = Depends(get_current_user),
):
    """Create or update a daily log. Upserts — partial updates merge fields."""
    admin = get_supabase_admin()
    log_date = body.log_date or date.today().isoformat()

    insert_data = body.model_dump(exclude_none=True)
    insert_data["user_id"] = user["id"]
    insert_data["log_date"] = log_date

    # Compute averages if mood/energy provided
    mood_values = [v for v in [
        body.morning_mood, body.afternoon_mood, body.evening_mood
    ] if v is not None]
    energy_values = [v for v in [
        body.morning_energy, body.afternoon_energy, body.evening_energy
    ] if v is not None]

    if mood_values:
        insert_data["avg_mood"] = round(sum(mood_values) / len(mood_values), 2)
    if energy_values:
        insert_data["avg_energy"] = round(sum(energy_values) / len(energy_values), 2)

    result = (
        admin.table("daily_logs")
        .upsert(insert_data, on_conflict="user_id,log_date")
        .execute()
    )
    if not result.data:
        raise HTTPException(500, "Failed to save daily log")
    return result.data[0]


@router.get("/today", response_model=DailyLogResponse)
async def get_today_log(user: dict = Depends(get_current_user)):
    """Get today's daily log."""
    admin = get_supabase_admin()
    result = (
        admin.table("daily_logs")
        .select("*")
        .eq("user_id", user["id"])
        .eq("log_date", date.today().isoformat())
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "No log for today yet")
    return result.data


@router.get("/", response_model=list[DailyLogResponse])
async def list_daily_logs(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    limit: int = Query(30, ge=1, le=90),
    user: dict = Depends(get_current_user),
):
    """List daily logs within a date range."""
    admin = get_supabase_admin()
    query = admin.table("daily_logs").select("*").eq("user_id", user["id"])

    if from_date:
        query = query.gte("log_date", from_date)
    if to_date:
        query = query.lte("log_date", to_date)

    result = query.order("log_date", desc=True).limit(limit).execute()
    return result.data or []


@router.get("/{log_date}", response_model=DailyLogResponse)
async def get_daily_log(
    log_date: str,
    user: dict = Depends(get_current_user),
):
    """Get a daily log by date."""
    admin = get_supabase_admin()
    result = (
        admin.table("daily_logs")
        .select("*")
        .eq("user_id", user["id"])
        .eq("log_date", log_date)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(404, f"No log for {log_date}")
    return result.data
