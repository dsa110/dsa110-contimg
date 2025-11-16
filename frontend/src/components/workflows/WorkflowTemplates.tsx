/**
 * Workflow Templates Component
 * Astronomy-specific workflow templates with parameter presets
 */
import { useState } from "react";
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Button,
  Chip,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
} from "@mui/material";
import { PlayArrow, Save, Download, Build, Image, GridOn, Science } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: "calibration" | "imaging" | "mosaic" | "analysis";
  icon: React.ReactNode;
  parameters: Record<string, any>;
  casaScript?: string; // Generated CASA script
}

const TEMPLATES: WorkflowTemplate[] = [
  {
    id: "calibrate-new-obs",
    name: "Calibrate New Observation",
    description: "Full calibration workflow for a new observation",
    category: "calibration",
    icon: <Build />,
    parameters: {
      solve_delay: true,
      solve_bandpass: true,
      solve_gains: true,
      gain_solint: "inf",
      gain_calmode: "ap",
      auto_fields: true,
      min_pb: 0.5,
    },
    casaScript: `# Calibrate New Observation
gaincal(vis='{ms_path}', caltable='{k_table}', caltype='K')
bandpass(vis='{ms_path}', caltable='{bp_table}', gaintable=['{k_table}'])
gaincal(vis='{ms_path}', caltable='{g_table}', gaintable=['{k_table}', '{bp_table}'])
applycal(vis='{ms_path}', gaintable=['{k_table}', '{bp_table}', '{g_table}'])`,
  },
  {
    id: "image-calibrated-ms",
    name: "Image Calibrated MS",
    description: "Create image from calibrated Measurement Set",
    category: "imaging",
    icon: <Image />,
    parameters: {
      imsize: [2048, 2048],
      cell: "1arcsec",
      weighting: "briggs",
      robust: 0.5,
      niter: 1000,
      threshold: "0.1mJy",
    },
    casaScript: `# Image Calibrated MS
tclean(vis='{ms_path}',
       imagename='{image_name}',
       imsize={imsize},
       cell='{cell}',
       weighting='{weighting}',
       robust={robust},
       niter={niter},
       threshold='{threshold}')`,
  },
  {
    id: "create-mosaic",
    name: "Create Mosaic from Images",
    description: "Combine multiple images into a mosaic",
    category: "mosaic",
    icon: <GridOn />,
    parameters: {
      method: "linear",
      combine: "mean",
      clipmin: 0.0,
    },
  },
  {
    id: "ese-investigation",
    name: "ESE Candidate Investigation",
    description: "Investigate Extreme Scattering Event candidates",
    category: "analysis",
    icon: <Science />,
    parameters: {
      min_sigma: 5.0,
      time_range_days: 30,
      include_photometry: true,
    },
  },
  {
    id: "full-pipeline",
    name: "Full Pipeline Workflow",
    description: "Complete pipeline: conversion → calibration → imaging",
    category: "imaging",
    icon: <PlayArrow />,
    parameters: {
      start_time: "",
      end_time: "",
      solve_delay: true,
      solve_bandpass: true,
      solve_gains: true,
      imsize: [2048, 2048],
      cell: "1arcsec",
    },
    casaScript: `# Full Pipeline Workflow
# Step 1: Convert UVH5 to MS
# (handled by pipeline)

# Step 2: Calibrate
gaincal(vis='{ms_path}', caltable='{k_table}', caltype='K')
bandpass(vis='{ms_path}', caltable='{bp_table}', gaintable=['{k_table}'])
gaincal(vis='{ms_path}', caltable='{g_table}', gaintable=['{k_table}', '{bp_table}'])
applycal(vis='{ms_path}', gaintable=['{k_table}', '{bp_table}', '{g_table}'])

# Step 3: Image
tclean(vis='{ms_path}',
       imagename='{image_name}',
       imsize={imsize},
       cell='{cell}',
       weighting='briggs',
       robust=0.5,
       niter=1000,
       threshold='0.1mJy')`,
  },
  {
    id: "quick-calibration",
    name: "Quick Calibration (Gains Only)",
    description: "Fast calibration workflow with gain calibration only",
    category: "calibration",
    icon: <Build />,
    parameters: {
      solve_gains: true,
      gain_solint: "60s",
      gain_calmode: "ap",
      auto_fields: true,
    },
    casaScript: `# Quick Calibration - Gains Only
gaincal(vis='{ms_path}', 
        caltable='{g_table}',
        solint='{gain_solint}',
        calmode='{gain_calmode}')`,
  },
  {
    id: "deep-imaging",
    name: "Deep Imaging",
    description: "High-sensitivity imaging with extended cleaning",
    category: "imaging",
    icon: <Image />,
    parameters: {
      imsize: [4096, 4096],
      cell: "0.5arcsec",
      weighting: "briggs",
      robust: -0.5,
      niter: 10000,
      threshold: "0.01mJy",
      multiscale: true,
    },
    casaScript: `# Deep Imaging
tclean(vis='{ms_path}',
       imagename='{image_name}',
       imsize={imsize},
       cell='{cell}',
       weighting='{weighting}',
       robust={robust},
       niter={niter},
       threshold='{threshold}',
       multiscale={multiscale})`,
  },
];

