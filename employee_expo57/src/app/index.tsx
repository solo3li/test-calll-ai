import React from "react";
import { View, StyleSheet } from "react-native";
import { WindowFrame } from "../components/WindowFrame";
import { TopTabBar } from "../components/TopTabBar";
import { ActiveCallView } from "../components/ActiveCallView";
import { DialpadView } from "../components/DialpadView";
import { HistoryView } from "../components/HistoryView";
import { ContactsView } from "../components/ContactsView";
import { TransferModal } from "../components/TransferModal";
import { IncomingCallModal } from "../components/IncomingCallModal";
import { DevStateSwitcher } from "../components/DevStateSwitcher";
import { useCall } from "../context/CallContext";

export default function Index() {
  const { activeTab, callState } = useCall();

  const isCallActive = callState === "CONNECTED" || callState === "ON_HOLD";

  return (
    <WindowFrame>
      {/* Top Tab Bar */}
      <TopTabBar />

      {/* Main View Area based on Active Tab */}
      <View style={styles.content}>
        {activeTab === "dialpad" && (isCallActive ? <ActiveCallView /> : <DialpadView />)}
        {activeTab === "history" && <HistoryView />}
        {activeTab === "contacts" && <ContactsView />}
      </View>

      {/* Modals & Helpers */}
      <TransferModal />
      <IncomingCallModal />
      <DevStateSwitcher />
    </WindowFrame>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
  },
});
