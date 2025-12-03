/**
 * Authentication Types
 *
 * Types for user authentication and authorization.
 */

/**
 * User role for authorization
 */
export type UserRole = "viewer" | "operator" | "admin";

/**
 * Authenticated user information
 */
export interface User {
  /** Unique user identifier */
  id: string;
  /** Username for display */
  username: string;
  /** Email address */
  email: string;
  /** User's role */
  role: UserRole;
  /** User's full name (optional) */
  fullName?: string;
  /** Avatar URL (optional) */
  avatarUrl?: string;
  /** When the user was created */
  createdAt?: string;
  /** Last login timestamp */
  lastLogin?: string;
}

/**
 * Login credentials
 */
export interface LoginCredentials {
  /** Username or email */
  username: string;
  /** Password */
  password: string;
  /** Remember login across sessions */
  rememberMe?: boolean;
}

/**
 * Authentication token response
 */
export interface AuthTokens {
  /** Access token for API requests */
  accessToken: string;
  /** Refresh token for obtaining new access tokens */
  refreshToken?: string;
  /** Token type (usually 'Bearer') */
  tokenType: string;
  /** Access token expiration in seconds */
  expiresIn: number;
}

/**
 * Authentication state
 */
export interface AuthState {
  /** Current authenticated user */
  user: User | null;
  /** Whether authentication is loading */
  isLoading: boolean;
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  /** Authentication error message */
  error: string | null;
  /** Auth tokens */
  tokens: AuthTokens | null;
}

/**
 * Permission levels for features
 */
export const PERMISSIONS = {
  // Read operations
  VIEW_IMAGES: ["viewer", "operator", "admin"],
  VIEW_SOURCES: ["viewer", "operator", "admin"],
  VIEW_JOBS: ["viewer", "operator", "admin"],
  VIEW_HEALTH: ["viewer", "operator", "admin"],

  // Write operations
  CREATE_JOB: ["operator", "admin"],
  REIMAGE: ["operator", "admin"],
  RATE_IMAGE: ["operator", "admin"],
  CANCEL_JOB: ["operator", "admin"],

  // Admin operations
  MANAGE_USERS: ["admin"],
  MANAGE_SETTINGS: ["admin"],
  CLEAR_CACHE: ["admin"],
  DELETE_DATA: ["admin"],
} as const;

export type Permission = keyof typeof PERMISSIONS;

/**
 * Check if a user has a specific permission
 */
export function hasPermission(
  user: User | null,
  permission: Permission
): boolean {
  if (!user) return false;
  const allowedRoles = PERMISSIONS[permission];
  return allowedRoles.includes(user.role);
}
