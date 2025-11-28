/**
 * TabErrorBoundary - Lightweight error boundary for tab-level isolation
 *
 * Unlike the main ErrorBoundary, this component:
 * - Shows a compact inline error message
 * - Doesn't navigate away or require full page reload
 * - Provides quick retry functionality
 * - Isolates failures to individual tabs
 */
import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { Box, Typography, Button, Alert, Stack } from "@mui/material";
import { Refresh, ExpandMore, ExpandLess } from "@mui/icons-material";
import { classifyError } from "../utils/errorUtils";
import { captureError } from "../utils/errorTracking";

interface Props {
  children: ReactNode;
  /** Name of the tab for error reporting */
  tabName: string;
  /** Custom fallback UI */
  fallback?: ReactNode;
  /** Callback when error occurs */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

class TabErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[${this.props.tabName}] Tab error:`, error, errorInfo);

    // Capture for error tracking
    captureError(error, {
      componentStack: errorInfo.componentStack,
      tabName: this.props.tabName,
      errorBoundary: "tab",
    });

    // Call optional callback
    this.props.onError?.(error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    });
  };

  toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error, errorInfo, showDetails } = this.state;
      const classified = error ? classifyError(error) : null;
      const isDev = import.meta.env.DEV;

      return (
        <Box sx={{ p: 2 }}>
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" startIcon={<Refresh />} onClick={this.handleRetry}>
                Retry
              </Button>
            }
          >
            <Typography variant="body2" fontWeight="medium">
              {this.props.tabName} failed to load
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {classified?.message ?? "An unexpected error occurred"}
            </Typography>
          </Alert>

          {/* Development-only details toggle */}
          {isDev && error && (
            <Box sx={{ mt: 1 }}>
              <Button
                size="small"
                onClick={this.toggleDetails}
                endIcon={showDetails ? <ExpandLess /> : <ExpandMore />}
                sx={{ textTransform: "none" }}
              >
                {showDetails ? "Hide details" : "Show details"}
              </Button>

              {showDetails && (
                <Box
                  sx={{
                    mt: 1,
                    p: 2,
                    bgcolor: "#1e1e1e",
                    borderRadius: 1,
                    overflow: "auto",
                    maxHeight: 300,
                  }}
                >
                  <Typography
                    variant="caption"
                    component="pre"
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                      color: "#ff6b6b",
                      margin: 0,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {error.toString()}
                    {errorInfo?.componentStack && (
                      <>
                        {"\n\nComponent Stack:"}
                        {errorInfo.componentStack}
                      </>
                    )}
                  </Typography>
                  {classified && (
                    <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Type: {classified.type}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Retryable: {classified.retryable ? "Yes" : "No"}
                      </Typography>
                      {classified.statusCode && (
                        <Typography variant="caption" color="text.secondary">
                          Status: {classified.statusCode}
                        </Typography>
                      )}
                    </Stack>
                  )}
                </Box>
              )}
            </Box>
          )}
        </Box>
      );
    }

    return this.props.children;
  }
}

export default TabErrorBoundary;
