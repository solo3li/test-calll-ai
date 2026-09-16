import React from "react";
import { View, Text, StyleSheet, Modal, TouchableOpacity, ScrollView } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCall } from "../context/CallContext";

export const TransferModal: React.FC = () => {
  const { transferModalVisible, setTransferModalVisible, contacts, transferCall } = useCall();

  return (
    <Modal
      visible={transferModalVisible}
      transparent
      animationType="fade"
      onRequestClose={() => setTransferModalVisible(false)}
    >
      <View style={styles.backdrop}>
        <View style={styles.modalCard}>
          {/* Modal Header */}
          <View style={styles.modalHeader}>
            <View style={styles.headerLeft}>
              <Ionicons name="shuffle-outline" size={20} color={Colors.primaryTeal} />
              <Text style={styles.modalTitle}>Transfer Call</Text>
            </View>
            <TouchableOpacity
              onPress={() => setTransferModalVisible(false)}
              style={styles.closeBtn}
            >
              <Ionicons name="close" size={20} color={Colors.textMuted} />
            </TouchableOpacity>
          </View>

          <Text style={styles.subtitle}>
            Select an available agent or department to transfer this call:
          </Text>

          {/* Quick Department Transfer */}
          <View style={styles.quickQueuesRow}>
            <TouchableOpacity
              style={styles.queueBtn}
              onPress={() =>
                transferCall({
                  id: "q-sales",
                  name: "Sales Queue",
                  role: "Department",
                  extension: "100",
                  department: "Sales",
                  status: "available",
                })
              }
            >
              <Text style={styles.queueBtnText}>Sales (100)</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.queueBtn}
              onPress={() =>
                transferCall({
                  id: "q-support",
                  name: "Support Queue",
                  role: "Department",
                  extension: "200",
                  department: "Support",
                  status: "available",
                })
              }
            >
              <Text style={styles.queueBtnText}>Support (200)</Text>
            </TouchableOpacity>
          </View>

          {/* Colleagues list */}
          <ScrollView style={styles.agentList} showsVerticalScrollIndicator={false}>
            {contacts.map((agent) => {
              const isAvailable = agent.status === "available";
              return (
                <TouchableOpacity
                  key={agent.id}
                  style={[styles.agentRow, !isAvailable && styles.agentRowDisabled]}
                  disabled={!isAvailable}
                  onPress={() => transferCall(agent)}
                  activeOpacity={0.7}
                >
                  <View style={styles.agentInfo}>
                    <Text style={styles.agentName}>{agent.name}</Text>
                    <Text style={styles.agentRole}>
                      {agent.role} (Ext {agent.extension})
                    </Text>
                  </View>

                  <View style={styles.statusGroup}>
                    <View
                      style={[
                        styles.statusDot,
                        {
                          backgroundColor: isAvailable
                            ? Colors.liveGreen
                            : Colors.holdAmber,
                        },
                      ]}
                    />
                    <Text style={styles.statusLabel}>
                      {isAvailable ? "Available" : "Busy"}
                    </Text>
                  </View>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          {/* Cancel Button */}
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={() => setTransferModalVisible(false)}
          >
            <Text style={styles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.75)",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    width: "100%",
    maxWidth: 340,
    backgroundColor: Colors.card,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    padding: 18,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 10,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  modalTitle: {
    color: Colors.textWhite,
    fontSize: 16,
    fontWeight: "bold",
  },
  closeBtn: {
    padding: 4,
  },
  subtitle: {
    color: Colors.textMuted,
    fontSize: 12,
    marginBottom: 14,
    lineHeight: 16,
  },
  quickQueuesRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 14,
  },
  queueBtn: {
    flex: 1,
    backgroundColor: "rgba(0, 196, 180, 0.12)",
    borderWidth: 1,
    borderColor: Colors.primaryTealBorder,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: "center",
  },
  queueBtnText: {
    color: Colors.primaryTeal,
    fontSize: 12,
    fontWeight: "600",
  },
  agentList: {
    maxHeight: 180,
    marginBottom: 14,
  },
  agentRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255, 255, 255, 0.05)",
  },
  agentRowDisabled: {
    opacity: 0.4,
  },
  agentInfo: {
    flex: 1,
  },
  agentName: {
    color: Colors.textWhite,
    fontSize: 13,
    fontWeight: "600",
  },
  agentRole: {
    color: Colors.textMuted,
    fontSize: 11,
    marginTop: 2,
  },
  statusGroup: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusLabel: {
    color: Colors.textMuted,
    fontSize: 11,
  },
  cancelButton: {
    backgroundColor: "rgba(255, 255, 255, 0.06)",
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
  },
  cancelText: {
    color: Colors.textWhite,
    fontSize: 13,
    fontWeight: "500",
  },
});
