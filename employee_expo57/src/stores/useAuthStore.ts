import { create } from "zustand";
import { Platform } from "react-native";
import { apiRequest } from "../constants/api";

export interface EmployeeProfile {
  id: number;
  user_id: number;
  username: string;
  extension: string;
  display_name: string;
  department: string;
  status: "ready" | "break" | "busy" | "offline";
  status_display: string;
  avatar_url: string;
  is_active: boolean;
}

export interface CentrifugoConfig {
  ws_url: string;
  token: string;
  channel: string;
}

interface AuthState {
  token: string | null;
  employee: EmployeeProfile | null;
  centrifugoConfig: CentrifugoConfig | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (identifier: string, password: string) => Promise<boolean>;
  logout: () => void;
  updateStatus: (status: "ready" | "break" | "busy") => Promise<void>;
  restoreSession: () => Promise<void>;
  clearError: () => void;
}

const STORAGE_KEY_TOKEN = "employee_auth_token";
const STORAGE_KEY_EMP = "employee_profile";
const STORAGE_KEY_CENT = "centrifugo_config";

function getStorageItem(key: string): string | null {
  try {
    if (Platform.OS === "web" && typeof window !== "undefined" && window.localStorage) {
      return window.localStorage.getItem(key);
    }
  } catch (e) {
    // Ignore storage errors
  }
  return null;
}

function setStorageItem(key: string, value: string): void {
  try {
    if (Platform.OS === "web" && typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(key, value);
    }
  } catch (e) {
    // Ignore storage errors
  }
}

function removeStorageItem(key: string): void {
  try {
    if (Platform.OS === "web" && typeof window !== "undefined" && window.localStorage) {
      window.localStorage.removeItem(key);
    }
  } catch (e) {
    // Ignore storage errors
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getStorageItem(STORAGE_KEY_TOKEN),
  employee: (() => {
    const raw = getStorageItem(STORAGE_KEY_EMP);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  })(),
  centrifugoConfig: (() => {
    const raw = getStorageItem(STORAGE_KEY_CENT);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  })(),
  isAuthenticated: !!getStorageItem(STORAGE_KEY_TOKEN),
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  login: async (identifier: string, password: string): Promise<boolean> => {
    set({ isLoading: true, error: null });
    try {
      const data = await apiRequest<{
        status: string;
        token: string;
        employee: EmployeeProfile;
        centrifugo: CentrifugoConfig;
        message?: string;
      }>("/api/call-center/auth/login/", {
        method: "POST",
        body: JSON.stringify({ identifier, password }),
      });

      if (data.status === "success" && data.token) {
        setStorageItem(STORAGE_KEY_TOKEN, data.token);
        setStorageItem(STORAGE_KEY_EMP, JSON.stringify(data.employee));
        setStorageItem(STORAGE_KEY_CENT, JSON.stringify(data.centrifugo));

        set({
          token: data.token,
          employee: data.employee,
          centrifugoConfig: data.centrifugo,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });

        return true;
      } else {
        set({
          isLoading: false,
          error: data.message || "فشل تسجيل الدخول",
        });
        return false;
      }
    } catch (err: any) {
      set({
        isLoading: false,
        error: err.message || "حدث خطأ في الاتصال بالخادم",
      });
      return false;
    }
  },

  logout: () => {
    removeStorageItem(STORAGE_KEY_TOKEN);
    removeStorageItem(STORAGE_KEY_EMP);
    removeStorageItem(STORAGE_KEY_CENT);

    set({
      token: null,
      employee: null,
      centrifugoConfig: null,
      isAuthenticated: false,
      error: null,
    });
  },

  updateStatus: async (status: "ready" | "break" | "busy") => {
    const { token, employee } = get();
    if (!token || !employee) return;

    // Optimistic UI update
    set({
      employee: {
        ...employee,
        status,
        status_display: status === "ready" ? "متاح (Ready)" : status === "break" ? "استراحة (Break)" : "مشغول (Busy)",
      },
    });

    try {
      const data = await apiRequest<{ status: string; employee: EmployeeProfile }>(
        "/api/call-center/employees/status/",
        {
          method: "POST",
          body: JSON.stringify({ status }),
        },
        token
      );

      if (data.status === "success") {
        setStorageItem(STORAGE_KEY_EMP, JSON.stringify(data.employee));
        set({ employee: data.employee });
      }
    } catch (err) {
      console.error("Failed to update employee status:", err);
    }
  },

  restoreSession: async () => {
    const token = getStorageItem(STORAGE_KEY_TOKEN);
    if (!token) {
      set({ isAuthenticated: false, isLoading: false });
      return;
    }

    try {
      const data = await apiRequest<{
        status: string;
        employee: EmployeeProfile;
        centrifugo: CentrifugoConfig;
      }>("/api/call-center/auth/me/", { method: "GET" }, token);

      if (data.status === "success") {
        setStorageItem(STORAGE_KEY_EMP, JSON.stringify(data.employee));
        setStorageItem(STORAGE_KEY_CENT, JSON.stringify(data.centrifugo));
        set({
          token,
          employee: data.employee,
          centrifugoConfig: data.centrifugo,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        get().logout();
      }
    } catch {
      // If network fails keep cached session or logout if 401
      set({ isLoading: false });
    }
  },
}));
