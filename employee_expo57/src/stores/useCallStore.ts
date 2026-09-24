import { create } from "zustand";
import { Platform } from "react-native";
import { Room, RoomEvent, Track, RemoteTrack, RemoteParticipant } from "livekit-client";
import { Centrifuge } from "centrifuge";
import { apiRequest } from "../constants/api";
import { useAuthStore } from "./useAuthStore";
import { useDirectoryStore } from "./useDirectoryStore";
import { MOCK_HISTORY, CallRecord, ContactItem, MOCK_CONTACTS } from "../constants/mockData";

export type CallState = "IDLE" | "DIALING" | "RINGING" | "CONNECTED" | "ON_HOLD";
export type TabKey = "dialpad" | "history" | "contacts";

export interface ActiveCallData {
  callerName: string;
  phoneNumber: string;
  extension?: string;
  durationSeconds: number;
  sentiment: string;
  summaryBullets: string[];
  roomName: string;
}

export interface IncomingCallData {
  roomName: string;
  callerName: string;
  callerExtension: string;
  callerDepartment: string;
  callType: "direct_internal" | "queue" | "transfer" | "ring_back";
  queueName?: string;
}

interface CallStoreState {
  activeTab: TabKey;
  callState: CallState;
  activeCall: ActiveCallData;
  incomingCall: IncomingCallData | null;
  isMuted: boolean;
  isOnHold: boolean;
  dialpadInput: string;
  history: CallRecord[];
  historyFilter: "all" | "missed";
  contacts: ContactItem[];
  transferModalVisible: boolean;
  incomingModalVisible: boolean;
  playingAudioId: string | null;

  // Real-time connections
  livekitRoom: Room | null;
  centrifuge: Centrifuge | null;

  // Actions
  setActiveTab: (tab: TabKey) => void;
  setDialpadInput: (val: string) => void;
  setHistoryFilter: (filter: "all" | "missed") => void;
  setTransferModalVisible: (visible: boolean) => void;
  setIncomingModalVisible: (visible: boolean) => void;
  setPlayingAudioId: (id: string | null) => void;

  // Call Lifecycle
  initSignaling: () => void;
  disconnectSignaling: () => void;
  startCall: (targetNumberOrExt?: string, targetName?: string) => Promise<void>;
  answerCall: () => Promise<void>;
  declineCall: () => void;
  endCall: () => void;
  toggleMute: () => void;
  toggleHold: () => void;
  transferCall: (targetExtension: string) => Promise<void>;
  simulateIncomingCall: () => void;
}

let callTimerInterval: any = null;

const INITIAL_CALL_DATA: ActiveCallData = {
  callerName: "",
  phoneNumber: "",
  durationSeconds: 0,
  sentiment: "Positive / جيدة",
  summaryBullets: [
    "مكالمة صوتية مشفرة بتقنية WebRTC",
    "جودة صوت نقية وفورية بدون زمن تأخير",
  ],
  roomName: "",
};

