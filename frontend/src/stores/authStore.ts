/**
 * Authentication Store
 *
 * Zustand store for managing authentication state.
 * Connects to the backend /api/v1/auth/* endpoints.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import apiClient from "../api/client";
import type {
  User,
  AuthTokens,
  LoginCredentials,
  AuthState,
  UserRole,
} from "../types/auth";

interface AuthActions {
  /** Log in with credentials */
  login: (credentials: LoginCredentials) => Promise<void>;
  /** Log out the current user */
  logout: () => void;
  /** Refresh the access token */
  refreshTokens: () => Promise<void>;
  /** Update user profile */
  updateUser: (updates: Partial<User>) => void;
  /** Clear any error */
  clearError: () => void;
  /** Set loading state */
  setLoading: (isLoading: boolean) => void;
  /** Check if token is expired */
  isTokenExpired: () => boolean;
  /** Fetch current user from API */
  fetchCurrentUser: () => Promise<void>;
}

type AuthStore = AuthState & AuthActions;

// Token storage key
const TOKEN_KEY = "dsa110_auth_tokens";

// API base path
const AUTH_API_BASE = "/api/v1/auth";

/**
 * Parse JWT token to extract expiration
 */
function parseJwt(token: string): { exp?: number; sub?: string } | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

/**
 * API response types matching backend schemas
 */
interface ApiLoginResponse {
  user: {
    id: string;
    username: string;
    email: string;
    role: string;
    full_name?: string;
    created_at?: string;
    last_login?: string;
  };
  tokens: {
    access_token: string;
    refresh_token?: string;
    token_type: string;
    expires_in: number;
  };
}

interface ApiUserResponse {
  id: string;
  username: string;
  email: string;
  role: string;
  full_name?: string;
  created_at?: string;
  last_login?: string;
}

interface ApiTokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

/**
 * Convert API user response to frontend User type
 */
function mapApiUser(apiUser: ApiUserResponse): User {
  return {
    id: apiUser.id,
    username: apiUser.username,
    email: apiUser.email,
    role: apiUser.role as UserRole,
    fullName: apiUser.full_name,
    createdAt: apiUser.created_at,
    lastLogin: apiUser.last_login,
  };
}

/**
 * Convert API token response to frontend AuthTokens type
 */
function mapApiTokens(apiTokens: ApiTokenResponse): AuthTokens {
  return {
    accessToken: apiTokens.access_token,
    refreshToken: apiTokens.refresh_token,
    tokenType: apiTokens.token_type,
    expiresIn: apiTokens.expires_in,
  };
}

/**
 * Call the backend login API
 */
async function apiLogin(
  credentials: LoginCredentials
): Promise<{ user: User; tokens: AuthTokens }> {
  const response = await apiClient.post<ApiLoginResponse>(
    `${AUTH_API_BASE}/login`,
    {
      username: credentials.username,
      password: credentials.password,
      remember_me: credentials.rememberMe ?? false,
    }
  );

  return {
    user: mapApiUser(response.data.user),
    tokens: mapApiTokens(response.data.tokens),
  };
}

/**
 * Call the backend refresh API
 */
async function apiRefresh(refreshToken: string): Promise<AuthTokens> {
  const response = await apiClient.post<ApiTokenResponse>(
    `${AUTH_API_BASE}/refresh`,
    {
      refresh_token: refreshToken,
    }
  );

  return mapApiTokens(response.data);
}

/**
 * Call the backend logout API
 */
async function apiLogout(refreshToken?: string): Promise<void> {
  try {
    await apiClient.post(`${AUTH_API_BASE}/logout`, {
      refresh_token: refreshToken,
    });
  } catch {
    // Ignore logout errors - we'll clear local state anyway
  }
}

/**
 * Call the backend /me API to get current user
 */
async function apiGetCurrentUser(accessToken: string): Promise<User> {
  const response = await apiClient.get<ApiUserResponse>(`${AUTH_API_BASE}/me`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return mapApiUser(response.data);
}

/**
 * Authentication store using Zustand with persistence
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isLoading: false,
      isAuthenticated: false,
      error: null,
      tokens: null,

      // Actions
      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });
        try {
          const { user, tokens } = await apiLogin(credentials);
          set({
            user,
            tokens,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          set({
            user: null,
            tokens: null,
            isAuthenticated: false,
            isLoading: false,
            error: error instanceof Error ? error.message : "Login failed",
          });
          throw error;
        }
      },

      logout: () => {
        const { tokens } = get();
        // Call backend logout to invalidate refresh token
        apiLogout(tokens?.refreshToken);
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          error: null,
        });
        // Clear any stored tokens
        localStorage.removeItem(TOKEN_KEY);
      },

      refreshTokens: async () => {
        const { tokens } = get();
        if (!tokens?.refreshToken) {
          get().logout();
          return;
        }

        set({ isLoading: true });
        try {
          const newTokens = await apiRefresh(tokens.refreshToken);
          set({
            tokens: newTokens,
            isLoading: false,
          });
        } catch {
          // Refresh failed - log out
          get().logout();
        }
      },

      fetchCurrentUser: async () => {
        const { tokens } = get();
        if (!tokens?.accessToken) {
          return;
        }

        set({ isLoading: true });
        try {
          const user = await apiGetCurrentUser(tokens.accessToken);
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch {
          // Token invalid - log out
          get().logout();
        }
      },

      updateUser: (updates: Partial<User>) => {
        const { user } = get();
        if (user) {
          set({ user: { ...user, ...updates } });
        }
      },

      clearError: () => set({ error: null }),

      setLoading: (isLoading: boolean) => set({ isLoading }),

      isTokenExpired: () => {
        const { tokens } = get();
        if (!tokens?.accessToken) return true;

        const payload = parseJwt(tokens.accessToken);
        if (!payload?.exp) {
          // If no expiration in token, assume valid
          return false;
        }
        // Add 30 second buffer for clock skew
        return Date.now() >= (payload.exp * 1000) - 30000;
      },
    }),
    {
      name: "dsa110-auth",
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

/**
 * Hook to get authentication status
 */
export function useAuth() {
  const { user, isAuthenticated, isLoading, error, login, logout } =
    useAuthStore();
  return { user, isAuthenticated, isLoading, error, login, logout };
}

/**
 * Hook to check user permissions
 */
export function usePermissions() {
  const user = useAuthStore((state) => state.user);

  return {
    hasRole: (role: UserRole) => user?.role === role,
    isAdmin: user?.role === "admin",
    isOperator: user?.role === "operator" || user?.role === "admin",
    isViewer: !!user,
    canWrite: user?.role === "operator" || user?.role === "admin",
  };
}
