import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  LinearProgress,
} from '@mui/material';
import { useCachePerformance } from '../../api/queries';

export default function CachePerformance() {
  const { data: performance, isLoading, error } = useCachePerformance();

  if (error) {
    return (
      <Alert severity="error">
        Failed to load cache performance: {error instanceof Error ? error.message : 'Unknown error'}
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!performance) {
    return <Alert severity="info">No performance data available</Alert>;
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Cache Performance
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body1" fontWeight="bold">
                  Hit Rate
                </Typography>
                <Typography variant="h6">{performance.hit_rate.toFixed(2)}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={performance.hit_rate}
                color="success"
                sx={{ height: 12, borderRadius: 4 }}
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body1" fontWeight="bold">
                  Miss Rate
                </Typography>
                <Typography variant="h6">{performance.miss_rate.toFixed(2)}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={performance.miss_rate}
                color="error"
                sx={{ height: 12, borderRadius: 4 }}
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  Request Statistics
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Backend: {performance.backend_type}
                </Typography>
                <Typography variant="body1" sx={{ mt: 2 }}>
                  Total Requests: {performance.total_requests.toLocaleString()}
                </Typography>
                <Typography variant="body1">
                  Hits: {performance.hits.toLocaleString()}
                </Typography>
                <Typography variant="body1">
                  Misses: {performance.misses.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