export const useCallStore = create<CallStoreState>((set, get) => ({
  activeTab: "dialpad",
  callState: "IDLE",
  activeCall: INITIAL_CALL_DATA,
  incomingCall: null,
  isMuted: false,
  isOnHold: false,
  dialpadInput: "102",
  history: MOCK_HISTORY,
  historyFilter: "all",
  contacts: MOCK_CONTACTS,
  transferModalVisible: false,
  incomingModalVisible: false,
  playingAudioId: null,
  livekitRoom: null,
  centrifuge: null,

  setActiveTab: (tab: TabKey) => set({ activeTab: tab }),
  setDialpadInput: (val: string) => set({ dialpadInput: val }),
  setHistoryFilter: (filter: "all" | "missed") => set({ historyFilter: filter }),
  setTransferModalVisible: (visible: boolean) => set({ transferModalVisible: visible }),
  setIncomingModalVisible: (visible: boolean) => set({ incomingModalVisible: visible }),
  setPlayingAudioId: (id: string | null) => set({ playingAudioId: id }),

  initSignaling: () => {
    const auth = useAuthStore.getState();
    const config = auth.centrifugoConfig;
    if (!config || !auth.employee) return;

    // Disconnect previous instance if any
    const existing = get().centrifuge;
    if (existing) {
      existing.disconnect();
    }

    try {
      const centrifuge = new Centrifuge(config.ws_url, {
        token: config.token,
      });

      // 1. Personal Employee Channel for direct incoming calls
      const empSub = centrifuge.newSubscription(config.channel);
      empSub.on("publication", (ctx) => {
        const payload = ctx.data;
        if (payload.event === "incoming_call") {
          set({
            incomingCall: {
              roomName: payload.room_name,
              callerName: payload.caller_name || "متصل غير معروف",
              callerExtension: payload.caller_extension || "",
              callerDepartment: payload.caller_department || "",
              callType: payload.call_type || "direct_internal",
              queueName: payload.queue_name,
            },
            incomingModalVisible: true,
          });
        } else if (payload.event === "call_ended") {
          get().endCall();
        }
      });
      empSub.subscribe();

      // 2. Presence Channel for live status updates of coworkers
      const presenceSub = centrifuge.newSubscription("employees:presence");
      presenceSub.on("publication", (ctx) => {
        const payload = ctx.data;
        if (payload.event === "status_change" && payload.employee) {
          useDirectoryStore.getState().updateEmployeeLiveStatus(payload.employee);
        }
      });
      presenceSub.subscribe();

      // 3. Queue Broadcast Channel
      const queueSub = centrifuge.newSubscription("queues:broadcast");
      queueSub.on("publication", (ctx) => {
        const payload = ctx.data;
        if (payload.event === "call_accepted") {
          // If another agent answered the queue call, dismiss our modal
          if (get().incomingCall?.roomName === payload.room_name) {
            const currentEmpId = useAuthStore.getState().employee?.id;
            if (payload.accepted_by?.id !== currentEmpId) {
              set({ incomingModalVisible: false, incomingCall: null });
            }
          }
        }
      });
      queueSub.subscribe();

      centrifuge.connect();
      set({ centrifuge });
    } catch (e) {
      console.error("Centrifugo initialization failed:", e);
    }
  },

  disconnectSignaling: () => {
    const { centrifuge, livekitRoom } = get();
    if (centrifuge) centrifuge.disconnect();
    if (livekitRoom) livekitRoom.disconnect();
    set({ centrifuge: null, livekitRoom: null });
  },

  startCall: async (targetNumberOrExt?: string, targetName?: string) => {
    const target = targetNumberOrExt || get().dialpadInput || "102";
    const token = useAuthStore.getState().token;
    if (!token) return;

    set({
      callState: "DIALING",
      activeCall: {
        callerName: targetName || `تحويلة: ${target}`,
        phoneNumber: target,
        extension: target,
        durationSeconds: 0,
        sentiment: "Positive / جيدة",
        summaryBullets: [
          "جاري الاتصال والربط عبر WebRTC...",
          `الطرف الآخر: ${target}`,
        ],
        roomName: "",
      },
    });

    try {
      const data = await apiRequest<{
        status: string;
        room_name: string;
        target_name: string;
        livekit_url: string;
        livekit_token: string;
        call_type: string;
      }>("/api/call-center/calls/dial/", {
        method: "POST",
        body: JSON.stringify({ target }),
      }, token);

      if (data.status === "success") {
        set((state) => ({
          callState: "RINGING",
          activeCall: {
            ...state.activeCall,
            callerName: data.target_name,
            roomName: data.room_name,
          },
        }));

        // Connect to LiveKit WebRTC Room
        if (Platform.OS === "web") {
          const room = new Room({
            adaptiveStream: true,
            dynacast: true,
          });

          // Handle incoming audio stream from the other party
          room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: any, participant: RemoteParticipant) => {
            if (track.kind === Track.Kind.Audio) {
              const audioElement = track.attach();
              audioElement.play().catch((err) => console.log("Audio play error:", err));
            }
          });

          // When the other person joins, move state to CONNECTED
          room.on(RoomEvent.ParticipantConnected, () => {
            set({ callState: "CONNECTED" });
            if (!callTimerInterval) {
              callTimerInterval = setInterval(() => {
                set((state) => ({
                  activeCall: {
                    ...state.activeCall,
                    durationSeconds: state.activeCall.durationSeconds + 1,
                  },
                }));
              }, 1000);
            }
          });

          // When the other person leaves or disconnects, end call immediately if no other callers remain
          room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
            console.log("Remote participant disconnected:", participant.identity);
            const isBot = participant.identity === "queue-manager"
              || participant.identity.startsWith("queue-")
              || participant.identity.startsWith("transfer-")
              || participant.identity === "transfer-bot";
            if (isBot) {
              console.log("System bot disconnected (handoff complete), call continuing with caller.");
              return;
            }
            const remaining = Array.from(room.remoteParticipants.values()).filter(
              (p) => p.identity !== "queue-manager"
                && !p.identity.startsWith("queue-")
                && !p.identity.startsWith("transfer-")
                && p.identity !== participant.identity
            );
            if (remaining.length === 0) {
              console.log("All remote participants left. Ending call.");
              get().endCall();
            }
          });

          room.on(RoomEvent.Disconnected, () => {
            console.log("LiveKit room disconnected");
            get().endCall();
          });

          // Join room and enable microphone
          await room.connect(data.livekit_url, data.livekit_token);
          try {
            if (typeof navigator !== "undefined" && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
              await room.localParticipant.setMicrophoneEnabled(true);
            } else {
              console.warn("navigator.mediaDevices.getUserMedia is unavailable in current context (requires HTTPS or localhost)");
            }
          } catch (micErr) {
            console.warn("Failed to enable microphone:", micErr);
          }

          set({ livekitRoom: room });
        } else {
          // Non-web fallback timer
          set({ callState: "CONNECTED" });
          if (!callTimerInterval) {
            callTimerInterval = setInterval(() => {
              set((state) => ({
                activeCall: {
                  ...state.activeCall,
                  durationSeconds: state.activeCall.durationSeconds + 1,
                },
              }));
            }, 1000);
          }
        }
      }
    } catch (err: any) {
      alert(err.message || "فشل الاتصال");
      get().endCall();
    }
  },

  answerCall: async () => {
    const { incomingCall } = get();
    const token = useAuthStore.getState().token;
    if (!incomingCall || !token) return;

    set({
      incomingModalVisible: false,
      callState: "CONNECTED",
      activeCall: {
        callerName: incomingCall.callerName,
        phoneNumber: incomingCall.callerExtension,
        extension: incomingCall.callerExtension,
        durationSeconds: 0,
        sentiment: "Neutral / طبيعية",
        summaryBullets: [
          `مكالمة واردة من: ${incomingCall.callerName} (${incomingCall.callerDepartment || "داخلي"})`,
          `نوع المكالمة: ${incomingCall.callType === "queue" ? incomingCall.queueName || "طابور" : "اتصال مباشر"}`,
        ],
        roomName: incomingCall.roomName,
      },
    });

    // Start duration ticker
    if (callTimerInterval) clearInterval(callTimerInterval);
    callTimerInterval = setInterval(() => {
      set((state) => ({
        activeCall: {
          ...state.activeCall,
          durationSeconds: state.activeCall.durationSeconds + 1,
        },
      }));
    }, 1000);

    try {
      const data = await apiRequest<{
        status: string;
        room_name: string;
        livekit_url: string;
        livekit_token: string;
      }>("/api/call-center/calls/token/", {
        method: "POST",
        body: JSON.stringify({ room_name: incomingCall.roomName }),
      }, token);

      if (data.status === "success" && Platform.OS === "web") {
        const room = new Room({
          adaptiveStream: true,
          dynacast: true,
        });

        room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
          if (track.kind === Track.Kind.Audio) {
            const el = track.attach();
            el.play().catch((e) => console.log("Audio play error:", e));
          }
        });

        // When the other person leaves or disconnects, end call immediately if no other callers remain
        room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
          console.log("Remote participant disconnected:", participant.identity);
          const isBot = participant.identity === "queue-manager"
            || participant.identity.startsWith("queue-")
            || participant.identity.startsWith("transfer-")
            || participant.identity === "transfer-bot";
          if (isBot) {
            console.log("System bot disconnected (handoff complete), call continuing with caller.");
            return;
          }
          const remaining = Array.from(room.remoteParticipants.values()).filter(
            (p) => p.identity !== "queue-manager"
              && !p.identity.startsWith("queue-")
              && !p.identity.startsWith("transfer-")
              && p.identity !== participant.identity
          );
          if (remaining.length === 0) {
            console.log("All remote participants left. Ending call.");
            get().endCall();
          }
        });

        room.on(RoomEvent.Disconnected, () => {
          console.log("LiveKit room disconnected");
          get().endCall();
        });

        await room.connect(data.livekit_url, data.livekit_token);
        try {
          if (typeof navigator !== "undefined" && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
            await room.localParticipant.setMicrophoneEnabled(true);
          } else {
            console.warn("navigator.mediaDevices.getUserMedia is unavailable in current context (requires HTTPS or localhost)");
          }
        } catch (micErr) {
          console.warn("Failed to enable microphone:", micErr);
        }

        set({ livekitRoom: room, incomingCall: null });
      }
    } catch (err) {
      console.error("Failed to join incoming call room:", err);
    }
  },

  declineCall: () => {
    const { incomingCall } = get();
    const token = useAuthStore.getState().token;
    if (incomingCall?.roomName && token) {
      apiRequest("/api/call-center/calls/hangup/", {
        method: "POST",
        body: JSON.stringify({ room_name: incomingCall.roomName }),
      }, token).catch((err) => console.log("Decline hangup API error:", err));
    }
    set({ incomingModalVisible: false, incomingCall: null });
  },

  endCall: () => {
    if (callTimerInterval) {
      clearInterval(callTimerInterval);
      callTimerInterval = null;
    }

    const { livekitRoom, activeCall, incomingCall } = get();
    const roomNameToHangup = activeCall.roomName || incomingCall?.roomName;

    if (livekitRoom) {
      try {
        livekitRoom.disconnect();
      } catch (e) {
        // Ignore disconnect errors
      }
    }

    // Notify backend and all peers via /api/calls/hangup/
    const token = useAuthStore.getState().token;
    if (roomNameToHangup && token) {
      apiRequest("/api/call-center/calls/hangup/", {
        method: "POST",
        body: JSON.stringify({ room_name: roomNameToHangup }),
      }, token).catch((err) => console.log("Hangup API error:", err));
    }

    // Add to history
    if (activeCall.callerName && activeCall.durationSeconds > 0) {
      const newRecord: CallRecord = {
        id: Date.now().toString(),
        callerName: activeCall.callerName,
        phoneNumber: activeCall.phoneNumber,
        type: "outbound",
        timestamp: "الآن",
        duration: `${Math.floor(activeCall.durationSeconds / 60)} د ${activeCall.durationSeconds % 60} ث`,
        aiSummary: "مكالمة WebRTC عبر LiveKit",
        hasRecording: false,
        sentiment: "positive",
      };
      set((state) => ({
        history: [newRecord, ...state.history],
      }));
    }

    set({
      callState: "IDLE",
      isMuted: false,
      isOnHold: false,
      livekitRoom: null,
      activeCall: INITIAL_CALL_DATA,
      incomingModalVisible: false,
      incomingCall: null,
    });
  },

  toggleMute: () => {
    const { isMuted, livekitRoom } = get();
    const next = !isMuted;
    set({ isMuted: next });

    if (livekitRoom?.localParticipant) {
      livekitRoom.localParticipant.setMicrophoneEnabled(!next);
    }
  },

  toggleHold: () => {
    const { isOnHold, callState } = get();
    const next = !isOnHold;
    set({
      isOnHold: next,
      callState: next ? "ON_HOLD" : "CONNECTED",
    });
  },

  transferCall: async (targetExtension: string) => {
    const token = useAuthStore.getState().token;
    const { activeCall, livekitRoom } = get();
    if (!token || !activeCall.roomName) return;

    try {
      await apiRequest("/api/call-center/calls/transfer/", {
        method: "POST",
        body: JSON.stringify({
          room_name: activeCall.roomName,
          target: targetExtension,
        }),
      }, token);

      // Disconnect local participant ONLY from LiveKit room without deleting room on server
      if (livekitRoom) {
        try {
          livekitRoom.disconnect();
        } catch (e) {
          // ignore
        }
      }

      if (callTimerInterval) {
        clearInterval(callTimerInterval);
        callTimerInterval = null;
      }

      set({
        transferModalVisible: false,
        livekitRoom: null,
        callState: "IDLE",
        activeCall: {
          roomName: "",
          callerName: "",
          phoneNumber: "",
          extension: "",
          durationSeconds: 0,
          sentiment: "neutral",
          summaryBullets: [],
        },
      });

      alert(`جاري تحويل المكالمة إلى التحويلة ${targetExtension}...`);
    } catch (err: any) {
      alert(`فشل التحويل: ${err.message}`);
    }
  },

  simulateIncomingCall: () => {
    set({
      incomingCall: {
        roomName: `sim_room_${Date.now()}`,
        callerName: "سارة خليل (تجربة)",
        callerExtension: "102",
        callerDepartment: "الدعم الفني",
        callType: "direct_internal",
      },
      incomingModalVisible: true,
    });
  },
}));
