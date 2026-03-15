/**
 * HabitFlow AI — Notification Preferences Screen
 * Toggle preferences per notification type, preview schedule, test triggers.
 */

import React, { useState, useEffect } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, StyleSheet,
  Switch, ActivityIndicator, Alert,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { COLORS } from "../../constants";

// API imports
const API_BASE = "http://localhost:8000/v1";

const PREF_ITEMS = [
  {
    key: "habit_reminders",
    icon: "⏰",
    title: "Habit Reminders",
    desc: "AI-timed nudges when it's the perfect moment for each habit",
    color: COLORS.accent,
  },
  {
    key: "streak_alerts",
    icon: "🔥",
    title: "Streak Protectors",
    desc: "Evening alert when your streaks are at risk of breaking",
    color: "#FF6B8A",
  },
  {
    key: "nudges",
    icon: "💪",
    title: "Buddy Nudges",
    desc: "Get notified when a friend sends you a motivation nudge",
    color: "#00D9A6",
  },
  {
    key: "weekly_summary",
    icon: "📊",
    title: "Weekly Summary",
    desc: "Sunday evening AI review of your progress and insights",
    color: "#5CB8FF",
  },
  {
    key: "badge_earned",
    icon: "🏅",
    title: "Badge Earned",
    desc: "Celebrate when you unlock a new achievement",
    color: "#FFBE5C",
  },
  {
    key: "challenge_updates",
    icon: "🏆",
    title: "Challenge Updates",
    desc: "Leaderboard changes and challenge milestones",
    color: "#E91E63",
  },
];

