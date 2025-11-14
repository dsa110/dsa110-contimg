/**
 * Dead Letter Queue Statistics Component
 */
import { Card, CardContent, Typography, Box, Stack, Chip } from "@mui/material";
import {
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
} from "@mui/icons-material";
import { useDLQStats } from "../../api/queries";

export function DeadLetterQueueStats() {
  const { data: stats, isLoading } = useDLQStats();

  if (isLoading || !stats) {
    return <Typography>Loading...</Typography>;
  }

  const statItems = [
    { label: "Total", value: stats.total, icon: <ErrorIcon />, color: "default" as const },
    { label: "Pending", value: stats.pending, icon: <ScheduleIcon />, color: "warning" as const },
    { label: "Retrying", value: stats.retrying, icon: <ScheduleIcon />, color: "info" as const },
    {
      label: "Resolved",
      value: stats.resolved,
      icon: <CheckCircleIcon />,
      color: "success" as const,
    },
    { label: "Failed", value: stats.failed, icon: <CancelIcon />, color: "error" as const },
  ];

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Dead Letter Queue Statistics
        </Typography>
        <Stack direction="row" spacing={2} flexWrap="wrap">
          {statItems.map((item) => (
            <Box key={item.label} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Box sx={{ color: `${item.color}.main` }}>{item.icon}</Box>
              <Typography variant="body2" color="text.secondary">
                {item.label}:
              </Typography>
              <Chip label={item.value} color={item.color} size="small" />
            </Box>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}
