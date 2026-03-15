/**
 * HabitFlow AI — Notification Service (Expo)
 * Handles push token registration, local notification scheduling,
 * deep link routing from notifications, and permission management.
 */

import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";

// ─── Default notification behavior ───
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// ============================================================
// PERMISSION & TOKEN REGISTRATION
// ============================================================

/**
 * Request notification permissions and get the push token.
 * Registers with the backend API.
 */
export async function registerForPushNotifications() {
  // Must be a physical device
  if (!Device.isDevice) {
    console.log("Push notifications require a physical device");
    return null;
  }

  // Check existing permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  // Request if not granted
  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.log("Push notification permission denied");
    return null;
  }

  // Get Expo push token
  const tokenData = await Notifications.getExpoPushTokenAsync({
    projectId: "your-eas-project-id", // From app.json
  });
  const pushToken = tokenData.data;

  // Android: create notification channels
  if (Platform.OS === "android") {
    await createAndroidChannels();
  }

  // Register with backend
  try {
    const { default: api } = await import("./api");
    const platform = Platform.OS === "ios" ? "ios" : "android";
    await fetch(`${api.API_BASE || "http://localhost:8000/v1"}/notifications/register-token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${(await api.auth.getSession())?.access_token}`,
      },
      body: JSON.stringify({ push_token: pushToken, platform }),
    });
    console.log("Push token registered:", pushToken);
  } catch (err) {
    console.warn("Token registration error:", err);
  }

  return pushToken;
}

/**
 * Create Android notification channels for different notification types.
 */
async function createAndroidChannels() {
  await Notifications.setNotificationChannelAsync("habit_reminders", {
    name: "Habit Reminders",
    importance: Notifications.AndroidImportance.HIGH,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: "#7C6BFF",
    sound: "default",
  });

  await Notifications.setNotificationChannelAsync("streak_alerts", {
    name: "Streak Alerts",
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 500, 250, 500],
    lightColor: "#FF6B8A",
    sound: "default",
  });

  await Notifications.setNotificationChannelAsync("social", {
    name: "Buddy Nudges & Challenges",
    importance: Notifications.AndroidImportance.DEFAULT,
    lightColor: "#00D9A6",
    sound: "default",
  });

  await Notifications.setNotificationChannelAsync("weekly_summary", {
    name: "Weekly Summary",
    importance: Notifications.AndroidImportance.DEFAULT,
    sound: "default",
  });
}


// ============================================================
// LOCAL NOTIFICATION SCHEDULING
// ============================================================

/**
 * Schedule local notifications as a backup when server push
 * can't reach the device. Called on app open and when habits change.
 */
export async function scheduleLocalNotifications(schedule) {
  // Cancel all existing scheduled notifications
  await Notifications.cancelAllScheduledNotificationsAsync();

  if (!schedule?.notifications) return;

  const now = new Date();

  for (const item of schedule.notifications) {
    if (item.type === "habit_reminder" && item.scheduled_time) {
      const [hours, minutes] = item.scheduled_time.split(":").map(Number);
      const triggerDate = new Date(now);
      triggerDate.setHours(hours, minutes, 0, 0);

      // Skip if time has already passed today
      if (triggerDate <= now) continue;

      try {
        await Notifications.scheduleNotificationAsync({
          content: {
            title: `${item.habit_icon || "✨"} Time for ${item.habit_name || "your habit"}`,
            body: "Tap to check in and keep your streak alive! 🔥",
            data: {
              type: "habit_reminder",
              habit_id: item.habit_id,
              screen: "home",
            },
            sound: "default",
            ...(Platform.OS === "android" && { channelId: "habit_reminders" }),
          },
          trigger: {
            date: triggerDate,
          },
        });
      } catch (err) {
        console.warn("Schedule notification error:", err);
      }
    }

    if (item.type === "streak_protector") {
      const triggerDate = new Date(now);
      triggerDate.setHours(20, 0, 0, 0);
      if (triggerDate <= now) continue;

      try {
        await Notifications.scheduleNotificationAsync({
          content: {
            title: "🔥 Don't break your streaks!",
            body: "You still have incomplete habits today. Tap to check in!",
            data: { type: "streak_alert", screen: "home" },
            sound: "default",
            ...(Platform.OS === "android" && { channelId: "streak_alerts" }),
          },
          trigger: { date: triggerDate },
        });
      } catch (err) {
        console.warn("Schedule streak protector error:", err);
      }
    }
  }

  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  console.log(`Scheduled ${scheduled.length} local notifications`);
}


// ============================================================
// DEEP LINK HANDLER
// ============================================================

/**
 * Map notification data to navigation routes.
 * Returns { screen, params } for React Navigation.
 */
export function getNavigationFromNotification(notification) {
  const data = notification?.request?.content?.data;
  if (!data) return null;

  switch (data.type) {
    case "habit_reminder":
      return {
        screen: "Home",
        params: { highlightHabit: data.habit_id },
      };

    case "streak_alert":
      return {
        screen: "Home",
        params: { showStreakAlert: true },
      };

    case "nudge":
      return {
        screen: "Social",
        params: { showNudge: data.from_user_id },
      };

    case "badge_earned":
      return {
        screen: "Profile",
        params: { scrollToBadge: data.badge_id },
      };

    case "weekly_summary":
      return {
        screen: "Coach",
        params: { showWeeklyReview: true },
      };

    case "challenge_update":
      return {
        screen: "Social",
        params: { showChallenges: true },
      };

    default:
      return { screen: "Home", params: {} };
  }
}


// ============================================================
// LISTENERS (attach in App.js)
// ============================================================

/**
 * Set up notification listeners. Call in App.js useEffect.
 * Returns cleanup function.
 *
 * Usage:
 * ```
 * useEffect(() => {
 *   const cleanup = setupNotificationListeners(navigationRef);
 *   return cleanup;
 * }, []);
 * ```
 */
export function setupNotificationListeners(navigationRef) {
  // Notification received while app is foregrounded
  const foregroundSub = Notifications.addNotificationReceivedListener((notification) => {
    console.log("Notification received (foreground):", notification.request.content.title);
    // Could show an in-app toast here
  });

  // User tapped on notification
  const responseSub = Notifications.addNotificationResponseReceivedListener((response) => {
    console.log("Notification tapped:", response.notification.request.content.title);
    const nav = getNavigationFromNotification(response.notification);
    if (nav && navigationRef?.current) {
      navigationRef.current.navigate(nav.screen, nav.params);
    }
  });

  return () => {
    Notifications.removeNotificationSubscription(foregroundSub);
    Notifications.removeNotificationSubscription(responseSub);
  };
}


// ============================================================
// BADGE MANAGEMENT
// ============================================================

/**
 * Set app badge count (iOS) based on incomplete habits.
 */
export async function updateBadgeCount(incompleteCount) {
  try {
    await Notifications.setBadgeCountAsync(incompleteCount);
  } catch (err) {
    // Android might not support badge count
    console.warn("Badge count error:", err);
  }
}

/**
 * Clear app badge count.
 */
export async function clearBadgeCount() {
  try {
    await Notifications.setBadgeCountAsync(0);
  } catch (err) {
    console.warn("Clear badge error:", err);
  }
}
