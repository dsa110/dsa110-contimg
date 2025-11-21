/**
 * Sky View Page
 * JS9 FITS image viewer integration
 */
import { useState } from "react";
import {
  Container,
  Typography,
  Paper,
  Box,
  Grid,
  Switch,
  FormControlLabel,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Stack,
  Tabs,
  Tab,
} from "@mui/material";
import { CompareArrows } from "@mui/icons-material";
import ImageBrowser from "../components/Sky/ImageBrowser";
import DirectoryBrowser from "../components/QA/DirectoryBrowser";
import SkyViewer from "../components/Sky/SkyViewer";
import ImageControls from "../components/Sky/ImageControls";
import ImageMetadata from "../components/Sky/ImageMetadata";
import CatalogOverlayJS9 from "../components/Sky/CatalogOverlayJS9";
import RegionTools from "../components/Sky/RegionTools";
import RegionList from "../components/Sky/RegionList";
import ProfileTool from "../components/Sky/ProfileTool";
import ImageFittingTool from "../components/Sky/ImageFittingTool";
import SkyMap from "../components/Sky/SkyMap";
import PhotometryPlugin from "../components/Sky/plugins/PhotometryPlugin";
import ImageStatisticsPlugin from "../components/Sky/plugins/ImageStatisticsPlugin";
import CASAnalysisPlugin from "../components/Sky/plugins/CASAnalysisPlugin";
import MultiImageCompare from "../components/Sky/MultiImageCompare";
import QuickAnalysisPanel from "../components/Sky/QuickAnalysisPanel";
import type { ImageInfo } from "../api/types";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

