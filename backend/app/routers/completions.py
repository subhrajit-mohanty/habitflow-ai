"""
HabitFlow AI — Completion Routes (Check-ins)
The critical engagement path: check-in → streak → XP → badges.
"""

from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.dependencies import get_current_user
from app.database import get_supabase_admin
from app.models.schemas import CompletionCreate, CompletionResponse, CheckInResult
from app.services.streak_engine import update_habit_stats, award_xp
from app.services.badge_engine import check_and_award_badges

router = APIRouter(prefix="/completions", tags=["Completions"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CheckInResult)
async def create_completion(
    body: CompletionCreate,
    user: dict = Depends(get_current_user),
):
    """
    CHECK-IN — The most important endpoint in the app.
    
    Flow:
    1. Validate habit belongs to user & no duplicate for today
    2. Insert completion record
    3. Recalculate streak & habit stats
    4. Award XP (with streak bonus)
    5. Check for new badges
    6. Return enriched result
    """
    admin = get_supabase_admin()
    today = date.today()
    now = datetime.utcnow()

    # 1. Verify habit ownership
    habit_result = (
        admin.table("habits")
        .select("id, user_id, name")
        .eq("id", body.habit_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not habit_result.data:
        raise HTTPException(404, "Habit not found")

    # 2. Check for duplicate completion today
    existing = (
        admin.table("habit_completions")
        .select("id")
        .eq("habit_id", body.habit_id)
        .eq("completed_date", today.isoformat())
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already checked in for this habit today",
        )

    # 3. Insert completion
    completed_time = body.completed_time or now.strftime("%H:%M:%S")
    day_of_week = today.isoweekday()

    insert_data = {
        "habit_id": body.habit_id,
        "user_id": user["id"],
        "completed_date": today.isoformat(),
        "completed_time": completed_time,
        "day_of_week": day_of_week,
        "verification_type": body.verification_type,
        "mood_score": body.mood_score,
        "energy_score": body.energy_score,
        "note": body.note,
    }
    if body.photo_url:
        insert_data["photo_url"] = body.photo_url

    completion_result = admin.table("habit_completions").insert(insert_data).execute()
    if not completion_result.data:
        raise HTTPException(500, "Failed to create completion")

    completion = completion_result.data[0]

    # Async photo verification (fire-and-forget)
    if body.photo_url:
        import asyncio
        asyncio.create_task(_verify_photo(completion["id"], body.photo_url, habit_result.data["name"]))

    # 4. Update habit stats (streak, best_streak, total_completions, rate)
    stats = await update_habit_stats(body.habit_id, user["id"])

    # Update streak_day on the completion
    admin.table("habit_completions").update({
        "streak_day": stats["current_streak"],
    }).eq("id", completion["id"]).execute()

    # 5. Award XP
    xp_result = await award_xp(user["id"], stats["current_streak"])

    # Update XP on completion record
    admin.table("habit_completions").update({
        "xp_earned": xp_result["xp_earned"],
    }).eq("id", completion["id"]).execute()

    # 6. Check for new badges
    new_badges = await check_and_award_badges(
        user["id"], body.habit_id, stats["current_streak"]
    )

    # 7. Update daily log stats
    _update_daily_completion_stats(user["id"], today)

    return CheckInResult(
        completion=CompletionResponse(
            id=completion["id"],
            habit_id=completion["habit_id"],
            user_id=completion["user_id"],
            completed_at=completion.get("completed_at"),
            completed_date=completion["completed_date"],
            completed_time=completed_time,
            verification_type=completion.get("verification_type", "tap"),
            photo_url=completion.get("photo_url"),
            photo_verified=completion.get("photo_verified", False),
            mood_score=body.mood_score,
            energy_score=body.energy_score,
            note=body.note,
            xp_earned=xp_result["xp_earned"],
            streak_day=stats["current_streak"],
        ),
        xp_earned=xp_result["xp_earned"],
        new_streak=stats["current_streak"],
        new_badges=new_badges,
        level_up=xp_result["level_up"],
        new_level=xp_result["level"] if xp_result["level_up"] else None,
    )


@router.delete("/{completion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def undo_completion(
    completion_id: str,
    user: dict = Depends(get_current_user),
):
    """Undo a check-in. Recalculates streak and stats."""
    admin = get_supabase_admin()

    # Get the completion to know which habit to update
    completion = (
        admin.table("habit_completions")
        .select("id, habit_id, xp_earned")
        .eq("id", completion_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not completion.data:
        raise HTTPException(404, "Completion not found")

    habit_id = completion.data["habit_id"]
    xp_to_remove = completion.data.get("xp_earned", 0)

    # Delete the completion
    admin.table("habit_completions").delete().eq("id", completion_id).execute()

    # Recalculate habit stats
    await update_habit_stats(habit_id, user["id"])

    # Remove XP
    if xp_to_remove > 0:
        profile = (
            admin.table("profiles")
            .select("total_xp")
            .eq("id", user["id"])
            .single()
            .execute()
        ).data
        new_xp = max((profile.get("total_xp", 0)) - xp_to_remove, 0)
        admin.table("profiles").update({
            "total_xp": new_xp,
            "level": (new_xp // 100) + 1,
        }).eq("id", user["id"]).execute()

    return None


@router.get("/", response_model=list[CompletionResponse])
async def list_completions(
    habit_id: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    """List completions with optional filters."""
    admin = get_supabase_admin()
    query = (
        admin.table("habit_completions")
        .select("*")
        .eq("user_id", user["id"])
    )

    if habit_id:
        query = query.eq("habit_id", habit_id)
    if from_date:
        query = query.gte("completed_date", from_date)
    if to_date:
        query = query.lte("completed_date", to_date)

    query = query.order("completed_date", desc=True).limit(limit)
    result = query.execute()
    return result.data or []


# ============================================================
# Helper
# ============================================================

def _update_daily_completion_stats(user_id: str, log_date: date):
    """Update the daily_logs table with completion counts."""
    admin = get_supabase_admin()

    # Count today's completions
    completions = (
        admin.table("habit_completions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("completed_date", log_date.isoformat())
        .execute()
    )

    # Count total habits for today
    today_dow = log_date.isoweekday()
    habits = (
        admin.table("habits")
        .select("id, frequency_type, frequency_days")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .eq("is_archived", False)
        .execute()
    )
    total_today = sum(
        1 for h in (habits.data or [])
        if h["frequency_type"] == "daily" or today_dow in (h.get("frequency_days") or [])
    )

    completed = completions.count or 0
    pct = completed / max(total_today, 1)

    # Upsert daily log
    admin.table("daily_logs").upsert({
        "user_id": user_id,
        "log_date": log_date.isoformat(),
        "habits_completed": completed,
        "habits_total": total_today,
        "completion_pct": round(pct, 3),
    }, on_conflict="user_id,log_date").execute()


async def _verify_photo(completion_id: str, photo_url: str, habit_name: str):
    """
    Async photo verification using AI vision.
    Checks if the uploaded photo is relevant to the habit.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from app.config import get_settings
        settings = get_settings()

        # Use Gemini vision (free) for photo verification
        if settings.google_gemini_api_key:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_gemini_api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")

            response = model.generate_content([
                f"Is this photo evidence of someone doing the habit '{habit_name}'? "
                f"Reply with ONLY 'yes' or 'no'.",
                {"mime_type": "image/jpeg", "data": photo_url},
            ])
            verified = "yes" in response.text.lower()
        else:
            # If no vision API, auto-approve
            verified = True

        admin = get_supabase_admin()
        admin.table("habit_completions").update({
            "photo_verified": verified,
        }).eq("id", completion_id).execute()

        logger.info(f"Photo verification for {completion_id}: {verified}")
    except Exception as e:
        logger.warning(f"Photo verification failed for {completion_id}: {e}")
        # Don't fail the completion — just leave photo_verified as False
