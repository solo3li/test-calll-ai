import React, { useState, useEffect } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, TextInput, ActivityIndicator } from "react-native";
import { Ionicons, Feather } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCallStore } from "../stores/useCallStore";
import { useDirectoryStore } from "../stores/useDirectoryStore";
import { EmployeeProfile } from "../stores/useAuthStore";

export const ContactsView: React.FC = () => {
  const startCall = useCallStore((s) => s.startCall);
  const { employees, queues, isLoading, fetchDirectory } = useDirectoryStore();
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchDirectory();
  }, []);

  const filteredEmployees = employees.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      c.display_name.toLowerCase().includes(q) ||
      c.department.toLowerCase().includes(q) ||
      c.extension.includes(q)
    );
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "ready":
        return Colors.liveGreen;
      case "break":
        return Colors.holdAmber;
      case "busy":
        return Colors.endCallRed;
      default:
        return Colors.textSubtle;
    }
  };

  const renderEmployee = ({ item }: { item: EmployeeProfile }) => {
    const isAvailable = item.status === "ready";

    return (
      <View style={styles.contactCard}>
        <View style={styles.avatarBox}>
          <Text style={styles.avatarText}>
            {item.display_name
              .split(" ")
              .map((n) => n[0])
              .slice(0, 2)
              .join("")}
          </Text>
        </View>

        <View style={styles.contactDetails}>
          <View style={styles.nameRow}>
            <Text style={styles.nameText}>{item.display_name}</Text>
            <View
              style={[
                styles.statusIndicator,
                { backgroundColor: getStatusColor(item.status) },
              ]}
            />
          </View>
          <Text style={styles.roleText}>
            {item.department} • تحويلة: {item.extension}
          </Text>
        </View>

        <TouchableOpacity
          style={[styles.callBtn, !isAvailable && styles.callBtnDisabled]}
          onPress={() => startCall(item.extension, item.display_name)}
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
          placeholder="بحث عن زميل، تحويلة أو قسم..."
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
        <Text style={styles.sectionTitle}>طوابير الأقسام (QUEUES)</Text>
      </View>
      <View style={styles.queuesGrid}>
        {queues.length > 0 ? (
          queues.map((q) => (
            <TouchableOpacity
              key={q.id}
              style={styles.queueCard}
              onPress={() => startCall(q.code, q.name)}
            >
              <Ionicons name="headset-outline" size={18} color={Colors.primaryTeal} />
              <Text style={styles.queueName} numberOfLines={1}>
                {q.name.split(" ")[0]}
              </Text>
              <Text style={styles.queueExt}>كود: {q.code}</Text>
            </TouchableOpacity>
          ))
        ) : (
          <TouchableOpacity
            style={styles.queueCard}
            onPress={() => startCall("200", "طابور المبيعات")}
          >
            <Ionicons name="headset-outline" size={18} color={Colors.primaryTeal} />
            <Text style={styles.queueName}>المبيعات</Text>
            <Text style={styles.queueExt}>كود: 200</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Colleagues Section */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>الموظفون والتحويلات الداخلية</Text>
      </View>

      {isLoading && employees.length === 0 ? (
        <ActivityIndicator color={Colors.primaryTeal} style={{ marginTop: 20 }} />
      ) : (
        <FlatList
          data={filteredEmployees}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderEmployee}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <Text style={styles.emptyText}>لا يوجد موظفون متاحون حالياً</Text>
          }
        />
      )}
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
    textAlign: "right",
    outlineStyle: "none" as any,
  },
  sectionHeader: {
    marginBottom: 8,
  },
  sectionTitle: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: "bold",
    letterSpacing: 0.8,
    textAlign: "right",
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
  roleText: {
    color: Colors.textMuted,
    fontSize: 11,
    marginTop: 2,
    textAlign: "right",
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
  emptyText: {
    color: Colors.textSubtle,
    textAlign: "center",
    marginTop: 20,
    fontSize: 12,
  },
});
