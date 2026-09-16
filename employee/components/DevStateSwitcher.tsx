import React, { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { Colors } from "../constants/theme";
import { useCall } from "../context/CallContext";

export const DevStateSwitcher: React.FC = () => {
  const { resetToDefaultMock, simulateIncomingCall, endCall } = useCall();
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <TouchableOpacity
        style={styles.collapsedBadge}
        onPress={() => setCollapsed(false)}
        activeOpacity={0.7}
      >
        <Text style={styles.collapsedBadgeText}>🛠 Demo State</Text>
      </TouchableOpacity>
    );
  }

  return (
    <View style={styles.floatingBar}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>DEMO TEST CONTROLS</Text>
        <TouchableOpacity onPress={() => setCollapsed(true)}>
          <Text style={styles.hideText}>Hide</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.buttonsRow}>
        <TouchableOpacity
          style={styles.actionPill}
          onPress={resetToDefaultMock}
          activeOpacity={0.7}
        >
          <Text style={styles.actionPillText}>Mock Call</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionPill}
          onPress={simulateIncomingCall}
          activeOpacity={0.7}
        >
          <Text style={styles.actionPillText}>Ring Inbound</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionPill}
          onPress={endCall}
          activeOpacity={0.7}
        >
          <Text style={styles.actionPillText}>Idle Dialpad</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  floatingBar: {
    backgroundColor: "rgba(13, 20, 30, 0.95)",
    borderTopWidth: 1,
    borderTopColor: Colors.cardBorder,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  title: {
    color: Colors.textSubtle,
    fontSize: 9,
    fontWeight: "bold",
    letterSpacing: 0.8,
  },
  hideText: {
    color: Colors.textMuted,
    fontSize: 10,
  },
  buttonsRow: {
    flexDirection: "row",
    gap: 6,
  },
  actionPill: {
    flex: 1,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    borderRadius: 6,
    paddingVertical: 5,
    alignItems: "center",
  },
  actionPillText: {
    color: Colors.primaryTeal,
    fontSize: 11,
    fontWeight: "600",
  },
  collapsedBadge: {
    position: "absolute",
    bottom: 6,
    right: 12,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  collapsedBadgeText: {
    color: Colors.primaryTeal,
    fontSize: 10,
    fontWeight: "600",
  },
});
