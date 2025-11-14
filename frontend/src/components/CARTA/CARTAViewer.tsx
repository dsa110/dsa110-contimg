/**
 * CARTA Viewer Component - Option 2: Full WebSocket integration
 *
 * Native React component that connects to CARTA backend via WebSocket.
 * Provides full integration with dashboard while using CARTA's rendering.
 */

import { useEffect, useRef, useState } from "react";
import {
  Box,
  CircularProgress,
  Alert,
  Paper,
  Typography,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { CARTAClient, CARTAConfig } from "../../services/cartaClient";
import { logger } from "../../utils/logger";
import { CARTAImageRenderer } from "./CARTAImageRenderer";
import {
  CARTAMessageType,
  FileInfo,
  RasterTileData,
  SetRegionRequest,
  RegionType,
  Point,
} from "../../services/cartaProtobuf";

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
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [currentFileId, setCurrentFileId] = useState<number | null>(null);
  const [showFileInfo, setShowFileInfo] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const clientRef = useRef<CARTAClient | null>(null);
  const rendererRef = useRef<CARTAImageRenderer | null>(null);
  const regionsRef = useRef<Map<number, Point[]>>(new Map());

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

    cartaClient.onMessage(CARTAMessageType.OPEN_FILE_ACK, (ack: any) => {
      logger.info("File opened in CARTA", ack);
      setStatus("File loaded");
      if (ack.fileId !== undefined) {
        setCurrentFileId(ack.fileId);
      }
      if (ack.fileInfo) {
        setFileInfo(ack.fileInfo);
        setShowFileInfo(true);
        // Request initial image view
        if (ack.fileId !== undefined) {
          cartaClient
            .setImageView({
              fileId: ack.fileId,
              channel: 0,
              stokes: 0,
            })
            .catch((err) => {
              logger.error("Failed to set image view:", err);
              setError(`Failed to set image view: ${err.message}`);
            });
        }
      }
    });

    cartaClient.onMessage(CARTAMessageType.FILE_INFO_RESPONSE, (response: any) => {
      logger.info("File info received", response);
      if (response.fileInfo) {
        setFileInfo(response.fileInfo);
        setShowFileInfo(true);
      }
    });

    cartaClient.onMessage(CARTAMessageType.RASTER_TILE_DATA, (tileData: RasterTileData) => {
      logger.debug("Received raster tile data", tileData);
      if (rendererRef.current) {
        rendererRef.current.addTiles(tileData);
      }
    });

    cartaClient.onMessage(CARTAMessageType.SET_REGION_ACK, (ack: any) => {
      logger.info("Region set successfully", ack);
      if (ack.regionId !== undefined && rendererRef.current) {
        // Region was created/updated, re-render with regions
        // Note: renderRegions will be available via closure
        setTimeout(() => {
          if (rendererRef.current) {
            rendererRef.current.clearRegions();
            regionsRef.current.forEach((points, regionId) => {
              const color = `hsl(${(regionId * 60) % 360}, 70%, 50%)`;
              rendererRef.current?.drawRegion(points, color, 2, false);
            });
          }
        }, 0);
      }
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

  // Render regions overlay
  const renderRegions = () => {
    if (!rendererRef.current) {
      return;
    }

    rendererRef.current.clearRegions();
    regionsRef.current.forEach((points, regionId) => {
      const color = `hsl(${(regionId * 60) % 360}, 70%, 50%)`;
      rendererRef.current?.drawRegion(points, color, 2, false);
    });
  };

  // Initialize image renderer
  useEffect(() => {
    if (!canvasRef.current) {
      return;
    }

    try {
      rendererRef.current = new CARTAImageRenderer(canvasRef.current);
      logger.info("CARTA image renderer initialized");
    } catch (error) {
      logger.error("Failed to initialize image renderer:", error);
      setError("Failed to initialize image renderer");
    }

    return () => {
      if (rendererRef.current) {
        rendererRef.current.clear();
        rendererRef.current = null;
      }
    };
  }, []);

  // Handle canvas mouse events for region creation
  useEffect(() => {
    if (!canvasRef.current || !connected || !currentFileId) {
      return;
    }

    const canvas = canvasRef.current;
    let isDrawing = false;
    let currentPoints: Point[] = [];

    const handleMouseDown = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      currentPoints.push({ x, y });
      isDrawing = true;
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDrawing) {
        return;
      }
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      // Update preview
      if (rendererRef.current && currentPoints.length > 0) {
        renderRegions();
        rendererRef.current.drawRegion([...currentPoints, { x, y }], "#00ff00", 1, false);
      }
    };

    const handleMouseUp = async (e: MouseEvent) => {
      if (!isDrawing || currentPoints.length === 0) {
        return;
      }

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      currentPoints.push({ x, y });

      // Create region (rectangle for now)
      if (currentPoints.length >= 2 && client) {
        const regionId = Date.now(); // Simple ID generation
        const request: SetRegionRequest = {
          fileId: currentFileId,
          regionId,
          regionType: RegionType.RECTANGLE,
          controlPoints: currentPoints,
        };

        try {
          await client.setRegion(request);
          regionsRef.current.set(regionId, currentPoints);
          renderRegions();
        } catch (err) {
          logger.error("Failed to create region:", err);
        }
      }

      isDrawing = false;
      currentPoints = [];
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseup", handleMouseUp);

    return () => {
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseup", handleMouseUp);
    };
  }, [connected, currentFileId, client]);

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
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="caption">
            CARTA: {status}
            {fitsFilePath && ` | File: ${fitsFilePath.split("/").pop()}`}
            {currentFileId !== null && ` | File ID: ${currentFileId}`}
          </Typography>
          {fileInfo && (
            <Button
              size="small"
              variant="outlined"
              onClick={() => setShowFileInfo(!showFileInfo)}
              sx={{ color: "white", borderColor: "white" }}
            >
              {showFileInfo ? "Hide" : "Show"} File Info
            </Button>
          )}
        </Box>
      )}
      {showFileInfo && fileInfo && (
        <Accordion expanded={showFileInfo} sx={{ maxHeight: "200px", overflow: "auto" }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2">File Information</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <Typography variant="body2">
                <strong>Name:</strong> {fileInfo.name}
              </Typography>
              <Typography variant="body2">
                <strong>Type:</strong> {fileInfo.type}
              </Typography>
              <Typography variant="body2">
                <strong>Size:</strong> {(fileInfo.size / 1024 / 1024).toFixed(2)} MB
              </Typography>
              {fileInfo.dimensions && (
                <Typography variant="body2">
                  <strong>Dimensions:</strong> {fileInfo.dimensions.join(" × ")}
                </Typography>
              )}
              <Typography variant="body2">
                <strong>Data Type:</strong> {fileInfo.dataType}
              </Typography>
              {fileInfo.coordinateType && (
                <Typography variant="body2">
                  <strong>Coordinate Type:</strong> {fileInfo.coordinateType}
                </Typography>
              )}
              {fileInfo.hduList && fileInfo.hduList.length > 0 && (
                <Box>
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    <strong>HDUs:</strong>
                  </Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                    {fileInfo.hduList.map((hdu, idx) => (
                      <Chip key={idx} label={hdu} size="small" />
                    ))}
                  </Box>
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
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
