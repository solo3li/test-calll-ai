import React, { useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, TextInput } from "react-native";
import { Ionicons, Feather } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCall } from "../context/CallContext";
import { ContactItem } from "../constants/mockData";

export const ContactsView: React.FC = () => {
  const { contacts, startCall } = useCall();
  const [search, setSearch] = useState("");

  const filtered = contacts.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.role.toLowerCase().includes(q) ||
      c.extension.includes(q) ||
      c.department.toLowerCase().includes(q)
    );
  });

  const renderContact = ({ item }: { item: ContactItem }) => {
    const isAvailable = item.status === "available";
    const isOnCall = item.status === "on_call";

    return (
      <View style={styles.contactCard}>
        <View style={styles.avatarBox}>
          <Text style={styles.avatarText}>
            {item.name
              .split(" ")
              .map((n) => n[0])
              .join("")}
          </Text>
        </View>

        <View style={styles.contactDetails}>
          <View style={styles.nameRow}>
            <Text style={styles.nameText}>{item.name}</Text>
            <View
              style={[
                styles.statusIndicator,
                isAvailable
                  ? styles.statusAvailable
                  : isOnCall
                  ? styles.statusOnCall
                  : styles.statusAway,
              ]}
            />
          </View>
          <Text style={styles.roleText}>
            {item.role} • Ext: {item.extension}
          </Text>
        </View>

        <TouchableOpacity
          style={[styles.callBtn, !isAvailable && styles.callBtnDisabled]}
          onPress={() => startCall(item.extension, item.name)}
          disabled={!isAvailable}
          activeOpacity={0.7}
        >
          <Ionicons
            name="call"
            size={14}
            color={isAvailable ? "#0d141e" : Colors.textSubtle}
          />
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Search Contacts */}
      <View style={styles.searchBar}>
        <Feather name="search" size={16} color={Colors.textSubtle} style={{ marginRight: 8 }} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search colleagues & extensions..."
          placeholderTextColor={Colors.textSubtle}
          value={search}
          onChangeText={setSearch}
        />
        {search.length > 0 && (
          <TouchableOpacity onPress={() => setSearch("")}>
            <Feather name="x" size={15} color={Colors.textMuted} />
          </TouchableOpacity>
        )}
      </View>

      {/* Department Queues Section */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>DEPARTMENT QUEUES</Text>
      </View>
      <View style={styles.queuesGrid}>
        <TouchableOpacity
          style={styles.queueCard}
          onPress={() => startCall("100", "Sales Queue")}
        >
          <Ionicons name="headset-outline" size={18} color={Colors.primaryTeal} />
          <Text style={styles.queueName}>Sales</Text>
          <Text style={styles.queueExt}>Ext: 100</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.queueCard}
          onPress={() => startCall("200", "Support Queue")}
        >
          <Ionicons name="construct-outline" size={18} color={Colors.primaryTeal} />
          <Text style={styles.queueName}>Support</Text>
          <Text style={styles.queueExt}>Ext: 200</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.queueCard}
          onPress={() => startCall("300", "Billing Queue")}
        >
          <Ionicons name="card-outline" size={18} color={Colors.primaryTeal} />
          <Text style={styles.queueName}>Billing</Text>
          <Text style={styles.queueExt}>Ext: 300</Text>
        </TouchableOpacity>
      </View>

      {/* Colleagues Section */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>INTERNAL AGENTS</Text>
      </View>
      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        renderItem={renderContact}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    paddingHorizontal: 16,
    paddingTop: 12,
  },
  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    paddingHorizontal: 12,
    height: 38,
    marginBottom: 14,
  },
  searchInput: {
    flex: 1,
    color: Colors.textWhite,
    fontSize: 13,
  },
  sectionHeader: {
    marginBottom: 8,
  },
  sectionTitle: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: "bold",
    letterSpacing: 0.8,
  },
  queuesGrid: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 16,
  },
  queueCard: {
    flex: 1,
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    borderRadius: 10,
    padding: 10,
    alignItems: "center",
    gap: 4,
  },
  queueName: {
    color: Colors.textWhite,
    fontSize: 12,
    fontWeight: "600",
  },
  queueExt: {
    color: Colors.textSubtle,
    fontSize: 10,
  },
  listContent: {
    gap: 8,
    paddingBottom: 20,
  },
  contactCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    padding: 10,
    gap: 10,
  },
  avatarBox: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(0, 196, 180, 0.15)",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    color: Colors.primaryTeal,
    fontWeight: "bold",
    fontSize: 13,
  },
  contactDetails: {
    flex: 1,
  },
  nameRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  nameText: {
    color: Colors.textWhite,
    fontSize: 13,
    fontWeight: "600",
  },
  statusIndicator: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  statusAvailable: {
    backgroundColor: Colors.liveGreen,
  },
  statusOnCall: {
    backgroundColor: Colors.holdAmber,
  },
  statusAway: {
    backgroundColor: Colors.textSubtle,
  },
  roleText: {
    color: Colors.textMuted,
    fontSize: 11,
    marginTop: 2,
  },
  callBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.primaryTeal,
    alignItems: "center",
    justifyContent: "center",
  },
  callBtnDisabled: {
    backgroundColor: "rgba(255, 255, 255, 0.05)",
  },
});
