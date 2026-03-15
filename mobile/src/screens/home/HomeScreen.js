/**
 * HabitFlow AI — Home Screen (Expo React Native)
 * The primary daily engagement surface. Live check-ins with
 * celebrations, progress ring, AI insight rotation, mood tracker,
 * undo support, and weekly heatmap.
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, StyleSheet,
  Animated, Dimensions, RefreshControl, Modal,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import Svg, { Circle, Defs, LinearGradient as SvgGrad, Stop } from "react-native-svg";
import { COLORS } from "../../constants";
import { habitsApi, completionsApi, dailyLogsApi, gamificationApi, userApi, coachApi } from "../../services/api";
import FocusTimer from "../../components/FocusTimer";

const { width: SCREEN_W } = Dimensions.get("window");
const MOODS = ["😴", "😕", "😐", "🙂", "😄"];

export default function HomeScreen() {
  // Data state
  const [todayHabits, setTodayHabits] = useState([]);
  const [levelInfo, setLevelInfo] = useState({ current_level: 1, total_xp: 0, progress_pct: 0 });
  const [profile, setProfile] = useState(null);
  const [mood, setMood] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [aiInsight, setAiInsight] = useState(null);

  // UI state
  const [celebration, setCelebration] = useState(null);
  const [streakMilestone, setStreakMilestone] = useState(null);
  const [undoTarget, setUndoTarget] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timerHabit, setTimerHabit] = useState(null);

  // Animations
  const celebScale = useRef(new Animated.Value(0)).current;
  const celebOpacity = useRef(new Animated.Value(0)).current;
  const ringAnim = useRef(new Animated.Value(0)).current;

  // Computed
  const completed = todayHabits.filter((h) => h.is_completed_today).length;
  const total = todayHabits.length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  // Greeting
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good Morning ☀️" : hour < 17 ? "Good Afternoon 🌤️" : "Good Evening 🌙";
  const today = new Date();
  const dayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  // Fallback insight when AI insight hasn't loaded yet
  const fallbackInsight = "You complete 40% more habits on mornings you meditate first.";

  // ─── Load data ───
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [habits, level, prof] = await Promise.all([
        habitsApi.getToday(),
        gamificationApi.getLevelInfo(),
        userApi.getProfile(),
      ]);
      setTodayHabits(habits || []);
      setLevelInfo(level || { current_level: 1, total_xp: 0, progress_pct: 0 });
      setProfile(prof);

      // Fetch AI insight (non-blocking)
      coachApi.getDailyInsight()
        .then(res => setAiInsight(res?.insight))
        .catch(() => {});

      // Animate ring
      Animated.spring(ringAnim, {
        toValue: habits ? habits.filter((h) => h.is_completed_today).length / Math.max(habits.length, 1) : 0,
        friction: 6,
        useNativeDriver: false,
      }).start();
    } catch (err) {
      console.error("Load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  // ─── Check-in (entry point — may show Focus Timer for timed habits) ───
  const handleCheckIn = (habitStatus) => {
    if (habitStatus.is_completed_today) return;

    const habit = habitStatus.habit;

    // Show Focus Timer for habits longer than 2 minutes
    if (habit.duration_minutes > 2 || habit.verification_type === "timer") {
      setTimerHabit(habit);
      return;
    }

    doCheckIn(habitStatus);
  };

  // ─── Timer completion handler ───
  const handleTimerComplete = async (habitId) => {
    setTimerHabit(null);
    const item = todayHabits.find((h) => h.habit.id === habitId);
    if (item) doCheckIn(item);
  };

  // ─── Actual check-in API call ───
  const doCheckIn = async (habitStatus) => {
    const habit = habitStatus.habit;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

    // Optimistic update
    setTodayHabits((prev) =>
      prev.map((h) =>
        h.habit.id === habit.id ? { ...h, is_completed_today: true } : h
      )
    );

    try {
      const result = await completionsApi.checkIn({
        habit_id: habit.id,
        mood_score: mood !== null ? mood + 1 : undefined,
      });

      // Show celebration
      showCelebration({
        xp: result.xp_earned,
        habitName: habit.name,
        habitIcon: habit.icon,
        streak: result.new_streak,
        levelUp: result.level_up,
        newLevel: result.new_level,
        newBadges: result.new_badges || [],
      });

      // Show undo for 5 seconds
      setUndoTarget({ completionId: result.completion.id, habitId: habit.id });
      setTimeout(() => setUndoTarget(null), 5000);

      // Check streak milestones
      if ([7, 14, 21, 30, 50, 100].includes(result.new_streak)) {
        setTimeout(() => {
          setStreakMilestone({
            streak: result.new_streak,
            name: habit.name,
            icon: habit.icon,
          });
        }, 1800);
      }

      // Refresh level info
      const newLevel = await gamificationApi.getLevelInfo();
      setLevelInfo(newLevel);

      // Update ring animation
      const newCompleted = todayHabits.filter((h) => h.is_completed_today).length + 1;
      Animated.spring(ringAnim, {
        toValue: newCompleted / total,
        friction: 5,
        useNativeDriver: false,
      }).start();

    } catch (err) {
      // Revert optimistic update
      setTodayHabits((prev) =>
        prev.map((h) =>
          h.habit.id === habit.id ? { ...h, is_completed_today: false } : h
        )
      );
      console.error("Check-in error:", err);
    }
  };

  // ─── Undo ───
  const handleUndo = async () => {
    if (!undoTarget) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    // Optimistic revert
    setTodayHabits((prev) =>
      prev.map((h) =>
        h.habit.id === undoTarget.habitId ? { ...h, is_completed_today: false } : h
      )
    );
    setUndoTarget(null);

    try {
      await completionsApi.undo(undoTarget.completionId);
      const newLevel = await gamificationApi.getLevelInfo();
      setLevelInfo(newLevel);
    } catch (err) {
      console.error("Undo error:", err);
      loadData(); // Full refresh on error
    }
  };

  // ─── Mood log ───
  const handleMoodSelect = async (moodIndex) => {
    setMood(moodIndex);
    Haptics.selectionAsync();

    try {
      const period = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
      await dailyLogsApi.create({
        [`${period}_mood`]: moodIndex + 1,
      });
    } catch (err) {
      console.warn("Mood save error:", err);
    }
  };

  // ─── Celebration animation ───
  const showCelebration = (data) => {
    setCelebration(data);
    celebOpacity.setValue(1);
    celebScale.setValue(0);
    Animated.spring(celebScale, {
      toValue: 1,
      friction: 4,
      tension: 60,
      useNativeDriver: true,
    }).start();

    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

    // Auto dismiss
    setTimeout(() => {
      Animated.timing(celebOpacity, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start(() => setCelebration(null));
    }, 1600);
  };

  // ─── Sort habits: incomplete first, then by time ───
  const sortedHabits = [...todayHabits].sort((a, b) => {
    if (a.is_completed_today !== b.is_completed_today) {
      return a.is_completed_today ? 1 : -1;
    }
    const timeA = a.scheduled_time || a.habit.preferred_time || "99:99";
    const timeB = b.scheduled_time || b.habit.preferred_time || "99:99";
    return timeA.localeCompare(timeB);
  });

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.accent} />
        }
      >
        {/* ─── Header ─── */}
        <View style={styles.header}>
          <View>
            <Text style={styles.dateText}>
              {dayNames[today.getDay()]}, {monthNames[today.getMonth()]} {today.getDate()}
            </Text>
            <Text style={styles.greeting}>{greeting}</Text>
          </View>
          <View style={styles.headerRight}>
            <View style={styles.xpBadge}>
              <Text style={{ fontSize: 10 }}>⚡</Text>
              <Text style={styles.xpText}>{levelInfo.total_xp} XP</Text>
            </View>
            <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.avatar}>
              <Text style={styles.avatarText}>
                {(profile?.display_name || profile?.username || "U").charAt(0).toUpperCase()}
              </Text>
            </LinearGradient>
          </View>
        </View>

        {/* ─── Progress Card ─── */}
        <View style={styles.progressCard}>
          <View style={styles.ringContainer}>
            <Svg width={76} height={76}>
              <Defs>
                <SvgGrad id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <Stop offset="0%" stopColor="#7C6BFF" />
                  <Stop offset="100%" stopColor="#00D9A6" />
                </SvgGrad>
              </Defs>
              <Circle cx={38} cy={38} r={31} stroke={COLORS.surface} strokeWidth={6} fill="none" />
              <Circle
                cx={38} cy={38} r={31} stroke="url(#grad)" strokeWidth={6}
                fill="none" strokeLinecap="round"
                strokeDasharray={`${pct * 1.948} 194.8`}
                rotation={-90} origin="38,38"
              />
            </Svg>
            <View style={styles.ringCenter}>
              <Text style={styles.ringPct}>{pct}%</Text>
              <Text style={styles.ringLabel}>TODAY</Text>
            </View>
          </View>
          <View style={styles.progressInfo}>
            <Text style={styles.progressTitle}>
              <Text style={{ color: COLORS.mint, fontWeight: "800" }}>{completed}</Text> of {total} habits done
            </Text>
            {pct === 100 ? (
              <Text style={styles.progressPerfect}>🎉 Perfect day!</Text>
            ) : (
              <Text style={styles.progressSub}>{total - completed} remaining · You've got this!</Text>
            )}
            <View style={styles.pills}>
              <View style={[styles.pill, { borderColor: `${COLORS.accent}25`, backgroundColor: `${COLORS.accent}15` }]}>
                <Text style={[styles.pillText, { color: COLORS.accent }]}>Lv {levelInfo.current_level}</Text>
              </View>
              <View style={[styles.pill, { borderColor: `${COLORS.mint}25`, backgroundColor: `${COLORS.mint}15` }]}>
                <Text style={[styles.pillText, { color: COLORS.mint }]}>🔥 {Math.max(...todayHabits.map(h => h.habit.current_streak || 0), 0)}d best</Text>
              </View>
            </View>
          </View>
        </View>

        {/* ─── Mood Tracker ─── */}
        <View style={styles.moodCard}>
          <Text style={styles.moodLabel}>How are you feeling?</Text>
          <View style={styles.moodRow}>
            {MOODS.map((emoji, i) => (
              <TouchableOpacity
                key={i}
                onPress={() => handleMoodSelect(i)}
                style={[styles.moodBtn, mood === i && styles.moodBtnActive]}
                activeOpacity={0.7}
              >
                <Text style={{ fontSize: 22 }}>{emoji}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* ─── Habit List Header ─── */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Today's Habits</Text>
          <TouchableOpacity style={styles.addBtn}>
            <Text style={styles.addBtnText}>+ Add</Text>
          </TouchableOpacity>
        </View>

        {/* ─── Habit Cards ─── */}
        {sortedHabits.map((item) => {
          const h = item.habit;
          const done = item.is_completed_today;
          const isUndo = undoTarget?.habitId === h.id;
          const rateColor = (h.completion_rate || 0) >= 0.8 ? COLORS.mint : (h.completion_rate || 0) >= 0.6 ? "#FFBE5C" : "#FF6B8A";

          return (
            <TouchableOpacity
              key={h.id}
              onPress={() => handleCheckIn(item)}
              activeOpacity={done ? 1 : 0.7}
              style={[
                styles.habitCard,
                done && styles.habitCardDone,
              ]}
            >
              {/* Check button */}
              <View style={[
                styles.checkBtn,
                done ? styles.checkBtnDone : { backgroundColor: `${h.color || COLORS.accent}20` },
              ]}>
                {done ? (
                  <Text style={styles.checkMark}>✓</Text>
                ) : (
                  <Text style={{ fontSize: 22 }}>{h.icon}</Text>
                )}
              </View>

              {/* Info */}
              <View style={styles.habitInfo}>
                <View style={styles.habitNameRow}>
                  <Text style={[styles.habitName, done && styles.habitNameDone]}>{h.name}</Text>
                  {item.scheduled_time && h.ai_scheduling_enabled && (
                    <View style={styles.aiBadge}>
                      <Text style={styles.aiBadgeText}>AI</Text>
                    </View>
                  )}
                </View>
                <View style={styles.habitMeta}>
                  <Text style={styles.habitTime}>
                    🕐 {formatTime(item.scheduled_time || h.preferred_time)}
                  </Text>
                  <Text style={styles.habitDot}>·</Text>
                  <Text style={styles.habitDur}>{h.duration_minutes} min</Text>
                  <Text style={[styles.habitRate, { color: rateColor }]}>
                    {Math.round((h.completion_rate || 0) * 100)}%
                  </Text>
                </View>
              </View>

              {/* Streak + Undo */}
              <View style={styles.streakCol}>
                <View style={styles.streakRow}>
                  {(h.current_streak || 0) >= 7 && <Text style={{ fontSize: 10 }}>🔥</Text>}
                  <Text style={[
                    styles.streakNum,
                    done && { color: COLORS.mint },
                    (h.current_streak || 0) >= 7 && !done && { color: COLORS.accent },
                  ]}>
                    {h.current_streak || 0}
                  </Text>
                </View>
                <Text style={styles.streakLabel}>streak</Text>
                {done && isUndo && (
                  <TouchableOpacity onPress={handleUndo} style={styles.undoBtn}>
                    <Text style={styles.undoText}>Undo</Text>
                  </TouchableOpacity>
                )}
              </View>
            </TouchableOpacity>
          );
        })}

        {/* ─── AI Insight ─── */}
        <View style={styles.insightCard}>
          <View style={styles.insightHeader}>
            <Text style={{ fontSize: 16 }}>🧠</Text>
            <Text style={styles.insightLabel}>AI INSIGHT</Text>
          </View>
          <Text style={styles.insightText}>{aiInsight || fallbackInsight}</Text>
        </View>

        {/* ─── Weekly Heatmap Mini ─── */}
        <View style={styles.heatmapCard}>
          <View style={styles.heatmapHeader}>
            <Text style={styles.heatmapTitle}>This Week</Text>
            <TouchableOpacity>
              <Text style={styles.heatmapLink}>See all →</Text>
            </TouchableOpacity>
          </View>
          <View style={styles.heatmapRow}>
            {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => {
              const isToday = i === (today.getDay() === 0 ? 6 : today.getDay() - 1);
              return (
                <View key={i} style={styles.heatmapCol}>
                  <View style={[
                    styles.heatmapCell,
                    isToday && styles.heatmapCellToday,
                  ]}>
                    <Text style={styles.heatmapCellText}>{isToday ? `${pct}%` : "—"}</Text>
                  </View>
                  <Text style={[
                    styles.heatmapDay,
                    isToday && { color: COLORS.accent, fontWeight: "700" },
                  ]}>{d}</Text>
                </View>
              );
            })}
          </View>
        </View>
      </ScrollView>

      {/* ─── Celebration Modal ─── */}
      <Modal visible={!!celebration} transparent animationType="fade">
        <View style={styles.celebOverlay}>
          <Animated.View style={[
            styles.celebContent,
            { transform: [{ scale: celebScale }], opacity: celebOpacity },
          ]}>
            <Text style={styles.celebIcon}>{celebration?.habitIcon}</Text>
            <Text style={styles.celebXp}>+{celebration?.xp} XP</Text>
            <Text style={styles.celebMsg}>
              {celebration?.streak >= 7 ? "🔥 Streak bonus!" : "Nice one!"}
            </Text>
            <Text style={styles.celebHabit}>{celebration?.habitName} complete!</Text>
            {celebration?.levelUp && (
              <View style={styles.levelUpBadge}>
                <Text style={styles.levelUpText}>🎉 Level {celebration.newLevel}!</Text>
              </View>
            )}
            {(celebration?.newBadges || []).map((badge, i) => (
              <View key={i} style={styles.badgeEarned}>
                <Text style={{ fontSize: 20 }}>{badge.icon}</Text>
                <Text style={styles.badgeEarnedText}>{badge.name} earned!</Text>
              </View>
            ))}
          </Animated.View>
        </View>
      </Modal>

      {/* ─── Streak Milestone Modal ─── */}
      <Modal visible={!!streakMilestone} transparent animationType="fade">
        <TouchableOpacity
          style={styles.celebOverlay}
          activeOpacity={1}
          onPress={() => setStreakMilestone(null)}
        >
          <View style={styles.milestoneCard}>
            <Text style={{ fontSize: 56 }}>🏆</Text>
            <Text style={styles.milestoneLabel}>STREAK MILESTONE</Text>
            <Text style={styles.milestoneNumber}>{streakMilestone?.streak} Days</Text>
            <Text style={styles.milestoneHabit}>
              {streakMilestone?.icon} {streakMilestone?.name}
            </Text>
            <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.milestoneBonus}>
              <Text style={styles.milestoneBonusText}>+50 Bonus XP 🎉</Text>
            </LinearGradient>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* ─── Focus Timer ─── */}
      <FocusTimer
        visible={!!timerHabit}
        habit={timerHabit}
        onComplete={handleTimerComplete}
        onClose={() => setTimerHabit(null)}
      />
    </View>
  );
}

