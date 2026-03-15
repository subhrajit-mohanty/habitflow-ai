/**
 * HabitFlow AI — App Constants
 */

export const COLORS = {
  bg: "#08070D",
  card: "#111118",
  surface: "#1A1A24",
  accent: "#7C6BFF",
  mint: "#00D9A6",
  coral: "#FF6B8A",
  amber: "#FFBE5C",
  sky: "#5CB8FF",
  text: "#F0EEF6",
  sub: "#8E89A6",
  dim: "#504B66",
  border: "rgba(255,255,255,0.06)",
};

export const GOALS = [
  { id: "health", icon: "💪", label: "Get Healthier", color: "#4CAF50" },
  { id: "mindfulness", icon: "🧘", label: "Be More Mindful", color: "#9C6BFF" },
  { id: "productivity", icon: "⚡", label: "Boost Productivity", color: "#FF9800" },
  { id: "learning", icon: "📚", label: "Learn New Things", color: "#2196F3" },
  { id: "fitness", icon: "🏃", label: "Stay Fit", color: "#E91E63" },
  { id: "sleep", icon: "😴", label: "Sleep Better", color: "#5C6BC0" },
];

export const HABIT_TEMPLATES = [
  { id: "meditate", name: "Meditate 2 min", icon: "🧘", color: "#9C6BFF", category: "mindfulness", duration: 2, suggestedTime: "07:30", description: "Mindful breathing to start your day" },
  { id: "water", name: "Drink Water", icon: "💧", color: "#2196F3", category: "health", duration: 1, suggestedTime: "08:00", description: "A glass of water first thing" },
  { id: "read", name: "Read 5 Pages", icon: "📖", color: "#FF9800", category: "learning", duration: 10, suggestedTime: "21:00", description: "Wind down with a good book" },
  { id: "stretch", name: "Stretch", icon: "🤸", color: "#4CAF50", category: "fitness", duration: 2, suggestedTime: "07:00", description: "Quick morning stretch routine" },
  { id: "gratitude", name: "Gratitude Journal", icon: "🙏", color: "#E91E63", category: "mindfulness", duration: 3, suggestedTime: "22:00", description: "Write 3 things you're grateful for" },
  { id: "no_phone", name: "No Phone 1st Hour", icon: "📵", color: "#607D8B", category: "productivity", duration: 60, suggestedTime: "07:00", description: "Start your day device-free" },
  { id: "walk", name: "Walk 10 Min", icon: "🚶", color: "#8BC34A", category: "fitness", duration: 10, suggestedTime: "12:30", description: "A short walk outside" },
  { id: "breathe", name: "Deep Breathing", icon: "🌬️", color: "#00BCD4", category: "health", duration: 2, suggestedTime: "15:00", description: "4-7-8 breathing technique" },
  { id: "vocab", name: "Learn a New Word", icon: "🔤", color: "#3F51B5", category: "learning", duration: 2, suggestedTime: "09:00", description: "Expand your vocabulary daily" },
  { id: "tidy", name: "Tidy Up 5 Min", icon: "🧹", color: "#795548", category: "productivity", duration: 5, suggestedTime: "19:00", description: "Quick space declutter" },
];

export const WAKE_TIMES = [
  "5:00 AM", "5:30 AM", "6:00 AM", "6:30 AM", "7:00 AM",
  "7:30 AM", "8:00 AM", "8:30 AM", "9:00 AM", "9:30 AM", "10:00 AM",
];

export const SLEEP_TIMES = [
  "9:00 PM", "9:30 PM", "10:00 PM", "10:30 PM", "11:00 PM",
  "11:30 PM", "12:00 AM", "12:30 AM", "1:00 AM",
];
