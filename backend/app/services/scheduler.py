"""
HabitFlow AI — Background Notification Scheduler
Runs as a separate process or integrated with FastAPI via BackgroundTasks.
Handles timed delivery of habit reminders, streak protectors, and weekly summaries.

Run standalone: python -m app.services.scheduler
Or integrate with FastAPI using BackgroundTasks / APScheduler.
"""

import asyncio
import logging
from datetime import date, datetime, time, timedelta
from app.database import get_supabase_admin
from app.services.notification_service import (
    send_habit_reminder,
    send_streak_protector,
    send_weekly_summary,
    compute_daily_schedule,
)

logger = logging.getLogger(__name__)


async def run_habit_reminders():
    """
    Check all users' schedules and send habit reminders
    for the current time window (±5 min).
    Run every 5 minutes via cron or scheduler.
    """
    admin = get_supabase_admin()
    now = datetime.utcnow()
    current_time = now.strftime("%H:%M")

    # Time window: current ±5 min
    window_start = (now - timedelta(minutes=2)).strftime("%H:%M")
    window_end = (now + timedelta(minutes=2)).strftime("%H:%M")

    logger.info(f"Running habit reminders for window {window_start} - {window_end}")

    # Get all active habits scheduled in this window
    # Uses AI optimal time or preferred time
    habits = (
        admin.table("habits")
        .select("id, user_id, name, ai_optimal_time, preferred_time, ai_scheduling_enabled")
        .eq("is_active", True)
        .eq("is_archived", False)
        .execute()
    ).data or []

    sent_count = 0
    for habit in habits:
        scheduled = None
        if habit.get("ai_scheduling_enabled") and habit.get("ai_optimal_time"):
            scheduled = habit["ai_optimal_time"][:5]  # "HH:MM"
        elif habit.get("preferred_time"):
            scheduled = habit["preferred_time"][:5]

        if scheduled and window_start <= scheduled <= window_end:
            try:
                sent = await send_habit_reminder(habit["user_id"], habit["id"])
                if sent:
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error sending reminder for habit {habit['id']}: {e}")

    logger.info(f"Sent {sent_count} habit reminders")
    return sent_count


async def run_streak_protectors():
    """
    Send streak protection alerts to users with incomplete habits.
    Run at ~8PM local time (simplified: 20:00 UTC).
    """
    admin = get_supabase_admin()

    # Get all users with push tokens
    users = (
        admin.table("push_tokens")
        .select("user_id")
        .execute()
    ).data or []

    sent_count = 0
    for user in users:
        try:
            sent = await send_streak_protector(user["user_id"])
            if sent:
                sent_count += 1
        except Exception as e:
            logger.error(f"Streak protector error for {user['user_id']}: {e}")

    logger.info(f"Sent {sent_count} streak protectors")
    return sent_count


async def run_weekly_summaries():
    """
    Send weekly summary notifications.
    Run Sunday evening (~6PM local time).
    """
    if date.today().weekday() != 6:  # Sunday = 6
        logger.info("Not Sunday — skipping weekly summaries")
        return 0

    admin = get_supabase_admin()

    users = (
        admin.table("push_tokens")
        .select("user_id")
        .execute()
    ).data or []

    sent_count = 0
    for user in users:
        try:
            sent = await send_weekly_summary(user["user_id"])
            if sent:
                sent_count += 1
        except Exception as e:
            logger.error(f"Weekly summary error for {user['user_id']}: {e}")

    logger.info(f"Sent {sent_count} weekly summaries")
    return sent_count


# ============================================================
# Standalone runner (for cron / docker container)
# ============================================================

async def main():
    """Main scheduler loop. Run every 5 minutes."""
    logger.info("🔔 Notification scheduler started")
    while True:
        try:
            now = datetime.utcnow()
            minute = now.minute

            # Habit reminders: every 5 min
            if minute % 5 == 0:
                await run_habit_reminders()

            # Streak protectors: at 20:00 UTC
            if now.hour == 20 and minute == 0:
                await run_streak_protectors()

            # Weekly summaries: Sunday at 18:00 UTC
            if now.hour == 18 and minute == 0:
                await run_weekly_summaries()

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        # Sleep until next minute
        await asyncio.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
