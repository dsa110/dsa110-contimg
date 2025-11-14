/**
 * Form Validation Utilities
 * Provides inline validation helpers for forms
 */

export interface ValidationRule<T = any> {
  validate: (value: T) => boolean;
  message: string;
}

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

/**
 * Validates a value against multiple rules
 */
export function validateValue<T>(value: T, rules: ValidationRule<T>[]): ValidationResult {
  for (const rule of rules) {
    if (!rule.validate(value)) {
      return {
        isValid: false,
        error: rule.message,
      };
    }
  }
  return { isValid: true };
}

/**
 * Common validation rules
 */
export const validationRules = {
  required: <T>(message = "This field is required"): ValidationRule<T> => ({
    validate: (value: T) => {
      if (value === null || value === undefined) return false;
      if (typeof value === "string") return value.trim().length > 0;
      if (Array.isArray(value)) return value.length > 0;
      return true;
    },
    message,
  }),

  minLength: (min: number, message?: string): ValidationRule<string> => ({
    validate: (value: string) => value.length >= min,
    message: message || `Must be at least ${min} characters`,
  }),

  maxLength: (max: number, message?: string): ValidationRule<string> => ({
    validate: (value: string) => value.length <= max,
    message: message || `Must be no more than ${max} characters`,
  }),

  email: (message = "Invalid email address"): ValidationRule<string> => ({
    validate: (value: string) => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(value);
    },
    message,
  }),

  url: (message = "Invalid URL"): ValidationRule<string> => ({
    validate: (value: string) => {
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message,
  }),

  number: (message = "Must be a number"): ValidationRule<string | number> => ({
    validate: (value: string | number) => !isNaN(Number(value)),
    message,
  }),

  min: (min: number, message?: string): ValidationRule<number> => ({
    validate: (value: number) => value >= min,
    message: message || `Must be at least ${min}`,
  }),

  max: (max: number, message?: string): ValidationRule<number> => ({
    validate: (value: number) => value <= max,
    message: message || `Must be no more than ${max}`,
  }),

  range: (min: number, max: number, message?: string): ValidationRule<number> => ({
    validate: (value: number) => value >= min && value <= max,
    message: message || `Must be between ${min} and ${max}`,
  }),

  pattern: (regex: RegExp, message: string): ValidationRule<string> => ({
    validate: (value: string) => regex.test(value),
    message,
  }),

  path: (message = "Invalid file path"): ValidationRule<string> => ({
    validate: (value: string) => {
      // Basic path validation (Unix-style)
      return /^(\/|\.\/|\.\.\/)?([\w\-\.\/]+)*$/.test(value);
    },
    message,
  }),

  timeRange: (
    message = "End time must be after start time"
  ): ValidationRule<{
    start: string;
    end: string;
  }> => ({
    validate: (value: { start: string; end: string }) => {
      if (!value.start || !value.end) return true; // Let required rule handle empty values
      const start = new Date(value.start);
      const end = new Date(value.end);
      return end > start;
    },
    message,
  }),
};

/**
 * Hook-like function for real-time validation
 */
export function useFieldValidation<T>(value: T, rules: ValidationRule<T>[]): ValidationResult {
  return validateValue(value, rules);
}
