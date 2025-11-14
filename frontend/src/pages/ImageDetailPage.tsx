/**
 * Image Detail Page
 *
 * VAST-inspired image detail page with three-column layout:
 * - Column 1: Image details and metadata
 * - Column 2: Sky visualization (Aladin Lite)
 * - Column 3: Comments/Annotations
 *
 * Full-width sections below:
 * - Measurements table (using GenericTable)
 * - Runs table (using GenericTable)
 *
 * Inspired by VAST's image_detail.html
 *
 * @module pages/ImageDetailPage
 */

import { useState } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import {
  Container,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Button,
  Stack,
  Divider,
  Collapse,
  IconButton,
  Alert,
} from "@mui/material";
import { SkeletonLoader } from "../components/SkeletonLoader";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import {
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Link as LinkIcon,
  Visibility as VisibilityIcon,
} from "@mui/icons-material";
import { useImageDetail } from "../api/queries";
import GenericTable from "../components/GenericTable";
import type { TableColumn } from "../components/GenericTable";
// Types will be inferred from API responses

export default function ImageDetailPage() {
  const { imageId } = useParams<{ imageId: string }>();
  const navigate = useNavigate();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    measurements: true,
    runs: false, // Hide runs section since n_runs is always 0
  });

  // Fetch image data
  const {
    data: image,
    isLoading: imageLoading,
    error: imageError,
  } = useImageDetail(imageId ? parseInt(imageId, 10) : null);

  // Fetch previous/next image IDs for navigation (placeholder)
  const navigationIds = { previousId: null, nextId: null };

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Format coordinates
  const formatRA = (ra: number) => {
    const hours = Math.floor(ra / 15);
    const minutes = Math.floor((ra / 15 - hours) * 60);
    const seconds = ((ra / 15 - hours) * 60 - minutes) * 60;
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toFixed(2).padStart(5, "0")}`;
  };

  const formatDec = (dec: number) => {
    const sign = dec >= 0 ? "+" : "-";
    const absDec = Math.abs(dec);
    const degrees = Math.floor(absDec);
    const minutes = Math.floor((absDec - degrees) * 60);
    const seconds = ((absDec - degrees) * 60 - minutes) * 60;
    return `${sign}${degrees.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toFixed(2).padStart(5, "0")}`;
  };

  // Measurement columns for GenericTable
  const measurementColumns: TableColumn<any>[] = [
    {
      field: "name",
      label: "Name",
      sortable: true,
    },
    {
      field: "source_id",
      label: "Source ID",
      sortable: true,
      render: (value) => value || "N/A",
    },
    {
      field: "ra",
      label: "RA (deg)",
      sortable: true,
      render: (value) => (value ? value.toFixed(6) : "N/A"),
    },
    {
      field: "dec",
      label: "Dec (deg)",
      sortable: true,
      render: (value) => (value ? value.toFixed(6) : "N/A"),
    },
    {
      field: "flux_peak",
      label: "Peak Flux (mJy/beam)",
      sortable: true,
      render: (value, row) => {
        if (!value) return "N/A";
        const err = row.flux_peak_err ? ` ± ${row.flux_peak_err.toFixed(3)}` : "";
        return `${value.toFixed(3)}${err}`;
      },
    },
    {
      field: "flux_int",
      label: "Int. Flux (mJy)",
      sortable: true,
      render: (value, row) => {
        if (!value) return "N/A";
        const err = row.flux_int_err ? ` ± ${row.flux_int_err.toFixed(3)}` : "";
        return `${value.toFixed(3)}${err}`;
      },
    },
    {
      field: "snr",
      label: "SNR",
      sortable: true,
      render: (value) => (value ? value.toFixed(2) : "N/A"),
    },
    {
      field: "forced",
      label: "Forced",
      sortable: true,
      render: (value) => (value ? "Yes" : "No"),
    },
  ];

  // Run columns for GenericTable
  const runColumns: TableColumn<any>[] = [
    {
      field: "name",
      label: "Name",
      sortable: true,
      link: (row) => `/runs/${row.id}`,
    },
    {
      field: "time",
      label: "Run Datetime",
      sortable: true,
      render: (value) => new Date(value).toLocaleString(),
    },
    {
      field: "n_images",
      label: "Nr Images",
      sortable: true,
    },
    {
      field: "n_sources",
      label: "Nr Sources",
      sortable: true,
    },
    {
      field: "status",
      label: "Status",
      sortable: true,
      render: (value) => value.toUpperCase(),
    },
  ];

  if (imageLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={4} />
      </Container>
    );
  }

  if (imageError || !image) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">
          Failed to load image details.{" "}
          {imageError instanceof Error ? imageError.message : "Unknown error"}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Page Header */}
      <Box
        sx={{
          mb: 4,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Typography variant="h1" component="h1">
          <strong>Image:</strong> {image.name}
        </Typography>
        <Stack direction="row" spacing={1}>
          {/* External links */}
          {image.ra !== null && image.dec !== null && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<LinkIcon />}
              href={`https://simbad.u-strasbg.fr/simbad/sim-coo?Coord=${image.ra}d${image.dec}d`}
              target="_blank"
            >
              SIMBAD
            </Button>
          )}
          {/* Navigation */}
          {navigationIds?.previousId && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<ArrowBackIcon />}
              onClick={() => navigate(`/images/${navigationIds.previousId}`)}
            >
              Previous
            </Button>
          )}
          {navigationIds?.nextId && (
            <Button
              size="small"
              variant="outlined"
              endIcon={<ArrowForwardIcon />}
              onClick={() => navigate(`/images/${navigationIds.nextId}`)}
            >
              Next
            </Button>
          )}
        </Stack>
      </Box>

      {/* Three-Column Layout */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          gap: 3,
        }}
      >
        {/* Column 1: Details */}
        <Box>
          <Card>
            <CardHeader title="Details" />
            <CardContent>
              <Typography variant="body2" paragraph>
                <strong>Name:</strong> {image.name}
              </Typography>

              <Divider sx={{ my: 2 }} />

              {image.ra !== null && image.dec !== null && (
                <>
                  <Typography variant="body2" paragraph>
                    <strong>Position:</strong>
                    <br />
                    {image.ra_hms || formatRA(image.ra)} {image.dec_dms || formatDec(image.dec)}
                    <br />
                    <strong>Decimal:</strong> {image.ra.toFixed(6)} {image.dec.toFixed(6)}
                  </Typography>
                </>
              )}

              {image.l !== undefined &&
                image.l !== null &&
                image.b !== undefined &&
                image.b !== null && (
                  <Typography variant="body2" paragraph>
                    <strong>Galactic:</strong> {image.l.toFixed(6)} {image.b.toFixed(6)}
                  </Typography>
                )}

              {(image.beam_bmaj || image.beam_bmin || image.beam_bpa) && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" paragraph>
                    <strong>Beam:</strong>
                    <br />
                    {image.beam_bmaj && `BMAJ: ${(image.beam_bmaj * 3600).toFixed(3)}&Prime;`}
                    <br />
                    {image.beam_bmin && `BMIN: ${(image.beam_bmin * 3600).toFixed(3)}&Prime;`}
                    <br />
                    {image.beam_bpa !== null &&
                      image.beam_bpa !== undefined &&
                      `BPA: ${image.beam_bpa.toFixed(2)}&deg;`}
                  </Typography>
                </>
              )}

              {image.rms_median !== null && image.rms_median !== undefined && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" paragraph>
                    <strong>RMS:</strong>
                    <br />
                    Median: {image.rms_median.toFixed(3)} mJy
                    <br />
                    {image.rms_min !== null &&
                      image.rms_min !== undefined &&
                      `Min: ${image.rms_min.toFixed(3)} mJy`}
                    <br />
                    {image.rms_max !== null &&
                      image.rms_max !== undefined &&
                      `Max: ${image.rms_max.toFixed(3)} mJy`}
                  </Typography>
                </>
              )}

              {(image.frequency || image.bandwidth) && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" paragraph>
                    {image.frequency && (
                      <>
                        <strong>Frequency:</strong> {image.frequency.toFixed(1)} MHz
                        <br />
                      </>
                    )}
                    {image.bandwidth && (
                      <>
                        <strong>Bandwidth:</strong> {image.bandwidth.toFixed(1)} MHz
                      </>
                    )}
                  </Typography>
                </>
              )}

              <Divider sx={{ my: 2 }} />

              <Typography variant="body2" paragraph>
                <strong>Measurements:</strong> {image.n_meas.toLocaleString()}
                <br />
                <strong>Runs:</strong> {image.n_runs.toLocaleString()}
              </Typography>

              {image.path && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" paragraph>
                    <strong>Path:</strong>
                    <br />
                    <Box component="code" sx={{ fontSize: "0.75rem", wordBreak: "break-all" }}>
                      {image.path}
                    </Box>
                  </Typography>
                  <Button
                    variant="outlined"
                    startIcon={<VisibilityIcon />}
                    component={RouterLink}
                    to={`/carta?file=${encodeURIComponent(image.path)}`}
                    sx={{ mt: 1 }}
                    fullWidth
                  >
                    View in CARTA
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </Box>

        {/* Column 2: Sky Visualization (Aladin Lite) */}
        <Box>
          <Card>
            <CardHeader title="Sky View" />
            <CardContent>
              <Box
                id="aladin-lite-div"
                sx={{
                  width: "100%",
                  height: "400px",
                  border: "1px solid #ddd",
                  borderRadius: 1,
                }}
              >
                {/* Aladin Lite will be initialized here */}
                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                  Aladin Lite integration coming soon
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* Column 3: Comments/Annotations */}
        <Box>
          <Card>
            <CardHeader title="Comments & Annotations" />
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Comments system coming soon
              </Typography>
              {/* TODO: Add comments component */}
            </CardContent>
          </Card>
        </Box>
      </Box>

      {/* Full-width: Measurements Table */}
      <Box sx={{ mt: 3 }}>
        <Card>
          <CardHeader
            title="Measurements"
            action={
              <IconButton onClick={() => toggleSection("measurements")}>
                {expandedSections.measurements ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            }
          />
          <Collapse in={expandedSections.measurements}>
            <CardContent>
              <GenericTable<any>
                apiEndpoint={`/api/images/${imageId}/measurements`}
                columns={measurementColumns}
                title=""
                searchable={true}
                exportable={true}
                pageSize={25}
                onRowClick={(row: any) => {
                  if (row.source_id) {
                    navigate(`/sources/${row.source_id}`);
                  }
                }}
                transformData={(data) => ({
                  rows: data.items || [],
                  total: data.total || 0,
                })}
              />
            </CardContent>
          </Collapse>
        </Card>
      </Box>

      {/* Full-width: Runs Table */}
      {/* TODO: Implement runs table when API endpoint is available */}
      {false && image.n_runs > 0 && (
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardHeader
              title="Pipeline Runs"
              action={
                <IconButton onClick={() => toggleSection("runs")}>
                  {expandedSections.runs ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={expandedSections.runs}>
              <CardContent>
                <GenericTable<any>
                  apiEndpoint={`/api/images/${imageId}/runs`}
                  columns={runColumns}
                  title=""
                  searchable={true}
                  exportable={true}
                  onRowClick={(row) => navigate(`/runs/${row.id}`)}
                />
              </CardContent>
            </Collapse>
          </Card>
        </Box>
      )}
    </Container>
  );
}
