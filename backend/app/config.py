"""
HabitFlow AI — Configuration & Settings
Loads from environment variables / .env file
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "HabitFlow AI"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/v1"

    # Supabase
    supabase_url: str
    supabase_key: str  # anon/public key
    supabase_service_key: str  # service role key (server-side only)

    # JWT (Supabase uses its own JWT — we just verify)
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # AI / LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_gemini_api_key: str = ""
    ai_model: str = "claude-sonnet-4-20250514"
    ai_max_tokens: int = 1024
    free_ai_model: str = "gemini-2.0-flash"
    free_ai_provider: str = "gemini"  # "gemini" or "anthropic"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Firebase (push notifications)
    firebase_credentials_path: str = ""

    # Storage
    storage_bucket: str = "habitflow-uploads"
    max_upload_size_mb: int = 10

    # Rate Limits
    free_rate_limit: int = 60  # req/min
    pro_rate_limit: int = 120
    ai_rate_limit: int = 10
    free_ai_messages_per_week: int = 3

    # Subscription Limits
    free_max_habits: int = 3
    pro_max_habits: int = 50

    # XP Configuration
    xp_per_completion: int = 10
    xp_streak_bonus_multiplier: float = 1.5  # bonus after 7-day streak
    xp_per_level: int = 100  # XP needed per level

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
