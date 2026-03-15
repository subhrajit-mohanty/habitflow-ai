"""
HabitFlow AI — Notification Service
Handles push notification delivery via Firebase Cloud Messaging,
smart scheduling based on AI-computed optimal times, streak
protection alerts, nudge delivery, and weekly summaries.
"""

import json
import logging
from datetime import date, time, datetime, timedelta
from typing import Optional
from app.config import get_settings
from app.database import get_supabase_admin

logger = logging.getLogger(__name__)

# ─── Lazy Firebase init ───
_firebase_app = None

def _get_firebase():
    global _firebase_app
    if _firebase_app is None:
        import firebase_admin
        from firebase_admin import credentials
        settings = get_settings()
        if settings.firebase_credentials_path:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            logger.warning("Firebase credentials not configured — notifications disabled")
    return _firebase_app


# ============================================================
# CORE: Send Push Notification
# ============================================================

async def send_push(
    user_id: str,
    title: str,
    body: str,
    notification_type: str,
    data: dict = None,
    habit_id: str = None,
) -> bool:
    """
    Send a push notification to a user.
    Returns True if delivered, False otherwise.
    """
    admin = get_supabase_admin()

    # Get user's push token
    token_result = (
        admin.table("push_tokens")
        .select("token, platform")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not token_result.data:
        logger.debug(f"No push token for user {user_id}")
        return False

    token_record = token_result.data[0]
    push_token = token_record["token"]

    # Check notification preferences
    prefs = await get_user_notification_prefs(user_id)
    pref_map = {
        "habit_reminder": prefs.get("habit_reminders", True),
        "streak_alert": prefs.get("streak_alerts", True),
        "nudge": prefs.get("nudges", True),
        "weekly_summary": prefs.get("weekly_summary", True),
        "badge_earned": prefs.get("badge_earned", True),
        "challenge_update": prefs.get("challenge_updates", True),
    }
    if not pref_map.get(notification_type, True):
        logger.debug(f"Notification type {notification_type} disabled for user {user_id}")
        return False

    # Send via Firebase
    delivered = await _send_fcm(push_token, title, body, data or {})

    # Log the notification
    admin.table("notification_log").insert({
        "user_id": user_id,
        "habit_id": habit_id,
        "notification_type": notification_type,
        "title": title,
        "body": body,
        "push_token": push_token,
        "delivery_status": "sent" if delivered else "failed",
    }).execute()

    return delivered


async def _send_fcm(token: str, title: str, body: str, data: dict) -> bool:
    """Send via Firebase Cloud Messaging."""
    try:
        firebase = _get_firebase()
        if firebase is None:
            logger.warning("Firebase not initialized")
            return False

        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in data.items()},
            token=token,
            # iOS-specific
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        badge=1,
                        sound="default",
                        category="HABIT_REMINDER",
                    ),
                ),
            ),
            # Android-specific
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    icon="notification_icon",
                    color="#7C6BFF",
                    channel_id="habit_reminders",
                    sound="default",
                ),
            ),
        )

        response = messaging.send(message)
        logger.info(f"FCM sent: {response}")
        return True
    except Exception as e:
        logger.error(f"FCM send error: {e}")
        return False


# ============================================================
# SMART HABIT REMINDERS (AI-timed)
# ============================================================

async def send_habit_reminder(user_id: str, habit_id: str):
    """
    Send a contextual habit reminder.
    Uses AI-computed optimal time and personalizes the message
    based on streak, completion rate, and time of day.
    """
    admin = get_supabase_admin()

    # Get habit details
    habit = (
        admin.table("habits")
        .select("name, icon, current_streak, completion_rate, ai_optimal_time, preferred_time")
        .eq("id", habit_id)
        .single()
        .execute()
    ).data

    if not habit:
        return False

    streak = habit.get("current_streak", 0)
    rate = habit.get("completion_rate", 0)
    name = habit["name"]
    icon = habit.get("icon", "✨")

    # Check if already completed today
    today_check = (
        admin.table("habit_completions")
        .select("id")
        .eq("habit_id", habit_id)
        .eq("completed_date", date.today().isoformat())
        .execute()
    )
    if today_check.data:
        return False  # Already done today

    # Personalized message based on context
    if streak >= 21:
        title = f"{icon} Don't break a {streak}-day streak!"
        body = f"You've built a real habit with {name}. Keep the momentum going! 🔥"
    elif streak >= 7:
        title = f"{icon} {name} — {streak} days strong!"
        body = f"You're in the zone. Just {21 - streak} more days to form the habit! 💪"
    elif streak >= 3:
        title = f"{icon} Time for {name}"
        body = f"{streak}-day streak going! A quick {name} session keeps it alive."
    elif rate < 0.5:
        title = f"{icon} Small step: {name}"
        body = "Just 2 minutes. You don't need motivation, just a start. 🌱"
    else:
        title = f"{icon} {name} is waiting for you"
        body = "Tap to check in and earn XP! ✨"

    return await send_push(
        user_id=user_id,
        title=title,
        body=body,
        notification_type="habit_reminder",
        habit_id=habit_id,
        data={
            "type": "habit_reminder",
            "habit_id": habit_id,
            "screen": "home",
        },
    )


