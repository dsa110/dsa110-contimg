import React from "react";
import { Card, CardContent, Typography, Stack } from "@mui/material";
import type { StreamingConfig } from "../../api/queries";

interface ConfigurationCardProps {
  config?: StreamingConfig;
}

export const ConfigurationCard: React.FC<ConfigurationCardProps> = ({ config }) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Current Configuration
        </Typography>
        {config ? (
          <Stack spacing={1} sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Input Directory:</strong> {config.input_dir}
            </Typography>
            <Typography variant="body2">
              <strong>Output Directory:</strong> {config.output_dir}
            </Typography>
            <Typography variant="body2">
              <strong>Expected Subbands:</strong> {config.expected_subbands}
            </Typography>
            <Typography variant="body2">
              <strong>Chunk Duration:</strong> {config.chunk_duration} minutes
            </Typography>
            <Typography variant="body2">
              <strong>Max Workers:</strong> {config.max_workers}
            </Typography>
            <Typography variant="body2">
              <strong>Log Level:</strong> {config.log_level}
            </Typography>
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No configuration loaded
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};
