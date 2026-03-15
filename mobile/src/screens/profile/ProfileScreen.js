/**
 * HabitFlow AI — Profile Screen (Expo React Native)
 * User profile, level/XP progress, badge collection,
 * stats overview, and settings.
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, StyleSheet,
  ActivityIndicator, RefreshControl, Switch, Alert,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { COLORS } from "../../constants";
import { userApi, gamificationApi, auth } from "../../services/api";

export default function ProfileScreen() {
  const [profile, setProfile] = useState(null);
  const [levelInfo, setLevelInfo] = useState(null);
  const [badges, setBadges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [badgeFilter, setBadgeFilter] = useState("all");
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [prof, level, badgeList] = await Promise.all([
        userApi.getProfile(),
        gamificationApi.getLevelInfo(),
        gamificationApi.getBadges(),
      ]);
      setProfile(prof);
      setLevelInfo(level);
      setBadges(badgeList || []);
    } catch (err) {
      console.error("Profile load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const handleLogout = () => {
    Alert.alert("Log Out", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Log Out", style: "destructive",
        onPress: async () => {
          try { await auth.signOut(); } catch {}
        },
      },
    ]);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.accent} />
      </View>
    );
  }

  const earnedCount = badges.filter((b) => b.earned).length;
  const xpInLevel = levelInfo?.current_xp || 0;
  const xpToNext = levelInfo?.xp_to_next_level || 100;
  const progressPct = levelInfo?.progress_pct || 0;

  const filteredBadges = badges.filter((b) => {
    if (badgeFilter === "earned") return b.earned;
    if (badgeFilter === "locked") return !b.earned;
    return true;
  });

  const settingItems = [
    { label: "Notification Preferences", icon: "🔔", onPress: () => {} },
    { label: `Subscription · ${(profile?.subscription_tier || "free").charAt(0).toUpperCase() + (profile?.subscription_tier || "free").slice(1)}`, icon: "💎", accent: true, onPress: () => {} },
    { label: "Export My Data", icon: "📤", onPress: () => {} },
    { label: "Dark Mode", icon: "🌙", toggle: true, value: darkMode, onToggle: setDarkMode },
    { label: "Help & Feedback", icon: "💬", onPress: () => {} },
    { label: "Privacy Policy", icon: "🔒", onPress: () => {} },
    { label: "Log Out", icon: "👋", danger: true, onPress: handleLogout },
  ];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.accent} />}
    >
      {/* ─── Avatar & Name ─── */}
      <View style={styles.profileHeader}>
        <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(profile?.display_name || "U").charAt(0).toUpperCase()}
          </Text>
        </LinearGradient>
        <Text style={styles.name}>{profile?.display_name || "User"}</Text>
        <Text style={styles.username}>
          @{profile?.username || "user"} · {profile?.timezone?.split("/")[1] || ""}
        </Text>
        <Text style={styles.memberSince}>
          Member since {new Date(profile?.created_at).toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        </Text>
      </View>

      {/* ─── Level Card ─── */}
      <View style={styles.levelCard}>
        <LinearGradient
          colors={[`${COLORS.accent}14`, `${COLORS.mint}08`]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.levelGradient}
        >
          <View style={styles.levelRow}>
            <View>
              <Text style={styles.levelLabel}>LEVEL</Text>
              <Text style={styles.levelNumber}>{levelInfo?.current_level || 1}</Text>
            </View>
            <View style={{ alignItems: "flex-end" }}>
              <Text style={styles.levelLabel}>TOTAL XP</Text>
              <Text style={styles.xpNumber}>{levelInfo?.total_xp || 0}</Text>
            </View>
          </View>
          <View style={styles.xpBar}>
            <LinearGradient
              colors={["#7C6BFF", "#00D9A6"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={[styles.xpBarFill, { width: `${progressPct * 100}%` }]}
            />
          </View>
          <Text style={styles.xpToNext}>{xpToNext} XP to Level {(levelInfo?.current_level || 1) + 1}</Text>
        </LinearGradient>
      </View>

      {/* ─── Stats Row ─── */}
      <View style={styles.statsRow}>
        {[
          { label: "Active Habits", val: "5", icon: "🎯" },
          { label: "Best Streak", val: `${profile?.longest_streak || 0}`, icon: "🔥" },
          { label: "Badges", val: `${earnedCount}/${badges.length}`, icon: "🏅" },
        ].map((s, i) => (
          <View key={i} style={styles.statCard}>
            <Text style={{ fontSize: 18 }}>{s.icon}</Text>
            <Text style={styles.statVal}>{s.val}</Text>
            <Text style={styles.statLabel}>{s.label}</Text>
          </View>
        ))}
      </View>

      {/* ─── Badges ─── */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Badges</Text>
        <View style={styles.filterRow}>
          {["all", "earned", "locked"].map((f) => (
            <TouchableOpacity
              key={f}
              onPress={() => { setBadgeFilter(f); Haptics.selectionAsync(); }}
              style={[styles.filterBtn, badgeFilter === f && styles.filterBtnActive]}
            >
              <Text style={[styles.filterText, badgeFilter === f && styles.filterTextActive]}>
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={styles.badgesGrid}>
        {filteredBadges.map((badge, i) => (
          <TouchableOpacity
            key={badge.id}
            activeOpacity={0.7}
            style={[styles.badgeCard, !badge.earned && styles.badgeCardLocked]}
          >
            <Text style={[styles.badgeIcon, !badge.earned && { opacity: 0.3 }]}>
              {badge.icon}
            </Text>
            <View style={styles.badgeInfo}>
              <Text style={[styles.badgeName, !badge.earned && { color: COLORS.dim }]}>
                {badge.name}
              </Text>
              <Text style={styles.badgeMeta}>
                {badge.earned
                  ? `Earned ${new Date(badge.earned_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`
                  : badge.description}
              </Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {/* ─── Settings ─── */}
      <Text style={[styles.sectionTitle, { marginTop: 24, marginBottom: 10 }]}>Settings</Text>
      <View style={styles.settingsCard}>
        {settingItems.map((item, i) => (
          <TouchableOpacity
            key={i}
            onPress={item.toggle ? undefined : item.onPress}
            activeOpacity={item.toggle ? 1 : 0.7}
            style={[
              styles.settingRow,
              i < settingItems.length - 1 && styles.settingBorder,
            ]}
          >
            <View style={styles.settingLeft}>
              <Text style={{ fontSize: 16 }}>{item.icon}</Text>
              <Text style={[
                styles.settingLabel,
                item.danger && { color: "#FF6B8A" },
                item.accent && { color: COLORS.accent },
              ]}>{item.label}</Text>
            </View>
            {item.toggle ? (
              <Switch
                value={item.value}
                onValueChange={item.onToggle}
                trackColor={{ false: COLORS.surface, true: COLORS.mint }}
                thumbColor="#fff"
              />
            ) : (
              <Text style={styles.settingChevron}>›</Text>
            )}
          </TouchableOpacity>
        ))}
      </View>

      {/* ─── App Info ─── */}
      <View style={styles.appInfo}>
        <Text style={styles.appVersion}>HabitFlow AI v1.0.0</Text>
        <Text style={styles.appCredit}>Made with 💜</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { paddingHorizontal: 18, paddingTop: 14, paddingBottom: 100 },
  loadingContainer: { flex: 1, backgroundColor: COLORS.bg, alignItems: "center", justifyContent: "center" },

  // Profile header
  profileHeader: { alignItems: "center", marginBottom: 20, paddingTop: 8 },
  avatar: {
    width: 84, height: 84, borderRadius: 26, alignItems: "center", justifyContent: "center",
    marginBottom: 12, shadowColor: "#7C6BFF",
    shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.35, shadowRadius: 16, elevation: 8,
  },
  avatarText: { fontSize: 34, fontWeight: "800", color: "#fff" },
  name: { fontSize: 22, fontWeight: "800", color: COLORS.text, marginBottom: 2 },
  username: { fontSize: 13, color: COLORS.sub },
  memberSince: { fontSize: 11, color: COLORS.dim, marginTop: 2 },

  // Level card
  levelCard: { marginBottom: 16 },
  levelGradient: { borderRadius: 20, padding: 20, borderWidth: 1, borderColor: `${COLORS.accent}22` },
  levelRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 12 },
  levelLabel: { fontSize: 11, color: COLORS.sub, letterSpacing: 1, fontWeight: "600", marginBottom: 4 },
  levelNumber: { fontSize: 36, fontWeight: "800", color: COLORS.accent },
  xpNumber: { fontSize: 28, fontWeight: "800", color: COLORS.text },
  xpBar: { height: 8, borderRadius: 4, backgroundColor: COLORS.surface, overflow: "hidden", marginBottom: 6 },
  xpBarFill: { height: "100%", borderRadius: 4 },
  xpToNext: { fontSize: 11, color: COLORS.sub },

  // Stats
  statsRow: { flexDirection: "row", gap: 10, marginBottom: 20 },
  statCard: {
    flex: 1, backgroundColor: COLORS.card, borderRadius: 14, padding: 14,
    alignItems: "center", borderWidth: 1, borderColor: COLORS.border,
  },
  statVal: { fontSize: 22, fontWeight: "800", color: COLORS.text, marginTop: 4 },
  statLabel: { fontSize: 9, color: COLORS.dim, textTransform: "uppercase", letterSpacing: 0.5, marginTop: 2 },

  // Section
  sectionHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: COLORS.text },
  filterRow: { flexDirection: "row", gap: 4 },
  filterBtn: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, backgroundColor: COLORS.surface },
  filterBtnActive: { backgroundColor: COLORS.accent },
  filterText: { fontSize: 10, fontWeight: "600", color: COLORS.dim },
  filterTextActive: { color: "#fff" },

  // Badges
  badgesGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 4 },
  badgeCard: {
    width: (390 - 18 * 2 - 8) / 2, flexDirection: "row", alignItems: "center", gap: 12,
    backgroundColor: COLORS.card, borderRadius: 16, padding: 14,
    borderWidth: 1, borderColor: `${COLORS.accent}25`,
  },
  badgeCardLocked: { borderColor: COLORS.border, opacity: 0.45 },
  badgeIcon: { fontSize: 28 },
  badgeInfo: { flex: 1, minWidth: 0 },
  badgeName: { fontSize: 12, fontWeight: "700", color: COLORS.text },
  badgeMeta: { fontSize: 10, color: COLORS.dim, marginTop: 2 },

  // Settings
  settingsCard: {
    backgroundColor: COLORS.card, borderRadius: 16, overflow: "hidden",
    borderWidth: 1, borderColor: COLORS.border,
  },
  settingRow: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    paddingVertical: 14, paddingHorizontal: 16,
  },
  settingBorder: { borderBottomWidth: 1, borderBottomColor: COLORS.border },
  settingLeft: { flexDirection: "row", alignItems: "center", gap: 10 },
  settingLabel: { fontSize: 14, fontWeight: "500", color: COLORS.text },
  settingChevron: { fontSize: 16, color: COLORS.dim },

  // App info
  appInfo: { alignItems: "center", marginTop: 20, paddingBottom: 20 },
  appVersion: { fontSize: 11, color: COLORS.dim },
  appCredit: { fontSize: 10, color: COLORS.dim, marginTop: 2 },
});
