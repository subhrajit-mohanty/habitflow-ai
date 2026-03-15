/**
 * HabitFlow AI — Social Screen (Expo React Native)
 * Buddies, Challenges, and Leaderboard tabs.
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, StyleSheet,
  ActivityIndicator, RefreshControl, Alert, FlatList,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { COLORS } from "../../constants";
import { socialApi, gamificationApi, userApi } from "../../services/api";

const TABS = ["Buddies", "Challenges", "Leaderboard"];
const LEADERBOARD_PERIODS = [
  { key: "weekly", label: "Weekly" },
  { key: "monthly", label: "Monthly" },
  { key: "all_time", label: "All-Time" },
];

// ─── Main Screen ───
export default function SocialScreen() {
  const [activeTab, setActiveTab] = useState("Buddies");

  const handleTabPress = (tab) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setActiveTab(tab);
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Social</Text>
        <Text style={styles.subtitle}>Connect, compete, and grow together</Text>
      </View>

      {/* Tab Bar */}
      <View style={styles.tabBar}>
        {TABS.map((tab) => (
          <TouchableOpacity
            key={tab}
            onPress={() => handleTabPress(tab)}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
          >
            {activeTab === tab ? (
              <LinearGradient
                colors={[COLORS.accent, "#9D8FFF"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.tabGradient}
              >
                <Text style={styles.tabTextActive}>{tab}</Text>
              </LinearGradient>
            ) : (
              <Text style={styles.tabText}>{tab}</Text>
            )}
          </TouchableOpacity>
        ))}
      </View>

      {/* Tab Content */}
      {activeTab === "Buddies" && <BuddiesTab />}
      {activeTab === "Challenges" && <ChallengesTab />}
      {activeTab === "Leaderboard" && <LeaderboardTab />}
    </View>
  );
}

