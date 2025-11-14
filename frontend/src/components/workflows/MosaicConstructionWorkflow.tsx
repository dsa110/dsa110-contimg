/**
 * Mosaic Construction Workflow
 * Visual workflow for creating mosaics from images
 */
import { useState, useMemo } from "react";
import {
  Box,
  Paper,
  Typography,
  Grid,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Button,
  Card,
  CardContent,
  CardHeader,
  Stack,
  Chip,
  Checkbox,
  FormControlLabel,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  CheckCircle,
  Image,
  GridOn,
  Settings,
  PlayArrow,
  Assessment,
  Delete,
  Add,
} from "@mui/icons-material";
import { useImages, useCreateMosaic } from "../../api/queries";
import type { ImageInfo, Mosaic } from "../../api/types";

const MOSAIC_STEPS = [
  {
    label: "Select Images",
    description: "Choose images to include in the mosaic",
    icon: <Image />,
  },
  {
    label: "Configure Mosaic",
    description: "Set mosaic parameters and method",
    icon: <Settings />,
  },
  {
    label: "Preview & Validate",
    description: "Review selected images and validate configuration",
    icon: <Assessment />,
  },
  {
    label: "Create Mosaic",
    description: "Generate the mosaic",
    icon: <GridOn />,
  },
];

interface MosaicConstructionWorkflowProps {
  initialImages?: ImageInfo[];
  onMosaicCreated?: (mosaic: Mosaic) => void;
}

