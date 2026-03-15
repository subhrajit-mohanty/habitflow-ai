/**
 * HabitFlow AI — Coach Chat Screen (Expo React Native)
 * Production implementation with Claude API, typing indicators,
 * context cards, quick prompts, and conversation management.
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, Animated, KeyboardAvoidingView, Platform,
  ActivityIndicator, Keyboard, Dimensions, Alert,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { COLORS } from "../../constants";
import { coachApi, habitsApi, dailyLogsApi, gamificationApi } from "../../services/api";

const CONVERSATION_KEY = "habitflow_coach_conversation_id";

const { width: SCREEN_W } = Dimensions.get("window");

// ───────────────────────────────────
// Quick Prompt Suggestions
// ───────────────────────────────────
const QUICK_PROMPTS = [
  { icon: "📊", label: "Weekly review", prompt: "Can you give me a review of how my habits went this week?" },
  { icon: "💡", label: "Suggest habits", prompt: "Based on my goals and patterns, what new micro-habits would you suggest?" },
  { icon: "😤", label: "I keep skipping...", prompt: "I keep skipping some of my habits. What should I do?" },
  { icon: "🧪", label: "Habit stacking", prompt: "Help me create a morning habit stack with my existing habits." },
  { icon: "📈", label: "My best times", prompt: "When am I most productive? What do my patterns say?" },
  { icon: "🎯", label: "Motivation", prompt: "I'm feeling unmotivated today. Can you help me get back on track?" },
];

// ───────────────────────────────────
// Main Component
// ───────────────────────────────────
export default function CoachChatScreen() {
  // State
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [userContext, setUserContext] = useState(null);
  const [isLoadingContext, setIsLoadingContext] = useState(true);
  const [error, setError] = useState(null);

  // Refs
  const flatListRef = useRef(null);
  const inputRef = useRef(null);
  const typingDots = useRef([
    new Animated.Value(0),
    new Animated.Value(0),
    new Animated.Value(0),
  ]).current;

  // ─── Load persisted conversation and user context on mount ───
  useEffect(() => {
    (async () => {
      try {
        const savedConvId = await AsyncStorage.getItem(CONVERSATION_KEY);
        if (savedConvId) setConversationId(savedConvId);
      } catch {}
      loadUserContext();
    })();
  }, []);

  const loadUserContext = async () => {
    try {
      const [todayHabits, levelInfo] = await Promise.all([
        habitsApi.getToday(),
        gamificationApi.getLevelInfo(),
      ]);

      const completed = todayHabits.filter((h) => h.is_completed_today).length;
      const total = todayHabits.length;
      const habits = todayHabits.map((h) => ({
        name: h.habit.name,
        icon: h.habit.icon,
        streak: h.habit.current_streak,
        rate: Math.round((h.habit.completion_rate || 0) * 100),
        done: h.is_completed_today,
      }));

      setUserContext({
        habits,
        completed,
        total,
        level: levelInfo.current_level,
        xp: levelInfo.total_xp,
      });

      // Generate welcome message
      const welcomeMsg = {
        id: "welcome",
        role: "assistant",
        content: `Hey! 👋 You've done ${completed} of ${total} habits today. How can I help you stay on track?`,
        timestamp: new Date(),
      };
      setMessages([welcomeMsg]);
    } catch (err) {
      console.warn("Context load error:", err);
      // Fallback welcome
      setMessages([{
        id: "welcome",
        role: "assistant",
        content: "Hey! 👋 I'm your AI habit coach. How can I help you today?",
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoadingContext(false);
    }
  };

  // ─── Typing animation ───
  useEffect(() => {
    if (!isTyping) return;

    const animations = typingDots.map((dot, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(dot, { toValue: -3, duration: 300, delay: i * 150, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0, duration: 300, useNativeDriver: true }),
        ])
      )
    );
    animations.forEach((a) => a.start());
    return () => animations.forEach((a) => a.stop());
  }, [isTyping]);

  // ─── Send message ───
  const sendMessage = useCallback(async (text) => {
    const msg = text || input.trim();
    if (!msg || isTyping) return;

    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    Keyboard.dismiss();

    const userMsg = {
      id: `user-${Date.now()}`,
      role: "user",
      content: msg,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);
    setError(null);

    try {
      const response = await coachApi.chat({
        conversation_id: conversationId,
        message: msg,
      });

      if (!conversationId) {
        setConversationId(response.conversation_id);
        AsyncStorage.setItem(CONVERSATION_KEY, response.conversation_id).catch(() => {});
      }

      const aiMsg = {
        id: response.message_id || `ai-${Date.now()}`,
        role: "assistant",
        content: response.content,
        timestamp: new Date(response.created_at || Date.now()),
        tokens: response.tokens_used,
      };

      setMessages((prev) => [...prev, aiMsg]);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch (err) {
      const isQuotaError = err.message?.includes("quota exceeded") || err.message?.includes("429");
      if (isQuotaError) {
        Alert.alert(
          "Free AI Limit Reached",
          "The free AI quota has been exceeded. Add your own API key via OpenRouter to continue chatting with 100+ AI models (many are free!).",
          [
            { text: "Later", style: "cancel" },
            { text: "Add Key", onPress: () => {
              // Navigate to profile — user can add key there
              Alert.alert("Go to Profile", "Head to Profile → AI Coach to add your OpenRouter key.");
            }},
          ]
        );
      }
      setError(err.message);
    } finally {
      setIsTyping(false);
    }
  }, [input, isTyping, conversationId]);

  // ─── Scroll to bottom ───
  const scrollToBottom = () => {
    setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // ─── Render message bubble ───
  const renderMessage = ({ item: msg }) => {
    const isUser = msg.role === "user";
    return (
      <View style={[styles.msgRow, isUser && styles.msgRowUser]}>
        {!isUser && (
          <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.aiAvatar}>
            <Text style={styles.aiAvatarText}>H</Text>
          </LinearGradient>
        )}
        <View style={[
          styles.bubble,
          isUser ? styles.userBubble : styles.aiBubble,
        ]}>
          <Text style={[styles.msgText, isUser && styles.userMsgText]}>
            {formatCoachText(msg.content)}
          </Text>
          <Text style={[styles.timestamp, isUser && styles.userTimestamp]}>
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </Text>
        </View>
      </View>
    );
  };

  // ─── Typing indicator ───
  const renderTypingIndicator = () => (
    <View style={styles.msgRow}>
      <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.aiAvatar}>
        <Text style={styles.aiAvatarText}>H</Text>
      </LinearGradient>
      <View style={[styles.bubble, styles.aiBubble, styles.typingBubble]}>
        <View style={styles.typingDots}>
          {typingDots.map((dot, i) => (
            <Animated.View
              key={i}
              style={[
                styles.typingDot,
                { transform: [{ translateY: dot }] },
              ]}
            />
          ))}
        </View>
      </View>
    </View>
  );

  // ─── Context Card ───
  const renderContextCard = () => {
    if (!userContext || messages.length > 2) return null;
    return (
      <View style={styles.contextCard}>
        <LinearGradient
          colors={[`${COLORS.accent}12`, `${COLORS.mint}08`]}
          style={styles.contextGradient}
        >
          <View style={styles.contextHeader}>
            <Text style={styles.contextTitle}>YOUR CONTEXT TODAY</Text>
            <Text style={styles.contextStat}>
              {userContext.completed}/{userContext.total} done
            </Text>
          </View>
          <View style={styles.contextChips}>
            {userContext.habits.slice(0, 5).map((h, i) => (
              <View key={i} style={[
                styles.contextChip,
                { backgroundColor: h.rate >= 80 ? `${COLORS.mint}15` : h.rate >= 60 ? "#FFBE5C15" : `${COLORS.coral}15` },
              ]}>
                <Text style={[
                  styles.contextChipText,
                  { color: h.rate >= 80 ? COLORS.mint : h.rate >= 60 ? "#FFBE5C" : COLORS.coral },
                ]}>{h.icon} {h.streak}d</Text>
              </View>
            ))}
          </View>
          <View style={styles.contextMeta}>
            <Text style={styles.contextMetaText}>⚡ Level {userContext.level}</Text>
            <Text style={styles.contextMetaText}>✨ {userContext.xp} XP</Text>
          </View>
        </LinearGradient>
      </View>
    );
  };

  // ─── Quick Prompts ───
  const renderQuickPrompts = () => {
    if (messages.length > 2 || isTyping) return null;
    return (
      <View style={styles.quickPrompts}>
        <FlatList
          data={QUICK_PROMPTS}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={(_, i) => `qp-${i}`}
          contentContainerStyle={styles.quickPromptsContent}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.quickPromptChip}
              onPress={() => sendMessage(item.prompt)}
              activeOpacity={0.7}
            >
              <Text style={styles.quickPromptIcon}>{item.icon}</Text>
              <Text style={styles.quickPromptLabel}>{item.label}</Text>
            </TouchableOpacity>
          )}
        />
      </View>
    );
  };

  // ─── Loading state ───
  if (isLoadingContext) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.accent} />
        <Text style={styles.loadingText}>Preparing your coach...</Text>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
    >
      {/* Header */}
      <View style={styles.header}>
        <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.headerAvatar}>
          <Text style={styles.headerAvatarText}>H</Text>
        </LinearGradient>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>HabitFlow Coach</Text>
          <View style={styles.headerStatus}>
            <View style={styles.statusDot} />
            <Text style={styles.statusText}>Online</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.headerBtn}>
          <Text style={styles.headerBtnText}>☰</Text>
        </TouchableOpacity>
      </View>

      {/* Context Card */}
      {renderContextCard()}

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.messagesList}
        showsVerticalScrollIndicator={false}
        ListFooterComponent={isTyping ? renderTypingIndicator : null}
        onContentSizeChange={scrollToBottom}
      />

      {/* Quick Prompts */}
      {renderQuickPrompts()}

      {/* Input Bar */}
      <View style={styles.inputBar}>
        <View style={styles.inputContainer}>
          <TextInput
            ref={inputRef}
            value={input}
            onChangeText={setInput}
            placeholder="Ask your coach anything..."
            placeholderTextColor={COLORS.dim}
            style={styles.input}
            multiline
            maxLength={2000}
            returnKeyType="send"
            blurOnSubmit={false}
            onSubmitEditing={() => sendMessage()}
          />
          <TouchableOpacity
            onPress={() => sendMessage()}
            disabled={!input.trim() || isTyping}
            activeOpacity={0.7}
          >
            {input.trim() && !isTyping ? (
              <LinearGradient colors={["#7C6BFF", "#00D9A6"]} style={styles.sendBtn}>
                <Text style={styles.sendBtnText}>↑</Text>
              </LinearGradient>
            ) : (
              <View style={[styles.sendBtn, styles.sendBtnDisabled]}>
                <Text style={[styles.sendBtnText, { color: COLORS.dim }]}>↑</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

      </View>
    </KeyboardAvoidingView>
  );
}

