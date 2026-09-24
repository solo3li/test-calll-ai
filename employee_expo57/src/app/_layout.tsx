import React, { useEffect } from "react";
import { Platform } from "react-native";
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

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, restoreSession } = useAuthStore();
  const initSignaling = useCallStore((s) => s.initSignaling);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    restoreSession().then(() => {
      const auth = useAuthStore.getState();
      if (auth.isAuthenticated) {
        initSignaling();
      }
    });
  }, []);

  useEffect(() => {
    const inLogin = segments[0] === "login";
    if (!isAuthenticated && !inLogin) {
      router.replace("/login");
    } else if (isAuthenticated && inLogin) {
      router.replace("/");
    }
  }, [isAuthenticated, segments]);

  return <>{children}</>;
}

export default function RootLayout() {
  return (
    <CallProvider>
      <AuthGate>
        <Stack screenOptions={{ headerShown: false }} />
      </AuthGate>
    </CallProvider>
  );
}
