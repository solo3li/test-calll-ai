import React, { useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, TextInput } from "react-native";
import { Ionicons, Feather } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCall } from "../context/CallContext";
import { CallRecord } from "../constants/mockData";

export const HistoryView: React.FC = () => {
  const {
    history,
    historyFilter,
    setHistoryFilter,
    startCall,
    playingAudioId,
    setPlayingAudioId,
  } = useCall();

  const [searchQuery, setSearchQuery] = useState("");

  const filteredList = history.filter((item) => {
    if (historyFilter === "missed" && item.type !== "missed") return false;
    if (searchQuery.trim().length > 0) {
      const q = searchQuery.toLowerCase();
      return (
        item.callerName.toLowerCase().includes(q) ||
        item.phoneNumber.includes(q) ||
        item.aiSummary.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const togglePlayAudio = (id: string) => {
    if (playingAudioId === id) {
      setPlayingAudioId(null);
    } else {
      setPlayingAudioId(id);
    }
  };

  const renderCallItem = ({ item }: { item: CallRecord }) => {
    const isMissed = item.type === "missed";
    const isPlaying = playingAudioId === item.id;

    return (
      <View style={styles.cardItem}>
        {/* Top row: Icon, Name/Number, Timestamp */}
        <View style={styles.cardHeaderRow}>
          <View style={styles.callerIdentityRow}>
            <View style={[styles.typeIconBox, isMissed && styles.typeIconMissed]}>
              <Feather
                name={isMissed ? "phone-missed" : item.type === "inbound" ? "phone-incoming" : "phone-outgoing"}
                size={16}
                color={isMissed ? Colors.endCallRed : Colors.primaryTeal}
              />
            </View>
            <View>
              <Text style={styles.callerName}>{item.callerName}</Text>
              <Text style={styles.callerPhone}>{item.phoneNumber}</Text>
            </View>
          </View>

          <View style={styles.timeMeta}>
            <Text style={styles.timestampText}>{item.timestamp}</Text>
            <View style={styles.durationRow}>
              <Feather name="clock" size={11} color={Colors.textSubtle} />
              <Text style={styles.durationText}>{item.duration}</Text>
            </View>
          </View>
        </View>

        {/* AI Summary Snippet Card */}
        <View style={styles.aiSummarySnippet}>
          <Text style={styles.aiSnippetText}>{item.aiSummary}</Text>

          <View style={styles.actionButtonsRow}>
            {item.hasRecording && (
              <TouchableOpacity
                style={[styles.playButton, isPlaying && styles.playingButton]}
                onPress={() => togglePlayAudio(item.id)}
                activeOpacity={0.7}
              >
                <Ionicons
                  name={isPlaying ? "pause" : "play"}
                  size={12}
                  color={isPlaying ? Colors.primaryTeal : Colors.textWhite}
                />
                <Text style={[styles.playButtonText, isPlaying && { color: Colors.primaryTeal }]}>
                  {isPlaying ? "Playing..." : "Play"}
                </Text>
              </TouchableOpacity>
            )}

            <TouchableOpacity
              style={styles.callbackButton}
              onPress={() => startCall(item.phoneNumber, item.callerName)}
              activeOpacity={0.8}
            >
              <Ionicons name="call" size={11} color="#0d141e" />
              <Text style={styles.callbackButtonText}>Callback</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchBar}>
        <Feather name="search" size={16} color={Colors.textSubtle} style={{ marginRight: 8 }} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search history..."
          placeholderTextColor={Colors.textSubtle}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery("")}>
            <Feather name="x" size={15} color={Colors.textMuted} />
          </TouchableOpacity>
        )}
      </View>

      {/* Segmented Filter (All vs Missed) */}
      <View style={styles.filterRow}>
        <TouchableOpacity
          style={[styles.filterTab, historyFilter === "all" && styles.filterTabActive]}
          onPress={() => setHistoryFilter("all")}
        >
          <Text style={[styles.filterText, historyFilter === "all" && styles.filterTextActive]}>
            All
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterTab, historyFilter === "missed" && styles.filterTabActive]}
          onPress={() => setHistoryFilter("missed")}
        >
          <Text style={[styles.filterText, historyFilter === "missed" && styles.filterTextActive]}>
            Missed
          </Text>
        </TouchableOpacity>
      </View>

      {/* History List */}
      <FlatList
        data={filteredList}
        keyExtractor={(item) => item.id}
        renderItem={renderCallItem}
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
    marginBottom: 10,
  },
  searchInput: {
    flex: 1,
    color: Colors.textWhite,
    fontSize: 13,
  },
  filterRow: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: Colors.cardBorder,
    marginBottom: 12,
  },
  filterTab: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 8,
  },
  filterTabActive: {
    borderBottomWidth: 2,
    borderBottomColor: Colors.primaryTeal,
  },
  filterText: {
    color: Colors.textMuted,
    fontSize: 13,
    fontWeight: "500",
  },
  filterTextActive: {
    color: Colors.textWhite,
    fontWeight: "bold",
  },
  listContent: {
    paddingBottom: 20,
    gap: 12,
  },
  cardItem: {
    backgroundColor: Colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    padding: 12,
  },
  cardHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 8,
  },
  callerIdentityRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  typeIconBox: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "rgba(0, 196, 180, 0.12)",
    alignItems: "center",
    justifyContent: "center",
  },
  typeIconMissed: {
    backgroundColor: "rgba(239, 68, 68, 0.12)",
  },
  callerName: {
    color: Colors.textWhite,
    fontSize: 14,
    fontWeight: "bold",
  },
  callerPhone: {
    color: Colors.textMuted,
    fontSize: 12,
  },
  timeMeta: {
    alignItems: "flex-end",
  },
  timestampText: {
    color: Colors.textMuted,
    fontSize: 11,
    marginBottom: 2,
  },
  durationRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
  },
  durationText: {
    color: Colors.textSubtle,
    fontSize: 10,
  },
  aiSummarySnippet: {
    backgroundColor: Colors.cardSubtle,
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.04)",
  },
  aiSnippetText: {
    color: "#cbd5e1",
    fontSize: 12,
    lineHeight: 17,
    marginBottom: 8,
  },
  actionButtonsRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
    gap: 8,
  },
  playButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    gap: 5,
  },
  playingButton: {
    backgroundColor: "rgba(0, 196, 180, 0.18)",
  },
  playButtonText: {
    color: Colors.textWhite,
    fontSize: 11,
    fontWeight: "500",
  },
  callbackButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.primaryTeal,
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    gap: 4,
  },
  callbackButtonText: {
    color: "#0d141e",
    fontSize: 11,
    fontWeight: "bold",
  },
});
