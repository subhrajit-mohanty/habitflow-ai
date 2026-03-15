# HabitFlow AI — Mobile App

Cross-platform mobile app built with Expo (React Native).

## Quick Start

```bash
npm install
npx expo start
```

## Build for Stores

```bash
# Preview (internal testing)
eas build --platform all --profile preview

# Production
eas build --platform all --profile production

# Submit to stores
eas submit --platform ios --profile production
eas submit --platform android --profile production
```

## OTA Updates (no store review)

```bash
eas update --branch production --message "Description of changes"
```

## Project Structure

```
src/
├── constants/     — Colors, templates, config
├── services/      — API client, notification service
├── hooks/         — Zustand stores
└── screens/
    ├── onboarding/ — 6-step onboarding flow
    ├── home/       — Daily habits + check-in
    ├── coach/      — AI chat + weekly review
    ├── analytics/  — Charts + habit breakdowns
    ├── profile/    — Badges, level, settings
    └── settings/   — Notification preferences
```
