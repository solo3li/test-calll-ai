import { Platform } from "react-native";
import { Audio } from "expo-av";
import * as Haptics from "expo-haptics";

// High quality, fast-loading phone sounds (fallback URLs)
const INCOMING_RINGTONE_URL = "https://assets.mixkit.co/active_storage/sfx/1359/1359-preview.mp3"; // Melodic modern phone ring
const OUTGOING_RINGBACK_URL = "https://assets.mixkit.co/active_storage/sfx/2874/2874-preview.mp3"; // Softphone PBX ringback tone

class SoundService {
  private incomingSound: Audio.Sound | null = null;
  private outgoingSound: Audio.Sound | null = null;
  private hapticsInterval: any = null;
  private webAudioCtx: any = null;
  private webOscGain: any = null;
  private isRingingIncoming = false;
  private isRingingOutgoing = false;

  constructor() {
    this.configureAudioMode();
  }

  private async configureAudioMode() {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });
    } catch (e) {
      console.log("[SoundService] configureAudioMode note:", e);
    }
  }

  // ==================== Web Audio Tone Synthesizers ====================

  private startWebTone(freq1: number, freq2: number, onDuration: number, offDuration: number) {
    if (Platform.OS !== "web" || typeof window === "undefined") return;
    try {
      this.stopWebTone();
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      this.webAudioCtx = new AudioCtx();
      if (this.webAudioCtx.state === "suspended") {
        this.webAudioCtx.resume();
      }

      const osc1 = this.webAudioCtx.createOscillator();
      const osc2 = this.webAudioCtx.createOscillator();
      const gainNode = this.webAudioCtx.createGain();

      osc1.frequency.value = freq1;
      osc2.frequency.value = freq2;

      osc1.connect(gainNode);
      osc2.connect(gainNode);
      gainNode.connect(this.webAudioCtx.destination);

      // Pulse pattern
      const now = this.webAudioCtx.currentTime;
      gainNode.gain.setValueAtTime(0, now);

      const cycle = onDuration + offDuration;
      // Schedule 30 cycles
      for (let i = 0; i < 30; i++) {
        const start = now + (i * cycle);
        gainNode.gain.setValueAtTime(0.12, start);
        gainNode.gain.setValueAtTime(0, start + onDuration);
      }

      osc1.start(now);
      osc2.start(now);
      this.webOscGain = { osc1, osc2, gainNode };
    } catch (e) {
      console.log("[SoundService] Web audio tone error:", e);
    }
  }

  private stopWebTone() {
    if (this.webOscGain) {
      try {
        this.webOscGain.osc1.stop();
        this.webOscGain.osc2.stop();
        this.webOscGain.osc1.disconnect();
        this.webOscGain.osc2.disconnect();
      } catch (e) {}
      this.webOscGain = null;
    }
    if (this.webAudioCtx) {
      try {
        this.webAudioCtx.close();
      } catch (e) {}
      this.webAudioCtx = null;
    }
  }

  // ==================== Incoming Ringtone ====================

  async playIncomingRingtone() {
    if (this.isRingingIncoming) return;
    this.stopAll();
    this.isRingingIncoming = true;

    // 1. Trigger repeated vibration on mobile
    if (Platform.OS !== "web") {
      try {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        this.hapticsInterval = setInterval(() => {
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
        }, 1200);
      } catch (e) {
        console.log("[SoundService] Haptics error:", e);
      }
    }

    // 2. Play Audio Ringtone
    if (Platform.OS === "web") {
      // Use clean standard dual ring cadence (440Hz + 480Hz, 1.5s on, 2s off)
      this.startWebTone(440, 480, 1.5, 2.0);
    } else {
      try {
        const { sound } = await Audio.Sound.createAsync(
          { uri: INCOMING_RINGTONE_URL },
          { shouldPlay: true, isLooping: true, volume: 1.0 }
        );
        this.incomingSound = sound;
      } catch (e) {
        console.warn("[SoundService] Failed to load incoming sound:", e);
      }
    }
  }

  // ==================== Outgoing Ringback Tone ====================

  async playOutgoingRingback() {
    if (this.isRingingOutgoing) return;
    this.stopAll();
    this.isRingingOutgoing = true;

    if (Platform.OS === "web") {
      // Standard PBX ringback tone (400Hz + 450Hz, 1.2s on, 2.5s off)
      this.startWebTone(400, 450, 1.2, 2.5);
    } else {
      try {
        const { sound } = await Audio.Sound.createAsync(
          { uri: OUTGOING_RINGBACK_URL },
          { shouldPlay: true, isLooping: true, volume: 0.6 }
        );
        this.outgoingSound = sound;
      } catch (e) {
        console.warn("[SoundService] Failed to load outgoing sound:", e);
      }
    }
  }

  // ==================== Stop All ====================

  async stopAll() {
    this.isRingingIncoming = false;
    this.isRingingOutgoing = false;

    // Stop haptics
    if (this.hapticsInterval) {
      clearInterval(this.hapticsInterval);
      this.hapticsInterval = null;
    }

    // Stop Web Audio
    this.stopWebTone();

    // Stop Native Incoming Sound
    if (this.incomingSound) {
      const s = this.incomingSound;
      this.incomingSound = null;
      try {
        await s.stopAsync();
        await s.unloadAsync();
      } catch (e) {}
    }

    // Stop Native Outgoing Sound
    if (this.outgoingSound) {
      const s = this.outgoingSound;
      this.outgoingSound = null;
      try {
        await s.stopAsync();
        await s.unloadAsync();
      } catch (e) {}
    }
  }
}

export const soundService = new SoundService();
