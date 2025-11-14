/**
 * Error Tracking and Analytics
 * Integrates with Sentry for error tracking and provides error analytics
 *
 * NOTE: Sentry is currently not installed. To enable:
 * 1. npm install @sentry/react
 * 2. Set VITE_SENTRY_DSN environment variable
 * 3. Uncomment the Sentry import and initialization code below
 */

// Sentry integration (optional - only if DSN is provided)
// To enable: npm install @sentry/react and uncomment the import
// import * as Sentry from "@sentry/react";

let sentryInitialized = false;

/**
 * Initialize Sentry error tracking
 * Configured for free tier: 5,000 errors/month, 10,000 performance units/month
 *
 * NOTE: Currently disabled. To enable, install @sentry/react and uncomment the code.
 */
export function initErrorTracking(dsn?: string): void {
  if (!dsn || sentryInitialized) {
    if (!dsn) {
      // Silently ignore - Sentry not configured
    }
    return;
  }

  // Sentry initialization code (disabled - uncomment when Sentry is installed)
  /*
  try {
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE || "development",
      integrations: [
        Sentry.browserTracingIntegration({
          tracePropagationTargets: ["localhost", /^https:\/\/.*\.dsa110\.org/],
        }),
        Sentry.replayIntegration({
          maskAllText: true,
          blockAllMedia: true,
        }),
      ],
      tracesSampleRate: import.meta.env.MODE === "production" ? 0.05 : 0.1,
      replaysSessionSampleRate: 0.05,
      replaysOnErrorSampleRate: 1.0,
      beforeSend(event, hint) {
        return event;
      },
    });

    sentryInitialized = true;
    console.log("Sentry error tracking initialized (free tier)");
  } catch (error) {
    console.warn("Failed to initialize Sentry error tracking:", error);
  }
  */

  console.log(
    "Sentry error tracking is disabled. To enable, install @sentry/react and set VITE_SENTRY_DSN"
  );
}

/**
 * Capture an error to Sentry
 * Currently disabled - errors are logged to console only
 */
export function captureError(error: Error, context?: Record<string, unknown>): void {
  if (!sentryInitialized) {
    // Log to console when Sentry is not available
    console.error("Error captured (Sentry disabled):", error, context);
    return;
  }

  // Sentry capture code (disabled - uncomment when Sentry is installed)
  /*
  try {
    Sentry.captureException(error, {
      contexts: {
        custom: context || {},
      },
      tags: {
        source: "frontend",
      },
    });
  } catch (err) {
    console.warn("Failed to capture error to Sentry:", err);
  }
  */
}

/**
 * Capture a message to Sentry
 * Currently disabled - messages are logged to console only
 */
export function captureMessage(
  message: string,
  level: "info" | "warning" | "error" = "info"
): void {
  if (!sentryInitialized) {
    // Log to console when Sentry is not available
    console[level === "error" ? "error" : level === "warning" ? "warn" : "log"](
      `Message (Sentry disabled): ${message}`
    );
    return;
  }

  // Sentry capture code (disabled - uncomment when Sentry is installed)
  /*
  try {
    Sentry.captureMessage(message, level);
  } catch (err) {
    console.warn("Failed to capture message to Sentry:", err);
  }
  */
}

/**
 * Set user context for error tracking
 * Currently disabled
 */
export function setUserContext(_userId: string, _email?: string, _username?: string): void {
  if (!sentryInitialized) {
    return;
  }

  // Sentry user context code (disabled - uncomment when Sentry is installed)
  /*
  try {
    Sentry.setUser({
      id: userId,
      email,
      username,
    });
  } catch (err) {
    console.warn("Failed to set user context in Sentry:", err);
  }
  */
}

/**
 * Add breadcrumb for error tracking
 * Currently disabled
 */
export function addBreadcrumb(
  _message: string,
  _category: string,
  _level: "info" | "warning" | "error" = "info"
): void {
  if (!sentryInitialized) {
    return;
  }

  // Sentry breadcrumb code (disabled - uncomment when Sentry is installed)
  /*
  try {
    Sentry.addBreadcrumb({
      message,
      category,
      level,
      timestamp: Date.now() / 1000,
    });
  } catch (err) {
    console.warn("Failed to add breadcrumb to Sentry:", err);
  }
  */
}

/**
 * Clear user context (e.g., on logout)
 * Currently disabled
 */
export function clearUserContext(): void {
  if (!sentryInitialized) {
    return;
  }

  // Sentry clear user code (disabled - uncomment when Sentry is installed)
  /*
  try {
    Sentry.setUser(null);
  } catch (err) {
    console.warn("Failed to clear user context in Sentry:", err);
  }
  */
}
