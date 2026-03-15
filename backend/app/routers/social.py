"""
HabitFlow AI — Social Routes
Buddies, nudges, challenges.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.dependencies import get_current_user
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

    # Trigger push notification (fire-and-forget)
    import logging
    logger = logging.getLogger(__name__)
    try:
        from app.services.notification_service import send_buddy_nudge
        await send_buddy_nudge(
            from_user_id=user["id"],
            to_user_id=body.to_user_id,
            message=body.message,
            habit_id=body.habit_id,
        )
    except Exception as e:
        logger.warning(f"Nudge notification failed: {e}")

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


# ============================================================
# Challenges
# ============================================================

@router.post("/challenges", status_code=status.HTTP_201_CREATED, response_model=ChallengeResponse)
async def create_challenge(
    body: ChallengeCreate,
    user: dict = Depends(get_current_user),
):
    """Create a new habit challenge."""
    admin = get_supabase_admin()
    from datetime import date as date_type

    # Validate dates
    start = date_type.fromisoformat(body.start_date)
    end = date_type.fromisoformat(body.end_date)
    if end <= start:
        raise HTTPException(400, "End date must be after start date")
    if (end - start).days > 90:
        raise HTTPException(400, "Challenges can be at most 90 days long")

    result = admin.table("challenges").insert({
        "creator_id": user["id"],
        "title": body.title,
        "description": body.description,
        "habit_category": body.habit_category,
        "start_date": body.start_date,
        "end_date": body.end_date,
        "is_public": body.is_public,
        "max_participants": body.max_participants,
    }).execute()

    challenge = result.data[0]

    # Auto-join creator
    admin.table("challenge_participants").insert({
        "challenge_id": challenge["id"],
        "user_id": user["id"],
    }).execute()

    challenge["participant_count"] = 1
    return challenge


@router.get("/challenges")
async def list_challenges(
    active: Optional[bool] = Query(True),
    user: dict = Depends(get_current_user),
):
    """List public challenges. If active=True, only show ongoing/upcoming."""
    admin = get_supabase_admin()
    from datetime import date as date_type

    query = (
        admin.table("challenges")
        .select("*, challenge_participants(count)")
        .eq("is_public", True)
        .order("start_date", desc=True)
        .limit(30)
    )

    if active:
        query = query.gte("end_date", date_type.today().isoformat())

    result = query.execute()

    challenges = []
    for c in (result.data or []):
        participants = c.pop("challenge_participants", [])
        c["participant_count"] = participants[0].get("count", 0) if participants else 0
        challenges.append(c)

    return challenges


@router.get("/challenges/mine")
async def my_challenges(user: dict = Depends(get_current_user)):
    """List challenges the user has joined."""
    admin = get_supabase_admin()

    # Get challenge IDs user has joined
    participations = (
        admin.table("challenge_participants")
        .select("challenge_id, total_completions, current_streak, joined_at")
        .eq("user_id", user["id"])
        .execute()
    ).data or []

    if not participations:
        return []

    challenge_ids = [p["challenge_id"] for p in participations]
    challenges = (
        admin.table("challenges")
        .select("*")
        .in_("id", challenge_ids)
        .order("start_date", desc=True)
        .execute()
    ).data or []

    # Merge participation data
    part_map = {p["challenge_id"]: p for p in participations}
    result = []
    for c in challenges:
        p = part_map.get(c["id"], {})
        c["my_completions"] = p.get("total_completions", 0)
        c["my_streak"] = p.get("current_streak", 0)
        c["joined_at"] = p.get("joined_at")
        result.append(c)

    return result


@router.get("/challenges/{challenge_id}")
async def get_challenge(
    challenge_id: str,
    user: dict = Depends(get_current_user),
):
    """Get challenge details with leaderboard."""
    admin = get_supabase_admin()

    challenge = (
        admin.table("challenges")
        .select("*")
        .eq("id", challenge_id)
        .single()
        .execute()
    ).data
    if not challenge:
        raise HTTPException(404, "Challenge not found")

    # Get participants with profiles
    participants = (
        admin.table("challenge_participants")
        .select("user_id, total_completions, current_streak, joined_at, profiles(display_name, username, avatar_url)")
        .eq("challenge_id", challenge_id)
        .order("total_completions", desc=True)
        .execute()
    ).data or []

    # Check if user has joined
    user_joined = any(p["user_id"] == user["id"] for p in participants)

    challenge["participants"] = participants
    challenge["participant_count"] = len(participants)
    challenge["user_joined"] = user_joined

    return challenge


@router.post("/challenges/{challenge_id}/join")
async def join_challenge(
    challenge_id: str,
    user: dict = Depends(get_current_user),
):
    """Join a challenge."""
    admin = get_supabase_admin()
    from datetime import date as date_type

    challenge = (
        admin.table("challenges")
        .select("id, end_date, max_participants")
        .eq("id", challenge_id)
        .single()
        .execute()
    ).data
    if not challenge:
        raise HTTPException(404, "Challenge not found")

    # Check if ended
    if date_type.fromisoformat(challenge["end_date"]) < date_type.today():
        raise HTTPException(400, "This challenge has ended")

    # Check if already joined
    existing = (
        admin.table("challenge_participants")
        .select("id")
        .eq("challenge_id", challenge_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if existing.data:
        raise HTTPException(409, "Already joined this challenge")

    # Check participant limit
    count = (
        admin.table("challenge_participants")
        .select("id", count="exact")
        .eq("challenge_id", challenge_id)
        .execute()
    )
    if (count.count or 0) >= challenge["max_participants"]:
        raise HTTPException(400, "Challenge is full")

    admin.table("challenge_participants").insert({
        "challenge_id": challenge_id,
        "user_id": user["id"],
    }).execute()

    return {"status": "joined", "challenge_id": challenge_id}


@router.post("/challenges/{challenge_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_challenge(
    challenge_id: str,
    user: dict = Depends(get_current_user),
):
    """Leave a challenge."""
    admin = get_supabase_admin()
    result = (
        admin.table("challenge_participants")
        .delete()
        .eq("challenge_id", challenge_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Not in this challenge")
    return None
