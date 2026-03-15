"""
HabitFlow AI — Social Routes
Buddies, nudges, challenges.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.dependencies import get_current_user, require_pro
from app.database import get_supabase_admin
from app.models.schemas import (
    BuddyInviteRequest, BuddyPairResponse,
    NudgeRequest, NudgeResponse,
    ChallengeCreate, ChallengeResponse,
)

router = APIRouter(prefix="/social", tags=["Social"])


# ============================================================
# Buddies
# ============================================================

@router.post("/buddies/invite", status_code=status.HTTP_201_CREATED)
async def invite_buddy(
    body: BuddyInviteRequest,
    user: dict = Depends(get_current_user),
):
    """Invite a buddy by username."""
    admin = get_supabase_admin()

    # Find the target user
    target = (
        admin.table("profiles")
        .select("id")
        .eq("username", body.username)
        .single()
        .execute()
    )
    if not target.data:
        raise HTTPException(404, "User not found")

    target_id = target.data["id"]
    if target_id == user["id"]:
        raise HTTPException(400, "You can't buddy yourself")

    # Check for existing pair
    existing = (
        admin.table("buddy_pairs")
        .select("id, status")
        .or_(
            f"and(user_a_id.eq.{user['id']},user_b_id.eq.{target_id}),"
            f"and(user_a_id.eq.{target_id},user_b_id.eq.{user['id']})"
        )
        .execute()
    )
    if existing.data:
        pair = existing.data[0]
        if pair["status"] == "active":
            raise HTTPException(409, "Already buddies")
        if pair["status"] == "pending":
            raise HTTPException(409, "Invite already pending")

    # Create buddy pair
    result = admin.table("buddy_pairs").insert({
        "user_a_id": user["id"],
        "user_b_id": target_id,
        "invited_by": user["id"],
        "status": "pending",
    }).execute()

    return {"buddy_pair_id": result.data[0]["id"], "status": "pending"}


@router.get("/buddies")
async def list_buddies(user: dict = Depends(get_current_user)):
    """List all buddy pairs (active and pending)."""
    admin = get_supabase_admin()

    result = (
        admin.table("buddy_pairs")
        .select("*, profiles!buddy_pairs_user_a_id_fkey(id, username, display_name, avatar_url), profiles!buddy_pairs_user_b_id_fkey(id, username, display_name, avatar_url)")
        .or_(f"user_a_id.eq.{user['id']},user_b_id.eq.{user['id']}")
        .in_("status", ["active", "pending"])
        .order("created_at", desc=True)
        .execute()
    )

    buddies = []
    for pair in (result.data or []):
        # Determine which user is the buddy
        if pair.get("user_a_id") == user["id"]:
            buddy_profile = pair.get("profiles!buddy_pairs_user_b_id_fkey", {})
        else:
            buddy_profile = pair.get("profiles!buddy_pairs_user_a_id_fkey", {})

        buddies.append({
            "id": pair["id"],
            "buddy": buddy_profile,
            "status": pair["status"],
            "created_at": pair.get("created_at"),
        })

    return buddies


@router.post("/buddies/{pair_id}/accept")
async def accept_buddy(
    pair_id: str,
    user: dict = Depends(get_current_user),
):
    """Accept a buddy invite."""
    admin = get_supabase_admin()
    result = (
        admin.table("buddy_pairs")
        .update({"status": "active"})
        .eq("id", pair_id)
        .eq("user_b_id", user["id"])  # Only the invited user can accept
        .eq("status", "pending")
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Invite not found or already processed")
    return {"status": "active"}


@router.post("/buddies/{pair_id}/decline")
async def decline_buddy(
    pair_id: str,
    user: dict = Depends(get_current_user),
):
    """Decline a buddy invite."""
    admin = get_supabase_admin()
    result = (
        admin.table("buddy_pairs")
        .update({"status": "declined"})
        .eq("id", pair_id)
        .eq("user_b_id", user["id"])
        .eq("status", "pending")
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Invite not found")
    return {"status": "declined"}


@router.delete("/buddies/{pair_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_buddy(
    pair_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a buddy pair."""
    admin = get_supabase_admin()
    result = (
        admin.table("buddy_pairs")
        .update({"status": "removed"})
        .eq("id", pair_id)
        .or_(f"user_a_id.eq.{user['id']},user_b_id.eq.{user['id']}")
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Buddy pair not found")
    return None


# ============================================================
# Nudges
# ============================================================

@router.post("/nudges", status_code=status.HTTP_201_CREATED)
async def send_nudge(
    body: NudgeRequest,
    user: dict = Depends(get_current_user),
):
    """Send a nudge to a buddy."""
    admin = get_supabase_admin()

    # Verify they're buddies
    existing = (
        admin.table("buddy_pairs")
        .select("id")
        .or_(
            f"and(user_a_id.eq.{user['id']},user_b_id.eq.{body.to_user_id}),"
            f"and(user_a_id.eq.{body.to_user_id},user_b_id.eq.{user['id']})"
        )
        .eq("status", "active")
        .execute()
    )
    if not existing.data:
        raise HTTPException(403, "You can only nudge active buddies")

    result = admin.table("nudges").insert({
        "from_user_id": user["id"],
        "to_user_id": body.to_user_id,
        "message": body.message,
        "habit_id": body.habit_id,
    }).execute()

    # TODO: trigger push notification

    return {"nudge_id": result.data[0]["id"]}


@router.get("/nudges")
async def list_nudges(
    unread: Optional[bool] = Query(None),
    user: dict = Depends(get_current_user),
):
    """List received nudges."""
    admin = get_supabase_admin()
    query = (
        admin.table("nudges")
        .select("*, profiles!nudges_from_user_id_fkey(id, username, display_name, avatar_url)")
        .eq("to_user_id", user["id"])
    )
    if unread is True:
        query = query.eq("is_read", False)

    result = query.order("created_at", desc=True).limit(20).execute()

    nudges = []
    for n in (result.data or []):
        nudges.append({
            "id": n["id"],
            "from_user": n.get("profiles!nudges_from_user_id_fkey", {}),
            "message": n["message"],
            "habit_id": n.get("habit_id"),
            "is_read": n["is_read"],
            "created_at": n.get("created_at"),
        })
    return nudges


@router.post("/nudges/{nudge_id}/read")
async def mark_nudge_read(
    nudge_id: str,
    user: dict = Depends(get_current_user),
):
    """Mark a nudge as read."""
    admin = get_supabase_admin()
    admin.table("nudges").update({"is_read": True}).eq("id", nudge_id).eq("to_user_id", user["id"]).execute()
    return {"is_read": True}
