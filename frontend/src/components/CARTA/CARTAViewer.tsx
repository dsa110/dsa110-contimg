/**
 * CARTA Viewer Component - Option 2: Full WebSocket integration
 *
 * Native React component that connects to CARTA backend via WebSocket.
 * Provides full integration with dashboard while using CARTA's rendering.
 */

import { useEffect, useRef, useState } from "react";
import { Box, CircularProgress, Alert, Paper, Typography, Button } from "@mui/material";
import { CARTAClient, CARTAConfig } from "../../services/cartaClient";
import { logger } from "../../utils/logger";

interface CARTAViewerProps {
  /** CARTA backend URL (e.g., "http://localhost:9002" or "ws://localhost:9002") */
  backendUrl?: string;
  /** Initial FITS file path to open */
  fitsFilePath?: string;
  /** Height of the viewer */
  height?: string;
  /** Width of the viewer */
  width?: string;
  /** Show connection status */
  showStatus?: boolean;
}

/**
 * CARTAViewer - Native React component for CARTA integration
 *
 * This component connects to CARTA backend via WebSocket and provides
 * a canvas-based rendering interface. Full implementation requires
 * CARTA Protocol Buffer definitions and rendering logic.
 */
export default function CARTAViewer({
  backendUrl,
  fitsFilePath,
  height = "800px",
  width = "100%",
  showStatus = true,
}: CARTAViewerProps) {
  const [client, setClient] = useState<CARTAClient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<string>("Disconnected");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const clientRef = useRef<CARTAClient | null>(null);

  // Get backend URL from props or environment
  // Port 9002 is in the 9000-9099 range for External Integrations
  const cartaBackendUrl =
    backendUrl || import.meta.env.VITE_CARTA_BACKEND_URL || "ws://localhost:9002";

  useEffect(() => {
    // Ensure we have a WebSocket URL
    const wsUrl = cartaBackendUrl.startsWith("ws")
      ? cartaBackendUrl
      : cartaBackendUrl.replace(/^http/, "ws");

    const config: CARTAConfig = {
      backendUrl: wsUrl,
    };

    const cartaClient = new CARTAClient(config);
    clientRef.current = cartaClient;

    // Set up message handlers
    cartaClient.onMessage("REGISTER_VIEWER_ACK", (message) => {
      logger.info("CARTA viewer registered", message);
      setStatus("Connected");
      setConnected(true);
      setLoading(false);

      // Open file if provided
      if (fitsFilePath) {
        cartaClient
          .openFile(fitsFilePath)
          .then(() => {
            setStatus("File opened");
          })
          .catch((err) => {
            logger.error("Failed to open file:", err);
            setError(`Failed to open file: ${err.message}`);
          });
      }
    });

    cartaClient.onMessage("OPEN_FILE_ACK", (message) => {
      logger.info("File opened in CARTA", message);
      setStatus("File loaded");
      // TODO: Handle file info and start rendering
    });

    cartaClient.onMessage("FILE_INFO", (message) => {
      logger.info("File info received", message);
      // TODO: Display file information
    });

    // Connect to CARTA backend
    setStatus("Connecting...");
    cartaClient
      .connect()
      .then(() => {
        setClient(cartaClient);
        setStatus("Connected");
        setConnected(true);
        setLoading(false);
      })
      .catch((err) => {
        logger.error("Failed to connect to CARTA:", err);
        setError(err instanceof Error ? err.message : "Failed to connect to CARTA backend");
        setStatus("Connection failed");
        setLoading(false);
      });

    // Cleanup on unmount
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }
    };
  }, [cartaBackendUrl]); // Only reconnect if backend URL changes

  // Handle file path changes
  useEffect(() => {
    if (client && fitsFilePath && connected) {
      client
        .openFile(fitsFilePath)
        .then(() => {
          setStatus("File opened");
          setError(null);
        })
        .catch((err) => {
          logger.error("Failed to open file:", err);
          setError(`Failed to open file: ${err.message}`);
        });
    }
  }, [fitsFilePath, client, connected]);

  // Render to canvas (placeholder - requires CARTA rendering implementation)
  useEffect(() => {
    if (!canvasRef.current || !connected) {
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    // Set canvas size
    const container = canvas.parentElement;
    if (container) {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
    }

    // Placeholder rendering
    ctx.fillStyle = "#1e1e1e";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#ffffff";
    ctx.font = "16px Arial";
    ctx.textAlign = "center";
    ctx.fillText(
      "CARTA Viewer - Rendering implementation pending",
      canvas.width / 2,
      canvas.height / 2
    );
    ctx.fillText(
      "Connect to CARTA backend to view FITS files",
      canvas.width / 2,
      canvas.height / 2 + 30
    );
  }, [connected]);

  const handleReconnect = () => {
    setError(null);
    setLoading(true);
    setStatus("Reconnecting...");

    if (clientRef.current) {
      clientRef.current.disconnect();
    }

    // Trigger reconnection by updating backend URL (will trigger useEffect)
    // In a real implementation, you'd call connect() directly
    window.location.reload();
  };

  if (loading) {
    return (
      <Paper
        sx={{
          height,
          width,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <CircularProgress />
        {showStatus && (
          <Typography variant="body2" sx={{ mt: 2 }}>
            {status}
          </Typography>
        )}
      </Paper>
    );
  }

  if (error && !connected) {
    return (
      <Paper sx={{ height, width, p: 2 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={handleReconnect}>
              Retry
            </Button>
          }
        >
          {error}
          {showStatus && (
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Status: {status}
            </Typography>
          )}
        </Alert>
      </Paper>
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
      {showStatus && (
        <Box
          sx={{
            p: 1,
            bgcolor: connected ? "success.dark" : "error.dark",
            color: "white",
          }}
        >
          <Typography variant="caption">
            CARTA: {status}
            {fitsFilePath && ` | File: ${fitsFilePath.split("/").pop()}`}
          </Typography>
        </Box>
      )}
      <Box
        sx={{
          flex: 1,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <Box
          component="canvas"
          ref={canvasRef}
          sx={{
            width: "100%",
            height: "100%",
            display: "block",
            cursor: "crosshair",
          }}
        />
        {error && connected && (
          <Alert severity="warning" sx={{ position: "absolute", top: 8, left: 8, right: 8 }}>
            {error}
          </Alert>
        )}
      </Box>
    </Paper>
  );
}
