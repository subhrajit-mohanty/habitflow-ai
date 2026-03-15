# HabitFlow AI — FastAPI Backend Dockerfile
# Multi-stage build for minimal production image

# ──── Stage 1: Builder ────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ──── Stage 2: Production ────
FROM python:3.12-slim

LABEL maintainer="Subhrajit <subhrajit@habitflow.ai>"
LABEL description="HabitFlow AI Backend API"

# Security: non-root user
RUN groupadd -r habitflow && useradd -r -g habitflow -s /bin/false habitflow

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy app code
COPY app/ ./app/
COPY migrations/ ./migrations/

# Set ownership
RUN chown -R habitflow:habitflow /app

USER habitflow

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