// ─── Helpers ───
function formatTime(time24) {
  if (!time24) return "—";
  try {
    const [h, m] = time24.split(":");
    const hour = parseInt(h);
    const ampm = hour >= 12 ? "PM" : "AM";
    const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${h12}:${m} ${ampm}`;
  } catch {
    return time24;
  }
}

// ─── Styles ───
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  scrollContent: { paddingHorizontal: 18, paddingTop: 14, paddingBottom: 100 },

  // Header
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 },
  dateText: { fontSize: 12, color: COLORS.sub, fontWeight: "500", marginBottom: 2 },
  greeting: { fontSize: 26, fontWeight: "800", color: COLORS.text, letterSpacing: -0.5 },
  headerRight: { flexDirection: "row", alignItems: "center", gap: 8 },
  xpBadge: {
    flexDirection: "row", alignItems: "center", gap: 4,
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10,
    backgroundColor: `${COLORS.accent}15`, borderWidth: 1, borderColor: `${COLORS.accent}25`,
  },
  xpText: { fontSize: 11, fontWeight: "700", color: COLORS.accent },
  avatar: { width: 40, height: 40, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  avatarText: { fontSize: 16, fontWeight: "800", color: "#fff" },

  // Progress
  progressCard: {
    backgroundColor: COLORS.card, borderRadius: 22, padding: 20,
    borderWidth: 1, borderColor: COLORS.border,
    flexDirection: "row", alignItems: "center", gap: 20, marginBottom: 14,
  },
  ringContainer: { width: 76, height: 76, position: "relative" },
  ringCenter: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, alignItems: "center", justifyContent: "center" },
  ringPct: { fontSize: 20, fontWeight: "800", color: COLORS.text },
  ringLabel: { fontSize: 8, color: COLORS.dim, fontWeight: "600", letterSpacing: 0.5 },
  progressInfo: { flex: 1 },
  progressTitle: { fontSize: 15, fontWeight: "700", color: COLORS.text, marginBottom: 4 },
  progressPerfect: { fontSize: 12, color: COLORS.mint, fontWeight: "600" },
  progressSub: { fontSize: 12, color: COLORS.sub },
  pills: { flexDirection: "row", gap: 6, marginTop: 8 },
  pill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, borderWidth: 1 },
  pillText: { fontSize: 10, fontWeight: "700" },

  // Mood
  moodCard: {
    backgroundColor: COLORS.card, borderRadius: 16, padding: 12, paddingHorizontal: 16,
    borderWidth: 1, borderColor: COLORS.border, marginBottom: 14,
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
  },
  moodLabel: { fontSize: 13, fontWeight: "600", color: COLORS.sub },
  moodRow: { flexDirection: "row", gap: 4 },
  moodBtn: { padding: 4, borderRadius: 10, borderWidth: 1.5, borderColor: "transparent" },
  moodBtnActive: { backgroundColor: `${COLORS.accent}22`, borderColor: `${COLORS.accent}55` },

  // Section
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: COLORS.text },
  addBtn: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 10,
    backgroundColor: `${COLORS.accent}12`, borderWidth: 1, borderColor: `${COLORS.accent}22`,
  },
  addBtnText: { fontSize: 11, fontWeight: "700", color: COLORS.accent },

  // Habit Card
  habitCard: {
    backgroundColor: COLORS.card, borderRadius: 18, padding: 14, paddingHorizontal: 16,
    borderWidth: 1, borderColor: COLORS.border,
    flexDirection: "row", alignItems: "center", gap: 14, marginBottom: 8,
  },
  habitCardDone: { backgroundColor: `${COLORS.mint}06`, borderColor: `${COLORS.mint}18` },
  checkBtn: {
    width: 44, height: 44, borderRadius: 14,
    alignItems: "center", justifyContent: "center",
  },
  checkBtnDone: {
    backgroundColor: COLORS.mint,
    shadowColor: COLORS.mint, shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25, shadowRadius: 8, elevation: 4,
  },
  checkMark: { fontSize: 20, color: "#fff", fontWeight: "700" },
  habitInfo: { flex: 1, minWidth: 0 },
  habitNameRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  habitName: { fontSize: 14, fontWeight: "700", color: COLORS.text },
  habitNameDone: { textDecorationLine: "line-through", color: COLORS.sub },
  aiBadge: {
    backgroundColor: `${COLORS.accent}15`, paddingHorizontal: 5, paddingVertical: 1, borderRadius: 4,
  },
  aiBadgeText: { fontSize: 8, fontWeight: "700", color: COLORS.accent },
  habitMeta: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 3 },
  habitTime: { fontSize: 11, color: COLORS.dim },
  habitDot: { fontSize: 11, color: COLORS.dim },
  habitDur: { fontSize: 11, color: COLORS.dim },
  habitRate: { fontSize: 10, fontWeight: "600" },
  streakCol: { alignItems: "flex-end" },
  streakRow: { flexDirection: "row", alignItems: "center", gap: 3 },
  streakNum: { fontSize: 17, fontWeight: "800", color: COLORS.sub },
  streakLabel: { fontSize: 9, color: COLORS.dim, letterSpacing: 0.5 },
  undoBtn: {
    marginTop: 4, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6,
    backgroundColor: "#FF6B8A12", borderWidth: 1, borderColor: "#FF6B8A22",
  },
  undoText: { fontSize: 9, fontWeight: "600", color: "#FF6B8A" },

  // AI Insight
  insightCard: {
    marginTop: 16, borderRadius: 18, padding: 18,
    backgroundColor: `${COLORS.accent}08`, borderWidth: 1, borderColor: `${COLORS.accent}15`,
  },
  insightHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  insightLabel: { fontSize: 11, fontWeight: "700", color: COLORS.accent, letterSpacing: 1 },
  insightText: { fontSize: 13, color: COLORS.sub, lineHeight: 20 },

  // Heatmap
  heatmapCard: {
    marginTop: 14, backgroundColor: COLORS.card, borderRadius: 16, padding: 14, paddingHorizontal: 16,
    borderWidth: 1, borderColor: COLORS.border, marginBottom: 20,
  },
  heatmapHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  heatmapTitle: { fontSize: 12, fontWeight: "700", color: COLORS.sub },
  heatmapLink: { fontSize: 10, color: COLORS.accent, fontWeight: "600" },
  heatmapRow: { flexDirection: "row", gap: 6 },
  heatmapCol: { flex: 1, alignItems: "center", gap: 5 },
  heatmapCell: {
    width: "100%", height: 32, borderRadius: 8,
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    alignItems: "center", justifyContent: "center",
  },
  heatmapCellToday: { borderColor: `${COLORS.accent}55`, borderWidth: 1.5 },
  heatmapCellText: { fontSize: 9, fontWeight: "700", color: COLORS.dim },
  heatmapDay: { fontSize: 10, fontWeight: "500", color: COLORS.dim },

  // Celebration
  celebOverlay: {
    flex: 1, backgroundColor: "rgba(6,6,11,0.7)",
    alignItems: "center", justifyContent: "center",
  },
  celebContent: { alignItems: "center" },
  celebIcon: { fontSize: 48, marginBottom: 8 },
  celebXp: { fontSize: 28, fontWeight: "800", color: COLORS.accent },
  celebMsg: { fontSize: 15, fontWeight: "600", color: COLORS.text, marginTop: 4 },
  celebHabit: { fontSize: 12, color: COLORS.sub, marginTop: 4 },
  levelUpBadge: {
    marginTop: 12, paddingHorizontal: 16, paddingVertical: 8, borderRadius: 12,
    backgroundColor: `${COLORS.accent}22`,
  },
  levelUpText: { fontSize: 14, fontWeight: "700", color: COLORS.accent },
  badgeEarned: {
    flexDirection: "row", alignItems: "center", gap: 8, marginTop: 8,
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10,
    backgroundColor: `${COLORS.mint}15`,
  },
  badgeEarnedText: { fontSize: 12, fontWeight: "600", color: COLORS.mint },

  // Milestone
  milestoneCard: {
    alignItems: "center", padding: 32,
    backgroundColor: `${COLORS.accent}15`, borderRadius: 24,
    borderWidth: 1, borderColor: `${COLORS.accent}30`,
  },
  milestoneLabel: { fontSize: 14, fontWeight: "700", color: COLORS.accent, letterSpacing: 2, marginTop: 8 },
  milestoneNumber: { fontSize: 48, fontWeight: "800", color: COLORS.text, marginTop: 4 },
  milestoneHabit: { fontSize: 14, color: COLORS.sub, marginTop: 6 },
  milestoneBonus: {
    marginTop: 16, paddingHorizontal: 20, paddingVertical: 8, borderRadius: 12,
  },
  milestoneBonusText: { fontSize: 13, fontWeight: "700", color: "#fff" },
});
