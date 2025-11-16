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
  msPath: string;
  metadata: MSMetadata | undefined;
}

export function MSInspectionPanel({ msPath, metadata }: MSInspectionPanelProps) {
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
            <CardHeader title="Flagging Statistics" />
            <CardContent>
              <Typography variant="body2" gutterBottom>
                Total flagged: {((metadata.flagging_stats.total_fraction ?? 0) * 100).toFixed(1)}%
              </Typography>
              {metadata.flagging_stats.per_antenna &&
                Object.keys(metadata.flagging_stats.per_antenna).length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="body2">Per-Antenna Flagging</Typography>
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
