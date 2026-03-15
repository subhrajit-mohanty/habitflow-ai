# HabitFlow AI — API Reference

Base URL: `https://api.habitflow.ai/v1`
Auth: `Authorization: Bearer <supabase_jwt>`

## Auth (`/v1/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register with email/password |
| POST | `/auth/login` | Login with email/password |
| POST | `/auth/login/google` | Google OAuth |
| POST | `/auth/login/apple` | Apple Sign-In |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Invalidate session |
| DELETE | `/auth/account` | Delete account (GDPR) |

## Users (`/v1/users`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Get current profile |
| PATCH | `/users/me` | Update profile |
| POST | `/users/me/onboarding` | Complete onboarding |
| GET | `/users/search?q=` | Search users |
| GET | `/users/:username` | Get public profile |

## Habits (`/v1/habits`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/habits` | Create habit |
| GET | `/habits` | List habits |
| GET | `/habits/today` | Today's habits + status |
| GET | `/habits/templates` | Pre-built templates |
| GET | `/habits/:id` | Get habit detail |
| PATCH | `/habits/:id` | Update habit |
| DELETE | `/habits/:id` | Delete habit |
| POST | `/habits/:id/archive` | Archive habit |
| POST | `/habits/reorder` | Reorder habits |
| GET | `/habits/:id/calendar` | Monthly heatmap |

## Completions (`/v1/completions`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/completions` | Check-in (critical path) |
| DELETE | `/completions/:id` | Undo check-in |
| GET | `/completions` | List with filters |
| POST | `/completions/photo-upload` | Photo verification |

## Daily Logs (`/v1/daily-logs`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/daily-logs` | Create/update log |
| GET | `/daily-logs/today` | Today's log |
| GET | `/daily-logs` | List with date range |

## AI Coach (`/v1/coach`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/coach/chat` | Chat with AI coach |
| GET | `/coach/conversations` | List conversations |
| GET | `/coach/conversations/:id/messages` | Get messages |
| GET | `/coach/weekly-summary` | AI weekly review |
| POST | `/coach/habit-suggestions` | AI habit suggestions |

## Social (`/v1/social`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/social/buddies/invite` | Invite buddy |
| GET | `/social/buddies` | List buddies |
| POST | `/social/buddies/:id/accept` | Accept invite |
| POST | `/social/nudges` | Send nudge |
| GET | `/social/nudges` | List nudges |

## Analytics (`/v1/analytics`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/overview?period=30` | Overall stats |
| GET | `/analytics/habits/:id` | Per-habit analytics |
| GET | `/analytics/mood-correlations` | Mood correlations (Pro) |
| GET | `/analytics/best-times` | AI optimal times (Pro) |
| GET | `/analytics/trends` | Time-series data |

## Gamification (`/v1/gamification`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/gamification/badges` | All badges + status |
| GET | `/gamification/leaderboard` | XP leaderboard |
| GET | `/gamification/level-info` | Level + XP progress |

## Notifications (`/v1/notifications`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/notifications/register-token` | Register push token |
| GET | `/notifications/preferences` | Get preferences |
| PATCH | `/notifications/preferences` | Update preferences |
| GET | `/notifications/schedule` | Today's schedule |
| GET | `/notifications/history` | Notification log |

## Rate Limits
- Free: 60 req/min, 3 AI coach messages/week
- Pro: 120 req/min, unlimited AI coach
- AI endpoints: 10 req/min regardless of tier

## Error Format
```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "detail": {}
}
```
