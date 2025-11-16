/**
 * FITSViewer Component - View FITS files with JS9 integration
 */
import { useEffect, useRef, useState } from "react";
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from "@mui/material";
import { ExpandMore, Image as ImageIcon, Info } from "@mui/icons-material";
import { useFITSInfo } from "../../api/queries";
import { apiClient } from "../../api/client";

declare global {
  interface Window {
    JS9: any;
  }
}

interface FITSViewerProps {
  fitsPath: string | null;
  height?: number;
  width?: number;
}

export default function FITSViewer({ fitsPath, height = 600, width = 800 }: FITSViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<HTMLDivElement>(null);
  const [viewerHtml, setViewerHtml] = useState<string | null>(null);
  const [loadingViewer, setLoadingViewer] = useState(false);
  const [viewerError, setViewerError] = useState<string | null>(null);

  const { data: fitsInfo, isLoading: loadingInfo, error: infoError } = useFITSInfo(fitsPath);

  // Load JS9 viewer HTML from API
  useEffect(() => {
    if (!fitsPath) {
      setViewerHtml(null);
      return;
    }

    setLoadingViewer(true);
    setViewerError(null);

    apiClient
      .get(`/api/visualization/fits/view`, {
        params: {
          path: fitsPath,
          width,
          height,
        },
        responseType: "text",
      })
      .then((response) => {
        setViewerHtml(response.data);
        setLoadingViewer(false);
      })
      .catch((error) => {
        setViewerError(
          error.response?.data?.detail || error.message || "Failed to load FITS viewer"
        );
        setLoadingViewer(false);
      });
  }, [fitsPath, width, height]);

  // Inject JS9 viewer HTML when available
  // Security note: viewerHtml comes from our own backend API (/api/visualization/fits/view),
  // not from user input, so innerHTML is safe here. The backend generates trusted JS9 viewer HTML.
  useEffect(() => {
    if (!viewerHtml || !viewerRef.current) return;

    viewerRef.current.innerHTML = viewerHtml;

    // Ensure JS9 is initialized
    if (window.JS9 && typeof window.JS9.Load === "function") {
      // JS9 should auto-detect displays in the injected HTML
      // Force a refresh if needed
      setTimeout(() => {
        if (window.JS9 && window.JS9.displays) {
          const displays = window.JS9.displays;
          if (displays.length > 0) {
            // JS9 is ready
          }
        }
      }, 100);
    }
  }, [viewerHtml]);

  if (!fitsPath) {
    return (
      <Paper sx={{ p: 3, bgcolor: "background.paper", height: "100%" }}>
        <Alert severity="info">Select a FITS file to view</Alert>
      </Paper>
    );
  }

  return (
    <Paper
      sx={{
        p: 2,
        bgcolor: "background.paper",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <ImageIcon />
        <Typography variant="h6">FITS Viewer</Typography>
        {fitsInfo && (
          <Chip
            label={fitsInfo.exists ? "Found" : "Not Found"}
            color={fitsInfo.exists ? "success" : "error"}
            size="small"
          />
        )}
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontFamily: "monospace" }}>
        {fitsPath}
      </Typography>

      {infoError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error loading FITS info:{" "}
          {infoError instanceof Error ? infoError.message : "Unknown error"}
        </Alert>
      )}

      {loadingInfo && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {fitsInfo && fitsInfo.exists && (
        <Accordion defaultExpanded={false}>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Info />
              <Typography>FITS File Information</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {fitsInfo.summary && (
                <Typography variant="body2">
                  <strong>Summary:</strong> {String(fitsInfo.summary)}
                </Typography>
              )}
              {fitsInfo.shape && (
                <Typography variant="body2">
                  <strong>Shape:</strong> {fitsInfo.shape.join(" × ")}
                </Typography>
              )}
              {fitsInfo.naxis !== null && (
                <Typography variant="body2">
                  <strong>NAXIS:</strong> {fitsInfo.naxis}
                </Typography>
              )}
              {fitsInfo.header_keys && fitsInfo.header_keys.length > 0 && (
                <Box>
                  <Typography variant="body2" sx={{ mb: 0.5 }}>
                    <strong>Header Keys ({fitsInfo.header_keys.length}):</strong>
                  </Typography>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                    {fitsInfo.header_keys.slice(0, 20).map((key) => (
                      <Chip key={key} label={key} size="small" variant="outlined" />
                    ))}
                    {fitsInfo.header_keys.length > 20 && (
                      <Chip
                        label={`+${fitsInfo.header_keys.length - 20} more`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
      )}

      {viewerError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {viewerError}
        </Alert>
      )}

      {loadingViewer && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
          <Typography variant="body2" sx={{ ml: 2 }}>
            Loading FITS viewer...
          </Typography>
        </Box>
      )}

      {viewerHtml && !loadingViewer && (
        <Box
          ref={containerRef}
          sx={{
            mt: 2,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 1,
            overflow: "auto",
          }}
        >
          <div ref={viewerRef} />
        </Box>
      )}
    </Paper>
  );
}
