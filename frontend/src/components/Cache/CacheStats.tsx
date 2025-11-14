import React from "react";
import { Box, Card, CardContent, Typography, Grid, Alert, LinearProgress } from "@mui/material";
import { Cached } from "@mui/icons-material";
import { useCacheStatistics } from "../../api/queries";
import { SkeletonLoader } from "../SkeletonLoader";
import { EmptyState } from "../EmptyState";

export default function CacheStats() {
  const { data: stats, isLoading, error } = useCacheStatistics();

  if (error) {
    return (
      <Alert severity="error">
        Failed to load cache statistics: {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  if (isLoading) {
    return <SkeletonLoader variant="cards" rows={4} />;
  }

  if (!stats) {
    return (
      <EmptyState
        icon={<Cached sx={{ fontSize: 64, color: "text.secondary" }} />}
        title="No statistics available"
        description="Cache statistics will appear here once the cache system has been initialized and is storing data."
      />
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Cache Statistics
        </Typography>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Backend Type
                </Typography>
                <Typography variant="h6">{stats.backend_type}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Total Keys
                </Typography>
                <Typography variant="h4">{stats.total_keys.toLocaleString()}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Active Keys
                </Typography>
                <Typography variant="h4">{stats.active_keys.toLocaleString()}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Hit Rate
                </Typography>
                <Typography variant="h4">{stats.hit_rate.toFixed(1)}%</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Performance Metrics */}
        <Typography variant="subtitle1" gutterBottom>
          Performance Metrics
        </Typography>
        <Grid container spacing={2}>
          <Grid xs={12} md={6}>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="body2">Hit Rate</Typography>
                <Typography variant="body2">{stats.hit_rate.toFixed(2)}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats.hit_rate}
                color="success"
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>

            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="body2">Miss Rate</Typography>
                <Typography variant="body2">{stats.miss_rate.toFixed(2)}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={stats.miss_rate}
                color="error"
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          </Grid>

          <Grid xs={12} md={6}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Operations
                </Typography>
                <Typography variant="body1">Hits: {stats.hits.toLocaleString()}</Typography>
                <Typography variant="body1">Misses: {stats.misses.toLocaleString()}</Typography>
                <Typography variant="body1">Sets: {stats.sets.toLocaleString()}</Typography>
                <Typography variant="body1">Deletes: {stats.deletes.toLocaleString()}</Typography>
                <Typography variant="body1" sx={{ mt: 1, fontWeight: "bold" }}>
                  Total Requests: {stats.total_requests.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}
