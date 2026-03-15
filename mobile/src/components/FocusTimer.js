/**
 * HabitFlow AI — Focus Timer Component
 * A full-screen modal with circular countdown for timed habits
 * like meditation, reading, or exercise.
 */

import React, { useState, useEffect, useRef } from "react";
import {
  View, Text, TouchableOpacity, Modal, StyleSheet, Animated, Dimensions,
} from "react-native";
import Svg, { Circle, Defs, LinearGradient as SvgGrad, Stop } from "react-native-svg";
import * as Haptics from "expo-haptics";
import { COLORS } from "../constants";

const { width: SCREEN_W } = Dimensions.get("window");
const RING_SIZE = 180;
const RING_RADIUS = 78;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;
const STROKE_WIDTH = 8;

export default function FocusTimer({ visible, habit, onComplete, onClose }) {
  const totalSeconds = (habit?.duration_minutes || 1) * 60;

  const [secondsLeft, setSecondsLeft] = useState(totalSeconds);
  const [isRunning, setIsRunning] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const intervalRef = useRef(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const completionScale = useRef(new Animated.Value(0)).current;
  const completionOpacity = useRef(new Animated.Value(0)).current;

  // Reset state when habit changes or modal opens
  useEffect(() => {
    if (visible && habit) {
      const secs = (habit.duration_minutes || 1) * 60;
      setSecondsLeft(secs);
      setIsRunning(false);
      setIsFinished(false);
      completionScale.setValue(0);
      completionOpacity.setValue(0);
    }
  }, [visible, habit?.id]);

  // Countdown interval
  useEffect(() => {
    if (isRunning && secondsLeft > 0) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft((prev) => {
          if (prev <= 1) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
            setIsRunning(false);
            setIsFinished(true);
            handleFinished();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isRunning]);

  // Pulse animation while running
  useEffect(() => {
    if (isRunning) {
      const loop = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.04,
            duration: 1200,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 1200,
            useNativeDriver: true,
          }),
        ])
      );
      loop.start();
      return () => loop.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isRunning]);

  const handleFinished = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

    completionOpacity.setValue(1);
    completionScale.setValue(0);
    Animated.spring(completionScale, {
      toValue: 1,
      friction: 4,
      tension: 50,
      useNativeDriver: true,
    }).start();

    // Auto-complete after brief celebration
    setTimeout(() => {
      if (onComplete && habit) {
        onComplete(habit.id);
      }
    }, 1800);
  };

  const handlePlayPause = () => {
    if (isFinished) return;

    if (!isRunning) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } else {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }

    setIsRunning(!isRunning);
  };

  const handleDone = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsRunning(false);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    if (onComplete && habit) {
      onComplete(habit.id);
    }
  };

  const handleSkip = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsRunning(false);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    if (onComplete && habit) {
      onComplete(habit.id);
    }
  };

  const handleClose = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsRunning(false);
    if (onClose) onClose();
  };

  // Format seconds as MM:SS
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const timeDisplay = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

  // Progress: 0 (just started) to 1 (complete)
  const elapsed = totalSeconds - secondsLeft;
  const progress = totalSeconds > 0 ? elapsed / totalSeconds : 0;
  const strokeDashoffset = RING_CIRCUMFERENCE * (1 - progress);

  if (!habit) return null;

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        {/* Close button */}
        <TouchableOpacity style={styles.closeBtn} onPress={handleClose} activeOpacity={0.7}>
          <Text style={styles.closeBtnText}>✕</Text>
        </TouchableOpacity>

        {/* Habit info */}
        <Text style={styles.habitIcon}>{habit.icon}</Text>
        <Text style={styles.habitName}>{habit.name}</Text>
        <Text style={styles.habitDuration}>{habit.duration_minutes} min focus session</Text>

        {/* Timer ring */}
        {!isFinished ? (
          <Animated.View style={[styles.ringWrapper, { transform: [{ scale: pulseAnim }] }]}>
            <Svg width={RING_SIZE} height={RING_SIZE}>
              <Defs>
                <SvgGrad id="timerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <Stop offset="0%" stopColor="#7C6BFF" />
                  <Stop offset="100%" stopColor="#00D9A6" />
                </SvgGrad>
              </Defs>
              {/* Background track */}
              <Circle
                cx={RING_SIZE / 2}
                cy={RING_SIZE / 2}
                r={RING_RADIUS}
                stroke={COLORS.surface}
                strokeWidth={STROKE_WIDTH}
                fill="none"
              />
              {/* Progress arc */}
              <Circle
                cx={RING_SIZE / 2}
                cy={RING_SIZE / 2}
                r={RING_RADIUS}
                stroke="url(#timerGrad)"
                strokeWidth={STROKE_WIDTH}
                fill="none"
                strokeLinecap="round"
                strokeDasharray={`${RING_CIRCUMFERENCE}`}
                strokeDashoffset={strokeDashoffset}
                rotation={-90}
                origin={`${RING_SIZE / 2},${RING_SIZE / 2}`}
              />
            </Svg>
            {/* Time display in center */}
            <View style={styles.timeCenter}>
              <Text style={styles.timeText}>{timeDisplay}</Text>
              <Text style={styles.timeLabel}>
                {isRunning ? "FOCUS" : secondsLeft === totalSeconds ? "READY" : "PAUSED"}
              </Text>
            </View>
          </Animated.View>
        ) : (
          /* Completion celebration */
          <Animated.View style={[
            styles.celebrationContainer,
            { transform: [{ scale: completionScale }], opacity: completionOpacity },
          ]}>
            <Text style={styles.celebEmoji}>🎉</Text>
            <Text style={styles.celebText}>Session Complete!</Text>
            <Text style={styles.celebSub}>Great focus on {habit.name}</Text>
          </Animated.View>
        )}

        {/* Controls */}
        {!isFinished && (
          <View style={styles.controls}>
            {/* Play / Pause */}
            <TouchableOpacity
              style={styles.playBtn}
              onPress={handlePlayPause}
              activeOpacity={0.8}
            >
              <Text style={styles.playBtnText}>{isRunning ? "❚❚" : "▶"}</Text>
            </TouchableOpacity>

            {/* Done button (visible once timer has started) */}
            {secondsLeft < totalSeconds && (
              <TouchableOpacity style={styles.doneBtn} onPress={handleDone} activeOpacity={0.7}>
                <Text style={styles.doneBtnText}>Done Early</Text>
              </TouchableOpacity>
            )}
          </View>
        )}

        {/* Skip link */}
        {!isFinished && (
          <TouchableOpacity style={styles.skipBtn} onPress={handleSkip} activeOpacity={0.7}>
            <Text style={styles.skipText}>Skip Timer</Text>
          </TouchableOpacity>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(8,7,13,0.95)",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
  },
  closeBtn: {
    position: "absolute",
    top: 60,
    right: 24,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: COLORS.surface,
    alignItems: "center",
    justifyContent: "center",
  },
  closeBtnText: {
    fontSize: 16,
    color: COLORS.sub,
    fontWeight: "600",
  },
  habitIcon: {
    fontSize: 48,
    marginBottom: 8,
  },
  habitName: {
    fontSize: 22,
    fontWeight: "800",
    color: COLORS.text,
    textAlign: "center",
    marginBottom: 4,
  },
  habitDuration: {
    fontSize: 13,
    color: COLORS.sub,
    fontWeight: "500",
    marginBottom: 40,
  },
  ringWrapper: {
    width: RING_SIZE,
    height: RING_SIZE,
    position: "relative",
    marginBottom: 40,
  },
  timeCenter: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  timeText: {
    fontSize: 40,
    fontWeight: "800",
    color: COLORS.text,
    letterSpacing: 1,
    fontVariant: ["tabular-nums"],
  },
  timeLabel: {
    fontSize: 10,
    fontWeight: "700",
    color: COLORS.dim,
    letterSpacing: 2,
    marginTop: 2,
  },
  controls: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
    marginBottom: 24,
  },
  playBtn: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: COLORS.accent,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: COLORS.accent,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 14,
    elevation: 6,
  },
  playBtnText: {
    fontSize: 22,
    color: "#fff",
    fontWeight: "700",
  },
  doneBtn: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 16,
    backgroundColor: `${COLORS.mint}18`,
    borderWidth: 1,
    borderColor: `${COLORS.mint}35`,
  },
  doneBtnText: {
    fontSize: 14,
    fontWeight: "700",
    color: COLORS.mint,
  },
  skipBtn: {
    paddingVertical: 12,
    paddingHorizontal: 20,
  },
  skipText: {
    fontSize: 13,
    color: COLORS.dim,
    fontWeight: "600",
    textDecorationLine: "underline",
  },
  celebrationContainer: {
    alignItems: "center",
    marginBottom: 40,
  },
  celebEmoji: {
    fontSize: 64,
    marginBottom: 12,
  },
  celebText: {
    fontSize: 24,
    fontWeight: "800",
    color: COLORS.text,
    marginBottom: 4,
  },
  celebSub: {
    fontSize: 14,
    color: COLORS.sub,
    fontWeight: "500",
  },
});