export default function SkyViewPage() {
  const [selectedImage, setSelectedImage] = useState<ImageInfo | null>(null);
  const [browserMode, setBrowserMode] = useState<"database" | "filesystem">("filesystem");
  const [catalogOverlayVisible, setCatalogOverlayVisible] = useState(false);
  const [selectedCatalog, setSelectedCatalog] = useState<string>("all");
  const [selectedRegionId, setSelectedRegionId] = useState<number | null>(null);
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);

  // Construct FITS URL for selected image
  // For filesystem images (id=0), use the file path directly via visualization API
  // For database images, use the standard image API endpoint
  const fitsUrl = selectedImage
    ? selectedImage.id === 0
      ? `/api/visualization/file?path=${encodeURIComponent(selectedImage.path)}`
      : `/api/images/${selectedImage.id}/fits`
    : null;

  // Extract image center coordinates for catalog overlay
  // Note: This would ideally come from image WCS, but for now use center coordinates if available
  const imageCenter = selectedImage
    ? {
        ra: selectedImage.center_ra_deg || null,
        dec: selectedImage.center_dec_deg || null,
      }
    : { ra: null, dec: null };

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h2" component="h2" gutterBottom sx={{ mb: 4 }}>
          Sky View
        </Typography>

        {/* Interactive Sky Map */}
        <Box sx={{ mb: 4 }}>
          <SkyMap
            height={500}
            historyDays={90}
            showPointingHistory={true}
            showObservedFields={true}
          />
        </Box>

        <Grid container spacing={3}>
          {/* Image Browser Sidebar */}
          <Grid size={{ xs: 12, md: 4 }}>
            <Paper sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
              {/* Browser Mode Tabs */}
              <Tabs
                value={browserMode}
                onChange={(_, newValue) => setBrowserMode(newValue)}
                sx={{ borderBottom: 1, borderColor: "divider", px: 2 }}
              >
                <Tab label="File Browser" value="filesystem" />
                <Tab label="Database" value="database" />
              </Tabs>

              {/* Browser Content */}
              <Box sx={{ flexGrow: 1, overflow: "hidden" }}>
                {browserMode === "database" ? (
                  <ImageBrowser
                    onSelectImage={setSelectedImage}
                    selectedImageId={selectedImage?.id}
                  />
                ) : (
                  <DirectoryBrowser
                    initialPath="/stage/dsa110-contimg"
                    onSelectFile={(path, type) => {
                      if (type === "fits") {
                        // Create a minimal ImageInfo object from the file path
                        setSelectedImage({
                          id: 0, // Temporary ID for filesystem images
                          path,
                          ms_path: "filesystem",
                          type: "filesystem",
                          created_at: new Date().toISOString(),
                        } as ImageInfo);
                      }
                    }}
                  />
                )}
              </Box>
            </Paper>
          </Grid>

          {/* Main Image Display */}
          <Grid size={{ xs: 12, md: 8 }}>
            <Paper sx={{ p: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6">Image Display</Typography>
                <Button
                  variant="outlined"
                  startIcon={<CompareArrows />}
                  onClick={() => setCompareDialogOpen(true)}
                  size="small"
                >
                  Compare Images
                </Button>
              </Box>

              {/* Image Controls */}
              <ImageControls displayId="skyViewDisplay" />

              {/* Quick Analysis Panel - Always visible */}
              <Box sx={{ mb: 2 }}>
                <QuickAnalysisPanel displayId="skyViewDisplay" />
              </Box>

              {/* Catalog Overlay Toggle */}
              {selectedImage && imageCenter.ra !== null && imageCenter.dec !== null && (
                <Box sx={{ mb: 2 }}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <FormControlLabel
                      control={
                        <Switch
                          checked={catalogOverlayVisible}
                          onChange={(e) => setCatalogOverlayVisible(e.target.checked)}
                        />
                      }
                      label="Show Catalog Overlay"
                    />
                    {catalogOverlayVisible && (
                      <FormControl size="small" sx={{ minWidth: 120 }}>
                        <InputLabel>Catalog</InputLabel>
                        <Select
                          value={selectedCatalog}
                          onChange={(e) => setSelectedCatalog(e.target.value)}
                          label="Catalog"
                        >
                          <MenuItem value="all">All Catalogs</MenuItem>
                          <MenuItem value="nvss">NVSS</MenuItem>
                          <MenuItem value="first">FIRST</MenuItem>
                          <MenuItem value="racs">RACS</MenuItem>
                        </Select>
                      </FormControl>
                    )}
                  </Stack>
                  {catalogOverlayVisible && (
                    <CatalogOverlayJS9
                      displayId="skyViewDisplay"
                      ra={imageCenter.ra}
                      dec={imageCenter.dec}
                      radius={1.5}
                      catalog={selectedCatalog}
                      visible={catalogOverlayVisible}
                    />
                  )}
                </Box>
              )}

              {/* Region Tools */}
              {selectedImage && (
                <Box sx={{ mb: 2 }}>
                  <RegionTools
                    displayId="skyViewDisplay"
                    imagePath={selectedImage.path}
                    onRegionCreated={(region) => {
                      // Refresh region list
                      setSelectedRegionId(region.id);
                    }}
                  />
                </Box>
              )}

              {selectedImage && (
                <Box sx={{ mb: 2 }}>
                  <ProfileTool displayId="skyViewDisplay" imageId={selectedImage.id} />
                </Box>
              )}

              {selectedImage && (
                <Box sx={{ mb: 2 }}>
                  <ImageFittingTool
                    displayId="skyViewDisplay"
                    imageId={selectedImage.id}
                    imagePath={selectedImage.path}
                  />
                </Box>
              )}

              {/* Image Statistics Plugin */}
              {selectedImage && (
                <ImageStatisticsPlugin
                  displayId="skyViewDisplay"
                  imageInfo={{
                    noise_jy: selectedImage.noise_jy ?? undefined,
                    beam_major_arcsec: selectedImage.beam_major_arcsec ?? undefined,
                    beam_minor_arcsec: selectedImage.beam_minor_arcsec ?? undefined,
                    beam_pa_deg: selectedImage.beam_pa_deg ?? undefined,
                  }}
                />
              )}

              {/* Photometry Plugin */}
              {selectedImage && <PhotometryPlugin displayId="skyViewDisplay" />}

              {/* CASA Analysis Plugin */}
              {selectedImage && (
                <Box sx={{ mb: 2 }}>
                  <CASAnalysisPlugin displayId="skyViewDisplay" imagePath={selectedImage.path} />
                </Box>
              )}

              {/* Image Metadata */}
              {selectedImage && (
                <ImageMetadata
                  displayId="skyViewDisplay"
                  imageInfo={{
                    path: selectedImage.path,
                    type: selectedImage.type,
                    noise_jy: selectedImage.noise_jy ?? undefined,
                    beam_major_arcsec: selectedImage.beam_major_arcsec ?? undefined,
                    beam_minor_arcsec: selectedImage.beam_minor_arcsec ?? undefined,
                    beam_pa_deg: selectedImage.beam_pa_deg ?? undefined,
                  }}
                />
              )}

              <SkyViewer imagePath={fitsUrl} displayId="skyViewDisplay" height={600} />

              {/* Region List */}
              {selectedImage && (
                <Box sx={{ mt: 2 }}>
                  <RegionList
                    imagePath={selectedImage.path}
                    onRegionSelect={(region) => setSelectedRegionId(region.id)}
                    selectedRegionId={selectedRegionId}
                  />
                </Box>
              )}
            </Paper>
          </Grid>
        </Grid>

        {/* Multi-Image Compare Dialog */}
        <MultiImageCompare
          open={compareDialogOpen}
          onClose={() => setCompareDialogOpen(false)}
          initialImageA={selectedImage}
          initialImageB={null}
        />
      </Container>
    </>
  );
}
