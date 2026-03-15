/**
 * HabitFlow AI — Onboarding Step 0: Welcome
 */

import React, { useEffect, useRef } from "react";
import {
  View, Text, TextInput, StyleSheet, Animated,
  KeyboardAvoidingView, Platform, ScrollView,
} from "react-native";
import { COLORS } from "../../constants";
import { useOnboardingStore } from "../../hooks/useOnboardingStore";
import { LinearGradient } from "expo-linear-gradient";

export default function WelcomeScreen() {
  const { displayName, setDisplayName } = useOnboardingStore();
  const floatAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Float animation for logo
    Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, { toValue: -8, duration: 1500, useNativeDriver: true }),
        Animated.timing(floatAnim, { toValue: 0, duration: 1500, useNativeDriver: true }),
      ])
    ).start();

    // Fade in content
    Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }).start();
  }, []);

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        {/* Floating Logo */}
        <Animated.View
          style={[
            styles.logoContainer,
            { transform: [{ translateY: floatAnim }] },
          ]}
        >
          <LinearGradient
            colors={["#7C6BFF", "#00D9A6"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.logo}
          >
            <Text style={styles.logoText}>H</Text>
          </LinearGradient>
        </Animated.View>

        {/* Title */}
        <Animated.View style={{ opacity: fadeAnim }}>
          <Text style={styles.title}>Welcome to</Text>
          <Text style={styles.titleGradient}>HabitFlow AI</Text>
          <Text style={styles.subtitle}>
            Build tiny habits that stick — powered by AI that learns{" "}
            <Text style={{ fontStyle: "italic" }}>when</Text> you're most likely to succeed.
          </Text>
        </Animated.View>

        {/* Name Input */}
        <Animated.View style={[styles.inputSection, { opacity: fadeAnim }]}>
          <Text style={styles.label}>What should we call you?</Text>
          <TextInput
            value={displayName}
            onChangeText={setDisplayName}
            placeholder="Your name"
            placeholderTextColor={COLORS.dim}
            style={[
              styles.input,
              displayName.length >= 2 && styles.inputActive,
            ]}
            autoFocus
            maxLength={30}
          />
        </Animated.View>

        {/* Feature Pills */}
        <View style={styles.pillsContainer}>
          {["🧠 AI Smart Scheduling", "🔥 Streak Engine", "💬 AI Coach", "📊 Mood Insights", "👥 Buddy System"].map((text, i) => (
            <View key={i} style={styles.pill}>
              <Text style={styles.pillText}>{text}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    paddingTop: 50,
    paddingHorizontal: 22,
    alignItems: "center",
  },
  logoContainer: {
    marginBottom: 28,
    shadowColor: "#7C6BFF",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.35,
    shadowRadius: 20,
    elevation: 12,
  },
  logo: {
    width: 88,
    height: 88,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
  },
  logoText: {
    fontSize: 38,
    fontWeight: "800",
    color: "#fff",
  },
  title: {
    fontSize: 30,
    fontWeight: "800",
    color: COLORS.text,
    textAlign: "center",
    letterSpacing: -0.5,
  },
  titleGradient: {
    fontSize: 30,
    fontWeight: "800",
    textAlign: "center",
    letterSpacing: -0.5,
    color: "#7C6BFF", // Fallback — gradient text needs MaskedView in RN
  },
  subtitle: {
    fontSize: 15,
    color: COLORS.sub,
    textAlign: "center",
    lineHeight: 22,
    marginTop: 8,
    maxWidth: 300,
  },
  inputSection: {
    width: "100%",
    maxWidth: 320,
    marginTop: 40,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: COLORS.sub,
    marginBottom: 8,
  },
  input: {
    width: "100%",
    padding: 16,
    borderRadius: 16,
    backgroundColor: COLORS.surface,
    borderWidth: 1.5,
    borderColor: COLORS.border,
    color: COLORS.text,
    fontSize: 17,
    fontWeight: "600",
  },
  inputActive: {
    borderColor: "rgba(124, 107, 255, 0.4)",
  },
  pillsContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 8,
    marginTop: 32,
    paddingBottom: 120,
  },
  pill: {
    backgroundColor: COLORS.surface,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  pillText: {
    fontSize: 11,
    fontWeight: "600",
    color: COLORS.sub,
  },
});
