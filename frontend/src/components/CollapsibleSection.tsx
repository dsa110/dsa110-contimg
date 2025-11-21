/**
 * Collapsible Section Component
 * Reusable collapsible section for optimizing information density
 */
import React, { useState } from "react";
import { Box, Typography, IconButton, Collapse, Paper, alpha } from "@mui/material";
import type { SxProps, Theme } from "@mui/material";
import { ExpandMore } from "@mui/icons-material";

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultExpanded?: boolean;
  variant?: "default" | "outlined" | "elevation";
  headerActions?: React.ReactNode;
  sx?: SxProps<Theme>;
}

export default function CollapsibleSection({
  title,
  children,
  defaultExpanded = false,
  variant = "default",
  headerActions,
  sx,
}: CollapsibleSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const handleToggle = () => {
    setExpanded(!expanded);
  };

  const paperProps =
    variant === "outlined"
      ? { variant: "outlined" as const }
      : variant === "elevation"
        ? { elevation: 1 }
        : {};

  return (
    <Paper
      {...paperProps}
      sx={{
        mb: 2,
        overflow: "hidden",
        transition: "all 0.2s ease-in-out",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        "&:hover":
          variant === "default"
            ? {
                bgcolor: alpha("#fff", 0.02),
              }
            : {},
        ...sx,
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          cursor: "pointer",
          "&:hover": {
            bgcolor: "action.hover",
          },
          transition: "background-color 0.2s ease",
        }}
        onClick={handleToggle}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}>
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleToggle();
            }}
            sx={{
              transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease",
            }}
          >
            <ExpandMore />
          </IconButton>
          <Typography variant="h6" component="h3" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
        </Box>
        {headerActions && <Box onClick={(e) => e.stopPropagation()}>{headerActions}</Box>}
      </Box>
      <Collapse
        in={expanded}
        timeout="auto"
        unmountOnExit
        sx={{ flex: 1, display: "flex", flexDirection: "column" }}
      >
        <Box sx={{ p: 2, pt: 0, flex: 1 }}>{children}</Box>
      </Collapse>
    </Paper>
  );
}
