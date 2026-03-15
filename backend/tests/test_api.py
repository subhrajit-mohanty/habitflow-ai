"""
HabitFlow AI — Backend Tests
Basic tests for health check, auth, and habit CRUD.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "HabitFlow AI"


@pytest.mark.asyncio
async def test_habit_templates(client):
    response = await client.get("/v1/habits/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 5
    assert all("name" in t for t in templates)
    assert all("icon" in t for t in templates)
    assert all("duration_minutes" in t for t in templates)


@pytest.mark.asyncio
async def test_unauthenticated_access(client):
    """Protected endpoints should return 401 without auth."""
    endpoints = [
        "/v1/users/me",
        "/v1/habits",
        "/v1/habits/today",
        "/v1/completions",
        "/v1/daily-logs/today",
        "/v1/coach/conversations",
        "/v1/social/buddies",
        "/v1/analytics/overview",
        "/v1/gamification/badges",
    ]
    for endpoint in endpoints:
        response = await client.get(endpoint)
        assert response.status_code in (401, 422), f"{endpoint} returned {response.status_code}"
