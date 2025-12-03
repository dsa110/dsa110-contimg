/**
 * Authentication Store
 *
 * Zustand store for managing authentication state.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
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
}

type AuthStore = AuthState & AuthActions;

// Token storage key
const TOKEN_KEY = "dsa110_auth_tokens";

/**
 * Parse JWT token to extract expiration
 */
function parseJwt(token: string): { exp?: number } | null {
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
 * Simulated API call for login
 * In production, this would call the backend auth endpoint
 */
async function apiLogin(
  credentials: LoginCredentials
): Promise<{ user: User; tokens: AuthTokens }> {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500));

  // Demo users for development
  const demoUsers: Record<string, { password: string; user: User }> = {
    admin: {
      password: "admin",
      user: {
        id: "user-001",
        username: "admin",
        email: "admin@dsa110.caltech.edu",
        role: "admin",
        fullName: "System Administrator",
        createdAt: "2024-01-01T00:00:00Z",
        lastLogin: new Date().toISOString(),
      },
    },
    operator: {
      password: "operator",
      user: {
        id: "user-002",
        username: "operator",
        email: "operator@dsa110.caltech.edu",
        role: "operator",
        fullName: "Pipeline Operator",
        createdAt: "2024-01-15T00:00:00Z",
        lastLogin: new Date().toISOString(),
      },
    },
    viewer: {
      password: "viewer",
      user: {
        id: "user-003",
        username: "viewer",
        email: "viewer@dsa110.caltech.edu",
        role: "viewer",
        fullName: "Read-only User",
        createdAt: "2024-02-01T00:00:00Z",
        lastLogin: new Date().toISOString(),
      },
    },
  };

  const demoUser = demoUsers[credentials.username];
  if (!demoUser || demoUser.password !== credentials.password) {
    throw new Error("Invalid username or password");
  }

  // Generate mock tokens
  const expiresIn = credentials.rememberMe ? 86400 * 30 : 3600; // 30 days or 1 hour
  const tokens: AuthTokens = {
    accessToken: `demo_access_${Date.now()}`,
    refreshToken: credentials.rememberMe
      ? `demo_refresh_${Date.now()}`
      : undefined,
    tokenType: "Bearer",
    expiresIn,
  };

  return { user: demoUser.user, tokens };
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
          // In production, this would call the backend refresh endpoint
          // For demo, just extend the token
          const newTokens: AuthTokens = {
            ...tokens,
            accessToken: `demo_access_${Date.now()}`,
            expiresIn: 3600,
          };
          set({ tokens: newTokens, isLoading: false });
        } catch (error) {
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
          // For demo tokens, check against stored expiration
          return false;
        }
        return Date.now() >= payload.exp * 1000;
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
