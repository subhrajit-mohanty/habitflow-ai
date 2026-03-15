/**
 * HabitFlow AI — Onboarding Steps 1-5
 * GoalsScreen, HabitPickerScreen, ScheduleScreen,
 * NotificationsScreen, ReadyScreen
 */

import React, { useEffect, useRef } from "react";
import {
  View, Text, TouchableOpacity, ScrollView,
  StyleSheet, Animated,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { COLORS, GOALS, HABIT_TEMPLATES, WAKE_TIMES, SLEEP_TIMES } from "../../constants";
import { useOnboardingStore } from "../../hooks/useOnboardingStore";

// ═══════════════════════════════════
// STEP 1: Goals Selection
// ═══════════════════════════════════

export function GoalsScreen() {
  const { selectedGoals, toggleGoal } = useOnboardingStore();

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.emoji}>🎯</Text>
      <Text style={styles.heading}>What matters to you?</Text>
      <Text style={styles.subheading}>
        Pick up to <Text style={styles.bold}>3 goals</Text> — we'll suggest habits that match.
      </Text>

      {GOALS.map((goal, i) => {
        const selected = selectedGoals.includes(goal.id);
        return (
          <TouchableOpacity
            key={goal.id}
            onPress={() => toggleGoal(goal.id)}
            activeOpacity={0.7}
            style={[
              styles.optionRow,
              selected && { backgroundColor: goal.color + "12", borderColor: goal.color + "55" },
            ]}
          >
            <View style={[
              styles.optionIcon,
              { backgroundColor: selected ? goal.color + "25" : COLORS.surface },
            ]}>
              <Text style={{ fontSize: 24 }}>{goal.icon}</Text>
            </View>
            <Text style={[
              styles.optionLabel,
              selected && { color: COLORS.text },
            ]}>{goal.label}</Text>
            <View style={[
              styles.checkbox,
              selected && styles.checkboxActive,
            ]}>
              {selected && <Text style={styles.checkmark}>✓</Text>}
            </View>
          </TouchableOpacity>
        );
      })}

      <Text style={styles.counter}>{selectedGoals.length}/3 selected</Text>
    </ScrollView>
  );
}

// ═══════════════════════════════════
// STEP 2: Habit Picker
// ═══════════════════════════════════

export function HabitPickerScreen() {
  const { selectedGoals, selectedHabits, toggleHabit } = useOnboardingStore();

  // Prioritize habits matching selected goals
  const sorted = [...HABIT_TEMPLATES].sort((a, b) => {
    const aMatch = selectedGoals.includes(a.category) ? 0 : 1;
    const bMatch = selectedGoals.includes(b.category) ? 0 : 1;
    return aMatch - bMatch;
  });

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.emoji}>✨</Text>
      <Text style={styles.heading}>Pick your first habits</Text>
      <Text style={styles.subheading}>
        Choose up to <Text style={styles.bold}>5 micro-habits</Text> to start with.
      </Text>

      {sorted.map((habit) => {
        const selected = selectedHabits.includes(habit.id);
        return (
          <TouchableOpacity
            key={habit.id}
            onPress={() => toggleHabit(habit.id)}
            activeOpacity={0.7}
            style={[
              styles.habitRow,
              selected && { backgroundColor: habit.color + "10", borderColor: habit.color + "44" },
            ]}
          >
            <View style={[styles.habitIcon, { backgroundColor: habit.color + (selected ? "30" : "15") }]}>
              <Text style={{ fontSize: 20 }}>{habit.icon}</Text>
            </View>
            <View style={styles.habitInfo}>
              <Text style={[styles.habitName, selected && { color: COLORS.text }]}>{habit.name}</Text>
              <Text style={styles.habitDesc}>{habit.description}</Text>
            </View>
            <View style={styles.habitRight}>
              <Text style={styles.habitDuration}>{habit.duration} min</Text>
              {selected && (
                <LinearGradient
                  colors={["#7C6BFF", "#00D9A6"]}
                  style={styles.habitCheck}
                >
                  <Text style={styles.checkmark}>✓</Text>
                </LinearGradient>
              )}
            </View>
          </TouchableOpacity>
        );
      })}

      <Text style={styles.counter}>
        {selectedHabits.length}/5 selected
        {selectedHabits.length === 0 && " · pick at least 1"}
      </Text>
      <Text style={styles.tierNote}>Free plan: 3 habits · Pro: unlimited</Text>
    </ScrollView>
  );
}

