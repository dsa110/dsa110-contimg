import React from "react";
import { Box, Typography, LinearProgress, useTheme } from "@mui/material";
import {
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  TrendingUp,
  TrendingDown,
} from "@mui/icons-material";

interface StatusIndicatorProps {
  value: number;
  thresholds: { warning: number; critical: number };
  label: string;
  unit?: string;
  showTrend?: boolean;
  previousValue?: number;
  size?: "small" | "medium" | "large";
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  value,
  thresholds,
  label,
  unit = "%",
  showTrend = false,
  previousValue,
  size = "medium",
}) => {
  const theme = useTheme();

  const getStatus = (): "success" | "warning" | "error" => {
    // For resource usage metrics (CPU, Memory, Disk), lower is better
    // High usage is critical, low usage is healthy
    // Thresholds represent maximum values for each state
    if (value >= thresholds.critical) return "error"; // Above critical = red
    if (value >= thresholds.warning) return "warning"; // Above warning = yellow
    return "success"; // Below both thresholds = green (healthy)
  };

  const status = getStatus();

  const getColor = () => {
    switch (status) {
      case "success":
        return theme.palette.success.main;
      case "warning":
        return theme.palette.warning.main;
      case "error":
        return theme.palette.error.main;
    }
  };

  const getIcon = () => {
    switch (status) {
      case "success":
        return (
          <CheckCircle sx={{ fontSize: size === "large" ? 28 : size === "medium" ? 24 : 20 }} />
        );
      case "warning":
        return <Warning sx={{ fontSize: size === "large" ? 28 : size === "medium" ? 24 : 20 }} />;
      case "error":
        return <ErrorIcon sx={{ fontSize: size === "large" ? 28 : size === "medium" ? 24 : 20 }} />;
    }
  };

  const getTrendIcon = () => {
    if (!previousValue || !showTrend) return null;
    const diff = value - previousValue;
    if (Math.abs(diff) < 0.1) return null; // No significant change

    return diff > 0 ? (
      <TrendingUp
        sx={{ fontSize: 16, ml: 0.5, color: status === "error" ? "error.main" : "text.secondary" }}
      />
    ) : (
      <TrendingDown
        sx={{
          fontSize: 16,
          ml: 0.5,
          color: status === "success" ? "success.main" : "text.secondary",
        }}
      />
    );
  };

  const getSizeStyles = () => {
    switch (size) {
      case "large":
        return {
          padding: theme.spacing(2),
          minWidth: 140,
        };
      case "medium":
        return {
          padding: theme.spacing(1.5),
          minWidth: 120,
        };
      case "small":
        return {
          padding: theme.spacing(1),
          minWidth: 100,
        };
    }
  };

  const progressValue = Math.min(100, Math.max(0, value));

  return (
    <Box
      sx={{
        ...getSizeStyles(),
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        bgcolor:
          theme.palette.mode === "dark"
            ? `rgba(${status === "success" ? "76, 175, 80" : status === "warning" ? "255, 152, 0" : "244, 67, 54"}, 0.08)`
            : `rgba(${status === "success" ? "76, 175, 80" : status === "warning" ? "255, 152, 0" : "244, 67, 54"}, 0.05)`,
        borderRadius: 2,
        border: `1px solid ${getColor()}40`,
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: `0 4px 12px ${getColor()}30`,
        },
      }}
    >
      {/* Header with icon and label */}
      <Box sx={{ display: "flex", alignItems: "center", width: "100%", mb: 1 }}>
        <Box
          sx={{
            color: getColor(),
            display: "flex",
            alignItems: "center",
            mr: 1,
          }}
        >
          {getIcon()}
        </Box>
        <Typography
          variant={size === "large" ? "body1" : "body2"}
          sx={{
            fontWeight: 600,
            color: "text.primary",
            flexGrow: 1,
          }}
        >
          {label}
        </Typography>
      </Box>

      {/* Value with trend */}
      <Box sx={{ display: "flex", alignItems: "baseline", width: "100%", mb: 1 }}>
        <Typography
          variant={size === "large" ? "h4" : size === "medium" ? "h5" : "h6"}
          sx={{
            fontWeight: 700,
            color: getColor(),
            lineHeight: 1,
          }}
        >
          {value.toFixed(1)}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            ml: 0.5,
            fontWeight: 500,
          }}
        >
          {unit}
        </Typography>
        {getTrendIcon()}
      </Box>

      {/* Progress bar */}
      <Box sx={{ width: "100%", mt: 0.5 }}>
        <LinearProgress
          variant="determinate"
          value={progressValue}
          sx={{
            height: size === "large" ? 8 : 6,
            borderRadius: 1,
            bgcolor:
              theme.palette.mode === "dark" ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.1)",
            "& .MuiLinearProgress-bar": {
              bgcolor: getColor(),
              borderRadius: 1,
            },
          }}
        />
      </Box>

      {/* Status text */}
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          mt: 0.5,
          textTransform: "capitalize",
          fontWeight: 500,
        }}
      >
        {status === "success" ? "Healthy" : status === "warning" ? "Warning" : "Critical"}
      </Typography>
    </Box>
  );
};
