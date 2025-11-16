/**
 * CARTA Iframe Component - Option 1: Quick validation with iframe embedding
 *
 * Embeds CARTA frontend in an iframe for quick integration.
 * This provides full CARTA functionality with minimal code changes.
 */

import { Box, Paper, Alert, CircularProgress, Typography, Button } from "@mui/material";
import { useState, useEffect, useRef } from "react";
import { logger } from "../../utils/logger";

// API base URL - use environment variable or default to localhost
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface CARTAIframeProps {
  /** CARTA backend URL (e.g., "http://localhost:9002") */
  cartaBackendUrl?: string;
  /** CARTA frontend URL (e.g., "http://localhost:9003") - overrides environment variable */
  cartaFrontendUrl?: string;
  /** Initial FITS file path to open */
  fitsFilePath?: string;
  /** Height of the iframe */
  height?: string;
  /** Width of the iframe */
  width?: string;
  /** Additional query parameters to pass to CARTA */
  queryParams?: Record<string, string>;
}

/**
 * CARTAIframe - Embeds CARTA frontend in an iframe
 *
 * This component provides a quick way to integrate CARTA by embedding
 * the CARTA frontend application in an iframe. The CARTA backend should
 * be running separately.
 */
export default function CARTAIframe({
  cartaBackendUrl,
  cartaFrontendUrl,
  fitsFilePath,
  height = "800px",
  width = "100%",
  queryParams = {},
}: CARTAIframeProps) {
  const [cartaUrl, setCartaUrl] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionChecked, setConnectionChecked] = useState(false);
  const [starting, setStarting] = useState(false);
  const [autoStartAttempted, setAutoStartAttempted] = useState(false);
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    try {
      // Get CARTA frontend URL from prop, environment, or use default
      // Port 9003 is in the 9000-9099 range for External Integrations
      // Prop takes precedence over environment variable
      const frontendUrl =
        cartaFrontendUrl || import.meta.env.VITE_CARTA_FRONTEND_URL || "http://localhost:9003";
      const url = new URL(frontendUrl);

      // Add backend URL if provided
      if (cartaBackendUrl) {
        url.searchParams.set("backend", cartaBackendUrl);
      } else {
        // Use environment variable as fallback
        const envBackendUrl = import.meta.env.VITE_CARTA_BACKEND_URL;
        if (envBackendUrl) {
          url.searchParams.set("backend", envBackendUrl);
        }
      }

      // Add initial file path if provided
      if (fitsFilePath) {
        url.searchParams.set("file", fitsFilePath);
      }

      // Add any additional query parameters
      Object.entries(queryParams).forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });

      setCartaUrl(url.toString());
      logger.info("CARTA iframe URL configured", { url: url.toString() });

      // Set loading to false - the iframe will handle connection errors
      setLoading(false);

      // Set a timeout to check connection and potentially start CARTA
      const timeoutId = setTimeout(async () => {
        if (!connectionChecked && !autoStartAttempted) {
          setConnectionChecked(true);
          // Check CARTA status and try to start if needed
          const frontendUrlCheck =
            cartaFrontendUrl || import.meta.env.VITE_CARTA_FRONTEND_URL || "http://localhost:9003";
          await checkAndStartCARTA(frontendUrlCheck);
        }
      }, 5000); // Reduced timeout to 5 seconds for faster auto-start

      return () => {
        clearTimeout(timeoutId);
        // Clear any active polling interval on unmount
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to configure CARTA URL";
      logger.error("Failed to configure CARTA iframe:", err);
      setError(errorMessage);
      setLoading(false);
    }
  }, [cartaBackendUrl, cartaFrontendUrl, fitsFilePath, queryParams]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
        checkIntervalRef.current = null;
      }
    };
  }, []);

  /**
   * Check CARTA status and automatically start if not running
   */
  const checkAndStartCARTA = async (frontendUrl: string) => {
    if (autoStartAttempted || starting) {
      return; // Already attempted or in progress
    }

    setAutoStartAttempted(true);
    setStarting(true);

    try {
      // Check CARTA status
      const statusResponse = await fetch(`${API_BASE}/api/visualization/carta/status`);
      if (!statusResponse.ok) {
        throw new Error("Failed to check CARTA status");
      }

      const status = await statusResponse.json();

      // If CARTA is already running, clear error and reload
      if (status.running && status.backend_healthy) {
        logger.info("CARTA is running, reloading iframe");
        setError(null);
        setStarting(false);
        // Reload the iframe by updating the URL
        setCartaUrl((prev) => prev + (prev.includes("?") ? "&" : "?") + `_t=${Date.now()}`);
        return;
      }

      // CARTA is not running, try to start it
      logger.info("CARTA is not running, attempting to start...");
      const startResponse = await fetch(`${API_BASE}/api/visualization/carta/start`, {
        method: "POST",
      });

      if (!startResponse.ok) {
        const errorData = await startResponse.json();
        throw new Error(errorData.detail || "Failed to start CARTA");
      }

      const startResult = await startResponse.json();

      if (startResult.success) {
        logger.info("CARTA start initiated, waiting for services to be ready...", startResult);

        // Wait for services to be ready (poll status)
        let attempts = 0;
        const maxAttempts = 30; // 30 seconds max wait

        // Clear any existing interval before creating a new one
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }

        checkIntervalRef.current = setInterval(async () => {
          attempts++;
          try {
            const checkResponse = await fetch(`${API_BASE}/api/visualization/carta/status`);
            if (checkResponse.ok) {
              const checkStatus = await checkResponse.json();
              if (checkStatus.running && checkStatus.backend_healthy) {
                if (checkIntervalRef.current) {
                  clearInterval(checkIntervalRef.current);
                  checkIntervalRef.current = null;
                }
                logger.info("CARTA services are ready");
                setError(null);
                setStarting(false);
                // Reload the iframe
                setCartaUrl((prev) => prev + (prev.includes("?") ? "&" : "?") + `_t=${Date.now()}`);
              } else if (attempts >= maxAttempts) {
                if (checkIntervalRef.current) {
                  clearInterval(checkIntervalRef.current);
                  checkIntervalRef.current = null;
                }
                setStarting(false);
                setError(
                  `CARTA services started but not ready after ${maxAttempts} seconds. ` +
                    `Please check CARTA services manually:\n` +
                    `- CARTA Frontend: ${frontendUrl}\n` +
                    `- CARTA Backend: ${cartaBackendUrl || import.meta.env.VITE_CARTA_BACKEND_URL || "ws://localhost:9002"}`
                );
              }
            }
          } catch (err) {
            if (attempts >= maxAttempts) {
              if (checkIntervalRef.current) {
                clearInterval(checkIntervalRef.current);
                checkIntervalRef.current = null;
              }
              setStarting(false);
              logger.error("Failed to check CARTA status after start", err);
            }
          }
        }, 1000); // Check every second
      } else {
        // Start failed
        setStarting(false);
        setError(
          `Failed to start CARTA: ${startResult.message}\n\n` +
            `Please ensure CARTA services are running:\n` +
            `- CARTA Frontend: ${frontendUrl}\n` +
            `- CARTA Backend: ${cartaBackendUrl || import.meta.env.VITE_CARTA_BACKEND_URL || "ws://localhost:9002"}`
        );
      }
    } catch (err) {
      setStarting(false);
      const errorMessage = err instanceof Error ? err.message : "Failed to start CARTA";
      logger.error("Error starting CARTA", err);
      setError(
        `${errorMessage}\n\n` +
          `Please ensure CARTA services are running:\n` +
          `- CARTA Frontend: ${frontendUrl}\n` +
          `- CARTA Backend: ${cartaBackendUrl || import.meta.env.VITE_CARTA_BACKEND_URL || "ws://localhost:9002"}`
      );
    }
  };

  /**
   * Manual retry to start CARTA
   */
  const handleRetryStart = async () => {
    const frontendUrl =
      cartaFrontendUrl || import.meta.env.VITE_CARTA_FRONTEND_URL || "http://localhost:9003";
    setAutoStartAttempted(false);
    setError(null);
    await checkAndStartCARTA(frontendUrl);
  };

  if (loading || starting) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        height={height}
        width={width}
      >
        <CircularProgress />
        {starting && (
          <Typography variant="body1" sx={{ mt: 2 }}>
            Starting CARTA services...
          </Typography>
        )}
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2, whiteSpace: "pre-line" }} title="CARTA Connection Error">
        <Typography variant="h6" gutterBottom>
          CARTA Services Not Available
        </Typography>
        {error}
        <Box sx={{ mt: 2 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleRetryStart}
            disabled={starting}
            sx={{ mb: 2 }}
          >
            {starting ? "Starting..." : "Try Starting CARTA Automatically"}
          </Button>
          <Typography variant="body2" color="text.secondary">
            To use CARTA, you need to have CARTA services running:
          </Typography>
          <Typography component="pre" variant="body2" sx={{ mt: 1, fontSize: "0.875rem" }}>
            {`CARTA Frontend: ${cartaFrontendUrl || import.meta.env.VITE_CARTA_FRONTEND_URL || "http://localhost:9003"}
CARTA Backend: ${cartaBackendUrl || import.meta.env.VITE_CARTA_BACKEND_URL || "ws://localhost:9002"}`}
          </Typography>
        </Box>
      </Alert>
    );
  }

  if (!cartaUrl) {
    return (
      <Alert severity="warning" sx={{ m: 2 }}>
        CARTA frontend URL not configured. Set VITE_CARTA_FRONTEND_URL environment variable.
      </Alert>
    );
  }

  return (
    <Paper
      sx={{
        height,
        width,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        component="iframe"
        src={cartaUrl}
        sx={{
          width: "100%",
          height: "100%",
          border: "none",
          flex: 1,
        }}
        title="CARTA Viewer"
        allow="fullscreen"
        onLoad={() => {
          logger.info("CARTA iframe loaded successfully");
          setConnectionChecked(true);
          setError(null); // Clear any timeout errors if iframe loads
        }}
        onError={(e) => {
          logger.error("CARTA iframe failed to load", e);
          setConnectionChecked(true);
          setError(
            `Failed to load CARTA viewer from ${cartaFrontendUrl || import.meta.env.VITE_CARTA_FRONTEND_URL || "http://localhost:9003"}. ` +
              `Please ensure CARTA frontend service is running.`
          );
        }}
      />
    </Paper>
  );
}
