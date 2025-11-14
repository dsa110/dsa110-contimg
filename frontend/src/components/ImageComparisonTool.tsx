/**
 * Enhanced Image Comparison Tool
 * Advanced image comparison with before/after, epochs, and analysis
 */
import { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  Grid,
  Button,
  Tabs,
  Tab,
  Card,
  CardContent,
  CardHeader,
  Stack,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  Switch,
  FormControlLabel,
  Alert,
  Divider,
} from "@mui/material";
import {
  CompareArrows,
  Timeline,
  Assessment,
  Download,
  Settings,
  Visibility,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import MultiImageCompare from "./Sky/MultiImageCompare";
import ImageBrowser from "./Sky/ImageBrowser";
import type { ImageInfo } from "../api/types";
import { useImagesQuery } from "../api/queries";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

interface ImageComparisonToolProps {
  initialImageA?: ImageInfo | null;
  initialImageB?: ImageInfo | null;
  mode?: "before-after" | "epochs" | "custom";
}

export default function ImageComparisonTool({
  initialImageA = null,
  initialImageB = null,
  mode = "custom",
}: ImageComparisonToolProps) {
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  const [imageA, setImageA] = useState<ImageInfo | null>(initialImageA);
  const [imageB, setImageB] = useState<ImageInfo | null>(initialImageB);
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [comparisonMode, setComparisonMode] = useState<"before-after" | "epochs" | "custom">(mode);

  // Query for images if needed
  const { data: imagesData } = useImagesQuery({
    limit: 100,
    order_by: "created_at",
    order: "desc",
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleCompare = () => {
    if (imageA && imageB) {
      setCompareDialogOpen(true);
    }
  };

  // Find before/after images (calibrated vs uncalibrated, or different processing)
  const findBeforeAfterImages = () => {
    if (!imagesData?.items) return { before: null, after: null };

    // Try to find images with same source but different calibration status
    const imageA = imagesData.items.find((img) => img.calibrated === false);
    const imageB = imagesData.items.find(
      (img) => img.calibrated === true && img.source_id === imageA?.source_id
    );

    return { before: imageA || null, after: imageB || null };
  };

  // Find epoch images (same source, different times)
  const findEpochImages = () => {
    if (!imagesData?.items) return [];

    // Group by source_id and find multiple epochs
    const bySource = imagesData.items.reduce(
      (acc, img) => {
        if (img.source_id) {
          if (!acc[img.source_id]) {
            acc[img.source_id] = [];
          }
          acc[img.source_id].push(img);
        }
        return acc;
      },
      {} as Record<string, ImageInfo[]>
    );

    // Find sources with multiple epochs
    const multiEpoch = Object.values(bySource).filter((imgs) => imgs.length > 1);
    return multiEpoch.length > 0 ? multiEpoch[0] : [];
  };

  const beforeAfterImages = findBeforeAfterImages();
  const epochImages = findEpochImages();

  return (
    <Box>
      <Paper sx={{ mb: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Before/After" icon={<CompareArrows />} iconPosition="start" />
            <Tab label="Epochs" icon={<Timeline />} iconPosition="start" />
            <Tab label="Custom" icon={<Settings />} iconPosition="start" />
            <Tab label="Analysis" icon={<Assessment />} iconPosition="start" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Before/After Comparison
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Compare images before and after calibration or processing
            </Typography>

            {beforeAfterImages.before && beforeAfterImages.after ? (
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardHeader
                      title="Before"
                      subheader={beforeAfterImages.before.calibrated ? "Uncalibrated" : "Original"}
                    />
                    <CardContent>
                      <ImageBrowser
                        selectedImage={beforeAfterImages.before}
                        onImageSelect={setImageA}
                        images={imagesData?.items || []}
                      />
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={<Visibility />}
                        onClick={() => navigate(`/images/${beforeAfterImages.before?.id}`)}
                        sx={{ mt: 2 }}
                      >
                        View Details
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardHeader
                      title="After"
                      subheader={beforeAfterImages.after.calibrated ? "Calibrated" : "Processed"}
                    />
                    <CardContent>
                      <ImageBrowser
                        selectedImage={beforeAfterImages.after}
                        onImageSelect={setImageB}
                        images={imagesData?.items || []}
                      />
                      <Button
                        variant="outlined"
                        fullWidth
                        startIcon={<Visibility />}
                        onClick={() => navigate(`/images/${beforeAfterImages.after?.id}`)}
                        sx={{ mt: 2 }}
                      >
                        View Details
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12}>
                  <Button
                    variant="contained"
                    fullWidth
                    startIcon={<CompareArrows />}
                    onClick={() => {
                      setImageA(beforeAfterImages.before);
                      setImageB(beforeAfterImages.after);
                      setCompareDialogOpen(true);
                    }}
                  >
                    Compare Images
                  </Button>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">
                No before/after image pairs found. Images need to be marked with calibration status.
              </Alert>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Epoch Comparison
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Compare images of the same source at different observation times
            </Typography>

            {epochImages.length > 0 ? (
              <Grid container spacing={2}>
                {epochImages.map((img, idx) => (
                  <Grid item xs={12} sm={6} md={4} key={img.id}>
                    <Card>
                      <CardHeader
                        title={`Epoch ${idx + 1}`}
                        subheader={
                          img.created_at
                            ? new Date(img.created_at).toLocaleDateString()
                            : "Unknown date"
                        }
                      />
                      <CardContent>
                        <Stack spacing={1}>
                          <Chip
                            label={img.calibrated ? "Calibrated" : "Uncalibrated"}
                            size="small"
                          />
                          {img.center_ra_deg && img.center_dec_deg && (
                            <Typography variant="caption" color="text.secondary">
                              RA: {img.center_ra_deg.toFixed(4)}° | Dec:{" "}
                              {img.center_dec_deg.toFixed(4)}°
                            </Typography>
                          )}
                          <Button
                            variant="outlined"
                            size="small"
                            startIcon={<Visibility />}
                            onClick={() => navigate(`/images/${img.id}`)}
                          >
                            View
                          </Button>
                        </Stack>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
                <Grid item xs={12}>
                  <Button
                    variant="contained"
                    startIcon={<CompareArrows />}
                    onClick={() => {
                      if (epochImages.length >= 2) {
                        setImageA(epochImages[0]);
                        setImageB(epochImages[1]);
                        setCompareDialogOpen(true);
                      }
                    }}
                    disabled={epochImages.length < 2}
                  >
                    Compare First Two Epochs
                  </Button>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">
                No multi-epoch images found. Images need to share the same source_id.
              </Alert>
            )}
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Custom Comparison
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Select any two images to compare
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardHeader title="Image A" />
                  <CardContent>
                    <ImageBrowser
                      selectedImage={imageA}
                      onImageSelect={setImageA}
                      images={imagesData?.items || []}
                    />
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card>
                  <CardHeader title="Image B" />
                  <CardContent>
                    <ImageBrowser
                      selectedImage={imageB}
                      onImageSelect={setImageB}
                      images={imagesData?.items || []}
                    />
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<CompareArrows />}
                  onClick={handleCompare}
                  disabled={!imageA || !imageB}
                >
                  Compare Images
                </Button>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <Box sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Comparison Analysis
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Statistical comparison and difference analysis
            </Typography>

            {imageA && imageB ? (
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardHeader title="Image A Statistics" />
                    <CardContent>
                      <Stack spacing={1}>
                        <Typography variant="body2">
                          <strong>ID:</strong> {imageA.id}
                        </Typography>
                        {imageA.created_at && (
                          <Typography variant="body2">
                            <strong>Created:</strong> {new Date(imageA.created_at).toLocaleString()}
                          </Typography>
                        )}
                        {imageA.calibrated !== undefined && (
                          <Chip
                            label={imageA.calibrated ? "Calibrated" : "Uncalibrated"}
                            size="small"
                            color={imageA.calibrated ? "success" : "default"}
                          />
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card>
                    <CardHeader title="Image B Statistics" />
                    <CardContent>
                      <Stack spacing={1}>
                        <Typography variant="body2">
                          <strong>ID:</strong> {imageB.id}
                        </Typography>
                        {imageB.created_at && (
                          <Typography variant="body2">
                            <strong>Created:</strong> {new Date(imageB.created_at).toLocaleString()}
                          </Typography>
                        )}
                        {imageB.calibrated !== undefined && (
                          <Chip
                            label={imageB.calibrated ? "Calibrated" : "Uncalibrated"}
                            size="small"
                            color={imageB.calibrated ? "success" : "default"}
                          />
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12}>
                  <Alert severity="info">
                    Advanced comparison metrics (flux differences, RMS, etc.) would be calculated
                    here when the backend API supports it.
                  </Alert>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">Select two images in the Custom tab to perform analysis</Alert>
            )}
          </Box>
        </TabPanel>
      </Paper>

      {/* Multi-Image Compare Dialog */}
      <MultiImageCompare
        open={compareDialogOpen}
        onClose={() => setCompareDialogOpen(false)}
        initialImageA={imageA}
        initialImageB={imageB}
      />
    </Box>
  );
}
