/**
 * Authentication hook for accessing auth state and actions
 */
import { useCallback } from "react";
import { useAuthStore } from "@/stores/authStore";
import { hasPermission, type Permission } from "@/types/auth";

/**
 * Hook for authentication state and actions
 */
export function useAuth() {
  const {
    user,
    tokens,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    refreshTokens,
    clearError,
  } = useAuthStore();

  /**
   * Check if current user has a specific permission
   */
  const checkPermission = useCallback(
    (permission: Permission): boolean => {
      return hasPermission(user, permission);
    },
    [user]
  );

  /**
   * Check if current user has any of the specified permissions
   */
  const hasAnyPermission = useCallback(
    (permissions: Permission[]): boolean => {
      return permissions.some((permission) => hasPermission(user, permission));
    },
    [user]
  );

  /**
   * Check if current user has all of the specified permissions
   */
  const hasAllPermissions = useCallback(
    (permissions: Permission[]): boolean => {
      return permissions.every((permission) => hasPermission(user, permission));
    },
    [user]
  );

  return {
    // State
    user,
    tokens,
    isAuthenticated,
    isLoading,
    error,

    // Actions
    login,
    logout,
    refreshTokens,
    clearError,

    // Permission helpers
    checkPermission,
    hasAnyPermission,
    hasAllPermissions,
  };
}

/**
 * Hook for checking a single permission
 * Useful for conditional rendering
 */
export function usePermission(permission: Permission): boolean {
  const user = useAuthStore((state) => state.user);
  return hasPermission(user, permission);
}

/**
 * Hook for accessing just the current user
 */
export function useCurrentUser() {
  return useAuthStore((state) => state.user);
}

/**
 * Hook for accessing auth loading state
 */
export function useAuthLoading() {
  return useAuthStore((state) => state.isLoading);
}
