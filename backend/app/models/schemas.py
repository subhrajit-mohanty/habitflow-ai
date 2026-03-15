"""
HabitFlow AI — Completion, DailyLog, Coach, Social, Analytics Models
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================
# Completions (Check-ins)
# ============================================================

class CompletionCreate(BaseModel):
    habit_id: str
    completed_time: Optional[str] = None  # "14:30" — defaults to now
    verification_type: str = "tap"
    photo_url: Optional[str] = None
    mood_score: Optional[int] = Field(None, ge=1, le=5)
    energy_score: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = None


class CompletionResponse(BaseModel):
    id: str
    habit_id: str
    user_id: str
    completed_at: Optional[str] = None
    completed_date: str
    completed_time: str
    verification_type: str = "tap"
    photo_url: Optional[str] = None
    photo_verified: bool = False
    mood_score: Optional[int] = None
    energy_score: Optional[int] = None
    note: Optional[str] = None
    xp_earned: int = 10
    streak_day: Optional[int] = None


class CheckInResult(BaseModel):
    completion: CompletionResponse
    xp_earned: int
    new_streak: int
    new_badges: List[dict] = []
    level_up: bool = False
    new_level: Optional[int] = None


# ============================================================
# Daily Logs
# ============================================================

class DailyLogCreate(BaseModel):
    log_date: Optional[str] = None  # "2026-03-15" — defaults to today
    morning_mood: Optional[int] = Field(None, ge=1, le=5)
    morning_energy: Optional[int] = Field(None, ge=1, le=5)
    afternoon_mood: Optional[int] = Field(None, ge=1, le=5)
    afternoon_energy: Optional[int] = Field(None, ge=1, le=5)
    evening_mood: Optional[int] = Field(None, ge=1, le=5)
    evening_energy: Optional[int] = Field(None, ge=1, le=5)
    journal_entry: Optional[str] = None
    gratitude: Optional[List[str]] = None
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    sleep_quality: Optional[int] = Field(None, ge=1, le=5)


class DailyLogResponse(BaseModel):
    id: str
    user_id: str
    log_date: str
    morning_mood: Optional[int] = None
    morning_energy: Optional[int] = None
    afternoon_mood: Optional[int] = None
    afternoon_energy: Optional[int] = None
    evening_mood: Optional[int] = None
    evening_energy: Optional[int] = None
    avg_mood: Optional[float] = None
    avg_energy: Optional[float] = None
    journal_entry: Optional[str] = None
    gratitude: Optional[List[str]] = None
    sleep_hours: Optional[float] = None
    sleep_quality: Optional[int] = None
    habits_completed: int = 0
    habits_total: int = 0
    completion_pct: float = 0.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============================================================
# AI Coach
# ============================================================

class CoachChatRequest(BaseModel):
    conversation_id: Optional[str] = None  # None = new conversation
    message: str = Field(..., min_length=1, max_length=2000)


class CoachMessageResponse(BaseModel):
    conversation_id: str
    message_id: str
    role: str
    content: str
    tokens_used: int = 0
    created_at: Optional[str] = None


class CoachConversationResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    conversation_type: str = "chat"
    total_tokens: int = 0
    is_archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WeeklySummaryResponse(BaseModel):
    week_start: str
    week_end: str
    total_completions: int
    completion_rate: float
    best_habit: Optional[str] = None
    worst_habit: Optional[str] = None
    avg_mood: Optional[float] = None
    avg_energy: Optional[float] = None
    mood_habit_correlations: List[dict] = []
    ai_summary: str
    suggestions: List[str] = []


# ============================================================
# Social
# ============================================================

class BuddyInviteRequest(BaseModel):
    username: str


class BuddyPairResponse(BaseModel):
    id: str
    buddy: dict  # { id, username, display_name, avatar_url }
    status: str
    created_at: Optional[str] = None


class NudgeRequest(BaseModel):
    to_user_id: str
    message: str = "💪 Time to do your habit!"
    habit_id: Optional[str] = None


class NudgeResponse(BaseModel):
    id: str
    from_user: dict  # { id, username, display_name, avatar_url }
    message: str
    habit_id: Optional[str] = None
    is_read: bool = False
    created_at: Optional[str] = None


class ChallengeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    habit_category: Optional[str] = None
    start_date: str  # "2026-04-01"
    end_date: str
    is_public: bool = True
    max_participants: int = Field(default=50, ge=2, le=500)


class ChallengeResponse(BaseModel):
    id: str
    creator_id: str
    title: str
    description: Optional[str] = None
    habit_category: Optional[str] = None
    start_date: str
    end_date: str
    is_public: bool
    max_participants: int
    participant_count: int = 0
    created_at: Optional[str] = None


# ============================================================
# Analytics
# ============================================================

class HabitAnalytics(BaseModel):
    habit_id: str
    habit_name: str
    period_days: int
    completions: int
    completion_rate: float
    current_streak: int
    best_streak: int
    avg_completion_time: Optional[str] = None
    best_day_of_week: Optional[int] = None
    worst_day_of_week: Optional[int] = None
    mood_correlation: Optional[float] = None
    energy_correlation: Optional[float] = None


class OverallAnalytics(BaseModel):
    period_days: int
    total_habits: int
    active_habits: int
    total_completions: int
    overall_completion_rate: float
    total_xp: int
    level: int
    badges_earned: int
    avg_mood: Optional[float] = None
    avg_energy: Optional[float] = None
    best_day: Optional[str] = None
    habit_analytics: List[HabitAnalytics] = []
    mood_trend: List[dict] = []
    energy_trend: List[dict] = []


# ============================================================
# Gamification
# ============================================================

class BadgeResponse(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    category: str
    xp_reward: int
    earned: bool = False
    earned_at: Optional[str] = None


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    total_xp: int
    longest_streak: int


class LevelInfo(BaseModel):
    current_level: int
    current_xp: int
    xp_to_next_level: int
    total_xp: int
    progress_pct: float  # 0.0 to 1.0


# ============================================================
# Events (Behavior Tracking)
# ============================================================

class BehaviorEventCreate(BaseModel):
    event_type: str  # app_open, notification_tap, etc.
    event_data: dict = {}
    local_time: Optional[str] = None
    day_of_week: Optional[int] = None


# ============================================================
# Notifications
# ============================================================

class PushTokenRegister(BaseModel):
    push_token: str
    platform: str = Field(..., pattern="^(ios|android)$")


class NotificationPreferences(BaseModel):
    habit_reminders: bool = True
    streak_alerts: bool = True
    nudges: bool = True
    weekly_summary: bool = True
    badge_earned: bool = True
    challenge_updates: bool = True