# ============================================================
# STREAK PROTECTOR
# ============================================================

async def send_streak_protector(user_id: str):
    """
    Evening alert if user has active streaks at risk.
    Sent at ~8PM user local time if habits are incomplete.
    """
    admin = get_supabase_admin()
    today = date.today()

    # Get habits with active streaks that aren't completed today
    habits = (
        admin.table("habits")
        .select("id, name, icon, current_streak")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .gt("current_streak", 0)
        .execute()
    ).data or []

    # Check which aren't completed
    at_risk = []
    for h in habits:
        done = (
            admin.table("habit_completions")
            .select("id")
            .eq("habit_id", h["id"])
            .eq("completed_date", today.isoformat())
            .execute()
        )
        if not done.data:
            at_risk.append(h)

    if not at_risk:
        return False

    # Build message
    if len(at_risk) == 1:
        h = at_risk[0]
        title = f"🔥 {h['icon']} {h['current_streak']}-day streak at risk!"
        body = f"Your {h['name']} streak will break at midnight. Quick — just {h['name'].lower()} and keep it alive!"
    else:
        streaks = [f"{h['icon']}{h['current_streak']}d" for h in at_risk[:3]]
        title = f"🔥 {len(at_risk)} streaks at risk tonight!"
        body = f"Don't let {', '.join(streaks)} break. You still have time! 💪"

    return await send_push(
        user_id=user_id,
        title=title,
        body=body,
        notification_type="streak_alert",
        data={
            "type": "streak_alert",
            "screen": "home",
            "at_risk_count": str(len(at_risk)),
        },
    )


# ============================================================
# NUDGE FROM BUDDY
# ============================================================

async def send_buddy_nudge(
    from_user_id: str,
    to_user_id: str,
    message: str = None,
    habit_id: str = None,
):
    """Send a nudge notification from a buddy."""
    admin = get_supabase_admin()

    # Get sender info
    sender = (
        admin.table("profiles")
        .select("display_name, username")
        .eq("id", from_user_id)
        .single()
        .execute()
    ).data

    sender_name = sender.get("display_name") or sender.get("username") or "Your buddy"

    if habit_id:
        habit = (
            admin.table("habits")
            .select("name, icon")
            .eq("id", habit_id)
            .single()
            .execute()
        ).data
        title = f"💪 {sender_name} nudged you!"
        body = message or f"Time to do your {habit.get('icon', '')} {habit.get('name', 'habit')}!"
    else:
        title = f"💪 {sender_name} nudged you!"
        body = message or "Your buddy thinks you should check in on your habits! 💪"

    return await send_push(
        user_id=to_user_id,
        title=title,
        body=body,
        notification_type="nudge",
        habit_id=habit_id,
        data={
            "type": "nudge",
            "screen": "social",
            "from_user_id": from_user_id,
        },
    )


# ============================================================
# BADGE EARNED
# ============================================================

async def send_badge_notification(user_id: str, badge: dict):
    """Notify user they earned a new badge."""
    return await send_push(
        user_id=user_id,
        title=f"🏅 Badge Earned: {badge.get('icon', '🏆')} {badge['name']}!",
        body=f"{badge.get('description', 'You unlocked a new achievement!')} +{badge.get('xp_reward', 0)} XP",
        notification_type="badge_earned",
        data={
            "type": "badge_earned",
            "screen": "profile",
            "badge_id": badge["id"],
        },
    )


# ============================================================
# WEEKLY SUMMARY
# ============================================================

