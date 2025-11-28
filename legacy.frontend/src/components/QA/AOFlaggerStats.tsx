/**
 * AOFlagger Statistics Component
 * Displays detailed AOFlagger RFI detection statistics
 */
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Stack,
  Chip,
  LinearProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import {
  ExpandMore,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Info as InfoIcon,
} from "@mui/icons-material";
import type { FlaggingStats } from "../../api/types";

interface AOFlaggerStatsProps {
  stats: FlaggingStats;
  msPath?: string;
}

export function AOFlaggerStats({ stats, msPath }: AOFlaggerStatsProps) {
  const rfiPercentage = stats.rfi_percentage ?? stats.total_fraction ?? 0;
  const totalFlagged = (stats.total_fraction ?? 0) * 100;

  // Determine severity level
  const getSeverityLevel = (percentage: number) => {
    if (percentage < 10) return { level: "good", color: "success" as const, label: "Good" };
    if (percentage < 25) return { level: "moderate", color: "warning" as const, label: "Moderate" };
    return { level: "high", color: "error" as const, label: "High" };
  };

  const rfiFlaggedSeverity = getSeverityLevel(rfiPercentage * 100);
  const totalFlaggedSeverity = getSeverityLevel(totalFlagged);

  return (
    <Card>
      <CardHeader
        title="AOFlagger RFI Statistics"
        avatar={<WarningIcon />}
        subheader={msPath ? msPath.split("/").pop() : undefined}
      />
      <CardContent>
        <Stack spacing={3}>
          {/* Overview */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Box>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="text.secondary">
                    Total Flagged
                  </Typography>
                  <Chip
                    label={totalFlaggedSeverity.label}
                    color={totalFlaggedSeverity.color}
                    size="small"
                  />
                </Box>
                <Typography variant="h4" gutterBottom>
                  {totalFlagged.toFixed(1)}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(totalFlagged, 100)}
                  color={totalFlaggedSeverity.color}
                  sx={{ height: 8, borderRadius: 1 }}
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="text.secondary">
                    RFI Detected
                  </Typography>
                  <Chip
                    label={rfiFlaggedSeverity.label}
                    color={rfiFlaggedSeverity.color}
                    size="small"
                  />
                </Box>
                <Typography variant="h4" gutterBottom>
                  {(rfiPercentage * 100).toFixed(1)}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(rfiPercentage * 100, 100)}
                  color={rfiFlaggedSeverity.color}
                  sx={{ height: 8, borderRadius: 1 }}
                />
              </Box>
            </Grid>
          </Grid>

          {/* AOFlagger Configuration */}
          {(stats.aoflagger_version || stats.aoflagger_strategy) && (
            <Box>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <InfoIcon fontSize="small" /> AOFlagger Configuration
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 1 }}>
                {stats.aoflagger_version && (
                  <Chip
                    label={`v${stats.aoflagger_version}`}
                    size="small"
                    variant="outlined"
                    icon={<CheckIcon />}
                  />
                )}
                {stats.aoflagger_strategy && (
                  <Chip
                    label={`Strategy: ${stats.aoflagger_strategy}`}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                )}
              </Stack>
            </Box>
          )}

          {/* Quality Assessment */}
          <Box>
            {totalFlagged < 10 ? (
              <Alert severity="success" icon={<CheckIcon />}>
                Data quality is good. Low flagging percentage indicates minimal RFI contamination.
              </Alert>
            ) : totalFlagged < 25 ? (
              <Alert severity="warning">
                Moderate flagging detected. Review baseline and frequency statistics for affected
                channels.
              </Alert>
            ) : (
              <Alert severity="error">
                High flagging percentage detected. Significant RFI contamination may affect data
                quality. Consider re-observation or additional flagging strategies.
              </Alert>
            )}
          </Box>

          {/* Baseline RFI Statistics */}
          {stats.baseline_rfi_stats && Object.keys(stats.baseline_rfi_stats).length > 0 && (
            <Accordion defaultExpanded={totalFlagged > 25}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">
                  Baseline RFI Statistics ({Object.keys(stats.baseline_rfi_stats).length} baselines)
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Baseline</TableCell>
                        <TableCell align="right">RFI %</TableCell>
                        <TableCell align="right">Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(stats.baseline_rfi_stats)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .slice(0, 15)
                        .map(([baseline, rfi]) => {
                          const rfiPercent = (rfi as number) * 100;
                          const severity = getSeverityLevel(rfiPercent);
                          return (
                            <TableRow key={baseline}>
                              <TableCell sx={{ fontFamily: "monospace" }}>{baseline}</TableCell>
                              <TableCell align="right">{rfiPercent.toFixed(1)}%</TableCell>
                              <TableCell align="right">
                                <Chip label={severity.label} color={severity.color} size="small" />
                              </TableCell>
                            </TableRow>
                          );
                        })}
                    </TableBody>
                  </Table>
                </TableContainer>
                {Object.keys(stats.baseline_rfi_stats).length > 15 && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 1, display: "block" }}
                  >
                    Showing top 15 most affected baselines.{" "}
                    {Object.keys(stats.baseline_rfi_stats).length - 15} more available.
                  </Typography>
                )}
              </AccordionDetails>
            </Accordion>
          )}

          {/* Frequency RFI Statistics */}
          {stats.frequency_rfi_stats && Object.keys(stats.frequency_rfi_stats).length > 0 && (
            <Accordion defaultExpanded={totalFlagged > 25}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">
                  Frequency RFI Statistics ({Object.keys(stats.frequency_rfi_stats).length}{" "}
                  channels)
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                  RFI contamination by frequency channel. High percentages indicate narrow-band RFI.
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Channel</TableCell>
                        <TableCell align="right">RFI %</TableCell>
                        <TableCell align="right">Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(stats.frequency_rfi_stats)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .slice(0, 15)
                        .map(([channel, rfi]) => {
                          const rfiPercent = (rfi as number) * 100;
                          const severity = getSeverityLevel(rfiPercent);
                          return (
                            <TableRow key={channel}>
                              <TableCell>Channel {channel}</TableCell>
                              <TableCell align="right">{rfiPercent.toFixed(1)}%</TableCell>
                              <TableCell align="right">
                                <Chip label={severity.label} color={severity.color} size="small" />
                              </TableCell>
                            </TableRow>
                          );
                        })}
                    </TableBody>
                  </Table>
                </TableContainer>
                {Object.keys(stats.frequency_rfi_stats).length > 15 && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 1, display: "block" }}
                  >
                    Showing top 15 most affected channels.{" "}
                    {Object.keys(stats.frequency_rfi_stats).length - 15} more available.
                  </Typography>
                )}
              </AccordionDetails>
            </Accordion>
          )}

          {/* Time-based RFI Statistics */}
          {stats.time_rfi_stats && Object.keys(stats.time_rfi_stats).length > 0 && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="subtitle2">
                  Time RFI Statistics ({Object.keys(stats.time_rfi_stats).length} time slots)
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="caption" color="text.secondary" gutterBottom display="block">
                  RFI contamination over time. Peaks indicate transient RFI events.
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Time Slot</TableCell>
                        <TableCell align="right">RFI %</TableCell>
                        <TableCell align="right">Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(stats.time_rfi_stats)
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .slice(0, 15)
                        .map(([time, rfi]) => {
                          const rfiPercent = (rfi as number) * 100;
                          const severity = getSeverityLevel(rfiPercent);
                          return (
                            <TableRow key={time}>
                              <TableCell>Slot {time}</TableCell>
                              <TableCell align="right">{rfiPercent.toFixed(1)}%</TableCell>
                              <TableCell align="right">
                                <Chip label={severity.label} color={severity.color} size="small" />
                              </TableCell>
                            </TableRow>
                          );
                        })}
                    </TableBody>
                  </Table>
                </TableContainer>
                {Object.keys(stats.time_rfi_stats).length > 15 && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 1, display: "block" }}
                  >
                    Showing top 15 most affected time slots.{" "}
                    {Object.keys(stats.time_rfi_stats).length - 15} more available.
                  </Typography>
                )}
              </AccordionDetails>
            </Accordion>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
