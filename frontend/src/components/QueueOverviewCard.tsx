import { Box, Card, CardContent, Grid, Typography } from "@mui/material";
import type { QueueStats } from "../api/types";
import { MetricCard } from "./MetricCard";

export type QueueStatusKey = keyof QueueStats;

interface QueueOverviewCardProps {
  queue?: QueueStats | null;
  selectedStatus?: QueueStatusKey;
  onSelectStatus?: (status: QueueStatusKey) => void;
  title?: string;
  helperText?: string;
  size?: "small" | "medium" | "large";
  variant?: "card" | "inline";
}

const STATUS_CONFIG: Record<
  QueueStatusKey,
  { label: string; color: "primary" | "info" | "warning" | "success" | "error" }
> = {
  total: { label: "Total", color: "primary" },
  pending: { label: "Pending", color: "info" },
  in_progress: { label: "In Progress", color: "warning" },
  completed: { label: "Completed", color: "success" },
  failed: { label: "Failed", color: "error" },
  collecting: { label: "Collecting", color: "info" },
};

const STATUS_ORDER: QueueStatusKey[] = [
  "total",
  "pending",
  "in_progress",
  "completed",
  "failed",
  "collecting",
];

export function QueueOverviewCard({
  queue,
  selectedStatus,
  onSelectStatus,
  title = "Queue Overview",
  helperText,
  size = "small",
  variant = "card",
}: QueueOverviewCardProps) {
  const content = (
    <>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      {helperText && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {helperText}
        </Typography>
      )}
      <Grid container spacing={2}>
        {STATUS_ORDER.map((status) => {
          const config = STATUS_CONFIG[status];
          const value = queue?.[status] ?? 0;
          const isSelected = selectedStatus === status && !!onSelectStatus;

          return (
            <Grid item key={status} xs={12} sm={6} md={4}>
              <Box
                onClick={onSelectStatus ? () => onSelectStatus(status) : undefined}
                sx={{
                  cursor: onSelectStatus ? "pointer" : "default",
                  transition: "all 0.2s ease-in-out",
                  transform: isSelected ? "translateY(-2px)" : undefined,
                }}
              >
                <MetricCard label={config.label} value={value} color={config.color} size={size} />
              </Box>
            </Grid>
          );
        })}
      </Grid>
    </>
  );

  if (variant === "inline") {
    return <Box>{content}</Box>;
  }

  return (
    <Card>
      <CardContent>{content}</CardContent>
    </Card>
  );
}
