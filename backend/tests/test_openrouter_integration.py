"""
HabitFlow AI — OpenRouter Integration Dry-Run Tests
Tests the full OpenRouter integration without requiring real service dependencies.
All external modules (supabase, AI SDKs) are mocked at import level.
"""

import os
import sys
import types
import pytest
from unittest.mock import patch, MagicMock

# ─── Mock all heavy external modules before any app imports ───
MOCK_MODULES = [
    "supabase", "postgrest", "gotrue", "storage3", "realtime",
    "google", "google.generativeai",
    "anthropic",
    "redis", "firebase_admin",
    "sklearn", "sklearn.preprocessing",
    "PIL",
]

for mod_name in MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Mock supabase.create_client and Client
mock_supabase = sys.modules["supabase"]
mock_supabase.create_client = MagicMock(return_value=MagicMock())
mock_supabase.Client = MagicMock

# ─── Set env vars ───
os.environ.update({
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test-anon-key",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "JWT_SECRET": "test-jwt-secret",
    "GOOGLE_GEMINI_API_KEY": "test-gemini-key",
    "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "",
    "DEBUG": "true",
})

# Now safe to import app modules
from app.config import Settings
from app.services.ai_coach import (
    _call_openrouter,
    _resolve_provider,
    _call_provider,
    validate_api_key,
    QuotaExceededError,
)


# ============================================================
# 1. CONFIG — OpenRouter settings
# ============================================================

class TestConfig:
    def test_openrouter_defaults(self):
        s = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="k", supabase_service_key="sk", jwt_secret="s",
        )
        assert s.openrouter_base_url == "https://openrouter.ai/api/v1"
        assert s.openrouter_default_model == "google/gemini-2.0-flash-exp:free"
        print("  [PASS] Config: OpenRouter defaults loaded")

    def test_openrouter_custom_values(self):
        s = Settings(
            supabase_url="https://test.supabase.co",
            supabase_key="k", supabase_service_key="sk", jwt_secret="s",
            openrouter_base_url="https://custom.ai/v1",
            openrouter_default_model="anthropic/claude-3-haiku",
        )
        assert s.openrouter_base_url == "https://custom.ai/v1"
        assert s.openrouter_default_model == "anthropic/claude-3-haiku"
        print("  [PASS] Config: Custom OpenRouter values accepted")


# ============================================================
# 2. _call_openrouter
# ============================================================

class TestCallOpenRouter:
    @patch("app.services.ai_coach.get_settings")
    def test_call_openrouter_success(self, mock_settings):
        mock_settings.return_value = MagicMock(
            openrouter_base_url="https://openrouter.ai/api/v1",
        )

        with patch("openai.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client

            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock(message=MagicMock(content="Hello from OpenRouter!"))]
            mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
            mock_client.chat.completions.create.return_value = mock_resp

            result = _call_openrouter(
                system_prompt="You are a coach.",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=100,
                model="google/gemini-2.0-flash-exp:free",
                api_key="sk-or-test-key",
            )

            assert result["content"] == "Hello from OpenRouter!"
            assert result["tokens_used"] == 30
            assert result["provider"] == "openrouter"
            assert result["model"] == "google/gemini-2.0-flash-exp:free"

            MockOpenAI.assert_called_once_with(
                api_key="sk-or-test-key",
                base_url="https://openrouter.ai/api/v1",
            )

            call_args = mock_client.chat.completions.create.call_args
            msgs = call_args.kwargs.get("messages", call_args[1].get("messages") if len(call_args) > 1 else None)
            assert msgs[0]["role"] == "system"
            assert msgs[1]["role"] == "user"
            print("  [PASS] _call_openrouter: Correct API call structure")


# ============================================================
# 3. _resolve_provider — fallback chain
# ============================================================

