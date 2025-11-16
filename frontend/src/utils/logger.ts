/**
 * Centralized logging utility for the frontend application.
 *
 * Provides consistent logging interface that can be easily configured
 * for different environments (development vs production).
 */

type LogLevel = "debug" | "info" | "warn" | "error";

class Logger {
  private isDevelopment = import.meta.env.DEV;

  private shouldLog(level: LogLevel): boolean {
    if (this.isDevelopment) {
      return true; // Log everything in development
    }
    // In production, only log warnings and errors
    return level === "warn" || level === "error";
  }

  debug(...args: unknown[]): void {
    if (this.shouldLog("debug")) {
      console.debug("[DEBUG]", ...args);
    }
  }

  info(...args: unknown[]): void {
    if (this.shouldLog("info")) {
      console.info("[INFO]", ...args);
    }
  }

  warn(...args: unknown[]): void {
    if (this.shouldLog("warn")) {
      console.warn("[WARN]", ...args);
    }
  }

  error(...args: unknown[]): void {
    if (this.shouldLog("error")) {
      console.error("[ERROR]", ...args);
    }
  }

  /**
   * Log API errors with structured information
   */
  apiError(message: string, error: unknown): void {
    const errorInfo: Record<string, unknown> = {
      message,
    };

    if (error && typeof error === "object") {
      if ("response" in error) {
        const apiError = error as {
          response?: { status?: number; data?: unknown; statusText?: string };
        };
        errorInfo.status = apiError.response?.status;
        errorInfo.statusText = apiError.response?.statusText;
        errorInfo.data = apiError.response?.data;
        errorInfo.url = apiError.response?.data && typeof apiError.response.data === "object" && "url" in apiError.response.data
          ? (apiError.response.data as { url?: string }).url
          : undefined;
      }
      if ("message" in error) {
        errorInfo.errorMessage = (error as { message: string }).message;
      }
      if ("config" in error) {
        const axiosError = error as { config?: { url?: string; method?: string } };
        errorInfo.requestUrl = axiosError.config?.url;
        errorInfo.requestMethod = axiosError.config?.method;
      }
      if ("code" in error) {
        errorInfo.code = (error as { code?: string }).code;
      }
    }

    // Properly serialize the error object for console output
    try {
      this.error("API Error:", JSON.stringify(errorInfo, null, 2));
    } catch {
      // Fallback if JSON.stringify fails (circular references, etc.)
      this.error("API Error:", message, error);
    }
  }
}

export const logger = new Logger();
