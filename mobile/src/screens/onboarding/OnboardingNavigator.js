/**
 * HabitFlow AI — Onboarding Navigator
 * Wraps all onboarding steps with progress bar, navigation, and CTA.
 */

import React, { useRef, useEffect } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet,
  Animated, SafeAreaView, Dimensions,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { COLORS } from "../../constants";
import { useOnboardingStore } from "../../hooks/useOnboardingStore";

// Screens
import WelcomeScreen from "./WelcomeScreen";
import {
  GoalsScreen,
  HabitPickerScreen,
  ScheduleScreen,
  NotificationsScreen,
  ReadyScreen,
} from "./OnboardingScreens";

const { width: SCREEN_WIDTH } = Dimensions.get("window");

export default function OnboardingNavigator({ onComplete }) {
  const store = useOnboardingStore();
  const slideAnim = useRef(new Animated.Value(0)).current;
  const prevStep = useRef(0);

  // Animate slide on step change
  useEffect(() => {
    const direction = store.currentStep > prevStep.current ? 1 : -1;
    slideAnim.setValue(direction * 40);
    Animated.spring(slideAnim, {
      toValue: 0,
      friction: 20,
      tension: 100,
      useNativeDriver: true,
    }).start();
    prevStep.current = store.currentStep;
  }, [store.currentStep]);

  // Navigate to main app when onboarding completes
  useEffect(() => {
    if (store.isComplete) {
      onComplete?.();
    }
  }, [store.isComplete]);

  const handleNext = () => {
    if (store.currentStep === store.totalSteps - 1) {
      // Final step — submit
      store.submitOnboarding();
    } else {
      store.nextStep();
    }
  };

  const renderStep = () => {
    switch (store.currentStep) {
      case 0: return <WelcomeScreen />;
      case 1: return <GoalsScreen />;
      case 2: return <HabitPickerScreen />;
      case 3: return <ScheduleScreen />;
      case 4: return <NotificationsScreen onNext={store.nextStep} />;
      case 5: return <ReadyScreen />;
      default: return null;
    }
  };

  // Notifications step handles its own CTA
  const showBottomCTA = store.currentStep <= 3;

  return (
    <SafeAreaView style={styles.container}>
      {/* ─── Top Bar: Back + Progress ─── */}
      {store.currentStep > 0 && store.currentStep < 5 && (
        <View style={styles.topBar}>
          <TouchableOpacity onPress={store.prevStep} style={styles.backBtn}>
            <Text style={styles.backIcon}>‹</Text>
          </TouchableOpacity>

          <View style={styles.progressBar}>
            {Array.from({ length: store.totalSteps - 1 }, (_, i) => (
              <View key={i} style={styles.progressSegment}>
                {i < store.currentStep ? (
                  <LinearGradient
                    colors={["#7C6BFF", "#00D9A6"]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.progressFill}
                  />
                ) : (
                  <View style={styles.progressEmpty} />
                )}
              </View>
            ))}
          </View>

          <Text style={styles.stepCounter}>
            {store.currentStep}/{store.totalSteps - 1}
          </Text>
        </View>
      )}

      {/* ─── Step Content (animated) ─── */}
      <Animated.View
        style={[
          styles.contentContainer,
          { transform: [{ translateX: slideAnim }] },
        ]}
      >
        {renderStep()}
      </Animated.View>

      {/* ─── Bottom CTA ─── */}
      {showBottomCTA && (
        <View style={styles.bottomBar}>
          <TouchableOpacity
            onPress={handleNext}
            disabled={!store.canProceed()}
            activeOpacity={0.8}
          >
            {store.canProceed() ? (
              <LinearGradient
                colors={["#7C6BFF", "#00D9A6"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={[styles.ctaButton, { opacity: 1 }]}
              >
                <Text style={styles.ctaText}>
                  {store.currentStep === 0 ? "Let's Go" : "Continue"}
                </Text>
              </LinearGradient>
            ) : (
              <View style={[styles.ctaButton, styles.ctaDisabled]}>
                <Text style={[styles.ctaText, { color: COLORS.dim }]}>
                  {store.currentStep === 0 ? "Let's Go" : "Continue"}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bg,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 8,
    gap: 14,
  },
  backBtn: {
    padding: 4,
  },
  backIcon: {
    fontSize: 28,
    color: COLORS.sub,
    lineHeight: 28,
  },
  progressBar: {
    flex: 1,
    flexDirection: "row",
    gap: 4,
  },
  progressSegment: {
    flex: 1,
    height: 3,
    borderRadius: 2,
    overflow: "hidden",
  },
  progressFill: {
    flex: 1,
    borderRadius: 2,
  },
  progressEmpty: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: 2,
  },
  stepCounter: {
    fontSize: 12,
    color: COLORS.dim,
    fontWeight: "600",
    minWidth: 30,
    textAlign: "right",
  },
  contentContainer: {
    flex: 1,
  },
  bottomBar: {
    paddingHorizontal: 22,
    paddingBottom: 36,
    paddingTop: 16,
    backgroundColor: COLORS.bg,
  },
  ctaButton: {
    padding: 16,
    borderRadius: 16,
    alignItems: "center",
    shadowColor: "#7C6BFF",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 6,
  },
  ctaDisabled: {
    backgroundColor: COLORS.surface,
    shadowOpacity: 0,
    elevation: 0,
  },
  ctaText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#fff",
  },
});
