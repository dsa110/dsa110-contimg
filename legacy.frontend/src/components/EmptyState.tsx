import React from "react";
import { Box, Typography, Stack } from "@mui/material";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actions?: React.ReactNode[];
  children?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actions,
  children,
}) => (
  <Box sx={{ textAlign: "center", py: 8 }}>
    {icon && <Box sx={{ mb: 2, display: "flex", justifyContent: "center" }}>{icon}</Box>}
    <Typography variant="h5" gutterBottom>
      {title}
    </Typography>
    {description && (
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 600, mx: "auto" }}>
        {description}
      </Typography>
    )}
    {actions && (
      <Stack direction="row" spacing={2} justifyContent="center" sx={{ mb: 2 }}>
        {actions}
      </Stack>
    )}
    {children}
  </Box>
);
