/**
 * Enhanced Notification context with support for multiple toasts
 * Provides consistent error and success messages across the app
 */
import { createContext, useContext, useState, useCallback } from "react";
import type { ReactNode } from "react";
import { Snackbar, Alert, Box } from "@mui/material";
import type { AlertColor } from "@mui/material";

interface Notification {
  id: string;
  message: string;
  severity: AlertColor;
  autoHideDuration?: number;
}

interface NotificationContextType {
  showNotification: (message: string, severity?: AlertColor, autoHideDuration?: number) => void;
  showError: (message: string, autoHideDuration?: number) => void;
  showSuccess: (message: string, autoHideDuration?: number) => void;
  showWarning: (message: string, autoHideDuration?: number) => void;
  showInfo: (message: string, autoHideDuration?: number) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error("useNotifications must be used within NotificationProvider");
  }
  return context;
}

interface NotificationProviderProps {
  children: ReactNode;
  maxNotifications?: number;
}

export function NotificationProvider({
  children,
  maxNotifications = 5,
}: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const showNotification = useCallback(
    (msg: string, sev: AlertColor = "info", autoHideDuration = 6000) => {
      // Generate a unique notification ID
      // Note: Math.random() is acceptable here since notification IDs only need to be unique
      // for React keys, not cryptographically secure. If you need cryptographically secure
      // IDs (e.g., for security-sensitive features), use crypto.randomUUID() instead:
      // const id = crypto.randomUUID();
      const id = `${Date.now()}-${Math.random()}`;
      const notification: Notification = {
        id,
        message: msg,
        severity: sev,
        autoHideDuration,
      };

      setNotifications((prev) => {
        const updated = [notification, ...prev];
        // Limit the number of notifications
        return updated.slice(0, maxNotifications);
      });
    },
    [maxNotifications]
  );

  const showError = useCallback(
    (msg: string, autoHideDuration = 6000) => {
      showNotification(msg, "error", autoHideDuration);
    },
    [showNotification]
  );

  const showSuccess = useCallback(
    (msg: string, autoHideDuration = 4000) => {
      showNotification(msg, "success", autoHideDuration);
    },
    [showNotification]
  );

  const showWarning = useCallback(
    (msg: string, autoHideDuration = 5000) => {
      showNotification(msg, "warning", autoHideDuration);
    },
    [showNotification]
  );

  const showInfo = useCallback(
    (msg: string, autoHideDuration = 4000) => {
      showNotification(msg, "info", autoHideDuration);
    },
    [showNotification]
  );

  const handleClose = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  return (
    <NotificationContext.Provider
      value={{
        showNotification,
        showError,
        showSuccess,
        showWarning,
        showInfo,
      }}
    >
      {children}
      <Box
        sx={{
          position: "fixed",
          bottom: 16,
          right: 16,
          zIndex: 1400,
          display: "flex",
          flexDirection: "column",
          gap: 1,
          maxWidth: "400px",
          width: "100%",
        }}
      >
        {notifications.map((notification, index) => (
          <Snackbar
            key={notification.id}
            open={true}
            autoHideDuration={notification.autoHideDuration}
            onClose={() => handleClose(notification.id)}
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            sx={{
              position: "relative",
              bottom: `${index * 70}px`,
            }}
          >
            <Alert
              onClose={() => handleClose(notification.id)}
              severity={notification.severity}
              sx={{
                width: "100%",
                boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
              }}
            >
              {notification.message}
            </Alert>
          </Snackbar>
        ))}
      </Box>
    </NotificationContext.Provider>
  );
}
