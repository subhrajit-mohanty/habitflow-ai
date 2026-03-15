"""
HabitFlow AI — Database Client (Supabase)
"""

from supabase import create_client, Client
from functools import lru_cache
from app.config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """Public client — respects RLS policies, uses anon key."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


@lru_cache()
def get_supabase_admin() -> Client:
    """Admin client — bypasses RLS, uses service role key.
    Use ONLY for server-side operations (badge checks, notifications, etc.)
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)