// ───────────────────────────────────
// Text formatting (bold markdown)
// ───────────────────────────────────
function formatCoachText(text) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <Text key={i} style={{ fontWeight: "700", color: COLORS.text }}>
          {part.slice(2, -2)}
        </Text>
      );
    }
    return <Text key={i}>{part}</Text>;
  });
}

// ───────────────────────────────────
// Styles
// ───────────────────────────────────
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: COLORS.bg,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    color: COLORS.sub,
    fontSize: 14,
    marginTop: 12,
  },

  // Header
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
    backgroundColor: "rgba(17,17,24,0.95)",
  },
  headerAvatar: {
    width: 40,
    height: 40,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  headerAvatarText: { fontSize: 18, fontWeight: "800", color: "#fff" },
  headerInfo: { flex: 1, marginLeft: 12 },
  headerTitle: { fontSize: 15, fontWeight: "700", color: COLORS.text },
  headerStatus: { flexDirection: "row", alignItems: "center", gap: 5, marginTop: 2 },
  statusDot: {
    width: 6, height: 6, borderRadius: 3,
    backgroundColor: COLORS.mint,
  },
  statusText: { fontSize: 11, color: COLORS.mint, fontWeight: "600" },
  headerBtn: {
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  headerBtnText: { color: COLORS.sub, fontSize: 14 },

  // Context Card
  contextCard: { paddingHorizontal: 18, paddingTop: 12 },
  contextGradient: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: `${COLORS.accent}18`,
  },
  contextHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  contextTitle: { fontSize: 11, fontWeight: "700", color: COLORS.accent, letterSpacing: 1 },
  contextStat: { fontSize: 11, color: COLORS.dim },
  contextChips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  contextChip: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  contextChipText: { fontSize: 10, fontWeight: "600" },
  contextMeta: { flexDirection: "row", gap: 16, marginTop: 10 },
  contextMetaText: { fontSize: 11, color: COLORS.sub },

  // Messages
  messagesList: {
    paddingHorizontal: 18,
    paddingVertical: 16,
    gap: 14,
  },
  msgRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    marginBottom: 14,
  },
  msgRowUser: {
    justifyContent: "flex-end",
  },
  aiAvatar: {
    width: 30,
    height: 30,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 8,
  },
  aiAvatarText: { fontSize: 12, fontWeight: "800", color: "#fff" },
  bubble: {
    maxWidth: SCREEN_W * 0.78,
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  userBubble: {
    backgroundColor: COLORS.accent,
    borderBottomRightRadius: 6,
    shadowColor: COLORS.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  aiBubble: {
    backgroundColor: "#13131C",
    borderWidth: 1,
    borderColor: COLORS.border,
    borderBottomLeftRadius: 6,
  },
  msgText: {
    fontSize: 13.5,
    lineHeight: 21,
    color: COLORS.text,
  },
  userMsgText: {
    color: "#fff",
  },
  timestamp: {
    fontSize: 9,
    color: COLORS.dim,
    marginTop: 6,
    textAlign: "right",
  },
  userTimestamp: {
    color: "rgba(255,255,255,0.5)",
  },

  // Typing
  typingBubble: { paddingVertical: 16, paddingHorizontal: 20 },
  typingDots: { flexDirection: "row", gap: 4 },
  typingDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: COLORS.accent,
  },

  // Quick Prompts
  quickPrompts: {
    paddingBottom: 4,
  },
  quickPromptsContent: {
    paddingHorizontal: 18,
    gap: 6,
  },
  quickPromptChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  quickPromptIcon: { fontSize: 14 },
  quickPromptLabel: { fontSize: 12, fontWeight: "600", color: COLORS.sub },

  // Input Bar
  inputBar: {
    paddingHorizontal: 14,
    paddingBottom: Platform.OS === "ios" ? 28 : 16,
    paddingTop: 10,
    backgroundColor: COLORS.bg,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "flex-end",
    backgroundColor: COLORS.card,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
    gap: 10,
  },
  input: {
    flex: 1,
    color: COLORS.text,
    fontSize: 14,
    maxHeight: 80,
    paddingVertical: 6,
    lineHeight: 20,
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnDisabled: {
    backgroundColor: COLORS.surface,
  },
  sendBtnText: {
    fontSize: 18,
    fontWeight: "700",
    color: "#fff",
  },

});
