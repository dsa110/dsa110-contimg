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
  Grid,
  IconButton,
  Tooltip,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import FitScreenIcon from "@mui/icons-material/FitScreen";
import { CARTAClient } from "../../services/cartaClient";
import type { CARTAConfig } from "../../services/cartaClient";
import { logger } from "../../utils/logger";
import { env } from "../../config/env";
import { CARTAImageRenderer } from "./CARTAImageRenderer";
import { CARTAZoomPan } from "./CARTAZoomPan";
import CARTAProfilePlot from "./CARTAProfilePlot";
import CARTAHistogram from "./CARTAHistogram";
import CARTARegionSelector from "./CARTARegionSelector";
import type {
  FileInfo,
  RasterTileData,
  SetRegionRequest,
  Point,
  SpatialProfileData,
  SpectralProfileData,
  RegionHistogramData,
} from "../../services/cartaProtobuf";
import { RegionType, CARTAMessageType } from "../../services/cartaProtobuf";

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
  const [regionType, setRegionType] = useState<RegionType>(RegionType.RECTANGLE);
  const [spatialProfile, setSpatialProfile] = useState<SpatialProfileData | undefined>();
  const [spectralProfile, setSpectralProfile] = useState<SpectralProfileData | undefined>();
  const [histogram, setHistogram] = useState<RegionHistogramData | undefined>();
  const [showProfiles, setShowProfiles] = useState(false);
  const [showHistogram, setShowHistogram] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const clientRef = useRef<CARTAClient | null>(null);
  const rendererRef = useRef<CARTAImageRenderer | null>(null);
  const zoomPanRef = useRef<CARTAZoomPan | null>(null);
  const regionsRef = useRef<Map<number, Point[]>>(new Map());
  const isDrawingRef = useRef(false);
  const currentPointsRef = useRef<Point[]>([]);

  // Get backend URL from props or environment
  // Port 9002 is in the 9000-9099 range for External Integrations
  const cartaBackendUrl = backendUrl || env.VITE_CARTA_BACKEND_URL || "ws://localhost:9002";

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
    cartaClient.onMessage("REGISTER_VIEWER_ACK" as unknown as CARTAMessageType, (message) => {
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

    cartaClient.onMessage(CARTAMessageType.RASTER_TILE_DATA, async (tileData: RasterTileData) => {
      logger.debug("Received raster tile data", tileData);
      if (rendererRef.current) {
        await rendererRef.current.addTiles(tileData);
        // Re-render with zoom/pan transform if active
        if (zoomPanRef.current && canvasRef.current) {
          const ctx = canvasRef.current.getContext("2d");
          if (ctx) {
            ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
            zoomPanRef.current.applyTransform(ctx);
            // Re-render image (renderer will handle this)
            await rendererRef.current.addTiles(tileData);
            zoomPanRef.current.restoreTransform(ctx);
          }
        }
      }
    });

    cartaClient.onMessage(
      CARTAMessageType.SPATIAL_PROFILE_DATA,
      (profileData: SpatialProfileData) => {
        logger.info("Received spatial profile data", profileData);
        setSpatialProfile(profileData);
        setShowProfiles(true);
      }
    );

    cartaClient.onMessage(
      CARTAMessageType.SPECTRAL_PROFILE_DATA,
      (profileData: SpectralProfileData) => {
        logger.info("Received spectral profile data", profileData);
        setSpectralProfile(profileData);
        setShowProfiles(true);
      }
    );

    cartaClient.onMessage(
      CARTAMessageType.REGION_HISTOGRAM_DATA,
      (histogramData: RegionHistogramData) => {
        logger.info("Received region histogram data", histogramData);
        setHistogram(histogramData);
        setShowHistogram(true);
      }
    );

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

  // Initialize image renderer and zoom/pan
  useEffect(() => {
    if (!canvasRef.current) {
      return;
    }

    try {
      rendererRef.current = new CARTAImageRenderer(canvasRef.current);
      logger.info("CARTA image renderer initialized");

      // Initialize zoom/pan controller
      zoomPanRef.current = new CARTAZoomPan(
        canvasRef.current,
        {
          scale: 1.0,
          offsetX: 0,
          offsetY: 0,
          minScale: 0.1,
          maxScale: 10.0,
        },
        (_state) => {
          // Handle zoom/pan state changes - re-render if needed
          if (rendererRef.current && canvasRef.current) {
            const ctx = canvasRef.current.getContext("2d");
            if (ctx) {
              ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
              zoomPanRef.current?.applyTransform(ctx);
              // Re-render will be triggered by tile updates
            }
          }
        }
      );
      logger.info("CARTA zoom/pan controller initialized");
    } catch (error) {
      logger.error("Failed to initialize image renderer:", error);
      setError("Failed to initialize image renderer");
    }

    return () => {
      if (rendererRef.current) {
        rendererRef.current.clear();
        rendererRef.current = null;
      }
      if (zoomPanRef.current) {
        zoomPanRef.current.destroy();
        zoomPanRef.current = null;
      }
    };
  }, []);

  // Handle canvas mouse events for region creation (with zoom/pan coordinate conversion)
  useEffect(() => {
    if (!canvasRef.current || !connected || !currentFileId || !zoomPanRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    const zoomPan = zoomPanRef.current;

    const handleMouseDown = (e: MouseEvent) => {
      // Only start drawing if not panning (right-click or modifier key for pan)
      if (e.button === 0 && !e.ctrlKey && !e.metaKey) {
        const rect = canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const imageCoords = zoomPan.screenToImage(screenX, screenY);
        currentPointsRef.current = [{ x: imageCoords.x, y: imageCoords.y }];
        isDrawingRef.current = true;
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDrawingRef.current) {
        return;
      }
      const rect = canvas.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;
      const imageCoords = zoomPan.screenToImage(screenX, screenY);

      // Update preview based on region type
      if (rendererRef.current && currentPointsRef.current.length > 0) {
        renderRegions();
        const previewPoints = getPreviewPoints(currentPointsRef.current, imageCoords, regionType);
        rendererRef.current.drawRegion(previewPoints, "#00ff00", 1, false);
      }
    };

    const handleMouseUp = async (e: MouseEvent) => {
      if (!isDrawingRef.current || currentPointsRef.current.length === 0) {
        return;
      }

      const rect = canvas.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;
      const imageCoords = zoomPan.screenToImage(screenX, screenY);

      // Add final point
      currentPointsRef.current.push(imageCoords);

      // Create region based on type
      const controlPoints = getControlPointsForRegionType(currentPointsRef.current, regionType);

      if (controlPoints.length >= getMinPointsForRegionType(regionType) && client) {
        const regionId = Date.now();
        const request: SetRegionRequest = {
          fileId: currentFileId,
          regionId,
          regionType,
          controlPoints,
        };

        try {
          await client.setRegion(request);
          regionsRef.current.set(regionId, controlPoints);
          renderRegions();
        } catch (err) {
          logger.error("Failed to create region:", err);
        }
      }

      isDrawingRef.current = false;
      currentPointsRef.current = [];
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseup", handleMouseUp);

    return () => {
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseup", handleMouseUp);
    };
  }, [connected, currentFileId, client, regionType]);

  // Helper functions for region creation
  const getMinPointsForRegionType = (type: RegionType): number => {
    switch (type) {
      case RegionType.POINT:
        return 1;
      case RegionType.RECTANGLE:
      case RegionType.ELLIPSE:
        return 2;
      case RegionType.POLYGON:
        return 3;
      case RegionType.ANNULUS:
        return 3;
      default:
        return 2;
    }
  };

  const getControlPointsForRegionType = (points: Point[], type: RegionType): Point[] => {
    if (points.length === 0) {
      return [];
    }

    switch (type) {
      case RegionType.POINT:
        return [points[0]];
      case RegionType.RECTANGLE:
        if (points.length >= 2) {
          const [p1, p2] = points;
          return [p1, { x: p2.x, y: p1.y }, p2, { x: p1.x, y: p2.y }];
        }
        return points;
      case RegionType.ELLIPSE:
        if (points.length >= 2) {
          const [center, edge] = points;
          const radiusX = Math.abs(edge.x - center.x);
          const radiusY = Math.abs(edge.y - center.y);
          // Return center and radii
          return [center, { x: radiusX, y: radiusY }];
        }
        return points;
      case RegionType.POLYGON:
        return points;
      case RegionType.ANNULUS:
        if (points.length >= 3) {
          const [center, innerEdge, outerEdge] = points;
          return [center, innerEdge, outerEdge];
        }
        return points;
      default:
        return points;
    }
  };

  const getPreviewPoints = (
    startPoints: Point[],
    currentPoint: Point,
    type: RegionType
  ): Point[] => {
    switch (type) {
      case RegionType.POINT:
        return [currentPoint];
      case RegionType.RECTANGLE:
        if (startPoints.length > 0) {
          const p1 = startPoints[0];
          return [p1, { x: currentPoint.x, y: p1.y }, currentPoint, { x: p1.x, y: currentPoint.y }];
        }
        return [currentPoint];
      case RegionType.ELLIPSE:
        if (startPoints.length > 0) {
          const center = startPoints[0];
          const radiusX = Math.abs(currentPoint.x - center.x);
          const radiusY = Math.abs(currentPoint.y - center.y);
          // Generate ellipse points for preview
          const previewPoints: Point[] = [];
          for (let i = 0; i < 32; i++) {
            const angle = (i / 32) * 2 * Math.PI;
            previewPoints.push({
              x: center.x + radiusX * Math.cos(angle),
              y: center.y + radiusY * Math.sin(angle),
            });
          }
          return previewPoints;
        }
        return [currentPoint];
      case RegionType.POLYGON:
        return [...startPoints, currentPoint];
      case RegionType.ANNULUS:
        if (startPoints.length > 0) {
          const center = startPoints[0];
          // Draw two circles
          const innerRadius =
            startPoints.length > 1
              ? Math.hypot(startPoints[1].x - center.x, startPoints[1].y - center.y)
              : 10;
          const outerRadius = Math.hypot(currentPoint.x - center.x, currentPoint.y - center.y);
          const previewPoints: Point[] = [];
          // Inner circle
          for (let i = 0; i < 32; i++) {
            const angle = (i / 32) * 2 * Math.PI;
            previewPoints.push({
              x: center.x + innerRadius * Math.cos(angle),
              y: center.y + innerRadius * Math.sin(angle),
            });
          }
          // Outer circle
          for (let i = 0; i < 32; i++) {
            const angle = (i / 32) * 2 * Math.PI;
            previewPoints.push({
              x: center.x + outerRadius * Math.cos(angle),
              y: center.y + outerRadius * Math.sin(angle),
            });
          }
          return previewPoints;
        }
        return [currentPoint];
      default:
        return [currentPoint];
    }
  };

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
      {/* Controls Bar */}
      <Box
        sx={{
          p: 1,
          borderBottom: 1,
          borderColor: "divider",
          display: "flex",
          gap: 2,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <CARTARegionSelector
          selectedType={regionType}
          onTypeChange={setRegionType}
          disabled={!connected || !currentFileId}
        />
        <Box sx={{ flex: 1 }} />
        <Tooltip title="Zoom In">
          <IconButton
            size="small"
            onClick={() => zoomPanRef.current?.zoomIn()}
            disabled={!connected}
          >
            <ZoomInIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom Out">
          <IconButton
            size="small"
            onClick={() => zoomPanRef.current?.zoomOut()}
            disabled={!connected}
          >
            <ZoomOutIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Fit to Screen">
          <IconButton
            size="small"
            onClick={() => {
              if (fileInfo?.dimensions && fileInfo.dimensions.length >= 2) {
                zoomPanRef.current?.fitToCanvas(fileInfo.dimensions[0], fileInfo.dimensions[1]);
              } else {
                zoomPanRef.current?.reset();
              }
            }}
            disabled={!connected || !fileInfo}
          >
            <FitScreenIcon />
          </IconButton>
        </Tooltip>
        <Button
          size="small"
          variant={showProfiles ? "contained" : "outlined"}
          onClick={() => setShowProfiles(!showProfiles)}
          disabled={!spatialProfile && !spectralProfile}
        >
          Profiles
        </Button>
        <Button
          size="small"
          variant={showHistogram ? "contained" : "outlined"}
          onClick={() => setShowHistogram(!showHistogram)}
          disabled={!histogram}
        >
          Histogram
        </Button>
      </Box>
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
      <Grid container sx={{ flex: 1, overflow: "hidden" }}>
        <Grid sx={{ position: "relative" }} size={showProfiles || showHistogram ? 8 : 12}>
          <Box
            sx={{
              width: "100%",
              height: "100%",
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
                cursor: isDrawingRef.current ? "crosshair" : "grab",
              }}
            />
            {error && connected && (
              <Alert severity="warning" sx={{ position: "absolute", top: 8, left: 8, right: 8 }}>
                {error}
              </Alert>
            )}
          </Box>
        </Grid>
        {(showProfiles || showHistogram) && (
          <Grid sx={{ borderLeft: 1, borderColor: "divider", overflow: "auto" }} size={4}>
            <Box sx={{ p: 1, display: "flex", flexDirection: "column", gap: 2, height: "100%" }}>
              {showProfiles && (spatialProfile || spectralProfile) && (
                <CARTAProfilePlot
                  spatialProfile={spatialProfile}
                  spectralProfile={spectralProfile}
                  height={showHistogram ? "45%" : "100%"}
                />
              )}
              {showHistogram && histogram && (
                <CARTAHistogram histogramData={histogram} height={showProfiles ? "45%" : "100%"} />
              )}
            </Box>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
}