class TestResolveProvider:
    def _mock_admin(self, key_data=None):
        admin = MagicMock()
        result = MagicMock()
        result.data = key_data or []
        admin.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = result
        return admin

    @patch("app.services.ai_coach.get_supabase_admin")
    @patch("app.services.ai_coach.get_settings")
    def test_default_gemini(self, mock_settings, mock_admin_fn):
        mock_settings.return_value = MagicMock(free_ai_model="gemini-2.0-flash")
        mock_admin_fn.return_value = self._mock_admin()
        result = _resolve_provider("user-123", {})
        assert result["provider"] == "gemini"
        assert result["api_key"] is None
        print("  [PASS] Resolve: Default → Gemini")

    @patch("app.services.ai_coach.get_supabase_admin")
    @patch("app.services.ai_coach.get_settings")
    def test_openrouter_with_key(self, mock_settings, mock_admin_fn):
        mock_settings.return_value = MagicMock(openrouter_default_model="google/gemini-2.0-flash-exp:free")
        mock_admin_fn.return_value = self._mock_admin(
            key_data=[{"api_key_encrypted": "sk-or-key", "is_valid": True}]
        )
        result = _resolve_provider("user-123", {"preferred_ai_provider": "openrouter"})
        assert result["provider"] == "openrouter"
        assert result["api_key"] == "sk-or-key"
        print("  [PASS] Resolve: OpenRouter with valid key")

    @patch("app.services.ai_coach.get_supabase_admin")
    @patch("app.services.ai_coach.get_settings")
    def test_openrouter_custom_model(self, mock_settings, mock_admin_fn):
        mock_settings.return_value = MagicMock(openrouter_default_model="google/gemini-2.0-flash-exp:free")
        mock_admin_fn.return_value = self._mock_admin(
            key_data=[{"api_key_encrypted": "sk-or-key", "is_valid": True}]
        )
        result = _resolve_provider("user-123", {
            "preferred_ai_provider": "openrouter",
            "preferred_model": "meta-llama/llama-3-70b",
        })
        assert result["model"] == "meta-llama/llama-3-70b"
        print("  [PASS] Resolve: OpenRouter with custom model")

    @patch("app.services.ai_coach.get_supabase_admin")
    @patch("app.services.ai_coach.get_settings")
    def test_openrouter_no_key_fallback(self, mock_settings, mock_admin_fn):
        mock_settings.return_value = MagicMock(free_ai_model="gemini-2.0-flash")
        mock_admin_fn.return_value = self._mock_admin(key_data=[])
        result = _resolve_provider("user-123", {"preferred_ai_provider": "openrouter"})
        assert result["provider"] == "gemini"
        print("  [PASS] Resolve: OpenRouter no key → Gemini fallback")

    @patch("app.services.ai_coach.get_supabase_admin")
    @patch("app.services.ai_coach.get_settings")
    def test_anthropic_with_key(self, mock_settings, mock_admin_fn):
        mock_settings.return_value = MagicMock(ai_model="claude-sonnet-4-20250514")
        mock_admin_fn.return_value = self._mock_admin(
            key_data=[{"api_key_encrypted": "sk-ant-key", "is_valid": True}]
        )
        result = _resolve_provider("user-123", {"preferred_ai_provider": "anthropic"})
        assert result["provider"] == "anthropic"
        assert result["api_key"] == "sk-ant-key"
        print("  [PASS] Resolve: Anthropic with valid key")


# ============================================================
# 4. _call_provider — routing
# ============================================================

