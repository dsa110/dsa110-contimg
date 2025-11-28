/**
 * Unified Workspace Component
 * Allows multiple views in a single pane (multi-pane layout)
 */
import React, { useState } from "react";
import { Box, Paper, Typography, IconButton, Tabs, Tab, Button, Stack } from "@mui/material";
import { Close, Fullscreen, FullscreenExit } from "@mui/icons-material";

export interface WorkspaceView {
  id: string;
  title: string;
  component: React.ReactNode;
  closable?: boolean;
}

interface UnifiedWorkspaceProps {
  views: WorkspaceView[];
  defaultLayout?: "split-horizontal" | "split-vertical" | "grid";
  onClose?: (viewId: string) => void;
}

export default function UnifiedWorkspace({
  views,
  defaultLayout = "split-horizontal",
  onClose,
}: UnifiedWorkspaceProps) {
  const [layout, setLayout] = useState<"split-horizontal" | "split-vertical" | "grid">(
    defaultLayout
  );
  const [activeView, setActiveView] = useState<string | null>(views[0]?.id || null);
  const [fullscreenView, setFullscreenView] = useState<string | null>(null);

  if (views.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">No views available</Typography>
      </Paper>
    );
  }

  // If one view is fullscreen, show only that
  if (fullscreenView) {
    const view = views.find((v) => v.id === fullscreenView);
    if (!view) {
      setFullscreenView(null);
      return null;
    }

    return (
      <Box sx={{ position: "relative", height: "100%", width: "100%" }}>
        <Box
          sx={{
            position: "absolute",
            top: 8,
            right: 8,
            zIndex: 1000,
            display: "flex",
            gap: 1,
          }}
        >
          <IconButton
            size="small"
            onClick={() => setFullscreenView(null)}
            sx={{ bgcolor: "background.paper" }}
          >
            <FullscreenExit />
          </IconButton>
          {view.closable !== false && onClose && (
            <IconButton
              size="small"
              onClick={() => {
                onClose(view.id);
                setFullscreenView(null);
              }}
              sx={{ bgcolor: "background.paper" }}
            >
              <Close />
            </IconButton>
          )}
        </Box>
        <Box sx={{ height: "100%", width: "100%", overflow: "auto" }}>{view.component}</Box>
      </Box>
    );
  }

  // Render based on layout
  const renderLayout = () => {
    if (layout === "split-horizontal" && views.length >= 2) {
      return (
        <Box sx={{ display: "flex", height: "100%", gap: 1 }}>
          {views.slice(0, 2).map((view) => (
            <Box
              key={view.id}
              sx={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              <WorkspaceViewHeader
                view={view}
                onFullscreen={() => setFullscreenView(view.id)}
                onClose={onClose}
              />
              <Box sx={{ flex: 1, overflow: "auto" }}>{view.component}</Box>
            </Box>
          ))}
        </Box>
      );
    }

    if (layout === "split-vertical" && views.length >= 2) {
      return (
        <Box sx={{ display: "flex", flexDirection: "column", height: "100%", gap: 1 }}>
          {views.slice(0, 2).map((view) => (
            <Box
              key={view.id}
              sx={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              <WorkspaceViewHeader
                view={view}
                onFullscreen={() => setFullscreenView(view.id)}
                onClose={onClose}
              />
              <Box sx={{ flex: 1, overflow: "auto" }}>{view.component}</Box>
            </Box>
          ))}
        </Box>
      );
    }

    // Grid layout or single view
    return (
      <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <Tabs
          value={activeView || views[0].id}
          onChange={(_, value) => setActiveView(value)}
          sx={{ borderBottom: 1, borderColor: "divider" }}
        >
          {views.map((view) => (
            <Tab
              key={view.id}
              label={view.title}
              value={view.id}
              icon={
                <Box sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                  {view.closable !== false && onClose && (
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        onClose(view.id);
                      }}
                      sx={{ p: 0 }}
                    >
                      <Close fontSize="small" />
                    </IconButton>
                  )}
                </Box>
              }
              iconPosition="end"
            />
          ))}
        </Tabs>
        <Box sx={{ flex: 1, overflow: "auto", mt: 1 }}>
          {views
            .filter((view) => view.id === (activeView || views[0].id))
            .map((view) => (
              <Box key={view.id}>{view.component}</Box>
            ))}
        </Box>
      </Box>
    );
  };

  return (
    <Paper sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          p: 1,
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Typography variant="subtitle2" fontWeight={600}>
          Workspace
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button
            size="small"
            variant={layout === "split-horizontal" ? "contained" : "outlined"}
            onClick={() => setLayout("split-horizontal")}
            disabled={views.length < 2}
          >
            Split H
          </Button>
          <Button
            size="small"
            variant={layout === "split-vertical" ? "contained" : "outlined"}
            onClick={() => setLayout("split-vertical")}
            disabled={views.length < 2}
          >
            Split V
          </Button>
          <Button
            size="small"
            variant={layout === "grid" ? "contained" : "outlined"}
            onClick={() => setLayout("grid")}
          >
            Tabs
          </Button>
        </Stack>
      </Box>
      <Box sx={{ flex: 1, overflow: "hidden" }}>{renderLayout()}</Box>
    </Paper>
  );
}

function WorkspaceViewHeader({
  view,
  onFullscreen,
  onClose,
}: {
  view: WorkspaceView;
  onFullscreen: () => void;
  onClose?: (id: string) => void;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        p: 1,
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Typography variant="subtitle2" fontWeight={600}>
        {view.title}
      </Typography>
      <Box>
        <IconButton size="small" onClick={onFullscreen}>
          <Fullscreen fontSize="small" />
        </IconButton>
        {view.closable !== false && onClose && (
          <IconButton size="small" onClick={() => onClose(view.id)}>
            <Close fontSize="small" />
          </IconButton>
        )}
      </Box>
    </Box>
  );
}
