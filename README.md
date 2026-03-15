# HabitFlow AI

**AI-powered micro-habit builder** — Build tiny habits that stick, powered by machine learning that learns *when* you're most likely to succeed.

```
Expo (React Native)  ·  FastAPI (Python)  ·  Supabase (PostgreSQL)  ·  Claude AI
```

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Mobile Setup](#mobile-setup)
- [Database Setup](#database-setup)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Deployment](#deployment)
  - [Backend Deployment](#backend-deployment)
  - [Mobile Build & Submit](#mobile-build--submit)
- [App Store Submission Guide](#app-store-submission-guide)
  - [Pre-requisites Checklist](#pre-requisites-checklist)
  - [Required Assets](#required-assets)
  - [Store Metadata](#store-metadata)
  - [iOS Submission (App Store)](#ios-submission-app-store)
  - [Android Submission (Play Store)](#android-submission-play-store)
  - [App Review Tips](#app-review-tips)
  - [Post-Launch OTA Updates](#post-launch-ota-updates)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Overview

HabitFlow AI isn't another reminder app. It uses:

- **ML-powered scheduling** — learns when you're most productive and schedules habits at your optimal time
- **Conversational AI Coach** — Claude-powered habit coaching with your actual data (streaks, rates, mood patterns)
- **Gamification engine** — streaks, XP, levels, 13 badges, and community challenges
- **Mood-habit correlation** — discovers which habits actually improve your wellbeing
- **Social accountability** — buddy system with nudges and shared challenges

## Features

| Feature | Description |
|---------|-------------|
| Smart Scheduling | AI analyzes behavior patterns to find optimal habit windows |
| AI Coach | Claude-powered conversational coaching with weekly reviews |
| Streak Engine | XP rewards, streak bonuses, 13 unlockable badges |
| Photo Check-ins | Vision AI verifies habit completion photos |
| Mood Tracking | Morning/afternoon/evening mood + energy logging |
| Buddy System | Accountability partners with nudge notifications |
| Challenges | Community habit challenges with leaderboards |
| Analytics | Completion trends, heatmaps, mood-habit correlations |
| Push Notifications | AI-timed reminders, streak protectors, weekly summaries |

## Architecture

```
┌──────────────────────────────────────────┐
│        Expo (React Native) Mobile App     │
│  Onboarding · Home · Coach · Analytics    │
│  Profile · Social · Notifications         │
└────────────────┬─────────────────────────┘
                 │ HTTPS / JWT
┌────────────────▼─────────────────────────┐
│         FastAPI Backend (Python)           │
│  Auth · Habits · Completions · Coach      │
│  Social · Analytics · Gamification        │
│  Notifications · Events · Scheduler       │
└───┬────────────┬──────────────┬──────────┘
    │            │              │
┌───▼───┐  ┌────▼────┐  ┌─────▼─────┐
│Supabase│  │ Claude  │  │ Firebase  │
│  (PG)  │  │  API    │  │   FCM     │
│+ Auth  │  │(AI Coach│  │  (Push)   │
│+ RLS   │  │ + ML)   │  │           │
└────────┘  └─────────┘  └───────────┘
```

## Project Structure

```
habitflow/
├── README.md                      ← You are here
├── LICENSE
├── .gitignore
│
├── backend/                       ← FastAPI Backend
│   ├── app/
│   │   ├── main.py               ← App entry, middleware, CORS
│   │   ├── config.py             ← Settings from env vars
│   │   ├── database.py           ← Supabase client
│   │   ├── dependencies.py       ← Auth, guards, rate limits
│   │   ├── models/
│   │   │   ├── user.py           ← Profile schemas
│   │   │   ├── habit.py          ← Habit schemas
│   │   │   └── schemas.py        ← All other schemas
│   │   ├── routers/
│   │   │   ├── auth.py           ← Signup, login, OAuth
│   │   │   ├── users.py          ← Profile, onboarding
│   │   │   ├── habits.py         ← CRUD, today, templates
│   │   │   ├── completions.py    ← Check-in (critical path)
│   │   │   ├── daily_logs.py     ← Mood, energy, journal
│   │   │   ├── coach.py          ← AI chat, weekly summary
│   │   │   ├── social.py         ← Buddies, nudges
│   │   │   ├── analytics.py      ← Stats, correlations
│   │   │   ├── gamification.py   ← Badges, leaderboard, XP
│   │   │   ├── events.py         ← Behavior tracking
│   │   │   └── notifications.py  ← Push tokens, prefs
│   │   ├── services/
│   │   │   ├── streak_engine.py  ← Streak calc + XP
│   │   │   ├── badge_engine.py   ← Achievement detection
│   │   │   ├── ai_coach.py      ← Claude API integration
│   │   │   ├── notification_service.py ← FCM delivery
│   │   │   └── scheduler.py     ← Background cron jobs
│   │   └── ml/                   ← ML models (future)
│   ├── migrations/
│   │   ├── 001_schema.sql        ← Core database schema
│   │   └── 002_notifications.sql ← Push notification tables
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── .github/workflows/
│       └── backend.yml           ← CI/CD pipeline
│
├── mobile/                        ← Expo React Native App
│   ├── App.js                    ← Root with auth + navigation
│   ├── app.json                  ← Expo config
│   ├── eas.json                  ← EAS Build profiles
│   ├── package.json
│   ├── src/
│   │   ├── constants/index.js    ← Colors, templates, config
│   │   ├── services/
│   │   │   ├── api.js            ← Supabase + REST client
│   │   │   └── notifications.js  ← Push registration + local
│   │   ├── hooks/
│   │   │   └── useOnboardingStore.js ← Zustand state
│   │   └── screens/
│   │       ├── onboarding/       ← 6-step onboarding flow
│   │       ├── home/             ← Daily habits + check-in
│   │       ├── coach/            ← AI chat + weekly review
│   │       ├── analytics/        ← Charts + breakdowns
│   │       ├── profile/          ← Badges, level, settings
│   │       └── settings/         ← Notification preferences
│   └── .github/workflows/
│       └── mobile.yml            ← EAS Build + Submit
│
└── docs/                          ← Documentation
    └── API.md                    ← API reference
```

## Getting Started

### Prerequisites

- **Node.js** 20+ and npm
- **Python** 3.11+
- **Expo CLI**: `npm install -g expo-cli`
- **EAS CLI**: `npm install -g eas-cli`
- **Supabase** account (free tier works)
- **Anthropic** API key (for AI Coach)
- **Firebase** project (for push notifications)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase, Anthropic, Firebase credentials

# Run database migrations (in Supabase SQL Editor)
# Execute migrations/001_schema.sql
# Execute migrations/002_notifications.sql

# Start the server
uvicorn app.main:app --reload --port 8000

# API docs available at http://localhost:8000/docs
```

### Mobile Setup

```bash
cd mobile

# Install dependencies
npm install

# Configure environment
# Edit app.json → set your Expo project ID
# Edit eas.json → set Apple/Google credentials
# Edit src/services/api.js → set SUPABASE_URL and SUPABASE_KEY

# Start Expo dev server
npx expo start

# Run on devices
npx expo start --ios      # iOS Simulator
npx expo start --android  # Android Emulator
```

## Database Setup

1. Create a new Supabase project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** in your Supabase dashboard
3. Run `backend/migrations/001_schema.sql` — creates all tables, indexes, RLS policies, triggers, and seed data
4. Run `backend/migrations/002_notifications.sql` — creates push token and notification preference tables
5. Copy your project URL and keys from **Settings → API**

The schema includes:
- 14 tables with full Row Level Security
- Auto-updating timestamps via triggers
- Streak recalculation function
- 13 pre-seeded achievement badges
- Proper foreign key cascading

## Environment Variables

Create `backend/.env` from the example:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
JWT_SECRET=your-jwt-secret

# AI
ANTHROPIC_API_KEY=sk-ant-...
AI_MODEL=claude-sonnet-4-20250514

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

For mobile, set environment variables in `eas.json` under each build profile, or use EAS Secrets:

```bash
eas secret:create --name EXPO_PUBLIC_SUPABASE_URL --value "https://..." --scope project
```

## Running Locally

**Start both backend and mobile simultaneously:**

```bash
# Terminal 1: Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Mobile
cd mobile
npx expo start
```

The mobile app connects to `http://localhost:8000/v1` by default in development.

## Testing

```bash
# Backend tests
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v

# Mobile linting
cd mobile
npx eslint src/ --ext .js,.jsx
```

## Deployment

### Backend Deployment

**Option A: Docker + Cloud Run (recommended)**

```bash
cd backend

# Build Docker image
docker build -t habitflow-api .

# Test locally
docker run -p 8000:8000 --env-file .env habitflow-api

# Push to registry
docker tag habitflow-api gcr.io/YOUR_PROJECT/habitflow-api
docker push gcr.io/YOUR_PROJECT/habitflow-api

# Deploy to Cloud Run
gcloud run deploy habitflow-api \
  --image gcr.io/YOUR_PROJECT/habitflow-api \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --memory 512Mi \
  --port 8000
```

**Option B: Railway / Render (simpler)**

1. Connect your GitHub repo
2. Set root directory to `backend/`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Mobile Build & Submit

```bash
cd mobile

# Login to Expo
eas login

# Configure builds (first time only)
eas build:configure

# Build for both platforms
eas build --platform all --profile production

# Submit to stores
eas submit --platform ios --profile production
eas submit --platform android --profile production
```

---

## App Store Submission Guide

### Pre-requisites Checklist

Before submitting, complete these steps:

- [ ] **Apple Developer Account** — $99/year at [developer.apple.com/programs](https://developer.apple.com/programs/)
- [ ] **Google Play Developer Account** — $25 one-time at [play.google.com/console](https://play.google.com/console/)
- [ ] **EAS CLI installed and authenticated** — `npm install -g eas-cli && eas login`
- [ ] **Production Supabase project** — separate from development
- [ ] **Production environment variables** — all keys in `eas.json` or EAS Secrets
- [ ] **Firebase project configured** — APNs key uploaded for iOS push
- [ ] **Google Sign-In enabled** — in Supabase Auth + Google Cloud Console
- [ ] **Apple Sign-In enabled** — in Supabase Auth + Apple Developer Portal
- [ ] **Backend deployed and accessible** — health check passing at `/health`
- [ ] **Database migrations run** — both SQL files executed on production Supabase
- [ ] **Privacy policy page live** — at your domain (e.g., `habitflow.ai/privacy`)
- [ ] **Support email configured** — (e.g., `support@habitflow.ai`)

### Required Assets

#### iOS (App Store Connect)

| Asset | Specification | Required |
|-------|--------------|----------|
| App Icon | 1024×1024 PNG, no alpha, no rounded corners | Yes |
| iPhone 6.7" Screenshots | 1290×2796 px, min 3, max 10 | Yes |
| iPhone 6.5" Screenshots | 1284×2778 px (or 1242×2688) | Yes |
| iPad 12.9" Screenshots | 2048×2732 px | If supporting iPad |
| App Preview Video | Up to 30s, H.264 MP4, 1290×2796 | No |

#### Android (Google Play Console)

| Asset | Specification | Required |
|-------|--------------|----------|
| App Icon | 512×512 PNG, 32-bit with alpha | Yes |
| Feature Graphic | 1024×500 PNG or JPEG | Yes |
| Phone Screenshots | Min 2, max 8, 16:9 or 9:16, min 320px | Yes |
| 7" Tablet Screenshots | Min 1 if targeting tablets | No |
| Promo Video | YouTube URL, 30s–2min recommended | No |

**Screenshot Recommendations:** Show these 5 screens with device frames and captions:
1. Onboarding — "AI learns your optimal habit times"
2. Home — Habit list with streaks and check-in buttons
3. AI Coach — Chat conversation with personalized advice
4. Analytics — Charts, heatmap, mood correlations
5. Check-in Celebration — XP earned, streak milestone

### Store Metadata

**App Name:** HabitFlow AI

**Subtitle (iOS):** Smart Habits, Real Results

**Short Description (80 chars):**
Build tiny habits that stick — powered by AI that learns when you're most likely to succeed.

**Category:** Health & Fitness

**Keywords (iOS, 100 chars):**
habits, habit tracker, micro habits, AI coach, streak, mindfulness, productivity, self improvement, wellness

**Full Description:** See `docs/store-description.txt` for the full, optimized description.

### iOS Submission (App Store)

**Step 1: Build**
```bash
cd mobile
eas build --platform ios --profile production
```
EAS handles code signing, provisioning profiles, and certificate management automatically.

**Step 2: Submit to App Store Connect**
```bash
eas submit --platform ios --profile production
```
This uploads the `.ipa` to App Store Connect via Transporter.

**Step 3: Complete App Store Connect Setup**

1. Log into [App Store Connect](https://appstoreconnect.apple.com)
2. Go to your app → **App Information**
   - Set content rating (ESRB: Everyone)
   - Set age rating (4+)
   - Mark **Uses AI/ML features** = Yes (required since 2024)
3. Go to **Pricing and Availability**
   - Set to Free (with in-app purchases if using Pro subscription)
4. Go to **App Privacy**
   - Complete the privacy nutrition labels:
     - Data collected: Name, Email, Health & Fitness (mood), Usage Data, Diagnostics
     - Data linked to user: Name, Email, Health & Fitness
     - Data used for tracking: None
5. Go to your version → **App Review Information**
   - **CRITICAL:** Provide demo credentials:
     ```
     Email: test@habitflow.ai
     Password: TestAccount123!
     Notes: This account has pre-populated habits and streak data for review.
     ```
6. Upload screenshots and fill all metadata
7. Click **Submit for Review**

**Expected review time:** 24–48 hours. First submissions may take up to 72 hours.

### Android Submission (Play Store)

**Step 1: Build**
```bash
cd mobile
eas build --platform android --profile production
```
Produces an `.aab` (Android App Bundle), required by Play Store.

**Step 2: Submit to Play Console**
```bash
eas submit --platform android --profile production
```

**Step 3: Complete Play Console Setup**

1. Log into [Google Play Console](https://play.google.com/console/)
2. **Store listing** — Fill name, descriptions, screenshots, feature graphic
3. **Content rating** — Complete the IARC questionnaire
   - Content type: Utility / Productivity
   - No violence, no sexual content
   - User-generated content: Yes (journal entries, chat)
4. **Data safety**
   - Data collected: Name, email, health info (mood), app activity
   - Data shared: None
   - Encryption in transit: Yes
   - Data deletion: Users can request via account deletion
5. **App content** — Set target audience (13+), ads declaration (no ads)
6. **Pricing** — Free
7. **Countries** — Select all countries for distribution
8. Release to **Internal testing** first → then **Production** after testing

**Expected review time:** 1–7 days for first submission. Updates are typically 1–3 days.

### App Review Tips

**Critical — will cause rejection if missed:**

1. **Test Account** — Always provide demo login credentials in review notes. Apple WILL reject without this. Create an account with pre-populated habits.
2. **Privacy Policy** — Must be a live, accessible URL. Cover data collection, storage, third-party services (Supabase, Anthropic, Firebase).
3. **AI Disclosure** — Apple requires marking your app as using AI/ML. Be transparent about Claude API usage.
4. **In-App Purchases** — If using RevenueCat/Stripe for Pro tier, configure products in BOTH App Store Connect AND Play Console before submission.
5. **Data Safety Forms** — Both stores require detailed data collection declarations. Be thorough and accurate.

**Best practices:**

6. **Push Permission** — Don't request immediately on launch. HabitFlow asks during onboarding Step 4 — this is the correct pattern.
7. **Camera Permission** — Photo check-in uses the camera. The `NSCameraUsageDescription` in `app.json` explains why.
8. **Minimum Functionality** — Free tier (3 habits) should feel complete, not crippled. Both stores reject apps that feel like demos.
9. **Accessibility** — Test with VoiceOver (iOS) and TalkBack (Android). Add accessibility labels to all interactive elements.
10. **Crash-Free Rate** — Target >99.5%. Run TestFlight/Internal Testing for 3–7 days before submitting.

**Common rejection reasons:**
- No test account provided
- Broken functionality (crashes, API errors)
- Misleading screenshots
- Incomplete privacy policy
- Undeclared data collection
- App crashes on launch

### Post-Launch OTA Updates

For JavaScript-only changes (no native module changes), you can ship updates instantly without App Store review:

```bash
cd mobile
eas update --branch production --message "Bug fixes and performance improvements"
```

This uses Expo's OTA (Over-The-Air) update system. Users get the update on next app launch.

**When you need a full rebuild (new store submission):**
- Adding new native modules (e.g., camera, biometrics)
- Updating Expo SDK version
- Changing app.json configuration
- Adding new permissions

---

## API Reference

The backend exposes 55+ endpoints across 11 route groups. Full documentation is available at `/docs` when running in debug mode.

| Route Group | Prefix | Endpoints | Description |
|-------------|--------|-----------|-------------|
| Auth | `/v1/auth` | 7 | Signup, login, OAuth, refresh, logout |
| Users | `/v1/users` | 5 | Profile, onboarding, search |
| Habits | `/v1/habits` | 10 | CRUD, today view, templates, calendar |
| Completions | `/v1/completions` | 4 | Check-in, undo, photo upload |
| Daily Logs | `/v1/daily-logs` | 4 | Mood, energy, journal |
| AI Coach | `/v1/coach` | 5 | Chat, conversations, weekly summary |
| Social | `/v1/social` | 8 | Buddies, nudges, challenges |
| Analytics | `/v1/analytics` | 5 | Overview, per-habit, correlations |
| Gamification | `/v1/gamification` | 3 | Badges, leaderboard, level |
| Events | `/v1/events` | 1 | Behavior tracking (ML training) |
| Notifications | `/v1/notifications` | 6 | Tokens, preferences, schedule |

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Mobile | Expo (React Native) | Cross-platform, OTA updates, managed workflow |
| Backend | FastAPI (Python) | Async, great for ML, auto-generated docs |
| Database | Supabase (PostgreSQL) | Auth, RLS, real-time, free tier |
| AI | Claude API (Anthropic) | Best-in-class coaching quality |
| Push | Firebase Cloud Messaging | Reliable cross-platform delivery |
| State | Zustand | Lightweight, hooks-based state management |
| Navigation | React Navigation 7 | Standard React Native navigation |
| CI/CD | GitHub Actions + EAS | Automated builds and store submissions |

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with dedication by **Subhrajit** — VP & Head of Engineering