export default function NotificationPrefsScreen() {
  const [prefs, setPrefs] = useState({
    habit_reminders: true,
    streak_alerts: true,
    nudges: true,
    weekly_summary: true,
    badge_earned: true,
    challenge_updates: true,
  });
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadPrefs();
    loadSchedule();
  }, []);

  const loadPrefs = async () => {
    try {
      // In production: const data = await notificationsApi.getPreferences();
      // Mock for now
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  const loadSchedule = async () => {
    try {
      // In production: const data = await notificationsApi.getSchedule();
      setSchedule({
        notifications: [
          { habit_icon: "🤸", habit_name: "Stretch", scheduled_time: "07:00", type: "habit_reminder" },
          { habit_icon: "🧘", habit_name: "Meditate", scheduled_time: "07:30", type: "habit_reminder" },
          { habit_icon: "💧", habit_name: "Drink Water", scheduled_time: "08:00", type: "habit_reminder" },
          { habit_icon: "📖", habit_name: "Read 5 Pages", scheduled_time: "21:00", type: "habit_reminder" },
          { habit_icon: "🙏", habit_name: "Gratitude Journal", scheduled_time: "22:00", type: "habit_reminder" },
          { scheduled_time: "20:00", type: "streak_protector" },
        ],
      });
    } catch (err) {
      console.warn("Schedule load error:", err);
    }
  };

  const togglePref = async (key) => {
    Haptics.selectionAsync();
    const newVal = !prefs[key];
    setPrefs((p) => ({ ...p, [key]: newVal }));

    try {
      // In production: await notificationsApi.updatePreferences({ [key]: newVal });
    } catch (err) {
      // Revert on error
      setPrefs((p) => ({ ...p, [key]: !newVal }));
    }
  };

  const testNotification = (type) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Alert.alert("Test Sent!", `A test ${type} notification has been triggered. Check your notifications!`);
    // In production: await notificationsApi.trigger(type);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.accent} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <Text style={styles.title}>Notifications</Text>
      <Text style={styles.subtitle}>
        Smart reminders powered by AI — sent when you're most likely to act
      </Text>

      {/* AI Badge */}
      <View style={styles.aiBanner}>
        <LinearGradient
          colors={[`${COLORS.accent}12`, `${COLORS.mint}08`]}
          style={styles.aiBannerGrad}
        >
          <Text style={{ fontSize: 16 }}>🧠</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.aiBannerTitle}>AI-Optimized Timing</Text>
            <Text style={styles.aiBannerDesc}>
              Reminders adapt based on when you actually complete habits — not just when they're scheduled
            </Text>
          </View>
        </LinearGradient>
      </View>

      {/* Preference Toggles */}
      {PREF_ITEMS.map((item) => (
        <View key={item.key} style={styles.prefCard}>
          <View style={styles.prefLeft}>
            <View style={[styles.prefIcon, { backgroundColor: `${item.color}15` }]}>
              <Text style={{ fontSize: 20 }}>{item.icon}</Text>
            </View>
            <View style={styles.prefInfo}>
              <Text style={styles.prefTitle}>{item.title}</Text>
              <Text style={styles.prefDesc}>{item.desc}</Text>
            </View>
          </View>
          <Switch
            value={prefs[item.key]}
            onValueChange={() => togglePref(item.key)}
            trackColor={{ false: COLORS.surface, true: `${item.color}88` }}
            thumbColor={prefs[item.key] ? item.color : "#666"}
          />
        </View>
      ))}

      {/* Today's Schedule Preview */}
      {schedule && (
        <View style={styles.scheduleSection}>
          <Text style={styles.sectionTitle}>Today's Schedule</Text>
          <Text style={styles.sectionSubtitle}>
            {schedule.notifications.length} notifications planned
          </Text>

          <View style={styles.timeline}>
            {schedule.notifications.map((n, i) => (
              <View key={i} style={styles.timelineItem}>
                <View style={styles.timelineLeft}>
                  <Text style={styles.timelineTime}>{formatTime12(n.scheduled_time)}</Text>
                  <View style={styles.timelineDot} />
                  {i < schedule.notifications.length - 1 && <View style={styles.timelineLine} />}
                </View>
                <View style={styles.timelineCard}>
                  <Text style={{ fontSize: 16 }}>
                    {n.type === "streak_protector" ? "🔥" : n.habit_icon || "✨"}
                  </Text>
                  <View>
                    <Text style={styles.timelineTitle}>
                      {n.type === "streak_protector" ? "Streak Protector" : n.habit_name}
                    </Text>
                    <Text style={styles.timelineType}>
                      {n.type === "streak_protector" ? "Alert if habits incomplete" : "Habit reminder"}
                    </Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Test Section */}
      <View style={styles.testSection}>
        <Text style={styles.sectionTitle}>Test Notifications</Text>
        <Text style={styles.sectionSubtitle}>Send yourself a test notification</Text>

        <View style={styles.testButtons}>
          {[
            { label: "⏰ Habit Reminder", type: "habit-reminder" },
            { label: "🔥 Streak Alert", type: "streak-protector" },
            { label: "📊 Weekly Summary", type: "weekly-summary" },
          ].map((btn) => (
            <TouchableOpacity
              key={btn.type}
              onPress={() => testNotification(btn.type)}
              style={styles.testBtn}
              activeOpacity={0.7}
            >
              <Text style={styles.testBtnText}>{btn.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </ScrollView>
  );
}

function formatTime12(time24) {
  if (!time24) return "";
  const [h, m] = time24.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { paddingHorizontal: 18, paddingTop: 14, paddingBottom: 100 },
  loadingContainer: { flex: 1, backgroundColor: COLORS.bg, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 24, fontWeight: "800", color: COLORS.text, marginBottom: 4 },
  subtitle: { fontSize: 13, color: COLORS.sub, lineHeight: 20, marginBottom: 16 },

  // AI Banner
  aiBanner: { marginBottom: 18 },
  aiBannerGrad: {
    flexDirection: "row", gap: 12, alignItems: "flex-start",
    borderRadius: 16, padding: 16,
    borderWidth: 1, borderColor: `${COLORS.accent}20`,
  },
  aiBannerTitle: { fontSize: 13, fontWeight: "700", color: COLORS.accent, marginBottom: 2 },
  aiBannerDesc: { fontSize: 12, color: COLORS.sub, lineHeight: 18 },

  // Preferences
  prefCard: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    backgroundColor: COLORS.card, borderRadius: 16, padding: 14,
    borderWidth: 1, borderColor: COLORS.border, marginBottom: 8,
  },
  prefLeft: { flexDirection: "row", alignItems: "center", gap: 12, flex: 1, marginRight: 12 },
  prefIcon: { width: 44, height: 44, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  prefInfo: { flex: 1 },
  prefTitle: { fontSize: 14, fontWeight: "700", color: COLORS.text },
  prefDesc: { fontSize: 11, color: COLORS.dim, lineHeight: 16, marginTop: 2 },

  // Schedule
  scheduleSection: { marginTop: 24 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: COLORS.text, marginBottom: 2 },
  sectionSubtitle: { fontSize: 12, color: COLORS.dim, marginBottom: 14 },
  timeline: { gap: 0 },
  timelineItem: { flexDirection: "row", gap: 12 },
  timelineLeft: { width: 56, alignItems: "center" },
  timelineTime: { fontSize: 10, fontWeight: "600", color: COLORS.sub, marginBottom: 6 },
  timelineDot: {
    width: 10, height: 10, borderRadius: 5,
    backgroundColor: COLORS.accent, borderWidth: 2, borderColor: `${COLORS.accent}44`,
  },
  timelineLine: {
    width: 2, flex: 1, backgroundColor: `${COLORS.accent}22`, marginVertical: 2,
  },
  timelineCard: {
    flex: 1, flexDirection: "row", alignItems: "center", gap: 10,
    backgroundColor: COLORS.card, borderRadius: 12, padding: 12,
    borderWidth: 1, borderColor: COLORS.border, marginBottom: 8,
  },
  timelineTitle: { fontSize: 13, fontWeight: "600", color: COLORS.text },
  timelineType: { fontSize: 10, color: COLORS.dim, marginTop: 1 },

  // Test
  testSection: { marginTop: 24 },
  testButtons: { gap: 8 },
  testBtn: {
    backgroundColor: COLORS.surface, borderRadius: 12, padding: 14,
    alignItems: "center", borderWidth: 1, borderColor: COLORS.border,
  },
  testBtnText: { fontSize: 13, fontWeight: "600", color: COLORS.sub },
});
