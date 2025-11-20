/**
 * MS Inspection Panel
 * Displays detailed MS metadata in a listobs-like format
 */
import {
  Grid,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Alert,
} from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import type { MSMetadata } from "../../api/types";

interface MSInspectionPanelProps {
  msPath?: string;
  metadata: MSMetadata | undefined;
}

export function MSInspectionPanel({ metadata }: MSInspectionPanelProps) {
  if (!metadata) {
    return (
      <Alert severity="info">Select an MS to view inspection details (listobs-like summary)</Alert>
    );
  }

  return (
    <Grid container spacing={2}>
      {/* Overview */}
      <Grid size={12}>
        <Card>
          <CardHeader title="MS Overview" />
          <CardContent>
            <Grid container spacing={2}>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Time Range
                </Typography>
                <Typography variant="body1">
                  {metadata.start_time} → {metadata.end_time}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Duration: {metadata.duration_sec?.toFixed(1)}s
                </Typography>
              </Grid>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Frequency Coverage
                </Typography>
                <Typography variant="body1">
                  {metadata.freq_min_ghz?.toFixed(3)} - {metadata.freq_max_ghz?.toFixed(3)} GHz
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {metadata.num_channels} channels
                </Typography>
              </Grid>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Size
                </Typography>
                <Typography variant="body1">{metadata.size_gb?.toFixed(2) || "N/A"} GB</Typography>
              </Grid>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Calibration Status
                </Typography>
                <Chip
                  label={metadata.calibrated ? "Calibrated" : "Uncalibrated"}
                  color={metadata.calibrated ? "success" : "default"}
                  size="small"
                />
              </Grid>
              {metadata.imaging_backend && (
                <Grid
                  size={{
                    xs: 12,
                    md: 6,
                  }}
                >
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Imaging Backend
                  </Typography>
                  <Chip
                    label={metadata.imaging_backend === "wsclean" ? "WSClean" : "tclean"}
                    color={metadata.imaging_backend === "wsclean" ? "primary" : "secondary"}
                    size="small"
                  />
                  {metadata.imager && (
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                      {metadata.imager}
                    </Typography>
                  )}
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>
      </Grid>
      {/* Antennas */}
      {metadata.antennas && metadata.antennas.length > 0 && (
        <Grid
          size={{
            xs: 12,
            md: 6,
          }}
        >
          <Card>
            <CardHeader title={`Antennas (${metadata.antennas.length})`} />
            <CardContent>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>ID</TableCell>
                      <TableCell>Name</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metadata.antennas.map((ant) => (
                      <TableRow key={ant.antenna_id}>
                        <TableCell>{ant.antenna_id}</TableCell>
                        <TableCell>{ant.name}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      )}
      {/* Fields */}
      {metadata.fields && metadata.fields.length > 0 && (
        <Grid
          size={{
            xs: 12,
            md: 6,
          }}
        >
          <Card>
            <CardHeader title={`Fields (${metadata.fields.length})`} />
            <CardContent>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>ID</TableCell>
                      <TableCell>Name</TableCell>
                      <TableCell>RA (deg)</TableCell>
                      <TableCell>Dec (deg)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metadata.fields.map((field) => (
                      <TableRow key={field.field_id}>
                        <TableCell>{field.field_id}</TableCell>
                        <TableCell>{field.name}</TableCell>
                        <TableCell>{field.ra_deg.toFixed(4)}</TableCell>
                        <TableCell>{field.dec_deg.toFixed(4)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      )}
      {/* Flagging Statistics */}
      {metadata.flagging_stats && (
        <Grid size={12}>
          <Card>
            <CardHeader title="Flagging & RFI Statistics" />
            <CardContent>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Total flagged:{" "}
                    {((metadata.flagging_stats.total_fraction ?? 0) * 100).toFixed(1)}%
                  </Typography>
                  {metadata.flagging_stats.rfi_percentage !== undefined && (
                    <Typography variant="body2" color="warning.main" gutterBottom>
                      RFI detected: {(metadata.flagging_stats.rfi_percentage * 100).toFixed(1)}%
                    </Typography>
                  )}
                </Box>

                {/* AOFlagger Configuration */}
                {(metadata.flagging_stats.aoflagger_version ||
                  metadata.flagging_stats.aoflagger_strategy) && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      AOFlagger Configuration
                    </Typography>
                    <Stack direction="row" spacing={1}>
                      {metadata.flagging_stats.aoflagger_version && (
                        <Chip
                          label={`Version ${metadata.flagging_stats.aoflagger_version}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {metadata.flagging_stats.aoflagger_strategy && (
                        <Chip
                          label={metadata.flagging_stats.aoflagger_strategy}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Box>
                )}

                {/* Per-Antenna Flagging */}
                {metadata.flagging_stats.per_antenna &&
                  Object.keys(metadata.flagging_stats.per_antenna).length > 0 && (
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="body2">
                          Per-Antenna Flagging (with RFI Context)
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Antenna</TableCell>
                                <TableCell align="right">Flagged %</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {Object.entries(metadata.flagging_stats.per_antenna).map(
                                ([antId, frac]) => {
                                  const ant = metadata.antennas?.find(
                                    (a) => String(a.antenna_id) === antId
                                  );
                                  return (
                                    <TableRow key={antId}>
                                      <TableCell>
                                        {ant ? `${ant.name} (${antId})` : `Antenna ${antId}`}
                                      </TableCell>
                                      <TableCell align="right">
                                        {((frac as number) * 100).toFixed(1)}%
                                      </TableCell>
                                    </TableRow>
                                  );
                                }
                              )}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </AccordionDetails>
                    </Accordion>
                  )}

                {/* Baseline RFI Statistics */}
                {metadata.flagging_stats.baseline_rfi_stats &&
                  Object.keys(metadata.flagging_stats.baseline_rfi_stats).length > 0 && (
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="body2">Baseline RFI Statistics (Top 20)</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Baseline</TableCell>
                                <TableCell align="right">RFI %</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {Object.entries(metadata.flagging_stats.baseline_rfi_stats)
                                .sort(([, a], [, b]) => (b as number) - (a as number))
                                .slice(0, 20)
                                .map(([baseline, rfi]) => (
                                  <TableRow key={baseline}>
                                    <TableCell sx={{ fontFamily: "monospace" }}>
                                      {baseline}
                                    </TableCell>
                                    <TableCell align="right">
                                      {((rfi as number) * 100).toFixed(1)}%
                                    </TableCell>
                                  </TableRow>
                                ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                        {Object.keys(metadata.flagging_stats.baseline_rfi_stats).length > 20 && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ mt: 1, display: "block" }}
                          >
                            Showing top 20 of{" "}
                            {Object.keys(metadata.flagging_stats.baseline_rfi_stats).length}{" "}
                            baselines
                          </Typography>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  )}

                {/* Frequency RFI Statistics */}
                {metadata.flagging_stats.frequency_rfi_stats &&
                  Object.keys(metadata.flagging_stats.frequency_rfi_stats).length > 0 && (
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="body2">
                          Frequency RFI Statistics (Top 15 Channels)
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Channel</TableCell>
                                <TableCell align="right">RFI %</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {Object.entries(metadata.flagging_stats.frequency_rfi_stats)
                                .sort(([, a], [, b]) => (b as number) - (a as number))
                                .slice(0, 15)
                                .map(([channel, rfi]) => (
                                  <TableRow key={channel}>
                                    <TableCell>Channel {channel}</TableCell>
                                    <TableCell align="right">
                                      {((rfi as number) * 100).toFixed(1)}%
                                    </TableCell>
                                  </TableRow>
                                ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                        {Object.keys(metadata.flagging_stats.frequency_rfi_stats).length > 15 && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ mt: 1, display: "block" }}
                          >
                            Showing top 15 of{" "}
                            {Object.keys(metadata.flagging_stats.frequency_rfi_stats).length}{" "}
                            channels
                          </Typography>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      )}
      {/* Data Columns */}
      {metadata.data_columns && metadata.data_columns.length > 0 && (
        <Grid size={12}>
          <Card>
            <CardHeader title="Data Columns" />
            <CardContent>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                {metadata.data_columns.map((col) => (
                  <Chip key={col} label={col} size="small" />
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      )}
    </Grid>
  );
}
