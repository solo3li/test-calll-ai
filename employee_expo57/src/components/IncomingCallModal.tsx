import React from "react";
import { View, Text, StyleSheet, Modal, TouchableOpacity } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCallStore } from "../stores/useCallStore";

export const IncomingCallModal: React.FC = () => {
  const incomingModalVisible = useCallStore((s) => s.incomingModalVisible);
  const incomingCall = useCallStore((s) => s.incomingCall);
  const answerCall = useCallStore((s) => s.answerCall);
  const declineCall = useCallStore((s) => s.declineCall);

  if (!incomingModalVisible || !incomingCall) return null;

  const isQueue = incomingCall.callType === "queue";

  return (
    <Modal visible={incomingModalVisible} transparent animationType="slide">
      <View style={styles.backdrop}>
        <View style={styles.alertCard}>
          {/* Avatar & Pulse Indicator */}
          <View style={styles.avatarCircle}>
            <Ionicons name="person" size={32} color={Colors.primaryTeal} />
          </View>

          {/* Caller Name & Phone */}
          <Text style={styles.callerName}>{incomingCall.callerName}</Text>
          <Text style={styles.callerNumber}>
            تحويلة: {incomingCall.callerExtension || "داخلي"}
          </Text>

          {/* Queue Tag */}
          <View style={styles.queueTag}>
            <Text style={styles.queueTagText}>
              {isQueue
                ? `🔔 وارد من ${incomingCall.queueName || "طابور المبيعات"}`
                : `🔔 مكالمة داخلية مباشرة (${incomingCall.callerDepartment || "زميل"})`}
            </Text>
          </View>

          {/* AI / WebRTC Pre-Call Intent Box */}
          <View style={styles.aiSummaryBox}>
            <View style={styles.aiSummaryHeader}>
              <View style={styles.aiTitleGroup}>
                <Ionicons name="sparkles" size={14} color={Colors.primaryTeal} />
                <Text style={styles.aiSummaryTitle}>WebRTC Audio Stream</Text>
              </View>
              <View style={styles.sentimentBadge}>
                <Text style={styles.sentimentText}>LiveKit HD</Text>
              </View>
            </View>

            <View style={styles.bulletsList}>
              <View style={styles.bulletRow}>
                <View style={styles.bulletDot} />
                <Text style={styles.bulletText}>
                  اتصال صوتي مباشر وفوري بدون وسطاء SIP
                </Text>
              </View>
              <View style={styles.bulletRow}>
                <View style={styles.bulletDot} />
                <Text style={styles.bulletText}>
                  جاهز للربط بغرفة LiveKit المشفرة
                </Text>
              </View>
            </View>
          </View>

          {/* Decline & Answer Buttons */}
          <View style={styles.actionsRow}>
            <View style={styles.actionBtnCol}>
              <TouchableOpacity
                style={[styles.callBtn, styles.declineBtn]}
                onPress={declineCall}
                activeOpacity={0.8}
              >
                <Ionicons
                  name="call"
                  size={24}
                  color={Colors.textWhite}
                  style={{ transform: [{ rotate: "135deg" }] }}
                />
              </TouchableOpacity>
              <Text style={styles.btnLabel}>رفض</Text>
            </View>

            <View style={styles.actionBtnCol}>
              <TouchableOpacity
                style={[styles.callBtn, styles.answerBtn]}
                onPress={answerCall}
                activeOpacity={0.8}
              >
                <Ionicons name="call" size={24} color={Colors.textWhite} />
              </TouchableOpacity>
              <Text style={styles.btnLabel}>رد (قبول)</Text>
            </View>
          </View>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.82)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  alertCard: {
    width: "100%",
    maxWidth: 350,
    backgroundColor: Colors.card,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    alignItems: "center",
    padding: 22,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 16 },
    shadowOpacity: 0.6,
    shadowRadius: 28,
    elevation: 14,
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
    marginBottom: 14,
  },
  callerName: {
    color: Colors.textWhite,
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 4,
    textAlign: "center",
  },
  callerNumber: {
    color: Colors.textMuted,
    fontSize: 13,
    marginBottom: 10,
  },
  queueTag: {
    backgroundColor: "rgba(255, 255, 255, 0.06)",
    paddingVertical: 4,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginBottom: 16,
  },
  queueTagText: {
    color: Colors.primaryTeal,
    fontSize: 12,
    fontWeight: "500",
  },
  aiSummaryBox: {
    width: "100%",
    backgroundColor: "rgba(0, 196, 180, 0.05)",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(0, 196, 180, 0.22)",
    padding: 13,
    marginBottom: 24,
  },
  aiSummaryHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  aiTitleGroup: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  aiSummaryTitle: {
    color: Colors.primaryTeal,
    fontSize: 12,
    fontWeight: "bold",
  },
  sentimentBadge: {
    backgroundColor: "rgba(16, 185, 129, 0.18)",
    paddingHorizontal: 7,
    paddingVertical: 2.5,
    borderRadius: 6,
  },
  sentimentText: {
    color: Colors.liveGreen,
    fontSize: 10,
    fontWeight: "bold",
  },
  bulletsList: {
    gap: 6,
  },
  bulletRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  bulletDot: {
    width: 4.5,
    height: 4.5,
    borderRadius: 2.5,
    backgroundColor: Colors.primaryTeal,
    marginTop: 6,
  },
  bulletText: {
    flex: 1,
    color: "#e2e8f0",
    fontSize: 12,
    lineHeight: 17,
    textAlign: "right",
  },
  actionsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
    paddingHorizontal: 28,
  },
  actionBtnCol: {
    alignItems: "center",
    gap: 6,
  },
  callBtn: {
    width: 62,
    height: 62,
    borderRadius: 31,
    alignItems: "center",
    justifyContent: "center",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 5,
  },
  answerBtn: {
    backgroundColor: Colors.liveGreen,
    shadowColor: Colors.liveGreen,
  },
  declineBtn: {
    backgroundColor: Colors.endCallRed,
    shadowColor: Colors.endCallRed,
  },
  btnLabel: {
    color: Colors.textMuted,
    fontSize: 12,
    fontWeight: "500",
  },
});
