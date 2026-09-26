import React, { useEffect } from "react";
import { Platform, AppState, AppStateStatus } from "react-native";
import { Stack, useRouter, useSegments } from "expo-router";
import { CallProvider } from "../context/CallContext";
import { useAuthStore } from "../stores/useAuthStore";
import { useCallStore } from "../stores/useCallStore";

if (Platform.OS !== "web") {
  try {
    const { registerGlobals } = require("@livekit/react-native");
    registerGlobals();
  } catch (e) {
    console.warn("LiveKit registerGlobals note:", e);
  }
}

import { notificationService } from "../services/notificationService";

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isRestoring, restoreSession } = useAuthStore();
  const initSignaling = useCallStore((s) => s.initSignaling);
  const checkActiveIncomingCall = useCallStore((s) => s.checkActiveIncomingCall);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    restoreSession().then(() => {
      const auth = useAuthStore.getState();
      if (auth.isAuthenticated) {
        initSignaling();
        checkActiveIncomingCall();
        notificationService.registerForPushNotifications();
      }
    });

    const subscription = AppState.addEventListener("change", (nextAppState: AppStateStatus) => {
      if (nextAppState === "active") {
        const auth = useAuthStore.getState();
        if (auth.isAuthenticated) {
          initSignaling();
          checkActiveIncomingCall();
        }
      }
    });

    return () => {
      subscription.remove();
    };
  }, []);

  useEffect(() => {
    if (isRestoring) return;
    const inLogin = segments[0] === "login";
    if (!isAuthenticated && !inLogin) {
      router.replace("/login");
    } else if (isAuthenticated && inLogin) {
      router.replace("/");
      notificationService.registerForPushNotifications();
    }
  }, [isAuthenticated, isRestoring, segments]);

  return <>{children}</>;
}

import { SafeAreaProvider } from "react-native-safe-area-context";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <CallProvider>
        <AuthGate>
          <Stack screenOptions={{ headerShown: false }} />
        </AuthGate>
      </CallProvider>
    </SafeAreaProvider>
  );
}

