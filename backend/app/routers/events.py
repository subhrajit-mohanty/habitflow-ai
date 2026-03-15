"""
HabitFlow AI — Behavior Event Routes
Fire-and-forget events for ML model training.
"""

from fastapi import APIRouter, Depends, status
from app.dependencies import get_current_user
from app.database import get_supabase_admin
from app.models.schemas import BehaviorEventCreate

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def track_event(
    body: BehaviorEventCreate,
    user: dict = Depends(get_current_user),
):
    """Track a behavior event for ML training. Fire-and-forget."""
    admin = get_supabase_admin()
    try:
        admin.table("user_behavior_events").insert({
            "user_id": user["id"],
            "event_type": body.event_type,
            "event_data": body.event_data,
            "local_time": body.local_time,
            "day_of_week": body.day_of_week,
        }).execute()
    except Exception:
        pass  # Best effort — don't fail the request
    return {"accepted": True}
