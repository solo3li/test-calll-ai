import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from "react-native";
import { Ionicons, FontAwesome5 } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCall } from "../context/CallContext";

export const ActiveCallView: React.FC = () => {
  const {
    activeCall,
    isMuted,
    isOnHold,
    toggleMute,
    toggleHold,
    endCall,
    setTransferModalVisible,
    sendWhatsAppOrSms,
  } = useCall();

  const formatTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer} bounces={false}>
      {/* 1. Header: Active Call Status & Live Badge */}
      <View style={styles.topStatusRow}>
        <Text style={styles.activeCallLabel}>Active Call</Text>
        <View style={styles.liveBadge}>
          <Text style={styles.liveDot}>((•))</Text>
          <Text style={styles.liveText}>Live</Text>
        </View>
      </View>

      {/* 2. Caller Information */}
      <View style={styles.callerInfoSection}>
        <Text style={styles.callerName}>{activeCall.callerName}</Text>
        <Text style={styles.callerPhone}>{activeCall.phoneNumber}</Text>

        <View style={styles.timerRow}>
          <Ionicons name="time-outline" size={15} color={Colors.primary} />
          <Text style={styles.timerText}>{formatTime(activeCall.durationSeconds)}</Text>
        </View>
      </View>

      {/* 3. Call Controls */}
      <View style={styles.controlsRow}>
        {/* Mute */}
        <View style={styles.controlCol}>
          <TouchableOpacity
            style={[styles.roundButton, isMuted && styles.roundButtonActiveMute]}
            onPress={toggleMute}
            activeOpacity={0.7}
          >
            <Ionicons
              name={isMuted ? "mic-off" : "mic"}
              size={24}
              color={isMuted ? Colors.endCallRed : Colors.primary}
            />
          </TouchableOpacity>
          <Text style={[styles.controlLabel, isMuted && { color: Colors.endCallRed }]}>
            {isMuted ? "Muted" : "Mute"}
          </Text>
        </View>

        {/* Hold */}
        <View style={styles.controlCol}>
          <TouchableOpacity
            style={[styles.roundButton, isOnHold && styles.roundButtonActiveHold]}
            onPress={toggleHold}
            activeOpacity={0.7}
          >
            <Ionicons
              name={isOnHold ? "play" : "pause"}
              size={24}
              color={isOnHold ? Colors.holdAmber : Colors.primary}
            />
          </TouchableOpacity>
          <Text style={[styles.controlLabel, isOnHold && { color: Colors.holdAmber }]}>
            {isOnHold ? "On Hold" : "Hold"}
          </Text>
        </View>

        {/* Transfer */}
        <View style={styles.controlCol}>
          <TouchableOpacity
            style={styles.roundButton}
            onPress={() => setTransferModalVisible(true)}
            activeOpacity={0.7}
          >
            <Ionicons name="shuffle-outline" size={24} color={Colors.primary} />
          </TouchableOpacity>
          <Text style={styles.controlLabel}>Transfer</Text>
        </View>

        {/* End Call */}
        <View style={styles.controlCol}>
          <TouchableOpacity style={styles.endCallButton} onPress={endCall} activeOpacity={0.7}>
            <Ionicons name="call" size={24} color="#fff" style={{ transform: [{ rotate: "135deg" }] }} />
          </TouchableOpacity>
          <Text style={[styles.controlLabel, { color: Colors.endCallRed }]}>End Call</Text>
        </View>
      </View>

      {/* 4. AI Call Summary Card */}
      <View style={styles.summaryCard}>
        <View style={styles.summaryHeader}>
          <Text style={styles.summaryTitle}>AI Call Summary</Text>
          <View style={styles.sentimentBadge}>
            <Text style={styles.sentimentText}>{activeCall.sentiment}</Text>
          </View>
        </View>

        <View style={styles.bulletsList}>
          {activeCall.summaryBullets.map((bullet, idx) => (
            <View key={idx} style={styles.bulletRow}>
              <View style={styles.bulletDot} />
              <Text style={styles.bulletText}>{bullet}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 5. WhatsApp / SMS Action Button */}
      <TouchableOpacity style={styles.actionButton} onPress={sendWhatsAppOrSms} activeOpacity={0.8}>
        <View style={styles.actionIconGroup}>
          <FontAwesome5 name="whatsapp" size={20} color="#fff" style={styles.actionIcon} />
          <Ionicons name="chatbubble-ellipses" size={19} color="#fff" />
        </View>
        <Text style={styles.actionButtonText}>Send Summary via WhatsApp/SMS</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  contentContainer: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 20,
  },
  topStatusRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  activeCallLabel: {
    color: Colors.textMuted,
    fontSize: 14,
    fontWeight: "500",
  },
  liveBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  liveDot: {
    color: Colors.endCallRed,
    fontSize: 12,
    fontWeight: "bold",
  },
  liveText: {
    color: Colors.endCallRed,
    fontSize: 13,
    fontWeight: "bold",
  },
  callerInfoSection: {
    marginBottom: 26,
  },
  callerName: {
    color: Colors.textPrimary,
    fontSize: 25,
    fontWeight: "bold",
    letterSpacing: 0.3,
    marginBottom: 4,
  },
  callerPhone: {
    color: Colors.textMuted,
    fontSize: 15,
    marginBottom: 8,
  },
  timerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  timerText: {
    color: Colors.primary,
    fontSize: 14,
    fontWeight: "600",
  },
  controlsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 28,
  },
  controlCol: {
    alignItems: "center",
    gap: 8,
  },
  roundButton: {
    width: 58,
    height: 58,
    borderRadius: 29,
    borderWidth: 1.5,
    borderColor: Colors.primaryBorder,
    backgroundColor: Colors.primaryBg,
    alignItems: "center",
    justifyContent: "center",
  },
  roundButtonActiveMute: {
    borderColor: Colors.endCallRed,
    backgroundColor: Colors.endCallRedBg,
  },
  roundButtonActiveHold: {
    borderColor: Colors.holdAmber,
    backgroundColor: Colors.holdAmberBg,
  },
  endCallButton: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: Colors.endCallRed,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: Colors.endCallRed,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  controlLabel: {
    color: Colors.primary,
    fontSize: 12,
    fontWeight: "500",
  },
  summaryCard: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    padding: 16,
    marginBottom: 22,
  },
  summaryHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  summaryTitle: {
    color: Colors.primary,
    fontSize: 15,
    fontWeight: "600",
  },
  sentimentBadge: {
    backgroundColor: Colors.liveGreenBg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  sentimentText: {
    color: Colors.liveGreen,
    fontSize: 11,
    fontWeight: "600",
  },
  bulletsList: {
    gap: 10,
  },
  bulletRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  bulletDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: Colors.primaryBorder,
    marginTop: 7,
  },
  bulletText: {
    flex: 1,
    color: Colors.textPrimary,
    fontSize: 13.5,
    lineHeight: 19,
  },
  actionButton: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    gap: 10,
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 3,
  },
  actionIconGroup: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  actionIcon: {
    marginRight: 2,
  },
  actionButtonText: {
    color: "#fff",
    fontSize: 13.5,
    fontWeight: "600",
  },
});
