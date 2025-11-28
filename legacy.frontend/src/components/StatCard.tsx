import React from "react";
import { Card, CardContent, Stack, Box, Typography, Alert } from "@mui/material";
import { TrendingUp, TrendingDown } from "@mui/icons-material";

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  color?: "default" | "primary" | "success" | "warning" | "error";
  size?: "small" | "medium" | "large";
  trend?: number;
  trendLabel?: string;
  subtitle?: string;
  alert?: boolean;
  alertMessage?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  color = "default",
  size = "medium",
  trend,
  trendLabel,
  subtitle,
  alert,
  alertMessage,
}) => {
  const getVariant = () => {
    if (size === "large") return "h3";
    if (size === "medium") return "h4";
    return "h5";
  };

  const getColorValue = () => {
    if (color === "default") return "text.primary";
    return `${color}.main`;
  };

  return (
    <Card
      sx={{
        height: "100%",
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: 4,
        },
      }}
    >
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box sx={{ flex: 1 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant={getVariant()} color={getColorValue()} sx={{ fontWeight: 600 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mt: 0.5 }}
              >
                {subtitle}
              </Typography>
            )}
            {trend !== undefined && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 1 }}>
                {trend > 0 ? (
                  <TrendingUp fontSize="small" color={trend > 0 ? "success" : "error"} />
                ) : (
                  <TrendingDown fontSize="small" color={trend < 0 ? "error" : "success"} />
                )}
                <Typography variant="caption" color={trend > 0 ? "success.main" : "error.main"}>
                  {Math.abs(trend).toFixed(1)}% {trendLabel || ""}
                </Typography>
              </Box>
            )}
          </Box>
          {icon && <Box sx={{ color: getColorValue(), ml: 2 }}>{icon}</Box>}
        </Stack>
        {alert && alertMessage && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            {alertMessage}
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};
