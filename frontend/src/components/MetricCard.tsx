import React from "react";
import { Box, Typography, useTheme, alpha } from "@mui/material";
import { TrendingUp, TrendingDown, Remove } from "@mui/icons-material";

interface MetricCardProps {
  label: string;
  value: number | string;
  unit?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: number | string;
  color?: "primary" | "success" | "warning" | "error" | "info";
  size?: "small" | "medium" | "large";
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  trend,
  trendValue,
  color = "primary",
  size = "medium",
  icon,
}) => {
  const theme = useTheme();

  const getColorValue = () => {
    switch (color) {
      case "success":
        return theme.palette.success.main;
      case "warning":
        return theme.palette.warning.main;
      case "error":
        return theme.palette.error.main;
      case "info":
        return theme.palette.info.main;
      default:
        return theme.palette.primary.main;
    }
  };

  const getTrendIcon = () => {
    if (!trend) return null;

    switch (trend) {
      case "up":
        return (
          <TrendingUp
            sx={{ fontSize: 16, color: color === "error" ? "error.main" : "success.main" }}
          />
        );
      case "down":
        return (
          <TrendingDown
            sx={{ fontSize: 16, color: color === "success" ? "success.main" : "error.main" }}
          />
        );
      case "neutral":
        return <Remove sx={{ fontSize: 16, color: "text.secondary" }} />;
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case "large":
        return {
          padding: theme.spacing(2.5),
          minHeight: 120,
        };
      case "medium":
        return {
          padding: theme.spacing(2),
          minHeight: 100,
        };
      case "small":
        return {
          padding: theme.spacing(1.5),
          minHeight: 80,
        };
    }
  };

  const valueVariant = size === "large" ? "h3" : size === "medium" ? "h4" : "h5";
  const labelVariant = size === "large" ? "body1" : "body2";

  return (
    <Box
      sx={{
        ...getSizeStyles(),
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        bgcolor:
          theme.palette.mode === "dark"
            ? alpha(getColorValue(), 0.08)
            : alpha(getColorValue(), 0.05),
        borderRadius: 2,
        border: `1px solid ${alpha(getColorValue(), 0.2)}`,
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: `0 4px 12px ${alpha(getColorValue(), 0.2)}`,
          borderColor: alpha(getColorValue(), 0.4),
        },
      }}
    >
      {/* Header with icon and label */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Typography
          variant={labelVariant}
          sx={{
            color: "text.secondary",
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: 0.5,
            fontSize: size === "small" ? "0.7rem" : undefined,
          }}
        >
          {label}
        </Typography>
        {icon && <Box sx={{ color: getColorValue() }}>{icon}</Box>}
      </Box>

      {/* Value */}
      <Box sx={{ display: "flex", alignItems: "baseline", flexWrap: "wrap", gap: 0.5 }}>
        <Typography
          variant={valueVariant}
          sx={{
            fontWeight: 700,
            color: getColorValue(),
            lineHeight: 1.2,
          }}
        >
          {typeof value === "number" ? value.toLocaleString() : value}
        </Typography>
        {unit && (
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
              fontWeight: 500,
              ml: 0.5,
            }}
          >
            {unit}
          </Typography>
        )}
        {trend && getTrendIcon()}
        {trendValue && trend && (
          <Typography
            variant="caption"
            sx={{
              color:
                trend === "up" && color !== "error"
                  ? "success.main"
                  : trend === "down" && color !== "success"
                    ? "error.main"
                    : "text.secondary",
              fontWeight: 600,
              ml: 0.5,
            }}
          >
            {typeof trendValue === "number" && trendValue > 0 ? "+" : ""}
            {trendValue}
          </Typography>
        )}
      </Box>
    </Box>
  );
};