class TestCallProvider:
    @patch("app.services.ai_coach._call_gemini")
    def test_routes_gemini(self, mock_fn):
        mock_fn.return_value = {"content": "ok", "tokens_used": 10, "model": "g", "provider": "gemini"}
        r = _call_provider({"provider": "gemini", "model": "g", "api_key": None}, "s", [], 100)
        assert r["provider"] == "gemini"
        mock_fn.assert_called_once()
        print("  [PASS] _call_provider routes to Gemini")

    @patch("app.services.ai_coach._call_openrouter")
    def test_routes_openrouter(self, mock_fn):
        mock_fn.return_value = {"content": "ok", "tokens_used": 10, "model": "m", "provider": "openrouter"}
        r = _call_provider({"provider": "openrouter", "model": "m", "api_key": "k"}, "s", [], 100)
        assert r["provider"] == "openrouter"
        mock_fn.assert_called_once()
        print("  [PASS] _call_provider routes to OpenRouter")

    @patch("app.services.ai_coach._call_anthropic")
    def test_routes_anthropic(self, mock_fn):
        mock_fn.return_value = {"content": "ok", "tokens_used": 10, "model": "c", "provider": "anthropic"}
        r = _call_provider({"provider": "anthropic", "model": "c", "api_key": "k"}, "s", [], 100)
        assert r["provider"] == "anthropic"
        mock_fn.assert_called_once()
        print("  [PASS] _call_provider routes to Anthropic")


# ============================================================
# 5. QuotaExceededError
# ============================================================

class TestQuotaExceeded:
    def test_is_exception(self):
        err = QuotaExceededError("test")
        assert isinstance(err, Exception)
        assert str(err) == "test"
        print("  [PASS] QuotaExceededError is valid Exception")


# ============================================================
# 6. validate_api_key — OpenRouter
# ============================================================

class TestValidateApiKey:
    @patch("openai.OpenAI")
    @patch("app.services.ai_coach.get_settings")
    def test_valid_openrouter_key(self, mock_settings, MockOpenAI):
        mock_settings.return_value = MagicMock(
            openrouter_base_url="https://openrouter.ai/api/v1",
            openrouter_default_model="google/gemini-2.0-flash-exp:free",
        )
        MockOpenAI.return_value = MagicMock()
        assert validate_api_key("openrouter", "sk-or-test") is True
        MockOpenAI.assert_called_once_with(
            api_key="sk-or-test",
            base_url="https://openrouter.ai/api/v1",
        )
        print("  [PASS] validate_api_key: Valid OpenRouter key → True")

    @patch("openai.OpenAI")
    @patch("app.services.ai_coach.get_settings")
    def test_invalid_openrouter_key(self, mock_settings, MockOpenAI):
        mock_settings.return_value = MagicMock(
            openrouter_base_url="https://openrouter.ai/api/v1",
            openrouter_default_model="google/gemini-2.0-flash-exp:free",
        )
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Invalid key")
        assert validate_api_key("openrouter", "sk-or-bad") is False
        print("  [PASS] validate_api_key: Invalid OpenRouter key → False")


# ============================================================
# 7. Migration file
# ============================================================

class TestMigration:
    def test_migration_exists_and_valid(self):
        path = os.path.join(os.path.dirname(__file__), "..", "migrations", "005_openrouter_support.sql")
        assert os.path.exists(path), "Migration 005 not found"
        with open(path) as f:
            sql = f.read()
        assert "openrouter" in sql
        assert "preferred_model" in sql
        assert "user_api_keys" in sql
        assert "profiles" in sql
        print("  [PASS] Migration 005: Exists with correct content")


# ============================================================
# 8. Mobile files — static analysis
# ============================================================

class TestMobileFiles:
    def _read(self, rel_path):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "mobile", "src", *rel_path.split("/"))
        with open(path) as f:
            return f.read()

    def test_api_js_provider_model_param(self):
        content = self._read("services/api.js")
        assert "preferred_model: model" in content
        assert "model = null" in content
        print("  [PASS] api.js: setProviderPreference accepts model param")

    def test_profile_screen_openrouter(self):
        content = self._read("screens/profile/ProfileScreen.js")
        assert "openrouter" in content
        assert "sk-or-" in content
        assert "OpenRouter" in content
        assert "100+" in content
        print("  [PASS] ProfileScreen: OpenRouter provider option present")

    def test_coach_screen_quota_handling(self):
        content = self._read("screens/coach/CoachChatScreen.js")
        assert "quota exceeded" in content.lower() or "429" in content
        assert "Free AI Limit Reached" in content
        print("  [PASS] CoachChatScreen: Quota exceeded handling present")


