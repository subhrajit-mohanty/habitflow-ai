"""
HabitFlow AI — Main Application
FastAPI entry point with all routers, middleware, and CORS.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.config import get_settings
from app.routers import auth, users, habits, completions, daily_logs, coach, social, analytics, gamification, events, notifications


# ============================================================
# Lifespan (startup / shutdown)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    print(f"🚀 {settings.app_name} v{settings.app_version} starting...")
    print(f"   Debug: {settings.debug}")
    print(f"   Supabase: {settings.supabase_url[:30]}...")
    yield
    print("👋 Shutting down...")


# ============================================================
# App Instance
# ============================================================

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered micro-habit builder — backend API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# ============================================================
# Middleware
# ============================================================

# CORS — allow Expo dev client and production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",        # Expo dev
        "http://localhost:19006",       # Expo web
        "exp://localhost:8081",         # Expo Go
        "https://habitflow.ai",        # Production
        "https://api.habitflow.ai",    # API
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Response-Time"] = f"{elapsed:.4f}s"
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# ============================================================
# Register Routers
# ============================================================

PREFIX = settings.api_prefix  # /v1

app.include_router(auth.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(habits.router, prefix=PREFIX)
app.include_router(completions.router, prefix=PREFIX)
app.include_router(daily_logs.router, prefix=PREFIX)
app.include_router(coach.router, prefix=PREFIX)
app.include_router(social.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(gamification.router, prefix=PREFIX)
app.include_router(events.router, prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
async def health_check():
    from app.database import get_supabase_admin
    db_ok = True
    try:
        admin = get_supabase_admin()
        admin.table("profiles").select("id", count="exact").limit(0).execute()
    except Exception:
        db_ok = False

    health_status = "healthy" if db_ok else "degraded"
    return {
        "status": health_status,
        "app": settings.app_name,
        "version": settings.app_version,
        "checks": {"database": "ok" if db_ok else "unreachable"},
    }


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Docs disabled in production",
    }
