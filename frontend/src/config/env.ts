/**
 * Environment Configuration
 * Validates and exports environment variables with type safety.
 */

import { logger } from "../utils/logger";

interface EnvConfig {
  VITE_API_URL?: string;
  VITE_SENTRY_DSN?: string;
  VITE_CARTA_FRONTEND_URL?: string;
  VITE_CARTA_BACKEND_URL?: string;
  PROD: boolean;
  DEV: boolean;
}

/**
 * Validates and returns environment configuration
 *
 * Security: This function validates environment variables to ensure
 * they are properly configured and safe to use. It also provides
 * type safety and documentation for all environment variables.
 */
function validateEnv(): EnvConfig {
  const config: EnvConfig = {
    VITE_API_URL: import.meta.env.VITE_API_URL,
    VITE_SENTRY_DSN: import.meta.env.VITE_SENTRY_DSN,
    VITE_CARTA_FRONTEND_URL: import.meta.env.VITE_CARTA_FRONTEND_URL,
    VITE_CARTA_BACKEND_URL: import.meta.env.VITE_CARTA_BACKEND_URL,
    PROD: import.meta.env.PROD === true,
    DEV: import.meta.env.DEV === true,
  };

  // Validate URL formats if provided
  if (config.VITE_API_URL) {
    try {
      new URL(config.VITE_API_URL);
    } catch {
      logger.error(`Invalid VITE_API_URL format: ${config.VITE_API_URL}. Must be a valid URL.`);
      // Don't throw - use default behavior
    }
  }

  if (config.VITE_CARTA_FRONTEND_URL) {
    try {
      new URL(config.VITE_CARTA_FRONTEND_URL);
    } catch {
      logger.error(
        `Invalid VITE_CARTA_FRONTEND_URL format: ${config.VITE_CARTA_FRONTEND_URL}. Must be a valid URL.`
      );
    }
  }

  if (config.VITE_CARTA_BACKEND_URL) {
    try {
      new URL(config.VITE_CARTA_BACKEND_URL);
    } catch {
      logger.error(
        `Invalid VITE_CARTA_BACKEND_URL format: ${config.VITE_CARTA_BACKEND_URL}. Must be a valid URL.`
      );
    }
  }

  // Warn if sensitive data might be exposed
  // In production, ensure these are not exposed in client-side code
  if (config.PROD) {
    // Check for common secrets patterns (basic check)
    const envString = JSON.stringify(config);
    const secretPatterns = [/password/i, /secret/i, /key/i, /token/i, /api[_-]?key/i];

    for (const pattern of secretPatterns) {
      if (pattern.test(envString)) {
        logger.warn(
          "Potential sensitive data detected in environment variables. " +
            "Ensure no secrets are exposed via VITE_* variables."
        );
        break;
      }
    }
  }

  return config;
}

/**
 * Validated environment configuration
 *
 * Usage:
 * ```typescript
 * import { env } from './config/env';
 * const apiUrl = env.VITE_API_URL || '/api';
 * ```
 */
export const env = validateEnv();

/**
 * Environment variable documentation:
 *
 * - VITE_API_URL: Optional. Base URL for API requests (e.g., "http://localhost:8000/api").
 *   If not set, uses relative /api or origin-based detection.
 *
 * - VITE_SENTRY_DSN: Optional. Sentry DSN for error tracking. Only include if error tracking is enabled.
 *
 * - VITE_CARTA_FRONTEND_URL: Optional. CARTA frontend URL (e.g., "http://localhost:9003").
 *   Used for CARTA iframe integration.
 *
 * - VITE_CARTA_BACKEND_URL: Optional. CARTA backend URL. Used for CARTA integration.
 *
 * Security Notes:
 * - All VITE_* variables are exposed to the client-side code.
 * - NEVER expose secrets, API keys, passwords, or sensitive tokens via VITE_* variables.
 * - Use environment variables only for public configuration that is safe to expose.
 * - For secrets, use backend environment variables and pass them via secure API endpoints.
 */
