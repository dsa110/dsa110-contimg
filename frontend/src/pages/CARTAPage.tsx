/**
 * CARTA Integration Page
 *
 * Demonstrates both integration options:
 * - Option 1: Iframe embedding (quick validation)
 * - Option 2: WebSocket integration (full integration)
 */

import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Box,
  Tabs,
  Tab,
  Paper,
  Typography,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Stack,
} from "@mui/material";
import { CARTAIframe, CARTAViewer } from "../components/CARTA";
import DirectoryBrowser from "../components/QA/DirectoryBrowser";
import { logger } from "../utils/logger";
import { env } from "../config/env";

type IntegrationMode = "iframe" | "websocket";
type TabValue = "viewer" | "browser";

export default function CARTAPage({ embedded = false }: { embedded?: boolean }) {
  const [searchParams] = useSearchParams();
  const [integrationMode, setIntegrationMode] = useState<IntegrationMode>("iframe");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [tab, setTab] = useState<TabValue>("viewer");
  // Ports follow allocation strategy: 9000-9099 for External Integrations
  // CARTA Backend: 9002, CARTA Frontend: served by backend on 9002
  const [backendUrl, setBackendUrl] = useState<string>(
    env.VITE_CARTA_BACKEND_URL || "http://localhost:9002"
  );
  const [frontendUrl, setFrontendUrl] = useState<string>(
    env.VITE_CARTA_FRONTEND_URL || "http://localhost:9002"
  );

  // Handle file parameter from URL query string
  useEffect(() => {
    const fileParam = searchParams.get("file");
    const modeParam = searchParams.get("mode") as IntegrationMode | null;

    if (fileParam) {
      setSelectedFile(fileParam);
      setTab("viewer"); // Switch to viewer tab when file is provided
    }

    if (modeParam && (modeParam === "iframe" || modeParam === "websocket")) {
      setIntegrationMode(modeParam);
    }
  }, [searchParams]);

  const handleFileSelect = (path: string, type: string) => {
    if (type === "fits") {
      setSelectedFile(path);
      logger.info("File selected for CARTA:", path);
    }
  };

  const handleModeChange = (mode: IntegrationMode) => {
    setIntegrationMode(mode);
    logger.info("CARTA integration mode changed:", mode);
  };

  return (
    <Box sx={{ height: "calc(100vh - 64px)", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      {!embedded && (
        <Paper sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="h5" gutterBottom>
            CARTA Integration
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Cube Analysis and Rendering Tool for Astronomy - FITS file visualization
          </Typography>

          {/* Integration Mode Selector */}
          <Stack direction="row" spacing={2} sx={{ mt: 2 }} alignItems="center">
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Integration Mode</InputLabel>
              <Select
                value={integrationMode}
                label="Integration Mode"
                onChange={(e) => handleModeChange(e.target.value as IntegrationMode)}
              >
                <MenuItem value="iframe">Option 1: Iframe (Quick Validation)</MenuItem>
                <MenuItem value="websocket">Option 2: WebSocket (Full Integration)</MenuItem>
              </Select>
            </FormControl>

            {integrationMode === "iframe" && (
              <TextField
                size="small"
                label="CARTA Frontend URL"
                value={frontendUrl}
                onChange={(e) => setFrontendUrl(e.target.value)}
                sx={{ minWidth: 300 }}
              />
            )}

            <TextField
              size="small"
              label="CARTA Backend URL"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              sx={{ minWidth: 300 }}
            />

            {selectedFile && (
              <Button variant="outlined" size="small" onClick={() => setSelectedFile(null)}>
                Clear File
              </Button>
            )}
          </Stack>

          {integrationMode === "iframe" && (
            <Alert severity="success" sx={{ mt: 2 }}>
              <strong>Iframe Mode (Recommended):</strong> Embeds CARTA's official frontend with full
              functionality. Uses CARTA's built-in Protocol Buffer support via WASM modules. This is
              the officially supported integration method.
            </Alert>
          )}

          {integrationMode === "websocket" && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              <strong>WebSocket Mode (Experimental - Not Functional):</strong> Direct WebSocket
              connection to CARTA backend. <strong>This mode does not work</strong> because it
              requires CARTA's internal Protocol Buffer definitions (.proto files) which are not
              publicly available. Use Iframe Mode instead.
            </Alert>
          )}
        </Paper>
      )}

      {/* Main Content */}
      <Box sx={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Tabs */}
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v as TabValue)}
          orientation="vertical"
          sx={{
            borderRight: 1,
            borderColor: "divider",
            minWidth: 150,
            bgcolor: "background.paper",
          }}
        >
          <Tab label="CARTA Viewer" value="viewer" />
          <Tab label="File Browser" value="browser" />
        </Tabs>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {tab === "viewer" && (
            <Box sx={{ flex: 1, overflow: "hidden" }}>
              {integrationMode === "iframe" ? (
                <CARTAIframe
                  cartaBackendUrl={backendUrl}
                  cartaFrontendUrl={frontendUrl}
                  fitsFilePath={selectedFile || undefined}
                  height="100%"
                />
              ) : (
                <CARTAViewer
                  backendUrl={backendUrl}
                  fitsFilePath={selectedFile || undefined}
                  height="100%"
                  showStatus={true}
                />
              )}
            </Box>
          )}

          {tab === "browser" && (
            <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
              <DirectoryBrowser onSelectFile={handleFileSelect} />
            </Box>
          )}
        </Box>
      </Box>

      {/* Footer Status */}
      {selectedFile && (
        <Paper
          sx={{
            p: 1,
            borderTop: 1,
            borderColor: "divider",
            bgcolor: "info.dark",
            color: "white",
          }}
        >
          <Typography variant="caption">Selected File: {selectedFile}</Typography>
        </Paper>
      )}
    </Box>
  );
}
