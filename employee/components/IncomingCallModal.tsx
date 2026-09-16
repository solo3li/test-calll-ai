import React from "react";
import { View, Text, StyleSheet, Modal, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCall } from "../context/CallContext";

export const IncomingCallModal: React.FC = () => {
  const { callState, activeCall, answerCall, declineCall } = useCall();

  if (callState !== "RINGING") return null;

  return (
    <Modal visible={callState === "RINGING"} transparent animationType="slide">
      <View style={styles.backdrop}>
        <View style={styles.alertCard}>
          <View style={styles.avatarCircle}>
            <Ionicons name="person" size={32} color={Colors.primaryTeal} />
          </View>

          <Text style={styles.callerName}>{activeCall.callerName}</Text>
          <Text style={styles.callerNumber}>{activeCall.phoneNumber}</Text>

          <View style={styles.queueTag}>
            <Text style={styles.queueTagText}>🔔 Inbound • Support Queue</Text>
          </View>

          <View style={styles.actionsRow}>
            <TouchableOpacity
              style={[styles.callBtn, styles.declineBtn]}
              onPress={declineCall}
              activeOpacity={0.8}
            >
              <Ionicons
                name="call"
                size={22}
                color={Colors.textWhite}
                style={{ transform: [{ rotate: "135deg" }] }}
              />
              <Text style={styles.btnLabel}>Decline</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.callBtn, styles.answerBtn]}
              onPress={answerCall}
              activeOpacity={0.8}
            >
              <Ionicons name="call" size={22} color={Colors.textWhite} />
              <Text style={styles.btnLabel}>Answer</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.8)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  alertCard: {
    width: "100%",
    maxWidth: 320,
    backgroundColor: Colors.card,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    alignItems: "center",
    padding: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.6,
    shadowRadius: 24,
    elevation: 12,
  },
  avatarCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: "rgba(0, 196, 180, 0.15)",
    borderWidth: 1.5,
    borderColor: Colors.primaryTeal,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 16,
  },
  callerName: {
    color: Colors.textWhite,
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 4,
  },
  callerNumber: {
    color: Colors.textMuted,
    fontSize: 14,
    marginBottom: 12,
  },
  queueTag: {
    backgroundColor: "rgba(255, 255, 255, 0.06)",
    paddingVertical: 4,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginBottom: 26,
  },
  queueTagText: {
    color: Colors.primaryTeal,
    fontSize: 12,
    fontWeight: "500",
  },
  actionsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
    paddingHorizontal: 20,
  },
  callBtn: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: "center",
    justifyContent: "center",
  },
  answerBtn: {
    backgroundColor: Colors.liveGreen,
  },
  declineBtn: {
    backgroundColor: Colors.endCallRed,
  },
  btnLabel: {
    position: "absolute",
    bottom: -22,
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: "500",
  },
});