interface WorkflowTemplatesProps {
  onTemplateSelect?: (template: WorkflowTemplate) => void;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function WorkflowTemplates({ _onTemplateSelect }: WorkflowTemplatesProps) {
  const navigate = useNavigate();
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [parameterValues, setParameterValues] = useState<Record<string, any>>({});

  const handleTemplateClick = (template: WorkflowTemplate) => {
    setSelectedTemplate(template);
    setParameterValues({ ...template.parameters });
    setDialogOpen(true);
  };

  const handleRunTemplate = () => {
    if (!selectedTemplate) return;

    // Navigate to appropriate page based on template category
    switch (selectedTemplate.category) {
      case "calibration":
        navigate("/calibration", {
          state: { template: selectedTemplate, parameters: parameterValues },
        });
        break;
      case "imaging":
        navigate("/control", {
          state: { template: selectedTemplate, parameters: parameterValues },
        });
        break;
      case "mosaic":
        navigate("/mosaics", {
          state: { template: selectedTemplate, parameters: parameterValues },
        });
        break;
      case "analysis":
        navigate("/sources", {
          state: { template: selectedTemplate, parameters: parameterValues },
        });
        break;
    }
    setDialogOpen(false);
  };

  const handleExportScript = () => {
    if (!selectedTemplate || !selectedTemplate.casaScript) return;

    // Replace placeholders with actual parameter values
    let script = selectedTemplate.casaScript;
    Object.entries(parameterValues).forEach(([key, value]) => {
      script = script.replace(new RegExp(`\\{${key}\\}`, "g"), String(value));
    });

    // Download as file
    const blob = new Blob([script], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedTemplate.id}.py`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleSaveTemplate = () => {
    if (!selectedTemplate) return;
    // Save custom template to localStorage or backend
    const customTemplates = JSON.parse(localStorage.getItem("customWorkflowTemplates") || "[]");
    customTemplates.push({
      ...selectedTemplate,
      parameters: parameterValues,
      custom: true,
    });
    localStorage.setItem("customWorkflowTemplates", JSON.stringify(customTemplates));
    setDialogOpen(false);
  };

  const categoryColors: Record<string, "primary" | "success" | "warning" | "error" | "info"> = {
    calibration: "primary",
    imaging: "success",
    mosaic: "warning",
    analysis: "error",
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Workflow Templates
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Astronomy-specific workflow templates with parameter presets
      </Typography>
      <Grid container spacing={2}>
        {TEMPLATES.map((template) => (
          <Grid
            key={template.id}
            size={{
              xs: 12,
              sm: 6,
              md: 4,
            }}
          >
            <Card
              sx={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                cursor: "pointer",
                "&:hover": {
                  boxShadow: 4,
                  transform: "translateY(-2px)",
                  transition: "all 0.2s",
                },
              }}
              onClick={() => handleTemplateClick(template)}
            >
              <CardHeader
                avatar={
                  <Box
                    sx={{
                      color: categoryColors[template.category] || "default",
                      display: "flex",
                      alignItems: "center",
                    }}
                  >
                    {template.icon}
                  </Box>
                }
                title={template.name}
                subheader={
                  <Chip
                    label={template.category}
                    size="small"
                    color={categoryColors[template.category] || "default"}
                    sx={{ mt: 0.5 }}
                  />
                }
              />
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  {template.description}
                </Typography>
              </CardContent>
              <Box sx={{ p: 2, pt: 0 }}>
                <Button
                  variant="contained"
                  fullWidth
                  startIcon={<PlayArrow />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTemplateClick(template);
                  }}
                >
                  Use Template
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>
      {/* Template Configuration Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Stack direction="row" spacing={2} alignItems="center">
            {selectedTemplate?.icon}
            <Box>
              <Typography variant="h6">{selectedTemplate?.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {selectedTemplate?.description}
              </Typography>
            </Box>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="subtitle2" gutterBottom sx={{ mb: 2 }}>
            Configure Parameters
          </Typography>
          <Grid container spacing={2}>
            {selectedTemplate &&
              Object.entries(parameterValues).map(([key, value]) => (
                <Grid
                  key={key}
                  size={{
                    xs: 12,
                    sm: 6,
                  }}
                >
                  {typeof value === "boolean" ? (
                    <FormControl fullWidth>
                      <InputLabel>{key.replace(/_/g, " ")}</InputLabel>
                      <Select
                        value={value ? "true" : "false"}
                        label={key.replace(/_/g, " ")}
                        onChange={(e) =>
                          setParameterValues({
                            ...parameterValues,
                            [key]: e.target.value === "true",
                          })
                        }
                      >
                        <MenuItem value="true">True</MenuItem>
                        <MenuItem value="false">False</MenuItem>
                      </Select>
                    </FormControl>
                  ) : typeof value === "number" ? (
                    <TextField
                      fullWidth
                      label={key.replace(/_/g, " ")}
                      type="number"
                      value={value}
                      onChange={(e) =>
                        setParameterValues({
                          ...parameterValues,
                          [key]: parseFloat(e.target.value) || 0,
                        })
                      }
                    />
                  ) : (
                    <TextField
                      fullWidth
                      label={key.replace(/_/g, " ")}
                      value={value}
                      onChange={(e) =>
                        setParameterValues({
                          ...parameterValues,
                          [key]: e.target.value,
                        })
                      }
                    />
                  )}
                </Grid>
              ))}
          </Grid>

          {selectedTemplate?.casaScript && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Generated CASA Script
              </Typography>
              <Box
                component="pre"
                sx={{
                  fontFamily: "monospace",
                  fontSize: "0.75rem",
                  bgcolor: "background.default",
                  p: 2,
                  borderRadius: 1,
                  overflow: "auto",
                  maxHeight: 200,
                }}
              >
                {selectedTemplate.casaScript}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          {selectedTemplate?.casaScript && (
            <Tooltip title="Export CASA script">
              <IconButton onClick={handleExportScript} color="primary">
                <Download />
              </IconButton>
            </Tooltip>
          )}
          <Button onClick={handleSaveTemplate} startIcon={<Save />} variant="outlined">
            Save Template
          </Button>
          <Button onClick={handleRunTemplate} variant="contained" startIcon={<PlayArrow />}>
            Run Workflow
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
