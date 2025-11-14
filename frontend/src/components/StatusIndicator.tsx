import React from "react";
import { Chip } from "@mui/material";
import { Circle } from "@mui/icons-material";

interface StatusIndicatorProps {
  value: number;
  thresholds: { good: number; warning: number };
  label: string;
  unit?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  value,
  thresholds,
  label,
  unit = "%",
}) => {
  const getColor = (): "success" | "warning" | "error" | "default" => {
    if (value >= thresholds.good) return "success";
    if (value >= thresholds.warning) return "warning";
    return "error";
  };

  return (
    <Chip
      icon={<Circle sx={{ fontSize: 8 }} />}
      label={`${label}: ${value}${unit}`}
      color={getColor()}
      size="small"
    />
  );
};
