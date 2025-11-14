/**
 * Offline Detection Hook
 * Detects when the application goes offline/online
 */

import { useState, useEffect } from "react";

export interface OfflineStatus {
  isOnline: boolean;
  wasOffline: boolean;
  lastOnlineTime: Date | null;
  lastOfflineTime: Date | null;
}

/**
 * Hook to detect online/offline status
 */
export function useOfflineDetection(): OfflineStatus {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [wasOffline, setWasOffline] = useState(false);
  const [lastOnlineTime, setLastOnlineTime] = useState<Date | null>(
    navigator.onLine ? new Date() : null
  );
  const [lastOfflineTime, setLastOfflineTime] = useState<Date | null>(
    navigator.onLine ? null : new Date()
  );

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setLastOnlineTime(new Date());
      if (wasOffline) {
        setWasOffline(false);
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
      setLastOfflineTime(new Date());
      setWasOffline(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // Also check periodically (in case events don't fire)
    const interval = setInterval(() => {
      const currentOnline = navigator.onLine;
      if (currentOnline !== isOnline) {
        if (currentOnline) {
          handleOnline();
        } else {
          handleOffline();
        }
      }
    }, 5000);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      clearInterval(interval);
    };
  }, [isOnline, wasOffline]);

  return {
    isOnline,
    wasOffline,
    lastOnlineTime,
    lastOfflineTime,
  };
}
