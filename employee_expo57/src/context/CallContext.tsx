import React, { createContext, useContext, useState, useEffect } from "react";
import { Linking, Platform, Alert } from "react-native";
import { INITIAL_ACTIVE_CALL, MOCK_HISTORY, MOCK_CONTACTS, CallRecord, ContactItem } from "../constants/mockData";

export type CallState = "IDLE" | "RINGING" | "CONNECTED" | "ON_HOLD";
export type TabKey = "dialpad" | "history" | "contacts";

interface ActiveCallData {
  callerName: string;
  phoneNumber: string;
  durationSeconds: number;
  sentiment: string;
  summaryBullets: string[];
}

interface CallContextType {
  activeTab: TabKey;
  setActiveTab: (tab: TabKey) => void;
  callState: CallState;
  setCallState: (state: CallState) => void;
  activeCall: ActiveCallData;
  isMuted: boolean;
  isOnHold: boolean;
  dialpadInput: string;
  setDialpadInput: (val: string) => void;
  history: CallRecord[];
  historyFilter: "all" | "missed";
  setHistoryFilter: (filter: "all" | "missed") => void;
  contacts: ContactItem[];
  transferModalVisible: boolean;
  setTransferModalVisible: (visible: boolean) => void;
  playingAudioId: string | null;
  setPlayingAudioId: (id: string | null) => void;
  
  // Actions
  toggleMute: () => void;
  toggleHold: () => void;
  endCall: () => void;
  startCall: (number?: string, name?: string) => void;
  answerCall: () => void;
  declineCall: () => void;
  transferCall: (contact: ContactItem) => void;
  sendWhatsAppOrSms: () => void;
  simulateIncomingCall: () => void;
  resetToDefaultMock: () => void;
}

const CallContext = createContext<CallContextType | undefined>(undefined);

export const CallProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<TabKey>("dialpad");
  const [callState, setCallState] = useState<CallState>("CONNECTED"); // Defaults to matching user's mockup!
  const [activeCall, setActiveCall] = useState<ActiveCallData>(INITIAL_ACTIVE_CALL);
  const [isMuted, setIsMuted] = useState(false);
  const [isOnHold, setIsOnHold] = useState(false);
  const [dialpadInput, setDialpadInput] = useState("+20 100 123 4567");
  const [history, setHistory] = useState<CallRecord[]>(MOCK_HISTORY);
  const [historyFilter, setHistoryFilter] = useState<"all" | "missed">("all");
  const [contacts] = useState<ContactItem[]>(MOCK_CONTACTS);
  const [transferModalVisible, setTransferModalVisible] = useState(false);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);

  // Active call live timer tick
  useEffect(() => {
    let interval: any = null;
    if (callState === "CONNECTED") {
      interval = setInterval(() => {
        setActiveCall((prev) => ({
          ...prev,
          durationSeconds: prev.durationSeconds + 1,
        }));
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [callState]);

  const toggleMute = () => {
    setIsMuted((prev) => !prev);
  };

  const toggleHold = () => {
    setIsOnHold((prev) => {
      const next = !prev;
      setCallState(next ? "ON_HOLD" : "CONNECTED");
      return next;
    });
  };

  const endCall = () => {
    setCallState("IDLE");
    setIsMuted(false);
    setIsOnHold(false);
  };

  const startCall = (number?: string, name?: string) => {
    const targetNum = number || dialpadInput || "+20 100 000 0000";
    const targetName = name || "Outgoing Customer";
    setActiveCall({
      callerName: targetName,
      phoneNumber: targetNum,
      durationSeconds: 0,
      sentiment: "Positive Sentiment",
      summaryBullets: [
        "Call initiated by agent",
        "Connecting through LiveKit WebRTC..."
      ]
    });
    setCallState("CONNECTED");
    setActiveTab("dialpad");
  };

  const answerCall = () => {
    setCallState("CONNECTED");
    setIsMuted(false);
    setIsOnHold(false);
  };

  const declineCall = () => {
    setCallState("IDLE");
  };

  const transferCall = (contact: ContactItem) => {
    setTransferModalVisible(false);
    if (Platform.OS === "web") {
      window.alert(`Call transferred to ${contact.name} (${contact.role} - Ext: ${contact.extension})`);
    } else {
      Alert.alert("Transfer Complete", `Transferred to ${contact.name} (Ext ${contact.extension})`);
    }
    endCall();
  };

  const sendWhatsAppOrSms = () => {
    const phone = activeCall.phoneNumber.replace(/[^0-9]/g, "");
    const text = encodeURIComponent(
      `Hello ${activeCall.callerName},\nHere is a summary of our conversation:\n- ${activeCall.summaryBullets.join(
        "\n- "
      )}\nThank you for contacting us!`
    );
    const waUrl = `https://wa.me/${phone}?text=${text}`;

    if (Platform.OS === "web") {
      window.open(waUrl, "_blank");
    } else {
      Linking.openURL(waUrl).catch(() => {
        Linking.openURL(`sms:${phone}?body=${text}`);
      });
    }
  };

  const simulateIncomingCall = () => {
    setActiveCall({
      callerName: "Karim Mostafa",
      phoneNumber: "+20 112 998 7766",
      durationSeconds: 0,
      sentiment: "Positive Sentiment",
      summaryBullets: [
        "Inbound inquiry: Customer checking order status #5432"
      ]
    });
    setCallState("RINGING");
    setActiveTab("dialpad");
  };

  const resetToDefaultMock = () => {
    setActiveCall(INITIAL_ACTIVE_CALL);
    setCallState("CONNECTED");
    setIsMuted(false);
    setIsOnHold(false);
    setActiveTab("dialpad");
  };

  return (
    <CallContext.Provider
      value={{
        activeTab,
        setActiveTab,
        callState,
        setCallState,
        activeCall,
        isMuted,
        isOnHold,
        dialpadInput,
        setDialpadInput,
        history,
        historyFilter,
        setHistoryFilter,
        contacts,
        transferModalVisible,
        setTransferModalVisible,
        playingAudioId,
        setPlayingAudioId,
        toggleMute,
        toggleHold,
        endCall,
        startCall,
        answerCall,
        declineCall,
        transferCall,
        sendWhatsAppOrSms,
        simulateIncomingCall,
        resetToDefaultMock,
      }}
    >
      {children}
    </CallContext.Provider>
  );
};

export const useCall = () => {
  const context = useContext(CallContext);
  if (!context) {
    throw new Error("useCall must be used within a CallProvider");
  }
  return context;
};
