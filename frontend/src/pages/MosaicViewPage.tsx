/**
 * Mosaic View Page
 * JS9 FITS mosaic viewer
 */
import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Container, Typography, Paper, Box, Alert, Chip, Button } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { ArrowBack } from "@mui/icons-material";
import SkyViewer from "../components/Sky/SkyViewer";
import { useMosaic } from "../api/queries";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { SkeletonLoader } from "../components/SkeletonLoader";

export default function MosaicViewPage() {
  const { mosaicId } = useParams<{ mosaicId: string }>();
  const navigate = useNavigate();

  const numericId = mosaicId ? parseInt(mosaicId, 10) : null;
  const { data: mosaic, isLoading, error } = useMosaic(numericId);

  // Construct FITS URL for mosaic
  const fitsUrl = numericId ? `/api/mosaics/${numericId}/fits` : null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "success" as const;
      case "in_progress":
        return "info" as const;
      case "pending":
        return "warning" as const;
      case "failed":
        return "error" as const;
      default:
        return "default" as const;
    }
  };

  if (isLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={3} />
      </Container>
    );
  }

  if (error || !mosaic) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">
          {error ? `Error loading mosaic: ${error}` : "Mosaic not found"}
        </Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate("/mosaics")} sx={{ mt: 2 }}>
          Back to Gallery
        </Button>
      </Container>
    );
  }

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box display="flex" alignItems="center" gap={2} mb={4}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate("/mosaics")} variant="outlined">
            Back to Gallery
          </Button>
          <Typography variant="h1" component="h1">
            {mosaic.name}
          </Typography>
          <Chip label={mosaic.status ?? ""} color={getStatusColor(mosaic.status)} size="small" />
        </Box>

        <Grid container spacing={3}>
          {/* Mosaic Metadata */}
          <Grid item xs={12} md={4} {...({} as any)}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Mosaic Information
              </Typography>

              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  <strong>Time Range:</strong>
                </Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  {mosaic.start_time ? new Date(mosaic.start_time).toLocaleString() : "N/A"} →<br />
                  {mosaic.end_time ? new Date(mosaic.end_time).toLocaleString() : "N/A"}
                </Typography>

                <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {mosaic.image_count !== undefined && (
                    <Chip label={`${mosaic.image_count} images`} size="small" variant="outlined" />
                  )}
                  {mosaic.noise_jy !== undefined && (
                    <Chip
                      label={`${(mosaic.noise_jy * 1000).toFixed(2)} mJy noise`}
                      size="small"
                      variant="outlined"
                    />
                  )}
                  {mosaic.source_count !== undefined && (
                    <Chip
                      label={`${mosaic.source_count} sources`}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </Box>

                {mosaic.created_at && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Created:</strong> {new Date(mosaic.created_at).toLocaleString()}
                    </Typography>
                  </Box>
                )}

                {mosaic.path && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary" noWrap>
                      <strong>Path:</strong> {mosaic.path.split("/").pop()}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Paper>
          </Grid>

          {/* Main Mosaic Display */}
          <Grid item xs={12} md={8} {...({} as any)}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
                Mosaic Display
              </Typography>

              <SkyViewer imagePath={fitsUrl} displayId="mosaicViewDisplay" height={700} />
            </Paper>
          </Grid>
        </Grid>
      </Container>
    </>
  );
}
