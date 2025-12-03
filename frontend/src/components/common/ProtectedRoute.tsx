/**
 * ProtectedRoute - Route guard component for authentication
 * Redirects unauthenticated users and enforces permissions
 */
import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth, usePermission } from "../../hooks/useAuth";
import type { Permission, UserRole } from "../../types/auth";

export interface ProtectedRouteProps {
  children: ReactNode;
  /** Required permission to access this route */
  permission?: Permission;
  /** Required roles (any of these) to access this route */
  requiredRoles?: UserRole[];
  /** Custom redirect path when unauthorized (default: /login) */
  redirectTo?: string;
  /** Custom fallback when loading auth state */
  loadingFallback?: ReactNode;
  /** Custom fallback when permission denied */
  unauthorizedFallback?: ReactNode;
}

/**
 * Loading state component
 */
function DefaultLoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
    </div>
  );
}

/**
 * Unauthorized state component
 */
function DefaultUnauthorizedFallback() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
        Access Denied
      </h1>
      <p className="text-gray-600 dark:text-gray-400">
        You don't have permission to access this page.
      </p>
    </div>
  );
}

/**
 * ProtectedRoute component
 */
export function ProtectedRoute({
  children,
  permission,
  requiredRoles,
  redirectTo = "/login",
  loadingFallback = <DefaultLoadingFallback />,
  unauthorizedFallback = <DefaultUnauthorizedFallback />,
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const hasRequiredPermission = permission ? usePermission(permission) : true;

  // Show loading state while checking auth
  if (isLoading) {
    return <>{loadingFallback}</>;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // Check role requirements
  if (requiredRoles && requiredRoles.length > 0) {
    if (!requiredRoles.includes(user.role)) {
      return <>{unauthorizedFallback}</>;
    }
  }

  // Check permission requirements
  if (permission && !hasRequiredPermission) {
    return <>{unauthorizedFallback}</>;
  }

  return <>{children}</>;
}

/**
 * HOC for protecting components with permission checks
 */
export function withPermission<P extends object>(
  Component: React.ComponentType<P>,
  permission: Permission
) {
  return function ProtectedComponent(props: P) {
    const hasAccess = usePermission(permission);

    if (!hasAccess) {
      return null;
    }

    return <Component {...props} />;
  };
}

/**
 * Component that only renders children if user has permission
 */
export function RequirePermission({
  permission,
  children,
  fallback = null,
}: {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const hasAccess = usePermission(permission);
  return hasAccess ? <>{children}</> : <>{fallback}</>;
}
