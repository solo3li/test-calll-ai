import React from "react";
import { View, StyleSheet, Platform, StatusBar } from "react-native";
import { Colors } from "../constants/theme";

interface WindowFrameProps {
  children: React.ReactNode;
}

export const WindowFrame: React.FC<WindowFrameProps> = ({ children }) => {
  const isWeb = Platform.OS === "web";

  return (
    <View style={styles.outerContainer}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.background} />
      <View style={[styles.windowContainer, isWeb && styles.webCardContainer]}>
        {/* Window title bar with dots (macOS / MicroSIP styling) */}
        <View style={styles.windowHeader}>
          <View style={styles.dotsRow}>
            <View style={[styles.dot, { backgroundColor: Colors.dotRed }]} />
            <View style={[styles.dot, { backgroundColor: Colors.dotYellow }]} />
            <View style={[styles.dot, { backgroundColor: Colors.dotGreen }]} />
          </View>
        </View>

        {/* Inner Content */}
        <View style={styles.contentArea}>{children}</View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  outerContainer: {
    flex: 1,
    backgroundColor: "#080c14",
    alignItems: "center",
    justifyContent: "center",
  },
  windowContainer: {
    flex: 1,
    width: "100%",
    backgroundColor: Colors.background,
    overflow: "hidden",
  },
  webCardContainer: {
    maxWidth: 390,
    height: 750,
    maxHeight: "96%",
    borderRadius: 20,
    borderWidth: 1,
    borderColor: Colors.cardBorder,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 16 },
    shadowOpacity: 0.6,
    shadowRadius: 32,
    elevation: 20,
  },
  windowHeader: {
    height: 36,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.background,
  },
  dotsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  dot: {
    width: 11,
    height: 11,
    borderRadius: 6,
  },
  contentArea: {
    flex: 1,
  },
});