// ═══════════════════════════════════
// STEP 3: Schedule
// ═══════════════════════════════════

export function ScheduleScreen() {
  const { wakeTime, sleepTime, setWakeTime, setSleepTime } = useOnboardingStore();

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      <Text style={styles.emoji}>⏰</Text>
      <Text style={styles.heading}>Your daily rhythm</Text>
      <Text style={styles.subheading}>
        This helps our AI schedule habits at{" "}
        <Text style={styles.bold}>the perfect moments</Text> in your day.
      </Text>

      {/* Wake Time */}
      <View style={styles.scheduleSection}>
        <View style={styles.scheduleHeader}>
          <View style={[styles.scheduleIcon, { backgroundColor: "rgba(255,190,92,0.12)" }]}>
            <Text style={{ fontSize: 22 }}>🌅</Text>
          </View>
          <View>
            <Text style={styles.scheduleTitle}>I usually wake up at</Text>
            <Text style={styles.scheduleValue}>{wakeTime}</Text>
          </View>
        </View>
        <View style={styles.timeChips}>
          {WAKE_TIMES.map((t) => (
            <TouchableOpacity
              key={t}
              onPress={() => setWakeTime(t)}
              style={[styles.timeChip, wakeTime === t && styles.timeChipActive]}
            >
              <Text style={[styles.timeChipText, wakeTime === t && { color: "#fff" }]}>{t}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Sleep Time */}
      <View style={styles.scheduleSection}>
        <View style={styles.scheduleHeader}>
          <View style={[styles.scheduleIcon, { backgroundColor: "rgba(92,107,192,0.12)" }]}>
            <Text style={{ fontSize: 22 }}>🌙</Text>
          </View>
          <View>
            <Text style={styles.scheduleTitle}>I usually go to bed at</Text>
            <Text style={styles.scheduleValue}>{sleepTime}</Text>
          </View>
        </View>
        <View style={styles.timeChips}>
          {SLEEP_TIMES.map((t) => (
            <TouchableOpacity
              key={t}
              onPress={() => setSleepTime(t)}
              style={[
                styles.timeChip,
                sleepTime === t && { backgroundColor: "#5C6BC0", borderColor: "transparent" },
              ]}
            >
              <Text style={[styles.timeChipText, sleepTime === t && { color: "#fff" }]}>{t}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* AI Note */}
      <View style={styles.aiNote}>
        <View style={styles.aiNoteHeader}>
          <Text style={{ fontSize: 12 }}>🧠</Text>
          <Text style={styles.aiNoteLabel}>AI NOTE</Text>
        </View>
        <Text style={styles.aiNoteText}>
          Our AI will analyze your behavior patterns over the first week and automatically
          optimize when each habit is scheduled. The more you use HabitFlow, the smarter it gets.
        </Text>
      </View>
    </ScrollView>
  );
}

// ═══════════════════════════════════
// STEP 4: Notifications
// ═══════════════════════════════════

export function NotificationsScreen({ onNext }) {
  const { setNotificationsEnabled } = useOnboardingStore();

  const handleEnable = () => {
    setNotificationsEnabled(true);
    onNext?.();
  };
  const handleSkip = () => {
    setNotificationsEnabled(false);
    onNext?.();
  };

  return (
    <ScrollView contentContainerStyle={[styles.scrollContent, { paddingTop: 50, alignItems: "center" }]}>
      <View style={styles.notifIconContainer}>
        <Text style={{ fontSize: 48 }}>🔔</Text>
      </View>

      <Text style={[styles.heading, { textAlign: "center" }]}>Stay on track</Text>
      <Text style={[styles.subheading, { textAlign: "center", maxWidth: 300 }]}>
        Gentle nudges at the <Text style={styles.bold}>perfect moment</Text> — our AI learns
        when you're most likely to complete each habit.
      </Text>

      <View style={styles.notifButtons}>
        <TouchableOpacity onPress={handleEnable} activeOpacity={0.8}>
          <LinearGradient
            colors={["#7C6BFF", "#00D9A6"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.notifPrimaryBtn}
          >
            <Text style={styles.notifPrimaryText}>Enable Smart Notifications</Text>
          </LinearGradient>
        </TouchableOpacity>
        <TouchableOpacity onPress={handleSkip} style={styles.notifSkipBtn}>
          <Text style={styles.notifSkipText}>Maybe later</Text>
        </TouchableOpacity>
      </View>

      {/* Features */}
      <View style={styles.notifFeatures}>
        {[
          { icon: "⏰", title: "AI-timed reminders", desc: "Sent when you're most likely to act" },
          { icon: "🔥", title: "Streak protectors", desc: "Nudge before your streak breaks" },
          { icon: "📊", title: "Weekly reviews", desc: "AI-powered insight summaries" },
        ].map((f, i) => (
          <View key={i} style={styles.notifFeatureRow}>
            <View style={styles.notifFeatureIcon}>
              <Text style={{ fontSize: 18 }}>{f.icon}</Text>
            </View>
            <View>
              <Text style={styles.notifFeatureTitle}>{f.title}</Text>
              <Text style={styles.notifFeatureDesc}>{f.desc}</Text>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

// ═══════════════════════════════════
// STEP 5: Ready / Summary
// ═══════════════════════════════════

export function ReadyScreen() {
  const store = useOnboardingStore();
  const scaleAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      friction: 4,
      tension: 60,
      useNativeDriver: true,
    }).start();
  }, []);

  const selectedGoalObjects = GOALS.filter((g) => store.selectedGoals.includes(g.id));
  const selectedHabitObjects = HABIT_TEMPLATES.filter((h) => store.selectedHabits.includes(h.id));

  return (
    <ScrollView contentContainerStyle={[styles.scrollContent, { paddingTop: 40, alignItems: "center" }]}>
      {/* Celebration */}
      <Animated.View style={{ transform: [{ scale: scaleAnim }], marginBottom: 20 }}>
        <LinearGradient
          colors={["#7C6BFF", "#00D9A6"]}
          style={styles.readyLogo}
        >
          <Text style={{ fontSize: 36 }}>🚀</Text>
        </LinearGradient>
      </Animated.View>

      <Text style={[styles.heading, { textAlign: "center" }]}>
        You're all set, <Text style={{ color: COLORS.accent }}>{store.displayName || "friend"}</Text>!
      </Text>
      <Text style={[styles.subheading, { textAlign: "center", maxWidth: 300, marginBottom: 28 }]}>
        Your {store.selectedHabits.length} habits are ready. Start small, stay consistent — your AI coach has your back.
      </Text>

      {/* Summary: Goals */}
      <View style={styles.summaryCard}>
        <Text style={styles.summaryLabel}>YOUR GOALS</Text>
        <View style={styles.summaryChips}>
          {selectedGoalObjects.map((g) => (
            <View key={g.id} style={[styles.summaryChip, { backgroundColor: g.color + "18" }]}>
              <Text style={[styles.summaryChipText, { color: g.color }]}>{g.icon} {g.label}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Summary: Habits */}
      <View style={styles.summaryCard}>
        <Text style={styles.summaryLabel}>YOUR HABITS</Text>
        <View style={styles.summaryChips}>
          {selectedHabitObjects.map((h) => (
            <View key={h.id} style={[styles.summaryHabitChip, { borderColor: h.color + "22", backgroundColor: h.color + "12" }]}>
              <Text style={{ fontSize: 16 }}>{h.icon}</Text>
              <Text style={styles.summaryHabitName}>{h.name}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Summary: Schedule */}
      <View style={[styles.summaryCard, { flexDirection: "row", justifyContent: "space-between" }]}>
        <View>
          <Text style={styles.summaryLabel}>WAKE</Text>
          <Text style={styles.summaryTimeValue}>🌅 {store.wakeTime}</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={{ alignItems: "flex-end" }}>
          <Text style={styles.summaryLabel}>SLEEP</Text>
          <Text style={styles.summaryTimeValue}>🌙 {store.sleepTime}</Text>
        </View>
      </View>

      {/* Start Button */}
      <TouchableOpacity
        onPress={store.submitOnboarding}
        disabled={store.isSubmitting}
        activeOpacity={0.8}
        style={{ width: "100%", maxWidth: 340, marginTop: 24 }}
      >
        <LinearGradient
          colors={["#7C6BFF", "#00D9A6"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.startButton}
        >
          <Text style={styles.startButtonText}>
            {store.isSubmitting ? "Setting up..." : "Start My Journey →"}
          </Text>
        </LinearGradient>
      </TouchableOpacity>

      <Text style={styles.startSubtext}>Your AI coach is already learning about you</Text>

      {store.error && (
        <Text style={styles.errorText}>{store.error}</Text>
      )}
    </ScrollView>
  );
}

// ═══════════════════════════════════
// SHARED STYLES
// ═══════════════════════════════════

const styles = StyleSheet.create({
  scrollContent: {
    paddingHorizontal: 22,
    paddingTop: 24,
    paddingBottom: 140,
  },
  emoji: { fontSize: 32, marginBottom: 6 },
  heading: { fontSize: 26, fontWeight: "800", color: COLORS.text, letterSpacing: -0.3, marginBottom: 6 },
  subheading: { fontSize: 14, color: COLORS.sub, lineHeight: 21, marginBottom: 22 },
  bold: { color: COLORS.text, fontWeight: "700" },
  counter: { fontSize: 12, color: COLORS.dim, textAlign: "center", marginTop: 14 },
  tierNote: { fontSize: 11, color: COLORS.dim, textAlign: "center", marginTop: 4 },

  // Goal option rows
  optionRow: {
    flexDirection: "row", alignItems: "center", gap: 14,
    padding: 16, borderRadius: 16,
    backgroundColor: COLORS.card, borderWidth: 1, borderColor: COLORS.border,
    marginBottom: 10,
  },
  optionIcon: {
    width: 48, height: 48, borderRadius: 14,
    alignItems: "center", justifyContent: "center",
  },
  optionLabel: { flex: 1, fontSize: 15, fontWeight: "700", color: COLORS.sub },
  checkbox: {
    width: 24, height: 24, borderRadius: 8,
    backgroundColor: COLORS.surface, borderWidth: 1.5, borderColor: COLORS.dim,
    alignItems: "center", justifyContent: "center",
  },
  checkboxActive: {
    backgroundColor: COLORS.accent, borderColor: "transparent",
  },
  checkmark: { fontSize: 14, color: "#fff", fontWeight: "700" },

  // Habit rows
  habitRow: {
    flexDirection: "row", alignItems: "center", gap: 12,
    padding: 14, borderRadius: 16,
    backgroundColor: COLORS.card, borderWidth: 1, borderColor: COLORS.border,
    marginBottom: 8,
  },
  habitIcon: { width: 42, height: 42, borderRadius: 12, alignItems: "center", justifyContent: "center" },
  habitInfo: { flex: 1 },
  habitName: { fontSize: 14, fontWeight: "700", color: COLORS.sub },
  habitDesc: { fontSize: 11, color: COLORS.dim, marginTop: 2 },
  habitRight: { alignItems: "flex-end" },
  habitDuration: { fontSize: 10, color: COLORS.dim },
  habitCheck: { width: 20, height: 20, borderRadius: 6, alignItems: "center", justifyContent: "center", marginTop: 4 },

  // Schedule
  scheduleSection: { marginBottom: 28 },
  scheduleHeader: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 14 },
  scheduleIcon: { width: 44, height: 44, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  scheduleTitle: { fontSize: 15, fontWeight: "700", color: COLORS.text },
  scheduleValue: { fontSize: 12, color: COLORS.sub },
  timeChips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  timeChip: {
    paddingVertical: 8, paddingHorizontal: 14, borderRadius: 12,
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
  },
  timeChipActive: { backgroundColor: COLORS.accent, borderColor: "transparent" },
  timeChipText: { fontSize: 12, fontWeight: "600", color: COLORS.sub },

  // AI Note
  aiNote: {
    padding: 14, borderRadius: 14,
    backgroundColor: "rgba(124,107,255,0.06)",
    borderWidth: 1, borderColor: "rgba(124,107,255,0.15)",
    marginTop: 8,
  },
  aiNoteHeader: { flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 6 },
  aiNoteLabel: { fontSize: 11, fontWeight: "700", color: COLORS.accent },
  aiNoteText: { fontSize: 12, color: COLORS.sub, lineHeight: 18 },

  // Notifications
  notifIconContainer: {
    width: 100, height: 100, borderRadius: 30,
    backgroundColor: "rgba(124,107,255,0.08)",
    borderWidth: 1, borderColor: "rgba(124,107,255,0.15)",
    alignItems: "center", justifyContent: "center",
    marginBottom: 28,
  },
  notifButtons: { width: "100%", maxWidth: 320, gap: 10, marginTop: 32 },
  notifPrimaryBtn: { padding: 16, borderRadius: 16, alignItems: "center" },
  notifPrimaryText: { fontSize: 16, fontWeight: "700", color: "#fff" },
  notifSkipBtn: { padding: 14, borderRadius: 16, backgroundColor: COLORS.surface, alignItems: "center" },
  notifSkipText: { fontSize: 14, fontWeight: "600", color: COLORS.sub },
  notifFeatures: { marginTop: 36, gap: 12, width: "100%", maxWidth: 320 },
  notifFeatureRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  notifFeatureIcon: {
    width: 40, height: 40, borderRadius: 12,
    backgroundColor: COLORS.surface, alignItems: "center", justifyContent: "center",
  },
  notifFeatureTitle: { fontSize: 13, fontWeight: "700", color: COLORS.text },
  notifFeatureDesc: { fontSize: 11, color: COLORS.dim, marginTop: 1 },

  // Ready screen
  readyLogo: {
    width: 80, height: 80, borderRadius: 24,
    alignItems: "center", justifyContent: "center",
  },
  summaryCard: {
    width: "100%", maxWidth: 340, padding: 14,
    borderRadius: 16, backgroundColor: COLORS.card,
    borderWidth: 1, borderColor: COLORS.border, marginBottom: 10,
  },
  summaryLabel: { fontSize: 10, color: COLORS.dim, letterSpacing: 1, marginBottom: 8, fontWeight: "600" },
  summaryChips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  summaryChip: { paddingVertical: 4, paddingHorizontal: 10, borderRadius: 8 },
  summaryChipText: { fontSize: 11, fontWeight: "600" },
  summaryHabitChip: {
    flexDirection: "row", alignItems: "center", gap: 6,
    paddingVertical: 5, paddingHorizontal: 10, borderRadius: 10,
    borderWidth: 1,
  },
  summaryHabitName: { fontSize: 11, fontWeight: "600", color: COLORS.text },
  summaryTimeValue: { fontSize: 16, fontWeight: "700", color: COLORS.text, marginTop: 4 },
  summaryDivider: { width: 1, backgroundColor: COLORS.border },
  startButton: {
    padding: 18, borderRadius: 18, alignItems: "center",
    shadowColor: "#7C6BFF", shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35, shadowRadius: 16, elevation: 8,
  },
  startButtonText: { fontSize: 17, fontWeight: "800", color: "#fff", letterSpacing: 0.3 },
  startSubtext: { fontSize: 11, color: COLORS.dim, marginTop: 12 },
  errorText: { fontSize: 12, color: COLORS.coral, marginTop: 10 },
});
