import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { apiRequest } from "../constants/api";
import { useAuthStore } from "../stores/useAuthStore";
import { useCallStore } from "../stores/useCallStore";

// Configure how notifications should be handled when app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  } as any),
});

class NotificationService {
  private isRegistered = false;
  private responseSubscription: any = null;
  private receivedSubscription: any = null;

  async registerForPushNotifications(): Promise<string | null> {
    if (Platform.OS === "web") {
      console.log("[NotificationService] Push notifications are not supported on web.");
      return null;
    }

    if (!Device.isDevice) {
      console.log("[NotificationService] Must use physical device for Push Notifications.");
      return null;
    }

    try {
      // 1. Android Notification Channel configuration for high priority incoming calls
      if (Platform.OS === "android") {
        await Notifications.setNotificationChannelAsync("call-notifications", {
          name: "Call Notifications",
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 500, 250, 500],
          lightColor: "#8b1d36",
          sound: "default",
          enableLights: true,
          enableVibrate: true,
          lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
          bypassDnd: true,
        });
      }

      // 2. Request user permissions
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;
      if (existingStatus !== "granted") {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }

      if (finalStatus !== "granted") {
        console.warn("[NotificationService] Push notification permission not granted:", finalStatus);
        return null;
      }

      // 3. Resolve Project ID for Expo Push Service
      const projectId =
        Constants?.expoConfig?.extra?.eas?.projectId ??
        Constants?.easConfig?.projectId;

      const tokenData = await Notifications.getExpoPushTokenAsync(
        projectId ? { projectId } : undefined
      );
      const pushToken = tokenData.data;
      console.log("[NotificationService] Expo Push Token obtained:", pushToken);

      // 4. Send token to Django backend
      await this.sendTokenToBackend(pushToken);
      this.isRegistered = true;

      // 5. Setup event listeners
      this.setupNotificationListeners();

      return pushToken;
    } catch (e) {
      console.warn("[NotificationService] Error registering for push notifications:", e);
      return null;
    }
  }

  async sendTokenToBackend(pushToken: string) {
    const authToken = useAuthStore.getState().token;
    if (!authToken || !pushToken) return;

    try {
      await apiRequest("/api/call-center/employees/push-token/", {
        method: "POST",
        body: JSON.stringify({ push_token: pushToken }),
      }, authToken);
      console.log("[NotificationService] Push token successfully synchronized with server.");
    } catch (err) {
      console.error("[NotificationService] Failed to send push token to backend:", err);
    }
  }

  private setupNotificationListeners() {
    if (this.responseSubscription || this.receivedSubscription) return;

    // Triggered when notification is received while app is open
    this.receivedSubscription = Notifications.addNotificationReceivedListener((notification) => {
      console.log("[NotificationService] Notification received:", notification.request.content.data);
    });

    // Triggered when user clicks / taps on notification (even when app was closed/background)
    this.responseSubscription = Notifications.addNotificationResponseReceivedListener((response) => {
      const data = (response.notification.request.content.data || {}) as Record<string, any>;
      console.log("[NotificationService] User tapped notification with data:", data);

      if (data && data.room_name && data.event === "incoming_call") {
        // Hydrate incoming call state into softphone store
        useCallStore.setState({
          incomingCall: {
            roomName: String(data.room_name),
            callerName: String(data.caller_name || "متصل وارد"),
            callerExtension: String(data.caller_extension || ""),
            callerDepartment: String(data.caller_department || ""),
            callType: (data.call_type || "direct_internal") as any,
            queueName: data.queue_name ? String(data.queue_name) : undefined,
            transferId: data.transfer_id ? String(data.transfer_id) : undefined,
            transferredBy: data.transferred_by ? String(data.transferred_by) : undefined,
          },
          incomingModalVisible: true,
        });
      }
    });
  }

  cleanup() {
    if (this.receivedSubscription) {
      this.receivedSubscription.remove();
      this.receivedSubscription = null;
    }
    if (this.responseSubscription) {
      this.responseSubscription.remove();
      this.responseSubscription = null;
    }
  }
}

export const notificationService = new NotificationService();
