import { create } from "zustand";
import { Platform } from "react-native";
import { Room, RoomEvent, Track, RemoteTrack, RemoteParticipant } from "livekit-client";
import { Centrifuge } from "centrifuge";
import { apiRequest } from "../constants/api";
import { useAuthStore } from "./useAuthStore";
import { useDirectoryStore } from "./useDirectoryStore";
import { MOCK_HISTORY, CallRecord, ContactItem, MOCK_CONTACTS } from "../constants/mockData";

export type CallState = "IDLE" | "DIALING" | "RINGING" | "CONNECTED" | "ON_HOLD" | "TRANSFERRING" | "HOLD";
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
  transferId?: string;
  transferredBy?: string;
  ringTimeoutSeconds?: number;
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

  // Transfer State
  transferId: string | null;
  transferTargetName: string;
  transferDurationSeconds: number;

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
  transferCall: (targetExtension: string, targetName?: string) => Promise<void>;
  cancelTransfer: () => Promise<void>;
  connectLiveKitRoom: (url: string, token: string, roomName: string, partnerName?: string) => Promise<void>;
  simulateIncomingCall: () => void;
}

let callTimerInterval: any = null;
let isTransferring = false;
let holdAudioInstance: any = null;

const playHoldAudio = () => {
  if (Platform.OS === "web" && typeof window !== "undefined") {
    try {
      if (holdAudioInstance) {
        holdAudioInstance.pause();
        holdAudioInstance.currentTime = 0;
      }
      const audio = new Audio("https://assets.mixkit.co/active_storage/sfx/2874/2874-preview.mp3");
      audio.loop = true;
      audio.play().catch((e) => console.log("Hold audio autoplay blocked/note:", e));
      holdAudioInstance = audio;
    } catch (e) {
      console.warn("Hold audio creation error:", e);
    }
  }
};

