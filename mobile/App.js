/**
 * HabitFlow AI — App Entry Point
 * Handles auth state, onboarding flow, and main app routing.
 */

import React, { useState, useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { supabase, userApi } from "./src/services/api";
import OnboardingNavigator from "./src/screens/onboarding/OnboardingNavigator";

// Import actual screen components
import HomeScreen from "./src/screens/home/HomeScreen";
import AnalyticsScreen from "./src/screens/analytics/AnalyticsScreen";
import CoachChatScreen from "./src/screens/coach/CoachChatScreen";
import ProfileScreen from "./src/screens/profile/ProfileScreen";

const Tab = createBottomTabNavigator();

// Social screen placeholder (no dedicated screen file yet)
function SocialScreen() {
  return (
    <View style={s.placeholder}>
      <Text style={s.placeholderText}>Social — Coming Soon</Text>
    </View>
  );
}

export default function App() {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState(null);
  const [onboardingDone, setOnboardingDone] = useState(false);

  useEffect(() => {
    // Check initial auth state
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session) checkOnboarding(session);
      else setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (session) checkOnboarding(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const checkOnboarding = async (session) => {
    try {
      const profile = await userApi.getProfile();
      setOnboardingDone(profile?.onboarding_completed ?? false);
    } catch {
      setOnboardingDone(false);
    }
    setLoading(false);
  };

  // Loading state
  if (loading) {
    return (
      <View style={s.loadingContainer}>
        <ActivityIndicator size="large" color="#7C6BFF" />
        <StatusBar style="light" />
      </View>
    );
  }

  // Not logged in — show onboarding (which includes signup)
  if (!session || !onboardingDone) {
    return (
      <View style={{ flex: 1, backgroundColor: "#08070D" }}>
        <OnboardingNavigator
          onComplete={() => setOnboardingDone(true)}
        />
        <StatusBar style="light" />
      </View>
    );
  }

  // Main app
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarStyle: {
            backgroundColor: "#111118",
            borderTopColor: "rgba(255,255,255,0.06)",
            paddingBottom: 24,
            paddingTop: 8,
            height: 80,
          },
          tabBarActiveTintColor: "#7C6BFF",
          tabBarInactiveTintColor: "#504B66",
          tabBarLabelStyle: { fontSize: 10, fontWeight: "600" },
        }}
      >
        <Tab.Screen
          name="Home"
          component={HomeScreen}
          options={{ tabBarLabel: "Home", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>⬡</Text> }}
        />
        <Tab.Screen
          name="Analytics"
          component={AnalyticsScreen}
          options={{ tabBarLabel: "Analytics", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>◈</Text> }}
        />
        <Tab.Screen
          name="Coach"
          component={CoachChatScreen}
          options={{ tabBarLabel: "Coach", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>◉</Text> }}
        />
        <Tab.Screen
          name="Social"
          component={SocialScreen}
          options={{ tabBarLabel: "Social", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>◎</Text> }}
        />
        <Tab.Screen
          name="Profile"
          component={ProfileScreen}
          options={{ tabBarLabel: "Profile", tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>◇</Text> }}
        />
      </Tab.Navigator>
      <StatusBar style="light" />
    </NavigationContainer>
  );
}

const s = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: "#08070D",
    alignItems: "center",
    justifyContent: "center",
  },
  placeholder: {
    flex: 1,
    backgroundColor: "#08070D",
    alignItems: "center",
    justifyContent: "center",
  },
  placeholderText: {
    fontSize: 18,
    color: "#8E89A6",
    fontWeight: "600",
  },
});
