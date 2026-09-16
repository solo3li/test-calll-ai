import React from "react";
import { Stack } from "expo-router";
import { CallProvider } from "../context/CallContext";

export default function RootLayout() {
  return (
    <CallProvider>
      <Stack screenOptions={{ headerShown: false }} />
    </CallProvider>
  );
}
