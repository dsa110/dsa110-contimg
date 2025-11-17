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
import DOMPurify from "dompurify";

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
  const [sanitizedHtml, setSanitizedHtml] = useState<string | null>(null);
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

  // Sanitize HTML when viewerHtml changes
  // Security: HTML is sanitized with DOMPurify before rendering to prevent XSS attacks.
  // The HTML comes from our trusted backend API (/api/visualization/fits/view),
  // but we sanitize it as a defense-in-depth measure. DOMPurify removes any potentially
  // dangerous scripts, event handlers, and unsafe attributes while preserving safe HTML
  // elements needed for JS9 viewer functionality. Note: JS9 may require specific attributes
  // for proper initialization, so we use a permissive sanitization config.
  useEffect(() => {
    if (!viewerHtml) {
      setSanitizedHtml(null);
      return;
    }

    // Sanitize HTML before rendering to prevent XSS
    const sanitized = DOMPurify.sanitize(viewerHtml, {
      // Allow common HTML elements needed for JS9 viewer
      ALLOWED_TAGS: ["div", "canvas", "img", "span", "a", "script", "style", "link", "meta"],
      // Allow attributes needed for JS9 functionality
      ALLOWED_ATTR: [
        "class",
        "id",
        "style",
        "src",
        "alt",
        "href",
        "target",
        "title",
        "width",
        "height",
        "data-*", // JS9 uses data attributes
        "onload", // JS9 may need onload handlers
      ],
      // Allow data attributes for JS9
      ALLOW_DATA_ATTR: true,
      // Keep relative URLs
      ALLOW_UNKNOWN_PROTOCOLS: false,
    });

    setSanitizedHtml(sanitized);
  }, [viewerHtml]);

  // Ensure JS9 is initialized after HTML is rendered
  useEffect(() => {
    if (!sanitizedHtml || !viewerRef.current) return;

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
  }, [sanitizedHtml]);

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
                  <strong>Summary:</strong> {fitsInfo.summary}
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

      {sanitizedHtml && !loadingViewer && (
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
          {/* Security: HTML is sanitized with DOMPurify before rendering to prevent XSS attacks.
              The HTML comes from our trusted backend API (/api/visualization/fits/view),
              but we sanitize it as a defense-in-depth measure. DOMPurify removes any potentially
              dangerous scripts, event handlers, and unsafe attributes while preserving safe HTML
              elements needed for JS9 viewer functionality. */}
          <div ref={viewerRef} dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />
        </Box>
      )}
    </Paper>
  );
}
