import React from "react";
import { Box, Skeleton, Paper } from "@mui/material";

interface SkeletonLoaderProps {
  variant?: "table" | "list" | "cards" | "form";
  rows?: number;
  columns?: number;
}

export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  variant = "list",
  rows = 5,
  columns = 4,
}) => {
  if (variant === "table") {
    return (
      <Paper sx={{ p: 2 }}>
        <Skeleton variant="rectangular" height={56} sx={{ mb: 2 }} />
        {Array.from({ length: rows }).map((_, i) => (
          <Box key={i} sx={{ display: "flex", gap: 2, mb: 2 }}>
            {Array.from({ length: columns }).map((_, j) => (
              <Skeleton key={j} variant="rectangular" height={40} sx={{ flex: 1 }} />
            ))}
          </Box>
        ))}
      </Paper>
    );
  }

  if (variant === "cards") {
    return (
      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} variant="rectangular" width={300} height={200} />
        ))}
      </Box>
    );
  }

  if (variant === "form") {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} variant="rectangular" height={56} />
        ))}
      </Box>
    );
  }

  // Default: list
  return (
    <Box>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={56} sx={{ mb: 1 }} />
      ))}
    </Box>
  );
};