export function MosaicConstructionWorkflow({
  initialImages = [],
  onMosaicCreated,
}: MosaicConstructionWorkflowProps) {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedImages, setSelectedImages] = useState<ImageInfo[]>(initialImages);
  const [mosaicParams, setMosaicParams] = useState({
    method: "linear",
    combine: "mean",
    clipmin: 0.0,
    clipmax: 1.0,
    name: "",
  });

  const { data: imagesData } = useImages({
    limit: 500,
    order_by: "created_at",
    order: "desc",
  });
  const createMosaic = useCreateMosaic();

  const handleStepChange = (step: number) => {
    if (step <= activeStep || (step === 1 && selectedImages.length > 0)) {
      setActiveStep(step);
    }
  };

  const handleNext = () => {
    if (activeStep < MOSAIC_STEPS.length - 1) {
      setActiveStep(activeStep + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleImageToggle = (image: ImageInfo) => {
    setSelectedImages((prev) => {
      const exists = prev.find((img) => img.id === image.id);
      if (exists) {
        return prev.filter((img) => img.id !== image.id);
      } else {
        return [...prev, image];
      }
    });
  };

  const handleCreateMosaic = () => {
    if (selectedImages.length < 2) {
      return;
    }

    // Find time range from selected images
    const times = selectedImages
      .map((img) => (img.created_at ? new Date(img.created_at).getTime() : null))
      .filter((t) => t !== null) as number[];

    if (times.length === 0) {
      return;
    }

    const startTime = new Date(Math.min(...times)).toISOString();
    const endTime = new Date(Math.max(...times)).toISOString();

    createMosaic.mutate(
      {
        start_time: startTime,
        end_time: endTime,
        ...mosaicParams,
      },
      {
        onSuccess: (mosaic) => {
          onMosaicCreated?.(mosaic);
          setActiveStep(MOSAIC_STEPS.length - 1);
        },
      }
    );
  };

  // Validate configuration
  const isValid = useMemo(() => {
    return (
      selectedImages.length >= 2 &&
      mosaicParams.name.trim().length > 0 &&
      mosaicParams.method.length > 0 &&
      mosaicParams.combine.length > 0
    );
  }, [selectedImages, mosaicParams]);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Mosaic Construction Workflow
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Step-by-step workflow to create mosaics from multiple images
      </Typography>
      <Stepper activeStep={activeStep} orientation="vertical">
        {MOSAIC_STEPS.map((step, index) => (
          <Step key={step.label} completed={index < activeStep}>
            <StepLabel
              StepIconComponent={({ active, completed }) => (
                <Box
                  sx={{
                    width: 40,
                    height: 40,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    bgcolor: completed
                      ? "success.main"
                      : active
                        ? "primary.main"
                        : "action.disabledBackground",
                    color: completed || active ? "white" : "action.disabled",
                  }}
                >
                  {completed ? <CheckCircle /> : step.icon}
                </Box>
              )}
              onClick={() => handleStepChange(index)}
              sx={{ cursor: index <= activeStep ? "pointer" : "default" }}
            >
              <Typography variant="h6">{step.label}</Typography>
              <Typography variant="body2" color="text.secondary">
                {step.description}
              </Typography>
            </StepLabel>
            <StepContent>
              <Box sx={{ mb: 2 }}>
                {index === 0 && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Select at least 2 images to create a mosaic:
                    </Typography>
                    <Grid container spacing={2}>
                      {imagesData?.items.map((image) => {
                        const isSelected = selectedImages.some((img) => img.id === image.id);
                        return (
                          <Grid
                            key={image.id}
                            size={{
                              xs: 12,
                              sm: 6,
                              md: 4,
                            }}
                          >
                            <Card
                              sx={{
                                border: isSelected ? 2 : 1,
                                borderColor: isSelected ? "primary.main" : "divider",
                                cursor: "pointer",
                                "&:hover": {
                                  boxShadow: 4,
                                },
                              }}
                              onClick={() => handleImageToggle(image)}
                            >
                              <CardContent>
                                <Stack direction="row" spacing={2} alignItems="center">
                                  <Checkbox checked={isSelected} />
                                  <Box sx={{ flexGrow: 1 }}>
                                    <Typography variant="subtitle2">Image {image.id}</Typography>
                                    {image.created_at && (
                                      <Typography variant="caption" color="text.secondary">
                                        {new Date(image.created_at).toLocaleDateString()}
                                      </Typography>
                                    )}
                                    {image.calibrated !== undefined && (
                                      <Chip
                                        label={image.calibrated ? "Calibrated" : "Uncalibrated"}
                                        size="small"
                                        color={image.calibrated ? "success" : "default"}
                                        sx={{ mt: 0.5 }}
                                      />
                                    )}
                                  </Box>
                                </Stack>
                              </CardContent>
                            </Card>
                          </Grid>
                        );
                      })}
                    </Grid>
                    <Alert
                      severity={selectedImages.length >= 2 ? "success" : "info"}
                      sx={{ mt: 2 }}
                    >
                      {selectedImages.length} image{selectedImages.length !== 1 ? "s" : ""} selected
                      {selectedImages.length < 2 && " (need at least 2)"}
                    </Alert>
                    <Button
                      variant="contained"
                      onClick={handleNext}
                      sx={{ mt: 2 }}
                      disabled={selectedImages.length < 2}
                    >
                      Continue to Configuration
                    </Button>
                  </Box>
                )}

                {index === 1 && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Configure mosaic parameters:
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid size={12}>
                        <TextField
                          fullWidth
                          label="Mosaic Name"
                          value={mosaicParams.name}
                          onChange={(e) =>
                            setMosaicParams({ ...mosaicParams, name: e.target.value })
                          }
                          placeholder="e.g., Field_2024_01_15"
                        />
                      </Grid>
                      <Grid
                        size={{
                          xs: 12,
                          sm: 6,
                        }}
                      >
                        <FormControl fullWidth>
                          <InputLabel>Method</InputLabel>
                          <Select
                            value={mosaicParams.method}
                            label="Method"
                            onChange={(e) =>
                              setMosaicParams({ ...mosaicParams, method: e.target.value })
                            }
                          >
                            <MenuItem value="linear">Linear</MenuItem>
                            <MenuItem value="spline">Spline</MenuItem>
                            <MenuItem value="nearest">Nearest</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid
                        size={{
                          xs: 12,
                          sm: 6,
                        }}
                      >
                        <FormControl fullWidth>
                          <InputLabel>Combine</InputLabel>
                          <Select
                            value={mosaicParams.combine}
                            label="Combine"
                            onChange={(e) =>
                              setMosaicParams({ ...mosaicParams, combine: e.target.value })
                            }
                          >
                            <MenuItem value="mean">Mean</MenuItem>
                            <MenuItem value="median">Median</MenuItem>
                            <MenuItem value="sum">Sum</MenuItem>
                            <MenuItem value="min">Min</MenuItem>
                            <MenuItem value="max">Max</MenuItem>
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid
                        size={{
                          xs: 12,
                          sm: 6,
                        }}
                      >
                        <TextField
                          fullWidth
                          label="Clip Min"
                          type="number"
                          value={mosaicParams.clipmin}
                          onChange={(e) =>
                            setMosaicParams({
                              ...mosaicParams,
                              clipmin: parseFloat(e.target.value) || 0,
                            })
                          }
                        />
                      </Grid>
                      <Grid
                        size={{
                          xs: 12,
                          sm: 6,
                        }}
                      >
                        <TextField
                          fullWidth
                          label="Clip Max"
                          type="number"
                          value={mosaicParams.clipmax}
                          onChange={(e) =>
                            setMosaicParams({
                              ...mosaicParams,
                              clipmax: parseFloat(e.target.value) || 1,
                            })
                          }
                        />
                      </Grid>
                    </Grid>
                    <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                      <Button onClick={handleBack}>Back</Button>
                      <Button variant="contained" onClick={handleNext} disabled={!isValid}>
                        Continue to Preview
                      </Button>
                    </Stack>
                  </Box>
                )}

                {index === 2 && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Review selected images and configuration:
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid
                        size={{
                          xs: 12,
                          md: 6,
                        }}
                      >
                        <Card>
                          <CardHeader title="Selected Images" />
                          <CardContent>
                            <List>
                              {selectedImages.map((image) => (
                                <ListItem
                                  key={image.id}
                                  secondaryAction={
                                    <IconButton edge="end" onClick={() => handleImageToggle(image)}>
                                      <Delete />
                                    </IconButton>
                                  }
                                >
                                  <ListItemIcon>
                                    <Image />
                                  </ListItemIcon>
                                  <ListItemText
                                    primary={`Image ${image.id}`}
                                    secondary={
                                      image.created_at
                                        ? new Date(image.created_at).toLocaleString()
                                        : "Unknown date"
                                    }
                                  />
                                </ListItem>
                              ))}
                            </List>
                          </CardContent>
                        </Card>
                      </Grid>
                      <Grid
                        size={{
                          xs: 12,
                          md: 6,
                        }}
                      >
                        <Card>
                          <CardHeader title="Configuration" />
                          <CardContent>
                            <Stack spacing={1}>
                              <Typography variant="body2">
                                <strong>Name:</strong> {mosaicParams.name || "Not set"}
                              </Typography>
                              <Typography variant="body2">
                                <strong>Method:</strong> {mosaicParams.method}
                              </Typography>
                              <Typography variant="body2">
                                <strong>Combine:</strong> {mosaicParams.combine}
                              </Typography>
                              <Typography variant="body2">
                                <strong>Clip Range:</strong> [{mosaicParams.clipmin},{" "}
                                {mosaicParams.clipmax}]
                              </Typography>
                            </Stack>
                          </CardContent>
                        </Card>
                      </Grid>
                    </Grid>
                    <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                      <Button onClick={handleBack}>Back</Button>
                      <Button variant="contained" onClick={handleNext} disabled={!isValid}>
                        Continue to Create
                      </Button>
                    </Stack>
                  </Box>
                )}

                {index === 3 && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      Create the mosaic with the configured parameters:
                    </Typography>
                    <Alert severity="info" sx={{ mb: 2 }}>
                      This will create a mosaic job. You can monitor progress in the Pipeline page.
                    </Alert>
                    <Stack direction="row" spacing={2}>
                      <Button onClick={handleBack}>Back</Button>
                      <Button
                        variant="contained"
                        startIcon={<PlayArrow />}
                        onClick={handleCreateMosaic}
                        disabled={!isValid || createMosaic.isPending}
                      >
                        {createMosaic.isPending ? "Creating..." : "Create Mosaic"}
                      </Button>
                    </Stack>
                    {createMosaic.isSuccess && (
                      <Alert severity="success" sx={{ mt: 2 }}>
                        Mosaic creation job started successfully!
                      </Alert>
                    )}
                    {createMosaic.isError && (
                      <Alert severity="error" sx={{ mt: 2 }}>
                        Failed to create mosaic: {String(createMosaic.error)}
                      </Alert>
                    )}
                  </Box>
                )}
              </Box>
            </StepContent>
          </Step>
        ))}
      </Stepper>
    </Paper>
  );
}
