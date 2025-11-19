import React from "react";
import { Card, CardContent, Typography, Stack, Box, LinearProgress } from "@mui/material";
import { Speed, Memory } from "@mui/icons-material";
import type { StreamingStatus } from "../../api/queries";

interface ResourceUsageCardProps {
  status?: StreamingStatus;
}

export const ResourceUsageCard: React.FC<ResourceUsageCardProps> = ({ status }) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Resource Usage
        </Typography>
        <Stack spacing={2} sx={{ mt: 2 }}>
          {status?.cpu_percent != null && (
            <Box>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mb: 0.5,
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  <Speed
                    sx={{
                      fontSize: 16,
                      verticalAlign: "middle",
                      mr: 0.5,
                    }}
                  />
                  CPU
                </Typography>
                <Typography variant="body2">{status.cpu_percent.toFixed(1)}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={status.cpu_percent}
                color={
                  status.cpu_percent > 80
                    ? "error"
                    : status.cpu_percent > 50
                      ? "warning"
                      : "primary"
                }
              />
            </Box>
          )}

          {status?.memory_mb != null && (
            <Box>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  mb: 0.5,
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  <Memory
                    sx={{
                      fontSize: 16,
                      verticalAlign: "middle",
                      mr: 0.5,
                    }}
                  />
                  Memory
                </Typography>
                <Typography variant="body2">{status.memory_mb.toFixed(0)} MB</Typography>
              </Box>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};
