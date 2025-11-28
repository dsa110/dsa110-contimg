import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import relativeTime from "dayjs/plugin/relativeTime";

// Extend dayjs with plugins
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(relativeTime);

// Standard formats
export const DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss";
export const DATETIME_FORMAT_WITH_MS = "YYYY-MM-DD HH:mm:ss.SSS";
export const DATE_FORMAT = "YYYY-MM-DD";
export const TIME_FORMAT = "HH:mm:ss";

/**
 * Format a date string, number (timestamp), or Date object to a standard datetime string.
 * Handles timestamps in seconds or milliseconds.
 * @param date The date to format
 * @param formatStr Optional custom format string
 * @returns Formatted date string or "N/A" if invalid
 */
export const formatDateTime = (
  date: string | number | Date | null | undefined,
  formatStr: string = DATETIME_FORMAT
): string => {
  if (!date) return "N/A";

  // Handle unix timestamp in seconds (common in this codebase)
  // If number is small (less than year 3000 in seconds), assume seconds
  const dateObj = typeof date === "number" && date < 100000000000 ? dayjs.unix(date) : dayjs(date);

  return dateObj.isValid() ? dateObj.format(formatStr) : "N/A";
};

/**
 * Format a date to relative time (e.g. "2 minutes ago")
 */
export const formatRelativeTime = (date: string | number | Date | null | undefined): string => {
  if (!date) return "N/A";
  const dateObj = typeof date === "number" && date < 100000000000 ? dayjs.unix(date) : dayjs(date);
  return dateObj.isValid() ? dateObj.fromNow() : "N/A";
};

export const formatDate = (date: string | number | Date | null | undefined): string => {
  return formatDateTime(date, DATE_FORMAT);
};

export const formatTime = (date: string | number | Date | null | undefined): string => {
  return formatDateTime(date, TIME_FORMAT);
};
