"""
HabitFlow AI — Notification Routes
Token registration, preferences, history, trigger endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.dependencies import get_current_user, get_user_profile
from app.database import get_supabase_admin
from app.models.schemas import PushTokenRegister, NotificationPreferences
from app.services.notification_service import (
    send_habit_reminder,
    send_streak_protector,
    send_weekly_summary,
    compute_daily_schedule,
    get_user_notification_prefs,
    update_notification_prefs,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============================================================
# Push Token Registration
# ============================================================

@router.post("/register-token")
async def register_push_token(
    body: PushTokenRegister,
    user: dict = Depends(get_current_user),
):
    """Register or update a device push token."""
    admin = get_supabase_admin()

    # Upsert token (one per user, update if exists)
    result = admin.table("push_tokens").upsert({
        "user_id": user["id"],
        "token": body.push_token,
        "platform": body.platform,
    }, on_conflict="user_id").execute()

    return {"registered": True, "platform": body.platform}


@router.delete("/register-token", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_push_token(user: dict = Depends(get_current_user)):
    """Remove push token (disable notifications)."""
    admin = get_supabase_admin()
    admin.table("push_tokens").delete().eq("user_id", user["id"]).execute()
    return None


# ============================================================
# Notification Preferences
# ============================================================

@router.get("/preferences", response_model=NotificationPreferences)
async def get_preferences(user: dict = Depends(get_current_user)):
    """Get notification preferences."""
    prefs = await get_user_notification_prefs(user["id"])
    return prefs


@router.patch("/preferences", response_model=NotificationPreferences)
async def update_preferences(
    body: NotificationPreferences,
    user: dict = Depends(get_current_user),
):
    """Update notification preferences."""
    prefs = body.model_dump(exclude_none=True)
    result = await update_notification_prefs(user["id"], prefs)
    return result


# ============================================================
# Notification History
# ============================================================

@router.get("/history")
async def get_notification_history(
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    """Get recent notification history."""
    admin = get_supabase_admin()
    result = (
        admin.table("notification_log")
        .select("*")
        .eq("user_id", user["id"])
        .order("sent_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ============================================================
# Today's Schedule (for client-side local notifications)
# ============================================================

@router.get("/schedule")
async def get_today_schedule(user: dict = Depends(get_current_user)):
    """
    Get today's computed notification schedule.
    The mobile app uses this to schedule local notifications
    as a backup when the server-side scheduler can't reach the device.
    """
    schedule = await compute_daily_schedule(user["id"])
    return {"date": str(__import__("datetime").date.today()), "notifications": schedule}


# ============================================================
# Manual Triggers (for testing / admin)
# ============================================================

@router.post("/trigger/habit-reminder/{habit_id}")
async def trigger_habit_reminder(
    habit_id: str,
    user: dict = Depends(get_current_user),
):
    """Manually trigger a habit reminder (for testing)."""
    sent = await send_habit_reminder(user["id"], habit_id)
    return {"sent": sent}


@router.post("/trigger/streak-protector")
async def trigger_streak_protector(user: dict = Depends(get_current_user)):
    """Manually trigger streak protection alert."""
    sent = await send_streak_protector(user["id"])
    return {"sent": sent}


@router.post("/trigger/weekly-summary")
async def trigger_weekly_summary(user: dict = Depends(get_current_user)):
    """Manually trigger weekly summary notification."""
    sent = await send_weekly_summary(user["id"])
    return {"sent": sent}
