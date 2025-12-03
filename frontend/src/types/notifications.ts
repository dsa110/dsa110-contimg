/**
 * Notification system types
 * Defines structures for in-app and external notifications
 */

/**
 * Notification severity levels
 */
export type NotificationSeverity = "info" | "success" | "warning" | "error";

/**
 * Notification categories for filtering
 */
export type NotificationCategory =
  | "system" // System health, service status
  | "pipeline" // Pipeline job completion, failures
  | "calibration" // Calibration quality alerts
  | "source" // Source detection, variability alerts
  | "data" // Data ingestion, storage alerts
  | "user"; // User actions, account notifications

/**
 * External notification channels
 */
export type NotificationChannel = "email" | "slack" | "webhook";

/**
 * A single notification item
 */
export interface Notification {
  /** Unique identifier */
  id: string;
  /** Notification title */
  title: string;
  /** Detailed message */
  message: string;
  /** Severity level */
  severity: NotificationSeverity;
  /** Category for filtering */
  category: NotificationCategory;
  /** When the notification was created */
  timestamp: string;
  /** Whether the user has read this notification */
  read: boolean;
  /** Whether the user has dismissed this notification */
  dismissed: boolean;
  /** Optional link to related resource */
  link?: string;
  /** Optional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Notification preference for a specific category/channel combination
 */
export interface NotificationPreference {
  /** Category this preference applies to */
  category: NotificationCategory;
  /** Whether to show in-app notifications */
  inApp: boolean;
  /** External channels to send to */
  channels: NotificationChannel[];
  /** Minimum severity to notify (notifications below this are filtered) */
  minSeverity: NotificationSeverity;
}

/**
 * User notification preferences
 */
export interface NotificationPreferences {
  /** Global enable/disable for all notifications */
  enabled: boolean;
  /** Enable/disable sound for notifications */
  soundEnabled: boolean;
  /** Enable/disable desktop notifications (browser) */
  desktopEnabled: boolean;
  /** Per-category preferences */
  categoryPreferences: NotificationPreference[];
  /** Email address for email notifications */
  email?: string;
  /** Slack webhook URL */
  slackWebhookUrl?: string;
  /** Custom webhook URL */
  webhookUrl?: string;
  /** Quiet hours (no notifications) */
  quietHours?: {
    enabled: boolean;
    startHour: number; // 0-23
    endHour: number; // 0-23
    timezone: string;
  };
}

/**
 * Default notification preferences
 */
export const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = {
  enabled: true,
  soundEnabled: false,
  desktopEnabled: false,
  categoryPreferences: [
    {
      category: "system",
      inApp: true,
      channels: [],
      minSeverity: "warning",
    },
    {
      category: "pipeline",
      inApp: true,
      channels: [],
      minSeverity: "info",
    },
    {
      category: "calibration",
      inApp: true,
      channels: [],
      minSeverity: "warning",
    },
    {
      category: "source",
      inApp: true,
      channels: [],
      minSeverity: "info",
    },
    {
      category: "data",
      inApp: true,
      channels: [],
      minSeverity: "warning",
    },
    {
      category: "user",
      inApp: true,
      channels: [],
      minSeverity: "info",
    },
  ],
};

/**
 * Notification filter options
 */
export interface NotificationFilters {
  /** Filter by read status */
  read?: boolean;
  /** Filter by categories */
  categories?: NotificationCategory[];
  /** Filter by severities */
  severities?: NotificationSeverity[];
  /** Filter by date range */
  dateRange?: {
    start: string;
    end: string;
  };
}

/**
 * Notification summary for badge display
 */
export interface NotificationSummary {
  /** Total unread count */
  unreadCount: number;
  /** Count by severity */
  bySeverity: Record<NotificationSeverity, number>;
  /** Count by category */
  byCategory: Record<NotificationCategory, number>;
  /** Most recent notification */
  mostRecent?: Notification;
}

/**
 * Severity priority for comparison (higher = more severe)
 */
export const SEVERITY_PRIORITY: Record<NotificationSeverity, number> = {
  info: 0,
  success: 1,
  warning: 2,
  error: 3,
};

/**
 * Check if a severity meets the minimum threshold
 */
export function meetsSeverityThreshold(
  severity: NotificationSeverity,
  minSeverity: NotificationSeverity
): boolean {
  return SEVERITY_PRIORITY[severity] >= SEVERITY_PRIORITY[minSeverity];
}

/**
 * Get display label for notification category
 */
export function getCategoryLabel(category: NotificationCategory): string {
  const labels: Record<NotificationCategory, string> = {
    system: "System",
    pipeline: "Pipeline",
    calibration: "Calibration",
    source: "Sources",
    data: "Data",
    user: "Account",
  };
  return labels[category];
}

/**
 * Get icon name for notification category
 */
export function getCategoryIcon(category: NotificationCategory): string {
  const icons: Record<NotificationCategory, string> = {
    system: "server",
    pipeline: "workflow",
    calibration: "target",
    source: "star",
    data: "database",
    user: "user",
  };
  return icons[category];
}
