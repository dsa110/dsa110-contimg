/**
 * LoginPage - Authentication page with login form
 *
 * Features:
 * - Username/password form with validation
 * - Demo users info panel for development
 * - Remember me option
 * - Redirect to original destination after login
 * - Error handling and loading states
 */
import { useState, useEffect, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

interface LocationState {
  from?: { pathname: string };
}

/**
 * Demo users info for development
 */
const DEMO_USERS = [
  {
    username: "admin",
    password: "admin",
    role: "Admin",
    description: "Full access to all features",
  },
  {
    username: "operator",
    password: "operator",
    role: "Operator",
    description: "Can run jobs and rate images",
  },
  {
    username: "viewer",
    password: "viewer",
    role: "Viewer",
    description: "Read-only access",
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Get redirect destination from location state
  const from = (location.state as LocationState)?.from?.pathname || "/";

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  // Clear errors on input change
  useEffect(() => {
    if (error || validationError) {
      clearError();
      setValidationError(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [username, password]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    // Validate inputs
    if (!username.trim()) {
      setValidationError("Username is required");
      return;
    }
    if (!password.trim()) {
      setValidationError("Password is required");
      return;
    }

    try {
      await login({ username: username.trim(), password, rememberMe });
      // Navigation happens via the useEffect when isAuthenticated changes
    } catch {
      // Error is handled by the store
    }
  };

  /**
   * Fill in demo user credentials
   */
  const fillDemoUser = (demoUser: { username: string; password: string }) => {
    setUsername(demoUser.username);
    setPassword(demoUser.password);
  };

  const displayError = validationError || error;

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-bg-default)" }}
    >
      <div className="w-full max-w-md">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: "var(--color-primary)" }}
          >
            DSA-110 Pipeline
          </h1>
          <p style={{ color: "var(--color-text-secondary)" }}>
            Sign in to access the continuum imaging pipeline
          </p>
        </div>

        {/* Login Card */}
        <div
          className="rounded-lg p-6 shadow-lg"
          style={{
            backgroundColor: "var(--color-bg-paper)",
            border: "1px solid var(--color-border)",
          }}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error Display */}
            {displayError && (
              <div
                className="p-3 rounded-md text-sm"
                style={{
                  backgroundColor: "var(--color-danger-bg)",
                  color: "var(--color-danger)",
                  border: "1px solid var(--color-danger)",
                }}
                role="alert"
              >
                {displayError}
              </div>
            )}

            {/* Username Field */}
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium mb-1"
                style={{ color: "var(--color-text-primary)" }}
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 rounded-md transition-colors"
                style={{
                  backgroundColor: "var(--color-bg-surface)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-primary)",
                }}
                placeholder="Enter your username"
                autoComplete="username"
                autoFocus
                disabled={isLoading}
              />
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium mb-1"
                style={{ color: "var(--color-text-primary)" }}
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-md transition-colors"
                style={{
                  backgroundColor: "var(--color-bg-surface)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-primary)",
                }}
                placeholder="Enter your password"
                autoComplete="current-password"
                disabled={isLoading}
              />
            </div>

            {/* Remember Me */}
            <div className="flex items-center">
              <input
                id="rememberMe"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-4 h-4 rounded"
                disabled={isLoading}
              />
              <label
                htmlFor="rememberMe"
                className="ml-2 text-sm"
                style={{ color: "var(--color-text-secondary)" }}
              >
                Remember me for 30 days
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 px-4 rounded-md font-medium transition-colors disabled:opacity-50"
              style={{
                backgroundColor: "var(--color-primary)",
                color: "white",
              }}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg
                    className="animate-spin h-4 w-4"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Signing in...
                </span>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>

        {/* Demo Users Panel */}
        <div
          className="mt-6 rounded-lg p-4"
          style={{
            backgroundColor: "var(--color-bg-paper)",
            border: "1px solid var(--color-border)",
          }}
        >
          <h3
            className="text-sm font-medium mb-3"
            style={{ color: "var(--color-text-primary)" }}
          >
            Demo Accounts
          </h3>
          <div className="space-y-2">
            {DEMO_USERS.map((user) => (
              <button
                key={user.username}
                type="button"
                onClick={() => fillDemoUser(user)}
                className="w-full text-left p-2 rounded-md transition-colors hover:opacity-80"
                style={{
                  backgroundColor: "var(--color-bg-surface)",
                  border: "1px solid var(--color-border)",
                }}
                disabled={isLoading}
              >
                <div className="flex items-center justify-between">
                  <span
                    className="font-medium text-sm"
                    style={{ color: "var(--color-text-primary)" }}
                  >
                    {user.username}
                  </span>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{
                      backgroundColor: "var(--color-primary)",
                      color: "white",
                    }}
                  >
                    {user.role}
                  </span>
                </div>
                <p
                  className="text-xs mt-1"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {user.description}
                </p>
              </button>
            ))}
          </div>
          <p
            className="text-xs mt-3"
            style={{ color: "var(--color-text-muted)" }}
          >
            Click on a demo account to auto-fill credentials
          </p>
        </div>

        {/* Footer */}
        <p
          className="text-center text-xs mt-6"
          style={{ color: "var(--color-text-muted)" }}
        >
          DSA-110 Continuum Imaging Pipeline • Deep Synoptic Array
        </p>
      </div>
    </div>
  );
}
