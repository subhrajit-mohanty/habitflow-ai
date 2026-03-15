/**
 * HabitFlow AI — Weekly Review Card
 * Shown at the top of Coach tab on Sundays, or accessible anytime.
 */

import React, { useState, useEffect } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet,
  ActivityIndicator,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { COLORS } from "../../constants";
import { coachApi } from "../../services/api";

export default function WeeklyReviewCard() {
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadReview();
  }, []);

  const loadReview = async () => {
    try {
      const data = await coachApi.getWeeklySummary();
      setReview(data);
    } catch (err) {
      setError("Couldn't load your weekly review");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <LinearGradient colors={[`${COLORS.accent}12`, `${COLORS.mint}08`]} style={styles.card}>
          <ActivityIndicator color={COLORS.accent} size="small" />
          <Text style={styles.loadingText}>Preparing your weekly review...</Text>
        </LinearGradient>
      </View>
    );
  }

  if (error || !review) return null;

  const ratePct = Math.round((review.completion_rate || 0) * 100);

  return (
    <View style={styles.container}>
      <TouchableOpacity onPress={() => setExpanded(!expanded)} activeOpacity={0.8}>
        <LinearGradient
          colors={[`${COLORS.accent}14`, `${COLORS.mint}08`]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.card}
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerLeft}>
              <Text style={{ fontSize: 18 }}>📊</Text>
              <Text style={styles.headerTitle}>Weekly Review</Text>
            </View>
            <Text style={styles.expandIcon}>{expanded ? "▾" : "▸"}</Text>
          </View>

          {/* Stats Row */}
          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{ratePct}%</Text>
              <Text style={styles.statLabel}>Completion</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.stat}>
              <Text style={styles.statValue}>{review.total_completions}</Text>
              <Text style={styles.statLabel}>Check-ins</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.stat}>
              <Text style={[styles.statValue, { color: COLORS.mint }]}>
                {review.avg_mood ? `${review.avg_mood}/5` : "—"}
              </Text>
              <Text style={styles.statLabel}>Avg Mood</Text>
            </View>
          </View>

          {/* Best/Worst */}
          <View style={styles.habitsRow}>
            {review.best_habit && (
              <View style={styles.habitPill}>
                <Text style={styles.habitPillLabel}>🏆 Best:</Text>
                <Text style={styles.habitPillValue}>{review.best_habit}</Text>
              </View>
            )}
            {review.worst_habit && (
              <View style={[styles.habitPill, { borderColor: `${COLORS.coral}25` }]}>
                <Text style={styles.habitPillLabel}>⚠️ Focus:</Text>
                <Text style={[styles.habitPillValue, { color: COLORS.coral }]}>{review.worst_habit}</Text>
              </View>
            )}
          </View>

          {/* AI Summary (expanded) */}
          {expanded && review.ai_summary && (
            <View style={styles.aiSummary}>
              <View style={styles.aiSummaryHeader}>
                <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.miniAvatar}>
                  <Text style={styles.miniAvatarText}>H</Text>
                </LinearGradient>
                <Text style={styles.aiSummaryLabel}>Coach's Take</Text>
              </View>
              <Text style={styles.aiSummaryText}>{review.ai_summary}</Text>
            </View>
          )}

          {!expanded && (
            <Text style={styles.tapHint}>Tap to see AI insights</Text>
          )}
        </LinearGradient>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 18,
    paddingTop: 12,
  },
  card: {
    borderRadius: 18,
    padding: 18,
    borderWidth: 1,
    borderColor: `${COLORS.accent}20`,
  },
  loadingText: {
    color: COLORS.sub,
    fontSize: 12,
    marginTop: 8,
    textAlign: "center",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  headerLeft: { flexDirection: "row", alignItems: "center", gap: 8 },
  headerTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: COLORS.text,
  },
  expandIcon: { fontSize: 14, color: COLORS.dim },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginBottom: 14,
  },
  stat: { alignItems: "center" },
  statValue: {
    fontSize: 22,
    fontWeight: "800",
    color: COLORS.text,
  },
  statLabel: {
    fontSize: 10,
    color: COLORS.dim,
    marginTop: 2,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  statDivider: {
    width: 1,
    backgroundColor: COLORS.border,
    marginVertical: 4,
  },
  habitsRow: {
    flexDirection: "row",
    gap: 8,
  },
  habitPill: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    padding: 8,
    borderRadius: 10,
    backgroundColor: "rgba(255,255,255,0.03)",
    borderWidth: 1,
    borderColor: `${COLORS.mint}25`,
  },
  habitPillLabel: { fontSize: 10, color: COLORS.dim },
  habitPillValue: { fontSize: 11, fontWeight: "700", color: COLORS.mint },
  aiSummary: {
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  aiSummaryHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 10,
  },
  miniAvatar: {
    width: 22,
    height: 22,
    borderRadius: 7,
    alignItems: "center",
    justifyContent: "center",
  },
  miniAvatarText: { fontSize: 10, fontWeight: "800", color: "#fff" },
  aiSummaryLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: COLORS.accent,
  },
  aiSummaryText: {
    fontSize: 13,
    color: COLORS.sub,
    lineHeight: 20,
  },
  tapHint: {
    fontSize: 10,
    color: COLORS.dim,
    textAlign: "center",
    marginTop: 10,
  },
});
