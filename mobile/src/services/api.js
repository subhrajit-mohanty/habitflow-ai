/**
 * HabitFlow AI — API Service
 * Communicates with FastAPI backend via Supabase + REST.
 */

import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL || "https://your-project.supabase.co";
const SUPABASE_KEY = process.env.EXPO_PUBLIC_SUPABASE_KEY || "your-anon-key";
const API_BASE = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/v1";

// ─── Supabase Client ───
export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// ─── Auth Helpers ───
export const auth = {
  signUp: async (email, password) => {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    return data;
  },

  signIn: async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  },

  signInWithGoogle: async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({ provider: "google" });
    if (error) throw error;
    return data;
  },

  signInWithApple: async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({ provider: "apple" });
    if (error) throw error;
    return data;
  },

  signOut: async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  },

  getSession: async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session;
  },
};

// ─── API Fetch Helper ───
async function apiFetch(endpoint, options = {}) {
  const session = await auth.getSession();
  const token = session?.access_token;

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
      ...options.headers,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: "Request failed" }));
    throw new Error(err.detail || err.message || `HTTP ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ─── User API ───
export const userApi = {
  getProfile: () => apiFetch("/users/me"),
  updateProfile: (data) => apiFetch("/users/me", { method: "PATCH", body: data }),
  completeOnboarding: (data) => apiFetch("/users/me/onboarding", { method: "POST", body: data }),
};

// ─── Habits API ───
export const habitsApi = {
  create: (data) => apiFetch("/habits", { method: "POST", body: data }),
  list: (params = "") => apiFetch(`/habits?${params}`),
  getToday: () => apiFetch("/habits/today"),
  get: (id) => apiFetch(`/habits/${id}`),
  update: (id, data) => apiFetch(`/habits/${id}`, { method: "PATCH", body: data }),
  delete: (id) => apiFetch(`/habits/${id}`, { method: "DELETE" }),
  archive: (id) => apiFetch(`/habits/${id}/archive`, { method: "POST" }),
  getTemplates: () => apiFetch("/habits/templates"),
  getCalendar: (id, month) => apiFetch(`/habits/${id}/calendar?month=${month}`),
  reorder: (habitIds) => apiFetch("/habits/reorder", { method: "POST", body: { habit_ids: habitIds } }),
};

// ─── Completions API ───
export const completionsApi = {
  checkIn: (data) => apiFetch("/completions", { method: "POST", body: data }),
  undo: (id) => apiFetch(`/completions/${id}`, { method: "DELETE" }),
  list: (params = "") => apiFetch(`/completions?${params}`),
};

// ─── Daily Logs API ───
export const dailyLogsApi = {
  create: (data) => apiFetch("/daily-logs", { method: "POST", body: data }),
  getToday: () => apiFetch("/daily-logs/today"),
  list: (params = "") => apiFetch(`/daily-logs?${params}`),
};

// ─── Coach API ───
export const coachApi = {
  chat: (data) => apiFetch("/coach/chat", { method: "POST", body: data }),
  getConversations: () => apiFetch("/coach/conversations"),
  getMessages: (convId) => apiFetch(`/coach/conversations/${convId}/messages`),
  getWeeklySummary: () => apiFetch("/coach/weekly-summary"),
  getHabitSuggestions: (goals) => apiFetch("/coach/habit-suggestions", { method: "POST", body: { goals } }),
};

// ─── Analytics API ───
export const analyticsApi = {
  getOverview: (period = 30) => apiFetch(`/analytics/overview?period=${period}`),
  getHabitAnalytics: (id, period = 30) => apiFetch(`/analytics/habits/${id}?period=${period}`),
  getMoodCorrelations: (period = 30) => apiFetch(`/analytics/mood-correlations?period=${period}`),
  getBestTimes: () => apiFetch("/analytics/best-times"),
  getTrends: (metric, period = 30) => apiFetch(`/analytics/trends?metric=${metric}&period=${period}`),
};

// ─── Social API ───
export const socialApi = {
  inviteBuddy: (username) => apiFetch("/social/buddies/invite", { method: "POST", body: { username } }),
  listBuddies: () => apiFetch("/social/buddies"),
  acceptBuddy: (pairId) => apiFetch(`/social/buddies/${pairId}/accept`, { method: "POST" }),
  sendNudge: (data) => apiFetch("/social/nudges", { method: "POST", body: data }),
  listNudges: (unread = false) => apiFetch(`/social/nudges?unread=${unread}`),
};

// ─── Gamification API ───
export const gamificationApi = {
  getBadges: () => apiFetch("/gamification/badges"),
  getLeaderboard: (period = "weekly") => apiFetch(`/gamification/leaderboard?period=${period}`),
  getLevelInfo: () => apiFetch("/gamification/level-info"),
};

// ─── Events API ───
export const eventsApi = {
  track: (eventType, eventData = {}) => {
    const now = new Date();
    apiFetch("/events", {
      method: "POST",
      body: {
        event_type: eventType,
        event_data: eventData,
        local_time: now.toTimeString().slice(0, 8),
        day_of_week: now.getDay() === 0 ? 7 : now.getDay(),
      },
    }).catch(() => {}); // fire-and-forget
  },
};
