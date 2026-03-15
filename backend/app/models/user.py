"""
HabitFlow AI — User & Profile Models
"""

from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class SubscriptionTier(str, Enum):
    free = "free"
    pro = "pro"
    lifetime = "lifetime"


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    wake_time: Optional[str] = None  # "07:00" format for JSON compat
    sleep_time: Optional[str] = None
    goals: Optional[List[str]] = None


class ProfileResponse(BaseModel):
    id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    subscription_tier: str = "free"
    total_xp: int = 0
    level: int = 1
    longest_streak: int = 0
    onboarding_completed: bool = False
    created_at: Optional[str] = None


class OnboardingRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=50)
    timezone: str = Field(default="UTC")
    goals: List[str] = Field(..., min_length=1, max_length=5)
    wake_time: str = Field(default="07:00")
    sleep_time: str = Field(default="23:00")
    initial_habits: List[str] = Field(default=[])
