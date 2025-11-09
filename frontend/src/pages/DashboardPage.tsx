import {
  Container,
  Typography,
  Paper,
  Box,
  CircularProgress,
  Alert,
  Stack,
} from '@mui/material';
import { usePipelineStatus, useSystemMetrics } from '../api/queries';
import ESECandidatesPanel from '../components/ESECandidatesPanel';
import PointingVisualization from '../components/PointingVisualization';

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading, error: statusError } = usePipelineStatus();
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useSystemMetrics();

  if (statusLoading || metricsLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 8, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="body1" sx={{ mt: 2 }}>
          Loading pipeline status...
        </Typography>
      </Container>
    );
  }

  if (statusError || metricsError) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">
          Failed to connect to DSA-110 pipeline API. Is the backend running at {import.meta.env.VITE_API_URL || 'http://localhost:8000'}?
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
        DSA-110 Continuum Imaging Pipeline
      </Typography>

      <Stack spacing={3}>
        {/* Row 1: Pipeline Status + System Health */}
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              Pipeline Status
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Queue Statistics
              </Typography>
              <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">Total: <strong>{status?.queue.total || 0}</strong></Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">Pending: <strong>{status?.queue.pending || 0}</strong></Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">In Progress: <strong>{status?.queue.in_progress || 0}</strong></Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">Completed: <strong>{status?.queue.completed || 0}</strong></Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">Failed: <strong>{status?.queue.failed || 0}</strong></Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">Collecting: <strong>{status?.queue.collecting || 0}</strong></Typography>
                </Box>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
                Calibration Sets
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Active: <strong>{status?.calibration_sets.length || 0}</strong>
              </Typography>
            </Box>
          </Paper>

        {/* System Health */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              System Health
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Resource Usage
              </Typography>
              <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">
                    CPU: <strong>{metrics?.cpu_percent?.toFixed(1) || 'N/A'}%</strong>
                  </Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">
                    Memory: <strong>{metrics?.mem_percent?.toFixed(1) || 'N/A'}%</strong>
                  </Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">
                    Disk: <strong>
                      {metrics?.disk_total && metrics?.disk_used
                        ? ((metrics.disk_used / metrics.disk_total) * 100).toFixed(1)
                        : 'N/A'}%
                    </strong>
                  </Typography>
                </Box>
                <Box sx={{ flex: '1 1 45%' }}>
                  <Typography variant="body2">
                    Load (1m): <strong>{metrics?.load_1?.toFixed(2) || 'N/A'}</strong>
                  </Typography>
                </Box>
              </Box>

              <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
                Last Updated
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                {metrics?.ts ? new Date(metrics.ts).toLocaleString() : 'N/A'}
              </Typography>
            </Box>
          </Paper>
        </Stack>

        {/* Recent Observations */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              Recent Observations
            </Typography>
            <Box sx={{ mt: 2 }}>
              {status?.recent_groups && status.recent_groups.length > 0 ? (
                <Box sx={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid #30363D' }}>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Group ID</th>
                        <th style={{ textAlign: 'left', padding: '8px' }}>State</th>
                        <th style={{ textAlign: 'right', padding: '8px' }}>Subbands</th>
                        <th style={{ textAlign: 'left', padding: '8px' }}>Calibrator</th>
                      </tr>
                    </thead>
                    <tbody>
                      {status.recent_groups.slice(0, 10).map((group) => (
                        <tr key={group.group_id} style={{ borderBottom: '1px solid #30363D' }}>
                          <td style={{ padding: '8px' }}>{group.group_id}</td>
                          <td style={{ padding: '8px' }}>{group.state}</td>
                          <td style={{ textAlign: 'right', padding: '8px' }}>
                            {group.subbands_present}/{group.expected_subbands}
                          </td>
                          <td style={{ padding: '8px' }}>
                            {group.has_calibrator ? '✓' : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No recent observations
                </Typography>
              )}
            </Box>
          </Paper>

        {/* Pointing Visualization */}
        <PointingVisualization height={500} showHistory={true} historyDays={7} />

        {/* ESE Candidates Panel */}
        <ESECandidatesPanel />

        {/* Status Summary */}
        <Alert severity="success">
          DSA-110 Frontend v0.2.0 - Enhanced dashboard with ESE monitoring, mosaic gallery,
          source tracking, and interactive visualizations now available!
        </Alert>
      </Stack>
    </Container>
  );
}

