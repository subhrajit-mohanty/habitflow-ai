"""
HabitFlow AI — Streak Freeze Routes
Duolingo-style streak protection: earn or buy freezes with XP.
"""

import logging
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.dependencies import get_current_user
from app.database import get_supabase_admin
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/streak-freeze", tags=["Streak Freeze"])


class PurchaseFreezeResponse(BaseModel):
    freezes_available: int
    xp_remaining: int
    xp_cost: int


class FreezeStatusResponse(BaseModel):
    freezes_available: int
    freezes_used_total: int
    max_freezes: int
    xp_cost_to_buy: int
    can_afford: bool


FREEZE_XP_COST = 100  # XP cost to buy one freeze
MAX_FREEZES = 3       # Max freezes a user can hold


@router.get("/status", response_model=FreezeStatusResponse)
async def get_freeze_status(user: dict = Depends(get_current_user)):
    """Get current streak freeze inventory."""
    admin = get_supabase_admin()
    profile = (
        admin.table("profiles")
        .select("streak_freezes_available, streak_freezes_used_total, total_xp")
        .eq("id", user["id"])
        .single()
        .execute()
    ).data

    available = profile.get("streak_freezes_available", 1)
    return FreezeStatusResponse(
        freezes_available=available,
        freezes_used_total=profile.get("streak_freezes_used_total", 0),
        max_freezes=MAX_FREEZES,
        xp_cost_to_buy=FREEZE_XP_COST,
        can_afford=profile.get("total_xp", 0) >= FREEZE_XP_COST,
    )


@router.post("/purchase", response_model=PurchaseFreezeResponse)
async def purchase_freeze(user: dict = Depends(get_current_user)):
    """Buy a streak freeze using XP."""
    admin = get_supabase_admin()
    profile = (
        admin.table("profiles")
        .select("streak_freezes_available, total_xp, level")
        .eq("id", user["id"])
        .single()
        .execute()
    ).data

    available = profile.get("streak_freezes_available", 0)
    total_xp = profile.get("total_xp", 0)

    if available >= MAX_FREEZES:
        raise HTTPException(400, f"Maximum {MAX_FREEZES} freezes. Use one before buying more.")

    if total_xp < FREEZE_XP_COST:
        raise HTTPException(400, f"Not enough XP. Need {FREEZE_XP_COST}, have {total_xp}.")

    new_xp = total_xp - FREEZE_XP_COST
    new_level = (new_xp // 100) + 1
    new_available = available + 1

    admin.table("profiles").update({
        "streak_freezes_available": new_available,
        "total_xp": new_xp,
        "level": new_level,
    }).eq("id", user["id"]).execute()

    return PurchaseFreezeResponse(
        freezes_available=new_available,
        xp_remaining=new_xp,
        xp_cost=FREEZE_XP_COST,
    )


@router.post("/activate")
async def activate_freeze(user: dict = Depends(get_current_user)):
    """
    Manually activate a streak freeze for today.
    Also called automatically by the streak engine when a day is missed.
    """
    admin = get_supabase_admin()
    today = date.today()

    profile = (
        admin.table("profiles")
        .select("streak_freezes_available, streak_freezes_used_total")
        .eq("id", user["id"])
        .single()
        .execute()
    ).data

    available = profile.get("streak_freezes_available", 0)
    if available <= 0:
        raise HTTPException(400, "No streak freezes available. Earn or purchase one first.")

    # Check if already used today
    existing = (
        admin.table("streak_freeze_log")
        .select("id")
        .eq("user_id", user["id"])
        .eq("freeze_date", today.isoformat())
        .execute()
    )
    if existing.data:
        raise HTTPException(409, "Streak freeze already active for today.")

    # Use the freeze
    admin.table("streak_freeze_log").insert({
        "user_id": user["id"],
        "freeze_date": today.isoformat(),
        "source": "purchased",
        "xp_cost": 0,
    }).execute()

    admin.table("profiles").update({
        "streak_freezes_available": available - 1,
        "streak_freezes_used_total": profile.get("streak_freezes_used_total", 0) + 1,
    }).eq("id", user["id"]).execute()

    return {
        "status": "activated",
        "freeze_date": today.isoformat(),
        "freezes_remaining": available - 1,
    }


@router.get("/history")
async def freeze_history(user: dict = Depends(get_current_user)):
    """Get streak freeze usage history."""
    admin = get_supabase_admin()
    result = (
        admin.table("streak_freeze_log")
        .select("*")
        .eq("user_id", user["id"])
        .order("freeze_date", desc=True)
        .limit(20)
        .execute()
    )
    return result.data or []
