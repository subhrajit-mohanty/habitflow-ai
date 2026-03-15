/**
 * HabitFlow AI — Analytics Screen (Expo React Native)
 * Stats overview, completion trends, mood/energy charts,
 * per-habit breakdown with expand, weekly heatmap.
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, StyleSheet,
  ActivityIndicator, RefreshControl,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { COLORS } from "../../constants";
import { analyticsApi } from "../../services/api";

const PERIODS = [
  { key: "week", label: "Week", days: 7 },
  { key: "month", label: "Month", days: 30 },
  { key: "3mo", label: "3 Months", days: 90 },
];
const WEEK_LABELS = ["M", "T", "W", "T", "F", "S", "S"];

export default function AnalyticsScreen() {
  const [period, setPeriod] = useState("month");
  const [data, setData] = useState(null);
  const [moodTrend, setMoodTrend] = useState([]);
  const [energyTrend, setEnergyTrend] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedHabit, setExpandedHabit] = useState(null);

  const periodDays = PERIODS.find((p) => p.key === period)?.days || 30;

  useEffect(() => { loadData(); }, [period]);

  const loadData = async () => {
    try {
      const [overview, moods, energies] = await Promise.all([
        analyticsApi.getOverview(periodDays),
        analyticsApi.getTrends("mood", periodDays),
        analyticsApi.getTrends("energy", periodDays),
      ]);
      setData(overview);
      setMoodTrend(moods || []);
      setEnergyTrend(energies || []);
    } catch (err) {
      console.error("Analytics load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.accent} />
      </View>
    );
  }

  const stats = [
    { label: "Completion Rate", val: `${Math.round((data?.overall_completion_rate || 0) * 100)}%`, icon: "✅", color: COLORS.mint },
    { label: "Avg Streak", val: data?.habit_analytics?.length ? (data.habit_analytics.reduce((a, h) => a + h.current_streak, 0) / data.habit_analytics.length).toFixed(1) : "0", icon: "🔥", color: COLORS.amber },
    { label: "Avg Mood", val: data?.avg_mood ? `${data.avg_mood}/5` : "—", icon: "😊", color: COLORS.accent },
    { label: "Avg Energy", val: data?.avg_energy ? `${data.avg_energy}/5` : "—", icon: "⚡", color: COLORS.sky },
  ];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.accent} />}
    >
      <Text style={styles.title}>Analytics</Text>
      <Text style={styles.subtitle}>Your habit intelligence</Text>

      {/* Period Selector */}
      <View style={styles.periodRow}>
        {PERIODS.map((p) => (
          <TouchableOpacity
            key={p.key}
            onPress={() => setPeriod(p.key)}
            style={[styles.periodBtn, period === p.key && styles.periodBtnActive]}
          >
            <Text style={[styles.periodText, period === p.key && styles.periodTextActive]}>{p.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Stats Grid */}
      <View style={styles.statsGrid}>
        {stats.map((s, i) => (
          <View key={i} style={styles.statCard}>
            <View style={styles.statHeader}>
              <Text style={styles.statLabel}>{s.label}</Text>
              <Text style={{ fontSize: 14 }}>{s.icon}</Text>
            </View>
            <Text style={styles.statValue}>{s.val}</Text>
          </View>
        ))}
      </View>

      {/* Mood & Energy Chart */}
      <View style={styles.chartCard}>
        <Text style={styles.chartTitle}>Mood & Energy</Text>
        <View style={styles.barChart}>
          {(moodTrend.length > 0 ? moodTrend.slice(-7) : Array(7).fill({ value: 0 })).map((m, i) => {
            const energySlice = energyTrend.slice(-7);
            const energy = (energySlice[i] || {}).value || 0;
            const moodVal = m.value || 0;
            return (
              <View key={i} style={styles.barCol}>
                <View style={styles.barPair}>
                  <View style={[styles.bar, { height: moodVal * 14, backgroundColor: COLORS.accent }]} />
                  <View style={[styles.bar, { height: energy * 14, backgroundColor: COLORS.mint }]} />
                </View>
                <Text style={styles.barLabel}>{WEEK_LABELS[i]}</Text>
              </View>
            );
          })}
        </View>
        <View style={styles.legend}>
          <LegendDot color={COLORS.accent} label="Mood" />
          <LegendDot color={COLORS.mint} label="Energy" />
        </View>
      </View>

      {/* Per-Habit Breakdown */}
      <Text style={styles.sectionTitle}>Per-Habit Breakdown</Text>
      {(data?.habit_analytics || []).map((h, i) => {
        const isOpen = expandedHabit === i;
        const rateColor = h.completion_rate >= 0.8 ? COLORS.mint : h.completion_rate >= 0.6 ? "#FFBE5C" : "#FF6B8A";
        const ratePct = Math.round(h.completion_rate * 100);

        return (
          <TouchableOpacity
            key={i}
            onPress={() => setExpandedHabit(isOpen ? null : i)}
            activeOpacity={0.7}
            style={[styles.habitCard, isOpen && { borderColor: `${COLORS.accent}30` }]}
          >
            <View style={styles.habitRow}>
              <View style={styles.habitInfo}>
                <Text style={styles.habitName}>{h.habit_name}</Text>
                <View style={styles.habitMeta}>
                  <Text style={styles.habitMetaText}>🔥 {h.current_streak}d</Text>
                  <Text style={[styles.habitRate, { color: rateColor }]}>{ratePct}%</Text>
                </View>
              </View>
              <View style={styles.miniBar}>
                <View style={[styles.miniBarFill, { width: `${ratePct}%`, backgroundColor: rateColor }]} />
              </View>
              <Text style={[styles.chevron, isOpen && { transform: [{ rotate: "180deg" }] }]}>▾</Text>
            </View>

            {isOpen && (
              <View style={styles.habitExpanded}>
                <View style={styles.expandedStats}>
                  {[
                    { label: "Best Streak", value: `${h.best_streak}d` },
                    { label: "Best Day", value: h.best_day_of_week ? WEEK_LABELS[h.best_day_of_week - 1] || "—" : "—" },
                    { label: "Completions", value: `${h.completions}` },
                  ].map((s, si) => (
                    <View key={si} style={styles.expandedStat}>
                      <Text style={styles.expandedStatLabel}>{s.label}</Text>
                      <Text style={styles.expandedStatValue}>{s.value}</Text>
                    </View>
                  ))}
                </View>
                {h.mood_correlation !== null && h.mood_correlation !== undefined && (
                  <View style={styles.correlationBox}>
                    <Text style={{ fontSize: 12 }}>🔗</Text>
                    <Text style={styles.correlationText}>
                      Mood impact: <Text style={{ fontWeight: "700", color: h.mood_correlation > 0.5 ? COLORS.mint : COLORS.amber }}>
                        +{h.mood_correlation.toFixed(1)}
                      </Text>
                    </Text>
                  </View>
                )}
              </View>
            )}
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}

function LegendDot({ color, label }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 5 }}>
      <View style={{ width: 8, height: 8, borderRadius: 3, backgroundColor: color }} />
      <Text style={{ fontSize: 10, color: COLORS.sub }}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { paddingHorizontal: 18, paddingTop: 14, paddingBottom: 100 },
  loadingContainer: { flex: 1, backgroundColor: COLORS.bg, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 24, fontWeight: "800", color: COLORS.text, marginBottom: 4 },
  subtitle: { fontSize: 13, color: COLORS.sub, marginBottom: 14 },

  periodRow: { flexDirection: "row", gap: 6, marginBottom: 16 },
  periodBtn: { paddingVertical: 7, paddingHorizontal: 18, borderRadius: 12, backgroundColor: COLORS.surface },
  periodBtnActive: { backgroundColor: COLORS.accent },
  periodText: { fontSize: 12, fontWeight: "600", color: COLORS.sub },
  periodTextActive: { color: "#fff" },

  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 16 },
  statCard: {
    width: (390 - 18 * 2 - 10) / 2, backgroundColor: COLORS.card,
    borderRadius: 16, padding: 16, borderWidth: 1, borderColor: COLORS.border,
  },
  statHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  statLabel: { fontSize: 10, color: COLORS.dim, textTransform: "uppercase", letterSpacing: 1, fontWeight: "600" },
  statValue: { fontSize: 24, fontWeight: "800", color: COLORS.text },

  chartCard: {
    backgroundColor: COLORS.card, borderRadius: 18, padding: 18,
    borderWidth: 1, borderColor: COLORS.border, marginBottom: 16,
  },
  chartTitle: { fontSize: 14, fontWeight: "700", color: COLORS.text, marginBottom: 14 },
  barChart: { flexDirection: "row", alignItems: "flex-end", gap: 10, height: 90 },
  barCol: { flex: 1, alignItems: "center", gap: 3 },
  barPair: { flexDirection: "row", gap: 3, alignItems: "flex-end", height: 70 },
  bar: { width: 14, borderRadius: 4 },
  barLabel: { fontSize: 9, color: COLORS.dim },
  legend: { flexDirection: "row", gap: 16, marginTop: 10, justifyContent: "center" },

  sectionTitle: { fontSize: 14, fontWeight: "700", color: COLORS.text, marginBottom: 10 },
  habitCard: {
    backgroundColor: COLORS.card, borderRadius: 16, marginBottom: 8,
    borderWidth: 1, borderColor: COLORS.border, overflow: "hidden",
  },
  habitRow: {
    flexDirection: "row", alignItems: "center", gap: 12, padding: 14, paddingHorizontal: 16,
  },
  habitInfo: { flex: 1 },
  habitName: { fontSize: 14, fontWeight: "700", color: COLORS.text },
  habitMeta: { flexDirection: "row", gap: 10, marginTop: 3 },
  habitMetaText: { fontSize: 11, color: COLORS.dim },
  habitRate: { fontSize: 11, fontWeight: "600" },
  miniBar: { width: 60, height: 6, borderRadius: 3, backgroundColor: COLORS.surface, overflow: "hidden" },
  miniBarFill: { height: "100%", borderRadius: 3 },
  chevron: { fontSize: 14, color: COLORS.dim },
  habitExpanded: { paddingHorizontal: 16, paddingBottom: 16 },
  expandedStats: { flexDirection: "row", gap: 8, marginBottom: 10 },
  expandedStat: { flex: 1, backgroundColor: COLORS.surface, borderRadius: 10, padding: 10, alignItems: "center" },
  expandedStatLabel: { fontSize: 9, color: COLORS.dim, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 3 },
  expandedStatValue: { fontSize: 15, fontWeight: "700", color: COLORS.text },
  correlationBox: {
    flexDirection: "row", alignItems: "center", gap: 8,
    backgroundColor: `${COLORS.accent}08`, borderRadius: 10, padding: 10,
    borderWidth: 1, borderColor: `${COLORS.accent}15`,
  },
  correlationText: { fontSize: 12, color: COLORS.sub },
});
