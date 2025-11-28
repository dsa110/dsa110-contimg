import React from "react";
import { Card, CardContent, Typography, Stack, Box, Divider } from "@mui/material";
import { Schedule } from "@mui/icons-material";
import type { StreamingMetrics } from "../../api/queries";

interface QueueStatsCardProps {
  metrics?: StreamingMetrics;
}

export const QueueStatsCard: React.FC<QueueStatsCardProps> = ({ metrics }) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Queue Statistics
        </Typography>
        {metrics?.queue_stats ? (
          <Stack spacing={1} sx={{ mt: 2 }}>
            {Object.entries(metrics.queue_stats).map(([state, count]) => (
              <Box key={state} sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="body2" color="text.secondary">
                  {state}
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {count}
                </Typography>
              </Box>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No queue data available
          </Typography>
        )}

        {metrics?.processing_rate_per_hour !== undefined && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              <Schedule sx={{ fontSize: 16, verticalAlign: "middle", mr: 0.5 }} />
              Processing Rate: {metrics.processing_rate_per_hour} groups/hour
            </Typography>
          </>
        )}
      </CardContent>
    </Card>
  );
};
