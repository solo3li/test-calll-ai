import React from "react";
import { View, Text, TouchableOpacity, StyleSheet, TextInput } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "../constants/theme";
import { useCall } from "../context/CallContext";

export const DialpadView: React.FC = () => {
  const { dialpadInput, setDialpadInput, startCall } = useCall();

  const keys = [
    { num: "1", sub: "" },
    { num: "2", sub: "ABC" },
    { num: "3", sub: "DEF" },
    { num: "4", sub: "GHI" },
    { num: "5", sub: "JKL" },
    { num: "6", sub: "MNO" },
    { num: "7", sub: "PQRS" },
    { num: "8", sub: "TUV" },
    { num: "9", sub: "WXYZ" },
    { num: "*", sub: "" },
    { num: "0", sub: "+" },
    { num: "#", sub: "" },
  ];

  const handleKeyPress = (num: string) => {
    setDialpadInput(dialpadInput + num);
  };

  const handleBackspace = () => {
    setDialpadInput(dialpadInput.slice(0, -1));
  };

  return (
    <View style={styles.container}>
      {/* Phone Number Display */}
      <View style={styles.displayRow}>
        <TextInput
          style={styles.numberInput}
          value={dialpadInput}
          onChangeText={setDialpadInput}
          placeholder="رقم التحويلة أو الطابور..."
          placeholderTextColor={Colors.textSubtle}
          keyboardType="phone-pad"
        />
        {dialpadInput.length > 0 && (
          <TouchableOpacity onPress={handleBackspace} style={styles.backspaceBtn}>
            <Ionicons name="backspace-outline" size={22} color={Colors.textMuted} />
          </TouchableOpacity>
        )}
      </View>

      {/* Speed Dial Queues */}
      <View style={styles.quickQueuesRow}>
        <TouchableOpacity
          style={styles.quickQueueChip}
          onPress={() => startCall("200", "طابور المبيعات")}
        >
          <Text style={styles.quickQueueText}>📞 طابور المبيعات (200)</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.quickQueueChip}
          onPress={() => startCall("102", "سارة (دعم)")}
        >
          <Text style={styles.quickQueueText}>👤 سارة (102)</Text>
        </TouchableOpacity>
      </View>

      {/* Dialpad 3x4 Grid */}
      <View style={styles.grid}>
        {keys.map((k) => (
          <TouchableOpacity
            key={k.num}
            style={styles.keyButton}
            onPress={() => handleKeyPress(k.num)}
            activeOpacity={0.6}
          >
            <Text style={styles.keyNumber}>{k.num}</Text>
            {k.sub ? <Text style={styles.keySub}>{k.sub}</Text> : null}
          </TouchableOpacity>
        ))}
      </View>

      {/* Call Button */}
      <View style={styles.bottomCallRow}>
        <TouchableOpacity
          style={styles.callActionButton}
          onPress={() => startCall()}
          activeOpacity={0.8}
        >
          <Ionicons name="call" size={24} color={Colors.textWhite} />
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 10,
    justifyContent: "space-between",
    paddingBottom: 16,
  },
  displayRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    paddingHorizontal: 16,
    height: 48,
    marginBottom: 8,
  },
  numberInput: {
    flex: 1,
    color: Colors.textWhite,
    fontSize: 18,
    fontWeight: "bold",
    letterSpacing: 1,
  },
  backspaceBtn: {
    padding: 4,
  },
  quickQueuesRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  quickQueueChip: {
    backgroundColor: Colors.card,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  quickQueueText: {
    color: Colors.primaryTeal,
    fontSize: 11,
    fontWeight: "600",
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    rowGap: 10,
  },
  keyButton: {
    width: "30%",
    aspectRatio: 1.3,
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    alignItems: "center",
    justifyContent: "center",
  },
  keyNumber: {
    color: Colors.textWhite,
    fontSize: 20,
    fontWeight: "bold",
  },
  keySub: {
    color: Colors.textMuted,
    fontSize: 9,
    fontWeight: "600",
    letterSpacing: 1,
    marginTop: 1,
  },
  bottomCallRow: {
    alignItems: "center",
    marginTop: 6,
  },
  callActionButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: Colors.liveGreen,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: Colors.liveGreen,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 10,
    elevation: 4,
  },
});
