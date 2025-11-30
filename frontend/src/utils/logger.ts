/**
 * Centralized Logging Utility
 *
 * Provides environment-aware logging that can be configured per environment.
 * In production, debug logs are suppressed while errors are always logged.
 *
 * Usage:
 *   import { logger } from '@/utils/logger';
 *   logger.debug('API retry attempt', { attempt: 1, url });
 *   logger.error('Failed to load image', error);
 */

type LogLevel = "debug" | "info" | "warn" | "error";

interface LogContext {
  [key: string]: unknown;
}

/**
 * Check if logging is enabled for the given level
 */
function isEnabled(level: LogLevel): boolean {
  const isDev = import.meta.env.DEV;

  // In production, only log warnings and errors
  if (!isDev && (level === "debug" || level === "info")) {
    return false;
  }

  return true;
}

/**
 * Format log message with context
 */
function formatMessage(message: string, context?: LogContext): string {
  if (!context || Object.keys(context).length === 0) {
    return message;
  }

  return `${message} ${JSON.stringify(context)}`;
}

/**
 * Log a debug message
 */
function debug(message: string, context?: LogContext): void {
  if (isEnabled("debug")) {
    // eslint-disable-next-line no-console
    console.debug(`[DEBUG] ${formatMessage(message, context)}`);
  }
}

/**
 * Log an info message
 */
function info(message: string, context?: LogContext): void {
  if (isEnabled("info")) {
    // eslint-disable-next-line no-console
    console.info(`[INFO] ${formatMessage(message, context)}`);
  }
}

/**
 * Log a warning message
 */
function warn(message: string, context?: LogContext): void {
  if (isEnabled("warn")) {
    console.warn(`[WARN] ${formatMessage(message, context)}`);
  }
}

/**
 * Log an error message
 */
function error(message: string, errorOrContext?: Error | LogContext): void {
  if (isEnabled("error")) {
    if (errorOrContext instanceof Error) {
      console.error(`[ERROR] ${message}`, errorOrContext);
    } else {
      console.error(`[ERROR] ${formatMessage(message, errorOrContext)}`);
    }
  }
}

/**
 * Logger instance
 */
export const logger = {
  debug,
  info,
  warn,
  error,
};

export default logger;
