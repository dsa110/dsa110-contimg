/**
 * ESE (Extreme Scattering Event) Candidates Panel
 * Shows live variability alerts with 5σ threshold
 */
import {
  Paper,
  Typography,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
} from '@mui/material';
import { CheckCircle } from '@mui/icons-material';
import { useESECandidates } from '../api/queries';
import type { ESECandidate } from '../api/types';

function getStatusColor(status: ESECandidate['status']) {
  switch (status) {
    case 'active':
      return 'error';
    case 'resolved':
      return 'success';
    case 'false_positive':
      return 'default';
    default:
      return 'default';
  }
}

export default function ESECandidatesPanel() {
  const { data, isLoading, error } = useESECandidates();

  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box display="flex" alignItems="center" gap={2}>
          <CircularProgress size={20} />
          <Typography>Loading ESE candidates...</Typography>
        </Box>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="warning">
          ESE candidates not available. This feature requires the enhanced API endpoints.
        </Alert>
      </Paper>
    );
  }

  const activeCandidates = data?.candidates.filter((c) => c.status === 'active') || [];

  return (
    <Paper sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">
          ESE Candidates
          {activeCandidates.length > 0 && (
            <Chip
              label={activeCandidates.length}
              color="error"
              size="small"
              sx={{ ml: 2 }}
            />
          )}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          5σ threshold | Auto-refresh: 10s
        </Typography>
      </Box>

      {data?.candidates.length === 0 ? (
        <Alert severity="success" icon={<CheckCircle />}>
          No ESE candidates detected. All monitored sources within normal variability.
        </Alert>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Source ID</TableCell>
                <TableCell align="right">σ Deviation</TableCell>
                <TableCell align="right">Current Flux</TableCell>
                <TableCell align="right">Baseline</TableCell>
                <TableCell align="right">First Detected</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data?.candidates.map((candidate) => (
                <TableRow
                  key={candidate.source_id}
                  sx={{
                    backgroundColor:
                      candidate.status === 'active' ? 'rgba(244, 67, 54, 0.05)' : 'inherit',
                  }}
                >
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {candidate.source_id}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      fontWeight="bold"
                      color={candidate.max_sigma_dev >= 10 ? 'error.main' : 'warning.main'}
                    >
                      {candidate.max_sigma_dev.toFixed(1)}σ
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {(candidate.current_flux_jy * 1000).toFixed(1)} mJy
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.secondary">
                      {(candidate.baseline_flux_jy * 1000).toFixed(1)} mJy
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" color="text.secondary">
                      {new Date(candidate.first_detection_at).toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={candidate.status.replace('_', ' ')}
                      color={getStatusColor(candidate.status)}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
}

