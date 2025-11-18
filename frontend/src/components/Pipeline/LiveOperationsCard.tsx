import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Stack,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Button,
  Skeleton,
} from "@mui/material";
import { formatDistanceToNow } from "date-fns";
import type { PipelineMetricsSummary, PipelineExecutionResponse } from "../../api/types";

interface LiveOperationsCardProps {
  summary?: PipelineMetricsSummary;
  isSummaryLoading?: boolean;
  executions?: PipelineExecutionResponse[];
  isExecutionsLoading?: boolean;
  onOpenPipeline?: () => void;
}

export function LiveOperationsCard({
  summary,
  isSummaryLoading,
  executions,
  isExecutionsLoading,
  onOpenPipeline,
}: LiveOperationsCardProps) {
  const statItems = [
    { label: "Total Jobs", value: summary?.total_jobs ?? "—" },
    { label: "Running", value: summary?.running_jobs ?? "—" },
    { label: "Completed", value: summary?.completed_jobs ?? "—" },
    { label: "Failed", value: summary?.failed_jobs ?? "—" },
  ];

  const successRate = summary ? `${(summary.success_rate * 100).toFixed(1)}%` : "N/A";
  const avgDuration = summary?.average_duration_seconds
    ? `${(summary.average_duration_seconds / 60).toFixed(1)} min`
    : "N/A";

  const topExecutions = executions?.slice(0, 3) ?? [];

  return (
    <Card>
      <CardHeader
        title="Live Operations"
        subheader={
          summary?.timestamp ? `Updated ${new Date(summary.timestamp).toLocaleString()}` : undefined
        }
        action={
          <Button size="small" onClick={onOpenPipeline}>
            Open Pipeline Monitor
          </Button>
        }
      />
      <CardContent>
        {isSummaryLoading ? (
          <Skeleton variant="rectangular" height={80} sx={{ mb: 2 }} />
        ) : (
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }}>
            {statItems.map((item) => (
              <Box key={item.label} sx={{ flex: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  {item.label}
                </Typography>
                <Typography variant="h5">{item.value}</Typography>
              </Box>
            ))}
          </Stack>
        )}

        <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mb: 2 }}>
          <Chip label={`Success Rate: ${successRate}`} color="success" variant="outlined" />
          <Chip label={`Avg Duration: ${avgDuration}`} color="info" variant="outlined" />
        </Stack>

        <Divider sx={{ my: 2 }} />

        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          Active Executions
        </Typography>

        {isExecutionsLoading ? (
          <Skeleton variant="rectangular" height={120} />
        ) : topExecutions.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No jobs are running right now. Launch a workflow to begin processing.
          </Typography>
        ) : (
          <List dense>
            {topExecutions.map((execution) => (
              <ListItem key={execution.id} sx={{ px: 0 }}>
                <ListItemText
                  primary={`#${execution.id} • ${execution.job_type}`}
                  secondary={`Status: ${execution.status.toUpperCase()} · Started ${
                    execution.started_at
                      ? formatDistanceToNow(new Date(execution.started_at * 1000), {
                          addSuffix: true,
                        })
                      : "unknown"
                  }`}
                />
                <Chip
                  label={execution.status}
                  size="small"
                  color={execution.status === "running" ? "primary" : "default"}
                  sx={{ ml: 1 }}
                />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
}
