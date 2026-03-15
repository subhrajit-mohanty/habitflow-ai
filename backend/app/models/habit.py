"""
HabitFlow AI — Habit Models
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class HabitCategory(str, Enum):
    health = "health"
    fitness = "fitness"
    mindfulness = "mindfulness"
    productivity = "productivity"
    learning = "learning"
    social = "social"
    nutrition = "nutrition"
    sleep = "sleep"
    general = "general"


class FrequencyType(str, Enum):
    daily = "daily"
    weekly = "weekly"
    custom = "custom"


class VerificationType(str, Enum):
    tap = "tap"
    photo = "photo"
    timer = "timer"
    gps = "gps"


class HabitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: str = "✨"
    color: str = "#6C63FF"
    category: HabitCategory = HabitCategory.general
    frequency_type: FrequencyType = FrequencyType.daily
    frequency_days: List[int] = Field(default=[1, 2, 3, 4, 5, 6, 7])
    preferred_time: Optional[str] = None  # "08:30" format
    duration_minutes: int = Field(default=2, ge=1, le=120)
    ai_scheduling_enabled: bool = True
    verification_type: VerificationType = VerificationType.tap
    stack_after_habit_id: Optional[str] = None


class HabitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    category: Optional[HabitCategory] = None
    frequency_type: Optional[FrequencyType] = None
    frequency_days: Optional[List[int]] = None
    preferred_time: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=120)
    ai_scheduling_enabled: Optional[bool] = None
    verification_type: Optional[VerificationType] = None
    stack_after_habit_id: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class HabitResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    icon: str = "✨"
    color: str = "#6C63FF"
    category: str = "general"
    frequency_type: str = "daily"
    frequency_days: List[int] = [1, 2, 3, 4, 5, 6, 7]
    preferred_time: Optional[str] = None
    duration_minutes: int = 2
    ai_scheduling_enabled: bool = True
    ai_optimal_time: Optional[str] = None
    ai_confidence_score: float = 0.0
    verification_type: str = "tap"
    stack_after_habit_id: Optional[str] = None
    is_active: bool = True
    is_archived: bool = False
    current_streak: int = 0
    best_streak: int = 0
    total_completions: int = 0
    completion_rate: float = 0.0
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class HabitReorderRequest(BaseModel):
    habit_ids: List[str] = Field(..., min_length=1)


class HabitTemplate(BaseModel):
    name: str
    description: str
    icon: str
    color: str
    category: str
    duration_minutes: int
    suggested_time: Optional[str] = None
