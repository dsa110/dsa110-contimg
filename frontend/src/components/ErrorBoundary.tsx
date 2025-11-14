/**
 * Error Boundary Component
 * Catches React rendering errors and displays a user-friendly error message
 */
import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { Box, Typography, Button, Paper, Alert, Stack, Card, CardContent } from "@mui/material";
import { ErrorOutline, Refresh, Home, Lightbulb } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { classifyError, getUserFriendlyMessage } from "../utils/errorUtils";
import { captureError } from "../utils/errorTracking";
import { getRecoverySuggestions } from "../utils/errorRecovery";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundaryInner extends Component<Props & { navigate: (path: string) => void }, State> {
  constructor(props: Props & { navigate: (path: string) => void }) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Use console.error here since logger might not be available if error occurs early
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    // Capture error to tracking service
    captureError(error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
    });

    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleGoHome = () => {
    this.handleReset();
    this.props.navigate("/dashboard");
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const error = this.state.error;
      const classified = error ? classifyError(error) : null;
      const userMessage = error ? getUserFriendlyMessage(error) : "An unexpected error occurred";
      const recoverySuggestions = classified ? getRecoverySuggestions(classified) : [];

      return (
        <Box sx={{ p: 3 }}>
          <Paper sx={{ p: 3 }}>
            <Alert severity="error" icon={<ErrorOutline />} sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Something went wrong
              </Typography>
              <Typography variant="body2">{userMessage}</Typography>
            </Alert>

            {/* Recovery Suggestions */}
            {recoverySuggestions.length > 0 && (
              <Card sx={{ mb: 2, bgcolor: "action.hover" }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <Lightbulb color="primary" fontSize="small" />
                    <Typography variant="subtitle2" fontWeight="bold">
                      Recovery Suggestions
                    </Typography>
                  </Stack>
                  <Stack spacing={1}>
                    {recoverySuggestions.map((suggestion, index) => (
                      <Box key={index}>
                        <Typography variant="body2" fontWeight="medium">
                          {suggestion.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {suggestion.description}
                        </Typography>
                        {suggestion.action && (
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={suggestion.action.onClick}
                            sx={{ mt: 0.5 }}
                          >
                            {suggestion.action.label}
                          </Button>
                        )}
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            )}

            <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
              <Button variant="contained" startIcon={<Refresh />} onClick={this.handleReset}>
                Try Again
              </Button>
              <Button variant="outlined" startIcon={<Home />} onClick={this.handleGoHome}>
                Go to Dashboard
              </Button>
            </Stack>

            {import.meta.env.DEV && error && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Error Details (Development Mode):
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    p: 2,
                    bgcolor: "#1e1e1e",
                    borderRadius: 1,
                    overflow: "auto",
                    fontSize: "0.75rem",
                    fontFamily: "monospace",
                    color: "#ff6b6b",
                    maxHeight: "400px",
                  }}
                >
                  {error.toString()}
                  {this.state.errorInfo?.componentStack && (
                    <>
                      {"\n\nComponent Stack:"}
                      {this.state.errorInfo.componentStack}
                    </>
                  )}
                </Box>
                {classified && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Error Type: {classified.type} | Retryable:{" "}
                      {classified.retryable ? "Yes" : "No"}
                      {classified.statusCode && ` | Status: ${classified.statusCode}`}
                    </Typography>
                  </Box>
                )}
              </Box>
            )}
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}

// Wrapper to use hooks
function ErrorBoundary(props: Props) {
  // Try to get navigate, but handle case where Router context might not be available
  let navigate: ((path: string) => void) | null = null;
  try {
    navigate = useNavigate();
  } catch (e) {
    // Router context not available, navigate will be null
    navigate = null;
  }

  const safeNavigate =
    navigate ||
    ((path: string) => {
      // Fallback: use window.location if navigate not available
      window.location.href = path;
    });

  return <ErrorBoundaryInner {...props} navigate={safeNavigate} />;
}

export default ErrorBoundary;
