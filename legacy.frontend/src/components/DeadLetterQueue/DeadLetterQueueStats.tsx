/**
 * Dead Letter Queue Statistics Component
 */
import { Typography, Box, Stack } from "@mui/material";
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
    return (
      <Typography variant="body2" color="text.secondary">
        Loading DLQ stats...
      </Typography>
    );
  }

  const statItems = [
    { label: "Total", value: stats.total, icon: ErrorIcon, color: "#757575" },
    { label: "Pending", value: stats.pending, icon: ScheduleIcon, color: "#ed6c02" },
    { label: "Retrying", value: stats.retrying, icon: ScheduleIcon, color: "#0288d1" },
    { label: "Resolved", value: stats.resolved, icon: CheckCircleIcon, color: "#2e7d32" },
    { label: "Failed", value: stats.failed, icon: CancelIcon, color: "#d32f2f" },
  ];

  return (
    <Box>
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Dead Letter Queue Statistics
      </Typography>
      <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 1 }}>
        {statItems.map((item) => {
          const Icon = item.icon;
          return (
            <Box key={item.label} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Typography variant="body2" color="text.secondary">
                {item.label}:
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 0.75,
                  px: 1,
                  py: 0.5,
                  borderRadius: 1,
                  bgcolor: item.color,
                  color: "white",
                }}
              >
                <Typography variant="body2" sx={{ fontWeight: "bold", fontSize: "0.875rem" }}>
                  {item.value}
                </Typography>
                <Icon sx={{ fontSize: 16 }} />
              </Box>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}