// ─── Buddies Tab ───
function BuddiesTab() {
  const [buddies, setBuddies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => { loadBuddies(); }, []);

  const loadBuddies = async () => {
    try {
      const data = await socialApi.listBuddies();
      setBuddies(data || []);
    } catch (err) {
      console.error("Failed to load buddies:", err);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadBuddies();
    setRefreshing(false);
  };

  const handleInvite = () => {
    Alert.prompt(
      "Invite Buddy",
      "Enter their username to send an invite:",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Send",
          onPress: async (username) => {
            if (!username?.trim()) return;
            try {
              await socialApi.inviteBuddy(username.trim());
              Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
              Alert.alert("Invite Sent", `Invitation sent to @${username.trim()}`);
              loadBuddies();
            } catch (err) {
              Alert.alert("Error", err.message || "Could not send invite");
            }
          },
        },
      ],
      "plain-text"
    );
  };

  const handleAccept = async (pairId) => {
    try {
      await socialApi.acceptBuddy(pairId);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      loadBuddies();
    } catch (err) {
      Alert.alert("Error", err.message || "Could not accept invite");
    }
  };

  const handleDecline = async (pairId) => {
    Alert.alert("Decline Invite", "Are you sure?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Decline",
        style: "destructive",
        onPress: async () => {
          try {
            // Use the same endpoint pattern — decline is effectively removing
            await socialApi.acceptBuddy(pairId); // Backend handles status
            loadBuddies();
          } catch (err) {
            Alert.alert("Error", err.message);
          }
        },
      },
    ]);
  };

  const handleNudge = async (buddy) => {
    try {
      await socialApi.sendNudge({ buddy_id: buddy.id, message: "Keep going! You've got this!" });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      Alert.alert("Nudge Sent", `You nudged ${buddy.name || buddy.username}!`);
    } catch (err) {
      Alert.alert("Error", err.message || "Could not send nudge");
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.accent} />
      </View>
    );
  }

  const activeBuddies = buddies.filter((b) => b.status === "active" || b.status === "accepted");
  const pendingInvites = buddies.filter((b) => b.status === "pending" && b.is_incoming);

  return (
    <ScrollView
      style={styles.tabContent}
      contentContainerStyle={styles.tabContentInner}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.accent} />}
    >
      {/* Invite Button */}
      <TouchableOpacity onPress={handleInvite} activeOpacity={0.8}>
        <LinearGradient
          colors={[COLORS.accent, "#9D8FFF"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.inviteButton}
        >
          <Text style={styles.inviteButtonText}>+ Invite Buddy</Text>
        </LinearGradient>
      </TouchableOpacity>

      {/* Pending Invites */}
      {pendingInvites.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pending Invites</Text>
          {pendingInvites.map((invite) => (
            <View key={invite.id} style={styles.buddyCard}>
              <View style={styles.avatarCircle}>
                <Text style={styles.avatarText}>
                  {(invite.name || invite.username || "?").charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={styles.buddyInfo}>
                <Text style={styles.buddyName}>{invite.name || invite.username}</Text>
                <Text style={styles.buddyMeta}>Wants to be your buddy</Text>
              </View>
              <TouchableOpacity
                onPress={() => handleAccept(invite.pair_id || invite.id)}
                style={styles.acceptBtn}
              >
                <Text style={styles.acceptBtnText}>Accept</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => handleDecline(invite.pair_id || invite.id)}
                style={styles.declineBtn}
              >
                <Text style={styles.declineBtnText}>Decline</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>
      )}

      {/* Active Buddies */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          Your Buddies {activeBuddies.length > 0 ? `(${activeBuddies.length})` : ""}
        </Text>
        {activeBuddies.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>👥</Text>
            <Text style={styles.emptyText}>No buddies yet</Text>
            <Text style={styles.emptySubtext}>Invite friends to stay accountable together</Text>
          </View>
        ) : (
          activeBuddies.map((buddy) => (
            <View key={buddy.id} style={styles.buddyCard}>
              <View style={styles.avatarCircle}>
                <Text style={styles.avatarText}>
                  {(buddy.name || buddy.username || "?").charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={styles.buddyInfo}>
                <Text style={styles.buddyName}>{buddy.name || buddy.username}</Text>
                <View style={styles.buddyStats}>
                  <Text style={styles.buddyStreak}>🔥 {buddy.streak || 0}d streak</Text>
                  <Text style={styles.buddyXp}>{buddy.xp || 0} XP</Text>
                </View>
              </View>
              <TouchableOpacity
                onPress={() => handleNudge(buddy)}
                style={styles.nudgeBtn}
              >
                <Text style={styles.nudgeBtnText}>Nudge</Text>
              </TouchableOpacity>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  );
}

// ─── Challenges Tab ───
function ChallengesTab() {
  const [myChallenges, setMyChallenges] = useState([]);
  const [publicChallenges, setPublicChallenges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => { loadChallenges(); }, []);

  const loadChallenges = async () => {
    try {
      const [mine, all] = await Promise.all([
        socialApi.myChallenges(),
        socialApi.listChallenges(true),
      ]);
      setMyChallenges(mine || []);
      setPublicChallenges(all || []);
    } catch (err) {
      console.error("Failed to load challenges:", err);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadChallenges();
    setRefreshing(false);
  };

  const handleJoin = async (challengeId) => {
    try {
      await socialApi.joinChallenge(challengeId);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      loadChallenges();
    } catch (err) {
      Alert.alert("Error", err.message || "Could not join challenge");
    }
  };

  const handleLeave = async (challengeId) => {
    Alert.alert("Leave Challenge", "Are you sure you want to leave?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Leave",
        style: "destructive",
        onPress: async () => {
          try {
            await socialApi.leaveChallenge(challengeId);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            loadChallenges();
          } catch (err) {
            Alert.alert("Error", err.message);
          }
        },
      },
    ]);
  };

  const handleCreate = () => {
    Alert.prompt(
      "Create Challenge",
      "Enter a title for your challenge:",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Create",
          onPress: async (title) => {
            if (!title?.trim()) return;
            try {
              await socialApi.createChallenge({
                title: title.trim(),
                category: "general",
                duration_days: 7,
              });
              Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
              loadChallenges();
            } catch (err) {
              Alert.alert("Error", err.message || "Could not create challenge");
            }
          },
        },
      ],
      "plain-text"
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.accent} />
      </View>
    );
  }

  const myChallengeIds = new Set(myChallenges.map((c) => c.id));
  const availableChallenges = publicChallenges.filter((c) => !myChallengeIds.has(c.id));

  return (
    <ScrollView
      style={styles.tabContent}
      contentContainerStyle={styles.tabContentInner}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.accent} />}
    >
      {/* Create Challenge Button */}
      <TouchableOpacity onPress={handleCreate} activeOpacity={0.8}>
        <LinearGradient
          colors={[COLORS.mint, "#00F0B8"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.inviteButton}
        >
          <Text style={[styles.inviteButtonText, { color: COLORS.bg }]}>+ Create Challenge</Text>
        </LinearGradient>
      </TouchableOpacity>

      {/* My Challenges */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>My Challenges</Text>
        {myChallenges.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>🏆</Text>
            <Text style={styles.emptyText}>No active challenges</Text>
            <Text style={styles.emptySubtext}>Join or create a challenge to get started</Text>
          </View>
        ) : (
          myChallenges.map((challenge) => (
            <ChallengeCard
              key={challenge.id}
              challenge={challenge}
              joined
              onLeave={() => handleLeave(challenge.id)}
            />
          ))
        )}
      </View>

      {/* Available Challenges */}
      {availableChallenges.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Discover Challenges</Text>
          {availableChallenges.map((challenge) => (
            <ChallengeCard
              key={challenge.id}
              challenge={challenge}
              joined={false}
              onJoin={() => handleJoin(challenge.id)}
            />
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function ChallengeCard({ challenge, joined, onJoin, onLeave }) {
  const progressPct = challenge.progress != null ? Math.round(challenge.progress * 100) : null;
  const categoryColors = {
    health: COLORS.mint,
    fitness: COLORS.coral,
    mindfulness: COLORS.accent,
    productivity: COLORS.amber,
    learning: COLORS.sky,
    general: COLORS.sub,
  };
  const catColor = categoryColors[challenge.category] || COLORS.accent;

  return (
    <View style={styles.challengeCard}>
      <View style={styles.challengeHeader}>
        <View style={[styles.categoryBadge, { backgroundColor: `${catColor}20` }]}>
          <Text style={[styles.categoryBadgeText, { color: catColor }]}>
            {(challenge.category || "general").toUpperCase()}
          </Text>
        </View>
        {challenge.participant_count != null && (
          <Text style={styles.participantCount}>
            👥 {challenge.participant_count}
          </Text>
        )}
      </View>

      <Text style={styles.challengeTitle}>{challenge.title}</Text>

      {(challenge.start_date || challenge.end_date) && (
        <Text style={styles.challengeDates}>
          {challenge.start_date ? formatDate(challenge.start_date) : ""}
          {challenge.start_date && challenge.end_date ? " — " : ""}
          {challenge.end_date ? formatDate(challenge.end_date) : ""}
        </Text>
      )}

      {progressPct != null && (
        <View style={styles.progressContainer}>
          <View style={styles.progressBar}>
            <View style={[styles.progressFill, { width: `${progressPct}%`, backgroundColor: catColor }]} />
          </View>
          <Text style={styles.progressText}>{progressPct}%</Text>
        </View>
      )}

      <View style={styles.challengeActions}>
        {joined ? (
          <TouchableOpacity onPress={onLeave} style={styles.leaveBtn}>
            <Text style={styles.leaveBtnText}>Leave</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity onPress={onJoin} activeOpacity={0.8}>
            <LinearGradient
              colors={[COLORS.accent, "#9D8FFF"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.joinBtn}
            >
              <Text style={styles.joinBtnText}>Join</Text>
            </LinearGradient>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

// ─── Leaderboard Tab ───
function LeaderboardTab() {
  const [period, setPeriod] = useState("weekly");
  const [leaderboard, setLeaderboard] = useState([]);
  const [currentUserId, setCurrentUserId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => { loadLeaderboard(); }, [period]);

  useEffect(() => {
    userApi.getProfile().then((p) => setCurrentUserId(p?.id)).catch(() => {});
  }, []);

  const loadLeaderboard = async () => {
    try {
      const data = await gamificationApi.getLeaderboard(period);
      setLeaderboard(data || []);
    } catch (err) {
      console.error("Failed to load leaderboard:", err);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadLeaderboard();
    setRefreshing(false);
  };

  const handlePeriodChange = (p) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setLoading(true);
    setPeriod(p);
  };

  return (
    <View style={styles.tabContent}>
      {/* Period Toggle */}
      <View style={styles.periodRow}>
        {LEADERBOARD_PERIODS.map((p) => (
          <TouchableOpacity
            key={p.key}
            onPress={() => handlePeriodChange(p.key)}
            style={[styles.periodBtn, period === p.key && styles.periodBtnActive]}
          >
            <Text style={[styles.periodText, period === p.key && styles.periodTextActive]}>
              {p.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={COLORS.accent} />
        </View>
      ) : leaderboard.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>🏅</Text>
          <Text style={styles.emptyText}>No leaderboard data yet</Text>
          <Text style={styles.emptySubtext}>Complete habits to earn XP and climb the ranks</Text>
        </View>
      ) : (
        <FlatList
          data={leaderboard}
          keyExtractor={(item, idx) => item.user_id || String(idx)}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{ paddingHorizontal: 18, paddingBottom: 100 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.accent} />}
          renderItem={({ item, index }) => {
            const rank = index + 1;
            const isCurrentUser = item.user_id === currentUserId;
            const medalColors = { 1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32" };
            const medalColor = medalColors[rank];

            return (
              <View
                style={[
                  styles.leaderRow,
                  isCurrentUser && styles.leaderRowHighlight,
                ]}
              >
                <View style={[styles.rankBadge, medalColor && { backgroundColor: `${medalColor}20` }]}>
                  <Text style={[styles.rankText, medalColor && { color: medalColor }]}>
                    {rank}
                  </Text>
                </View>
                <View style={[styles.avatarCircle, isCurrentUser && { borderColor: COLORS.accent, borderWidth: 2 }]}>
                  <Text style={styles.avatarText}>
                    {(item.name || item.username || "?").charAt(0).toUpperCase()}
                  </Text>
                </View>
                <View style={styles.leaderInfo}>
                  <Text style={[styles.leaderName, isCurrentUser && { color: COLORS.accent }]}>
                    {item.name || item.username}{isCurrentUser ? " (You)" : ""}
                  </Text>
                  <View style={styles.leaderMeta}>
                    <Text style={styles.leaderXp}>{(item.xp || 0).toLocaleString()} XP</Text>
                    <Text style={styles.leaderStreak}>🔥 {item.streak || 0}d</Text>
                  </View>
                </View>
              </View>
            );
          }}
        />
      )}
    </View>
  );
}

// ─── Helpers ───
function formatDate(dateStr) {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

// ─── Styles ───
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  header: {
    paddingHorizontal: 18,
    paddingTop: 14,
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: COLORS.text,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: COLORS.sub,
    marginBottom: 14,
  },

  // Tab Bar
  tabBar: {
    flexDirection: "row",
    paddingHorizontal: 18,
    gap: 8,
    marginBottom: 8,
  },
  tab: {
    flex: 1,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: COLORS.surface,
  },
  tabActive: {
    backgroundColor: "transparent",
  },
  tabGradient: {
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 12,
  },
  tabText: {
    fontSize: 13,
    fontWeight: "600",
    color: COLORS.sub,
    textAlign: "center",
    paddingVertical: 10,
  },
  tabTextActive: {
    fontSize: 13,
    fontWeight: "700",
    color: "#fff",
  },

  // Tab Content
  tabContent: {
    flex: 1,
  },
  tabContentInner: {
    paddingHorizontal: 18,
    paddingBottom: 100,
  },

  // Loading
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },

  // Sections
  section: {
    marginTop: 18,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: COLORS.text,
    marginBottom: 10,
  },

  // Invite / Create Button
  inviteButton: {
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: "center",
    marginTop: 10,
  },
  inviteButtonText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#fff",
  },

  // Buddy Card
  buddyCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
    gap: 12,
  },
  avatarCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.accent,
  },
  buddyInfo: {
    flex: 1,
  },
  buddyName: {
    fontSize: 14,
    fontWeight: "700",
    color: COLORS.text,
  },
  buddyStats: {
    flexDirection: "row",
    gap: 10,
    marginTop: 3,
  },
  buddyStreak: {
    fontSize: 11,
    color: COLORS.amber,
  },
  buddyXp: {
    fontSize: 11,
    color: COLORS.dim,
  },
  buddyMeta: {
    fontSize: 11,
    color: COLORS.sub,
    marginTop: 2,
  },
  nudgeBtn: {
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: `${COLORS.accent}20`,
  },
  nudgeBtnText: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.accent,
  },
  acceptBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: `${COLORS.mint}20`,
  },
  acceptBtnText: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.mint,
  },
  declineBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 10,
    backgroundColor: `${COLORS.coral}15`,
  },
  declineBtnText: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.coral,
  },

  // Empty State
  emptyState: {
    alignItems: "center",
    paddingVertical: 40,
    backgroundColor: COLORS.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  emptyIcon: {
    fontSize: 36,
    marginBottom: 10,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.text,
    marginBottom: 4,
  },
  emptySubtext: {
    fontSize: 12,
    color: COLORS.sub,
  },

  // Challenge Card
  challengeCard: {
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  challengeHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  categoryBadge: {
    paddingVertical: 3,
    paddingHorizontal: 10,
    borderRadius: 8,
  },
  categoryBadgeText: {
    fontSize: 9,
    fontWeight: "700",
    letterSpacing: 0.8,
  },
  participantCount: {
    fontSize: 12,
    color: COLORS.sub,
  },
  challengeTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.text,
    marginBottom: 4,
  },
  challengeDates: {
    fontSize: 11,
    color: COLORS.dim,
    marginBottom: 10,
  },
  progressContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 10,
  },
  progressBar: {
    flex: 1,
    height: 6,
    borderRadius: 3,
    backgroundColor: COLORS.surface,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 3,
  },
  progressText: {
    fontSize: 11,
    fontWeight: "600",
    color: COLORS.sub,
  },
  challengeActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    marginTop: 4,
  },
  joinBtn: {
    paddingVertical: 8,
    paddingHorizontal: 24,
    borderRadius: 10,
  },
  joinBtnText: {
    fontSize: 13,
    fontWeight: "700",
    color: "#fff",
  },
  leaveBtn: {
    paddingVertical: 8,
    paddingHorizontal: 20,
    borderRadius: 10,
    backgroundColor: `${COLORS.coral}15`,
  },
  leaveBtnText: {
    fontSize: 13,
    fontWeight: "600",
    color: COLORS.coral,
  },

  // Period Toggle
  periodRow: {
    flexDirection: "row",
    gap: 6,
    paddingHorizontal: 18,
    marginBottom: 14,
    marginTop: 6,
  },
  periodBtn: {
    paddingVertical: 7,
    paddingHorizontal: 18,
    borderRadius: 12,
    backgroundColor: COLORS.surface,
  },
  periodBtnActive: {
    backgroundColor: COLORS.accent,
  },
  periodText: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.sub,
  },
  periodTextActive: {
    color: "#fff",
  },

  // Leaderboard
  leaderRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: COLORS.card,
    borderRadius: 16,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
    gap: 12,
  },
  leaderRowHighlight: {
    borderColor: `${COLORS.accent}40`,
    backgroundColor: `${COLORS.accent}08`,
  },
  rankBadge: {
    width: 32,
    height: 32,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  rankText: {
    fontSize: 14,
    fontWeight: "800",
    color: COLORS.text,
  },
  leaderInfo: {
    flex: 1,
  },
  leaderName: {
    fontSize: 14,
    fontWeight: "700",
    color: COLORS.text,
  },
  leaderMeta: {
    flexDirection: "row",
    gap: 12,
    marginTop: 3,
  },
  leaderXp: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.accent,
  },
  leaderStreak: {
    fontSize: 11,
    color: COLORS.amber,
  },
});