async def send_weekly_summary(user_id: str):
    """Send the weekly review notification (Sunday evening)."""
    admin = get_supabase_admin()
    today = date.today()
    week_start = today - timedelta(days=7)

    # Quick stats
    completions = (
        admin.table("habit_completions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("completed_date", week_start.isoformat())
        .execute()
    )
    count = completions.count or 0

    habits = (
        admin.table("habits")
        .select("id")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    )
    total_possible = (len(habits.data) or 1) * 7
    rate = min(count / total_possible, 1.0)
    rate_pct = round(rate * 100)

    if rate_pct >= 80:
        title = "📊 Amazing week! Your review is ready"
        body = f"{rate_pct}% completion rate — you crushed it! Tap to see your full insights."
    elif rate_pct >= 50:
        title = "📊 Your weekly review is ready"
        body = f"{rate_pct}% this week with {count} check-ins. See what your AI coach says!"
    else:
        title = "📊 Weekly check-in"
        body = f"You completed {count} habits this week. Your AI coach has tips to improve!"

    return await send_push(
        user_id=user_id,
        title=title,
        body=body,
        notification_type="weekly_summary",
        data={
            "type": "weekly_summary",
            "screen": "coach",
            "completion_rate": str(rate_pct),
        },
    )


# ============================================================
# CHALLENGE UPDATE
# ============================================================

async def send_challenge_update(user_id: str, challenge_title: str, message: str):
    """Notify about challenge events (someone passed you, challenge ending, etc.)"""
    return await send_push(
        user_id=user_id,
        title=f"🏆 {challenge_title}",
        body=message,
        notification_type="challenge_update",
        data={"type": "challenge_update", "screen": "social"},
    )


# ============================================================
# SCHEDULER: Compute daily notification schedule
# ============================================================

async def compute_daily_schedule(user_id: str) -> list[dict]:
    """
    Compute today's notification schedule for a user.
    Returns list of {habit_id, scheduled_time, type}.
    Called by cron job at midnight or on app open.
    """
    admin = get_supabase_admin()

    # Get user profile for wake/sleep times
    profile = (
        admin.table("profiles")
        .select("wake_time, sleep_time, timezone")
        .eq("id", user_id)
        .single()
        .execute()
    ).data

    wake = profile.get("wake_time", "07:00")
    sleep_time = profile.get("sleep_time", "23:00")

    # Get active habits with scheduling info
    habits = (
        admin.table("habits")
        .select("id, name, icon, ai_optimal_time, preferred_time, ai_scheduling_enabled, frequency_type, frequency_days")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .eq("is_archived", False)
        .execute()
    ).data or []

    today_dow = date.today().isoweekday()
    schedule = []

    for h in habits:
        # Check if habit is scheduled for today
        if h["frequency_type"] == "weekly":
            if today_dow not in (h.get("frequency_days") or []):
                continue

        # Determine notification time
        if h.get("ai_scheduling_enabled") and h.get("ai_optimal_time"):
            notify_time = h["ai_optimal_time"]
        elif h.get("preferred_time"):
            notify_time = h["preferred_time"]
        else:
            # Default: 30 min after wake time
            notify_time = wake  # simplified

        schedule.append({
            "habit_id": h["id"],
            "habit_name": h["name"],
            "habit_icon": h.get("icon", "✨"),
            "scheduled_time": notify_time,
            "type": "habit_reminder",
        })

    # Add streak protector at 8PM (2 hours before typical sleep)
    schedule.append({
        "habit_id": None,
        "scheduled_time": "20:00",
        "type": "streak_protector",
    })

    # Sort by time
    schedule.sort(key=lambda x: x["scheduled_time"])
    return schedule


# ============================================================
# PREFERENCES
# ============================================================

async def get_user_notification_prefs(user_id: str) -> dict:
    """Get user's notification preferences."""
    admin = get_supabase_admin()
    result = (
        admin.table("notification_preferences")
        .select("*")
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if result.data:
        return result.data
    # Return defaults
    return {
        "habit_reminders": True,
        "streak_alerts": True,
        "nudges": True,
        "weekly_summary": True,
        "badge_earned": True,
        "challenge_updates": True,
    }


async def update_notification_prefs(user_id: str, prefs: dict) -> dict:
    """Update user's notification preferences."""
    admin = get_supabase_admin()
    result = (
        admin.table("notification_preferences")
        .upsert({"user_id": user_id, **prefs}, on_conflict="user_id")
        .execute()
    )
    return result.data[0] if result.data else prefs