# ============================================================
# 9. E2E — Full chat with OpenRouter (mocked)
# ============================================================

class TestE2EChat:
    @patch("app.services.ai_coach._call_openrouter")
    @patch("app.services.ai_coach.build_system_prompt")
    @patch("app.services.ai_coach.get_supabase_admin")
    @patch("app.services.ai_coach.get_settings")
    @pytest.mark.asyncio
    async def test_chat_with_openrouter(self, mock_settings, mock_admin_fn, mock_build, mock_call_or):
        from app.services.ai_coach import chat

        mock_settings.return_value = MagicMock(
            ai_max_tokens=1024,
            openrouter_default_model="google/gemini-2.0-flash-exp:free",
            free_ai_model="gemini-2.0-flash",
        )

        admin = MagicMock()
        mock_admin_fn.return_value = admin

        # Key lookup returns valid OpenRouter key
        key_result = MagicMock()
        key_result.data = [{"api_key_encrypted": "sk-or-user", "is_valid": True}]
        admin.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = key_result

        # Conversation insert
        conv_result = MagicMock()
        conv_result.data = [{"id": "conv-001"}]

        # Message insert
        msg_result = MagicMock()
        msg_result.data = [{"id": "msg-001", "created_at": "2026-03-15T10:00:00Z"}]

        # History
        hist_result = MagicMock()
        hist_result.data = [{"role": "user", "content": "How am I doing?"}]

        # Chain table operations
        admin.table.return_value.insert.return_value.execute.side_effect = [conv_result, msg_result, msg_result]
        admin.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = hist_result
        admin.rpc.return_value.execute.return_value = MagicMock()

        mock_build.return_value = "You are HabitFlow AI Coach..."
        mock_call_or.return_value = {
            "content": "Great job on your 5-day streak!",
            "tokens_used": 45,
            "model": "google/gemini-2.0-flash-exp:free",
            "provider": "openrouter",
        }

        result = await chat(
            user_id="user-123",
            conversation_id=None,
            user_message="How am I doing?",
            profile={"preferred_ai_provider": "openrouter"},
        )

        assert result["role"] == "assistant"
        assert result["provider"] == "openrouter"
        assert result["content"] == "Great job on your 5-day streak!"
        assert result["tokens_used"] == 45
        print("  [PASS] E2E: Full chat flow with OpenRouter")

    @patch("app.services.ai_coach._call_provider")
    @patch("app.services.ai_coach.build_system_prompt")
    @patch("app.services.ai_coach.get_supabase_admin")
    @patch("app.services.ai_coach.get_settings")
    @pytest.mark.asyncio
    async def test_gemini_quota_raises_error(self, mock_settings, mock_admin_fn, mock_build, mock_call):
        from app.services.ai_coach import chat

        mock_settings.return_value = MagicMock(
            ai_max_tokens=1024, free_ai_model="gemini-2.0-flash",
        )

        admin = MagicMock()
        mock_admin_fn.return_value = admin

        # No BYOK key → falls to Gemini
        key_result = MagicMock()
        key_result.data = []
        admin.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = key_result

        conv_result = MagicMock()
        conv_result.data = [{"id": "conv-002"}]
        msg_result = MagicMock()
        msg_result.data = [{"id": "msg-002", "created_at": "2026-03-15T10:00:00Z"}]
        admin.table.return_value.insert.return_value.execute.side_effect = [conv_result, msg_result]

        hist_result = MagicMock()
        hist_result.data = [{"role": "user", "content": "hi"}]
        admin.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = hist_result

        mock_build.return_value = "system"
        mock_call.side_effect = Exception("429 Resource Exhausted: quota exceeded")

        with pytest.raises(QuotaExceededError, match="Free AI quota exceeded"):
            await chat(
                user_id="user-456",
                conversation_id=None,
                user_message="hi",
                profile={"preferred_ai_provider": "gemini"},
            )
        print("  [PASS] E2E: Gemini 429 → QuotaExceededError")
