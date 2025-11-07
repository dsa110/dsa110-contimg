/**
 * CalibrationSPWPanel Component
 * 
 * Displays per-spectral-window flagging statistics for calibration QA.
 * Shows a table and visualization of SPW flagging rates.
 * 
 * **Note:** This is primarily a DIAGNOSTIC tool. The pipeline uses per-channel
 * flagging before calibration (preserves good channels). Flagging entire SPWs
 * should be a last resort if per-channel flagging is insufficient.
 * 
 * @module components/CalibrationSPWPanel
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  Alert,
  CircularProgress,
  Tooltip,
  IconButton,
  Tabs,
  Tab,
  Grid,
  Card,
  CardMedia,
  CardContent,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  BarChart as BarChartIcon,
  Download as DownloadIcon,
  Image as ImageIcon,
} from '@mui/icons-material';
import type { PerSPWStats } from '../api/types';
import { useBandpassPlots } from '../api/queries';

interface CalibrationSPWPanelProps {
  /** Per-SPW statistics to display */
  spwStats?: PerSPWStats[];
  /** MS path for generating plot */
  msPath?: string;
  /** Loading state */
  loading?: boolean;
}

export function CalibrationSPWPanel({
  spwStats,
  msPath,
  loading = false,
}: CalibrationSPWPanelProps) {
  const [plotUrl, setPlotUrl] = useState<string | null>(null);
  const [plotLoading, setPlotLoading] = useState(false);
  const [bandpassPlotTab, setBandpassPlotTab] = useState(0); // 0 = amplitude, 1 = phase
  
  const { data: bandpassPlots, isLoading: plotsLoading } = useBandpassPlots(msPath || null);

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      if (plotUrl) {
        URL.revokeObjectURL(plotUrl);
      }
    };
  }, [plotUrl]);

  const handleGeneratePlot = async () => {
    if (!msPath) return;
    
    setPlotLoading(true);
    try {
      const encodedPath = encodeURIComponent(msPath.replace(/^\//, ''));
      const response = await fetch(`/api/qa/calibration/${encodedPath}/spw-plot`);
      if (response.ok) {
        const blob = await response.blob();
        // Clean up previous URL if it exists
        if (plotUrl) {
          URL.revokeObjectURL(plotUrl);
        }
        const url = URL.createObjectURL(blob);
        setPlotUrl(url);
      } else {
        const errorText = await response.text().catch(() => 'Unknown error');
        console.error('Failed to generate plot:', response.status, errorText);
        // Could add user-facing error notification here
      }
    } catch (error) {
      console.error('Error generating plot:', error);
      // Could add user-facing error notification here
    } finally {
      setPlotLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  if (!spwStats || spwStats.length === 0) {
    return (
      <Alert severity="info">
        No per-SPW statistics available for this calibration.
      </Alert>
    );
  }

  const problematicSPWs = spwStats.filter(s => s.is_problematic);
  const sortedStats = [...spwStats].sort((a, b) => a.spw_id - b.spw_id);

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          Per-Spectral-Window Flagging Analysis
        </Typography>
        {msPath && (
          <Tooltip title="Generate visualization">
            <IconButton
              onClick={handleGeneratePlot}
              disabled={plotLoading}
              color="primary"
            >
              {plotLoading ? <CircularProgress size={24} /> : <BarChartIcon />}
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {problematicSPWs.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <strong>{problematicSPWs.length} problematic SPW(s) detected:</strong>{' '}
          {problematicSPWs.map(s => s.spw_id).join(', ')}
          {' '}— These SPWs show consistently high flagging rates and may indicate
          low S/N, RFI, or instrumental issues.
          <Box component="span" sx={{ display: 'block', mt: 1, fontSize: '0.875rem' }}>
            <strong>Note:</strong> Per-channel flagging is preferred (already done pre-calibration).
            Consider flagging entire SPWs only if per-channel flagging is insufficient.
          </Box>
        </Alert>
      )}

      {plotUrl && (
        <Box mb={2}>
          <Paper sx={{ p: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="subtitle2">Per-SPW Flagging Visualization</Typography>
              <IconButton
                size="small"
                onClick={() => {
                  const link = document.createElement('a');
                  link.href = plotUrl;
                  link.download = `spw_flagging_${msPath?.split('/').pop() || 'plot'}.png`;
                  link.click();
                }}
              >
                <DownloadIcon fontSize="small" />
              </IconButton>
            </Box>
            <Box
              component="img"
              src={plotUrl}
              alt="Per-SPW flagging visualization"
              sx={{ width: '100%', height: 'auto', maxHeight: '500px' }}
            />
          </Paper>
        </Box>
      )}

      {/* Bandpass Plots Section */}
      {bandpassPlots && bandpassPlots.plots.length > 0 && (
        <Box mb={2}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Bandpass Calibration Plots ({bandpassPlots.count} plots)
            </Typography>
            <Tabs value={bandpassPlotTab} onChange={(_, v) => setBandpassPlotTab(v)} sx={{ mb: 2 }}>
              <Tab label="Amplitude" />
              <Tab label="Phase" />
            </Tabs>
            <Grid container spacing={2}>
              {bandpassPlots.plots
                .filter(p => (bandpassPlotTab === 0 && p.type === 'amplitude') || (bandpassPlotTab === 1 && p.type === 'phase'))
                .map((plot) => (
                  <Grid item xs={12} sm={6} md={4} key={plot.filename}>
                    <Card>
                      <CardMedia
                        component="img"
                        height="200"
                        image={plot.url.startsWith('/') ? `/api${plot.url}` : plot.url}
                        alt={`${plot.type} SPW ${plot.spw !== null ? plot.spw : 'unknown'}`}
                        sx={{ objectFit: 'contain', bgcolor: 'background.paper' }}
                      />
                      <CardContent>
                        <Typography variant="caption" display="block">
                          SPW {plot.spw !== null ? plot.spw : '?'} - {plot.type}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => {
                            const link = document.createElement('a');
                            link.href = plot.url.startsWith('/') ? `/api${plot.url}` : plot.url;
                            link.download = plot.filename;
                            link.click();
                          }}
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
            </Grid>
            {bandpassPlots.plots.filter(p => (bandpassPlotTab === 0 && p.type === 'amplitude') || (bandpassPlotTab === 1 && p.type === 'phase')).length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                No {bandpassPlotTab === 0 ? 'amplitude' : 'phase'} plots available
              </Typography>
            )}
          </Paper>
        </Box>
      )}
      
      {plotsLoading && (
        <Box display="flex" justifyContent="center" p={2}>
          <CircularProgress size={24} />
        </Box>
      )}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><strong>SPW</strong></TableCell>
              <TableCell align="right"><strong>Flagged</strong></TableCell>
              <TableCell align="right"><strong>Avg/Ch</strong></TableCell>
              <TableCell align="right"><strong>High-Flag Ch</strong></TableCell>
              <TableCell align="center"><strong>Status</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedStats.map((stats) => (
              <TableRow
                key={stats.spw_id}
                sx={{
                  backgroundColor: stats.is_problematic ? 'error.light' : undefined,
                  '&:hover': { backgroundColor: 'action.hover' },
                }}
              >
                <TableCell><strong>{stats.spw_id}</strong></TableCell>
                <TableCell align="right">
                  {`${(stats.fraction_flagged * 100).toFixed(1)}%`}
                  <Typography variant="caption" color="text.secondary" display="block">
                    ({stats.flagged_solutions}/{stats.total_solutions})
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  {`${(stats.avg_flagged_per_channel * 100).toFixed(1)}%`}
                </TableCell>
                <TableCell align="right">
                  {`${stats.channels_with_high_flagging}/${stats.n_channels}`}
                </TableCell>
                <TableCell align="center">
                  {stats.is_problematic ? (
                    <Chip
                      icon={<WarningIcon />}
                      label="Problematic"
                      color="error"
                      size="small"
                    />
                  ) : (
                    <Chip
                      icon={<CheckIcon />}
                      label="OK"
                      color="success"
                      size="small"
                    />
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box mt={2}>
        <Typography variant="caption" color="text.secondary">
          <strong>Legend:</strong> Flagged = overall flagged fraction; Avg/Ch = average flagged
          fraction per channel; High-Flag Ch = channels with &gt;50% flagging. SPWs with
          &gt;80% average flagging or &gt;50% of channels with high flagging are marked as problematic.
          <Box component="span" sx={{ display: 'block', mt: 0.5 }}>
            <strong>Note:</strong> This is a diagnostic tool. Per-channel flagging (done pre-calibration)
            preserves good channels. Flagging entire SPWs should be a last resort.
          </Box>
        </Typography>
      </Box>
    </Box>
  );
}

