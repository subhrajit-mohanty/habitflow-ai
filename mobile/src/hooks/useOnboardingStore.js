/**
 * HabitFlow AI — Onboarding Store (Zustand)
 * Manages onboarding state across all steps.
 */

import { create } from "zustand";

export const useOnboardingStore = create((set, get) => ({
  // Step tracking
  currentStep: 0,
  totalSteps: 6,

  // Step 0: Welcome
  displayName: "",

  // Step 1: Goals
  selectedGoals: [],

  // Step 2: Habits
  selectedHabits: [],

  // Step 3: Schedule
  wakeTime: "7:00 AM",
  sleepTime: "11:00 PM",

  // Step 4: Notifications
  notificationsEnabled: null,

  // Completion
  isComplete: false,
  isSubmitting: false,
  error: null,

  // Actions
  setDisplayName: (name) => set({ displayName: name }),

  toggleGoal: (goalId) => set((state) => {
    const goals = state.selectedGoals;
    if (goals.includes(goalId)) {
      return { selectedGoals: goals.filter((id) => id !== goalId) };
    }
    if (goals.length >= 3) return state;
    return { selectedGoals: [...goals, goalId] };
  }),

  toggleHabit: (habitId) => set((state) => {
    const habits = state.selectedHabits;
    if (habits.includes(habitId)) {
      return { selectedHabits: habits.filter((id) => id !== habitId) };
    }
    if (habits.length >= 5) return state;
    return { selectedHabits: [...habits, habitId] };
  }),

  setWakeTime: (time) => set({ wakeTime: time }),
  setSleepTime: (time) => set({ sleepTime: time }),
  setNotificationsEnabled: (enabled) => set({ notificationsEnabled: enabled }),

  nextStep: () => set((state) => ({
    currentStep: Math.min(state.currentStep + 1, state.totalSteps - 1),
  })),

  prevStep: () => set((state) => ({
    currentStep: Math.max(state.currentStep - 1, 0),
  })),

  goToStep: (step) => set({ currentStep: step }),

  canProceed: () => {
    const state = get();
    switch (state.currentStep) {
      case 0: return state.displayName.trim().length >= 2;
      case 1: return state.selectedGoals.length >= 1;
      case 2: return state.selectedHabits.length >= 1;
      default: return true;
    }
  },

  // Submit onboarding to API
  submitOnboarding: async () => {
    const state = get();
    set({ isSubmitting: true, error: null });

    try {
      const { userApi } = await import("../services/api");
      
      // Convert times to 24h format for API
      const to24h = (timeStr) => {
        const [time, period] = timeStr.split(" ");
        let [hours, minutes] = time.split(":");
        hours = parseInt(hours);
        if (period === "PM" && hours !== 12) hours += 12;
        if (period === "AM" && hours === 12) hours = 0;
        return `${hours.toString().padStart(2, "0")}:${minutes}`;
      };

      await userApi.completeOnboarding({
        display_name: state.displayName,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        goals: state.selectedGoals,
        wake_time: to24h(state.wakeTime),
        sleep_time: to24h(state.sleepTime),
        initial_habits: state.selectedHabits,
      });

      // Request notification permissions if enabled
      if (state.notificationsEnabled) {
        try {
          const Notifications = await import("expo-notifications");
          await Notifications.requestPermissionsAsync();
        } catch (e) {
          console.warn("Notification permission error:", e);
        }
      }

      set({ isComplete: true, isSubmitting: false });
    } catch (err) {
      set({ error: err.message, isSubmitting: false });
    }
  },

  // Reset
  reset: () => set({
    currentStep: 0,
    displayName: "",
    selectedGoals: [],
    selectedHabits: [],
    wakeTime: "7:00 AM",
    sleepTime: "11:00 PM",
    notificationsEnabled: null,
    isComplete: false,
    isSubmitting: false,
    error: null,
  }),
}));
