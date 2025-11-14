/**
 * CARTA Iframe Component - Option 1: Quick validation with iframe embedding
 *
 * Embeds CARTA frontend in an iframe for quick integration.
 * This provides full CARTA functionality with minimal code changes.
 */

import { Box, Paper, Alert, CircularProgress } from "@mui/material";
import { useState, useEffect } from "react";
import { logger } from "../../utils/logger";

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
      setLoading(false);
      logger.info("CARTA iframe URL configured", { url: url.toString() });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to configure CARTA URL";
      logger.error("Failed to configure CARTA iframe:", err);
      setError(errorMessage);
      setLoading(false);
    }
  }, [cartaBackendUrl, cartaFrontendUrl, fitsFilePath, queryParams]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height={height} width={width}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Failed to configure CARTA: {error}
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
        }}
        onError={(e) => {
          logger.error("CARTA iframe failed to load", e);
          setError("Failed to load CARTA viewer");
        }}
      />
    </Paper>
  );
}