const stopHoldAudio = () => {
  if (holdAudioInstance) {
    try {
      holdAudioInstance.pause();
      holdAudioInstance.currentTime = 0;
    } catch (e) {}
    holdAudioInstance = null;
  }
};

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

  transferId: null,
  transferTargetName: "",
  transferDurationSeconds: 0,

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

      // 1. Personal Employee Channel for direct incoming calls & transfers
      const empSub = centrifuge.newSubscription(config.channel);
      empSub.on("publication", (ctx) => {
        const payload = ctx.data;
        console.log("[Centrifugo Event]", payload.event, payload);

        if (payload.event === "incoming_call") {
          set({
            incomingCall: {
              roomName: payload.room_name,
              callerName: payload.caller_name || "متصل غير معروف",
              callerExtension: payload.caller_extension || "",
              callerDepartment: payload.caller_department || "",
              callType: payload.call_type || "direct_internal",
              queueName: payload.queue_name,
              transferId: payload.transfer_id,
              transferredBy: payload.transferred_by,
              ringTimeoutSeconds: payload.ring_timeout_seconds,
            },
            incomingModalVisible: true,
          });
        } else if (payload.event === "transfer_hold") {
          // Caller is put on local hold
          isTransferring = true;
          if (get().livekitRoom) {
            try { get().livekitRoom?.disconnect(); } catch (e) {}
          }
          if (callTimerInterval) {
            clearInterval(callTimerInterval);
            callTimerInterval = null;
          }
          playHoldAudio();
          set((state) => ({
            callState: "HOLD",
            transferId: payload.transfer_id,
            activeCall: {
              ...state.activeCall,
              callerName: payload.target_name ? `تحويل إلى: ${payload.target_name}` : "جاري التحويل...",
              summaryBullets: [
                "المكالمة قيد التحويل إلى زميل متاح",
                "نغمة الانتظار تعمل حتى قبول الطرف الآخر",
              ],
            },
          }));
          callTimerInterval = setInterval(() => {
            set((state) => ({
              activeCall: {
                ...state.activeCall,
                durationSeconds: state.activeCall.durationSeconds + 1,
              },
            }));
          }, 1000);
        } else if (payload.event === "transfer_room_ready") {
          // New LiveKit room is ready
          stopHoldAudio();
          get().connectLiveKitRoom(
            payload.livekit_url,
            payload.livekit_token,
            payload.room_name,
            payload.partner_name || "الطرف الآخر"
          );
        } else if (payload.event === "transfer_success") {
          // Transferrer notified of success
          if (callTimerInterval) {
            clearInterval(callTimerInterval);
            callTimerInterval = null;
          }
          set({
            callState: "IDLE",
            transferId: null,
            activeCall: INITIAL_CALL_DATA,
          });
          alert(`✅ تم تحويل المكالمة بنجاح إلى: ${payload.transferred_to}`);
        } else if (payload.event === "transfer_cancelled") {
          // Transfer cancelled, reconnecting parties
          stopHoldAudio();
          alert("تم إلغاء التحويل واستعادة المكالمة");
          get().connectLiveKitRoom(
            payload.livekit_url,
            payload.livekit_token,
            payload.room_name,
            payload.partner_name || "الزميل"
          );
        } else if (payload.event === "transfer_failed") {
          stopHoldAudio();
          alert(`فشل التحويل: ${payload.message || "لم يرد أحد على المكالمة"}`);
          get().endCall();
        } else if (payload.event === "call_ended") {
          stopHoldAudio();
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
    stopHoldAudio();
    const { centrifuge, livekitRoom } = get();
    if (centrifuge) centrifuge.disconnect();
    if (livekitRoom) livekitRoom.disconnect();
    set({ centrifuge: null, livekitRoom: null });
  },

  connectLiveKitRoom: async (livekitUrl: string, livekitToken: string, roomName: string, partnerName?: string) => {
    const existing = get().livekitRoom;
    if (existing) {
      try { existing.disconnect(); } catch (e) {}
    }

    if (callTimerInterval) {
      clearInterval(callTimerInterval);
      callTimerInterval = null;
    }

    set((state) => ({
      callState: "CONNECTED",
      incomingModalVisible: false,
      incomingCall: null,
      transferId: null,
      activeCall: {
        ...state.activeCall,
        roomName,
        callerName: partnerName || state.activeCall.callerName || "مكالمة نشطة",
        durationSeconds: 0,
      },
    }));

    callTimerInterval = setInterval(() => {
      set((state) => ({
        activeCall: {
          ...state.activeCall,
          durationSeconds: state.activeCall.durationSeconds + 1,
        },
      }));
    }, 1000);

    if (Platform.OS === "web") {
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

      room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
        console.log("Remote participant disconnected:", participant.identity);
        const remaining = Array.from(room.remoteParticipants.values()).filter(
          (p) => !p.identity.startsWith("queue-") && !p.identity.startsWith("transfer-") && p.identity !== participant.identity
        );
        if (remaining.length === 0) {
          get().endCall();
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        if (isTransferring) {
          isTransferring = false;
          return;
        }
        get().endCall();
      });

      await room.connect(livekitUrl, livekitToken);

      // Attach any tracks that arrived early
      room.remoteParticipants.forEach((p) => {
        p.trackPublications.forEach((pub) => {
          if (pub.track && pub.track.kind === Track.Kind.Audio) {
            const el = pub.track.attach();
            el.play().catch((e) => console.log("Audio attach error:", e));
          }
        });
      });

      try {
        if (typeof navigator !== "undefined" && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
          await room.localParticipant.setMicrophoneEnabled(true);
        }
      } catch (micErr) {
        console.warn("Failed to enable mic:", micErr);
      }

      set({ livekitRoom: room });
    }
  },

  startCall: async (targetNumberOrExt?: string, targetName?: string) => {
    const target = targetNumberOrExt || get().dialpadInput.trim();
    if (!target) {
      alert("الرجاء إدخال رقم هاتف أو تحويلة للاتصال");
      return;
    }

    const token = useAuthStore.getState().token;
    if (!token) {
      alert("يرجى تسجيل الدخول للاتصال");
      return;
    }

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

        if (Platform.OS === "web") {
          const room = new Room({
            adaptiveStream: true,
            dynacast: true,
          });

          room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
            if (track.kind === Track.Kind.Audio) {
              const audioElement = track.attach();
              audioElement.play().catch((err) => console.log("Audio play error:", err));
            }
          });

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

          room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
            const remaining = Array.from(room.remoteParticipants.values()).filter(
              (p) => !p.identity.startsWith("queue-") && !p.identity.startsWith("transfer-") && p.identity !== participant.identity
            );
            if (remaining.length === 0) {
              get().endCall();
            }
          });

          room.on(RoomEvent.Disconnected, () => {
            if (isTransferring) {
              isTransferring = false;
              return;
            }
            get().endCall();
          });

          await room.connect(data.livekit_url, data.livekit_token);

          // Attach tracks
          room.remoteParticipants.forEach((p) => {
            p.trackPublications.forEach((pub) => {
              if (pub.track && pub.track.kind === Track.Kind.Audio) {
                const el = pub.track.attach();
                el.play().catch((e) => console.log("Audio attach error:", e));
              }
            });
          });

          try {
            if (typeof navigator !== "undefined" && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
              await room.localParticipant.setMicrophoneEnabled(true);
            }
          } catch (micErr) {
            console.warn("Failed to enable mic:", micErr);
          }

          set({ livekitRoom: room });
        }
      }
    } catch (err: any) {
      alert(`فشل الاتصال: ${err.message}`);
      set({ callState: "IDLE", activeCall: INITIAL_CALL_DATA });
    }
  },

  answerCall: async () => {
    const { incomingCall } = get();
    const token = useAuthStore.getState().token;
    if (!incomingCall || !token) return;

    // Check if this is an incoming transferred call
    if (incomingCall.callType === "transfer" && incomingCall.transferId) {
      try {
        await apiRequest("/api/call-center/calls/transfer/action/", {
          method: "POST",
          body: JSON.stringify({
            transfer_id: incomingCall.transferId,
            action: "answer",
          }),
        }, token);
        set({ incomingModalVisible: false });
        // The transfer_room_ready Centrifugo event will arrive and connect to LiveKit!
        return;
      } catch (err: any) {
        alert(`فشل الرد على التحويل: ${err.message}`);
        return;
      }
    }

    set({
      callState: "CONNECTED",
      incomingModalVisible: false,
      activeCall: {
        callerName: incomingCall.callerName,
        phoneNumber: incomingCall.callerExtension,
        extension: incomingCall.callerExtension,
        durationSeconds: 0,
        sentiment: "Positive / جيدة",
        summaryBullets: [
          "مكالمة واردة عبر شبكة الكول سنتر WebRTC",
          `المتصل: ${incomingCall.callerName} (تحويلة: ${incomingCall.callerExtension})`,
        ],
        roomName: incomingCall.roomName,
      },
    });

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

        room.on(RoomEvent.ParticipantDisconnected, (participant: RemoteParticipant) => {
          const remaining = Array.from(room.remoteParticipants.values()).filter(
            (p) => !p.identity.startsWith("queue-") && !p.identity.startsWith("transfer-") && p.identity !== participant.identity
          );
          if (remaining.length === 0) {
            get().endCall();
          }
        });

        room.on(RoomEvent.Disconnected, () => {
          if (isTransferring) {
            isTransferring = false;
            return;
          }
          get().endCall();
        });

        await room.connect(data.livekit_url, data.livekit_token);

        room.remoteParticipants.forEach((p) => {
          p.trackPublications.forEach((pub) => {
            if (pub.track && pub.track.kind === Track.Kind.Audio) {
              const el = pub.track.attach();
              el.play().catch((e) => console.log("Audio attach error:", e));
            }
          });
        });

        try {
          if (typeof navigator !== "undefined" && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === "function") {
            await room.localParticipant.setMicrophoneEnabled(true);
          }
        } catch (micErr) {
          console.warn("Failed to enable mic:", micErr);
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

    if (incomingCall?.callType === "transfer" && incomingCall.transferId && token) {
      apiRequest("/api/call-center/calls/transfer/action/", {
        method: "POST",
        body: JSON.stringify({
          transfer_id: incomingCall.transferId,
          action: "reject",
        }),
      }, token).catch((e) => console.log("Decline transfer error:", e));
    } else if (incomingCall?.roomName && token) {
      apiRequest("/api/call-center/calls/hangup/", {
        method: "POST",
        body: JSON.stringify({ room_name: incomingCall.roomName }),
      }, token).catch((err) => console.log("Decline hangup API error:", err));
    }

    set({ incomingModalVisible: false, incomingCall: null });
  },

  endCall: () => {
    stopHoldAudio();
    if (callTimerInterval) {
      clearInterval(callTimerInterval);
      callTimerInterval = null;
    }

    const { livekitRoom, activeCall, incomingCall } = get();
    const roomNameToHangup = activeCall.roomName || incomingCall?.roomName;

    if (livekitRoom) {
      try {
        livekitRoom.disconnect();
      } catch (e) {}
    }

    const token = useAuthStore.getState().token;
    if (roomNameToHangup && token) {
      apiRequest("/api/call-center/calls/hangup/", {
        method: "POST",
        body: JSON.stringify({ room_name: roomNameToHangup }),
      }, token).catch((err) => console.log("Hangup API error:", err));
    }

    set({
      callState: "IDLE",
      isMuted: false,
      isOnHold: false,
      livekitRoom: null,
      activeCall: INITIAL_CALL_DATA,
      incomingModalVisible: false,
      incomingCall: null,
      transferId: null,
      transferTargetName: "",
      transferDurationSeconds: 0,
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

  transferCall: async (targetExtension: string, targetName?: string) => {
    const token = useAuthStore.getState().token;
    const { activeCall, livekitRoom } = get();
    if (!token || !activeCall.roomName) return;

    try {
      const res = await apiRequest<{
        status: string;
        message: string;
        transfer_id: string;
        target: string;
        target_name: string;
      }>("/api/call-center/calls/transfer/", {
        method: "POST",
        body: JSON.stringify({
          room_name: activeCall.roomName,
          target: targetExtension,
        }),
      }, token);

      isTransferring = true;
      if (livekitRoom) {
        try { livekitRoom.disconnect(); } catch (e) {}
      }

      if (callTimerInterval) {
        clearInterval(callTimerInterval);
        callTimerInterval = null;
      }

      set({
        transferModalVisible: false,
        livekitRoom: null,
        callState: "TRANSFERRING",
        transferId: res.transfer_id,
        transferTargetName: res.target_name || targetName || targetExtension,
        transferDurationSeconds: 0,
      });

      callTimerInterval = setInterval(() => {
        set((state) => ({
          transferDurationSeconds: state.transferDurationSeconds + 1,
        }));
      }, 1000);
    } catch (err: any) {
      isTransferring = false;
      alert(`فشل التحويل: ${err.message}`);
    }
  },

  cancelTransfer: async () => {
    const token = useAuthStore.getState().token;
    const { transferId } = get();
    if (!token || !transferId) return;

    try {
      await apiRequest("/api/call-center/calls/transfer/cancel/", {
        method: "POST",
        body: JSON.stringify({ transfer_id: transferId }),
      }, token);
    } catch (err: any) {
      alert(`فشل إلغاء التحويل: ${err.message}`);
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
