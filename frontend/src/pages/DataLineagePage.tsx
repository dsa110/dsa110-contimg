/**
 * Data Lineage Page
 * Visualizes data flow: UVH5 → MS → Calibrated MS → Image → Mosaic
 * Shows calibration chain and processing parameters
 */
import { useState } from "react";
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
} from "@mui/material";
import {
  ArrowForward,
  ArrowDownward,
  Settings,
  Timeline,
  Visibility,
} from "@mui/icons-material";
import { useNavigate, useParams } from "react-router-dom";
import { useDataLineage, useDataInstance } from "../api/queries";
import DataLineageGraph from "../components/DataLineageGraph";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

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

const DATA_TYPE_LABELS: Record<string, string> = {
  uvh5: "UVH5",
  ms: "Measurement Set",
  calib_ms: "Calibrated MS",
  caltable: "Calibration Table",
  image: "Image",
  mosaic: "Mosaic",
  catalog: "Catalog",
  qa: "QA Report",
};

const DATA_TYPE_COLORS: Record<string, "primary" | "success" | "warning" | "error" | "info"> = {
  uvh5: "info",
  ms: "primary",
  calib_ms: "success",
  caltable: "warning",
  image: "primary",
  mosaic: "success",
  catalog: "info",
  qa: "default",
};

export default function DataLineagePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);

  const {
    data: lineage,
    isLoading: lineageLoading,
    error: lineageError,
  } = useDataLineage(id || "");
  const { data: currentInstance, isLoading: instanceLoading } = useDataInstance(id || "");

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleNavigateToData = (dataId: string, dataType: string) => {
    navigate(`/data/${dataType}/${dataId}`);
  };

  if (lineageLoading || instanceLoading) {
    return (
      <>
        <PageBreadcrumbs />
        <Container maxWidth="xl" sx={{ py: 4 }}>
          <Box sx={{ display: "flex", justifyContent: "center", p: 8 }}>
            <CircularProgress />
          </Box>
        </Container>
      </>
    );
  }

  if (lineageError || !lineage || !currentInstance) {
    return (
      <>
        <PageBreadcrumbs />
        <Container maxWidth="xl" sx={{ py: 4 }}>
          <Alert severity="error">
            Failed to load data lineage. {lineageError ? String(lineageError) : "Data not found."}
          </Alert>
        </Container>
      </>
    );
  }

  // Build processing chain visualization
  const processingChain = [
    ...Object.entries(lineage.parents).flatMap(([relType, parentIds]) =>
      parentIds.map((parentId) => ({
        id: parentId,
        relation: relType,
        direction: "parent" as const,
      }))
    ),
    { id: id || "", relation: "current", direction: "current" as const },
    ...Object.entries(lineage.children).flatMap(([relType, childIds]) =>
      childIds.map((childId) => ({ id: childId, relation: relType, direction: "child" as const }))
    ),
  ];

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
            Data Lineage & Provenance
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Trace data flow through the pipeline: UVH5 → MS → Calibrated MS → Image → Mosaic
          </Typography>
        </Box>

        {/* Current Data Instance Card */}
        <Card sx={{ mb: 3 }}>
          <CardHeader
            avatar={<Timeline color="primary" />}
            title="Current Data Instance"
            action={
              <Chip
                label={DATA_TYPE_LABELS[currentInstance.data_type] || currentInstance.data_type}
                color={
                  (DATA_TYPE_COLORS[currentInstance.data_type] || "info") as
                    | "primary"
                    | "success"
                    | "info"
                    | "warning"
                    | "error"
                }
                size="small"
              />
            }
          />
          <CardContent>
            <Grid container spacing={2}>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Data ID
                </Typography>
                <Typography variant="body1" sx={{ fontFamily: "monospace", mb: 2 }}>
                  {id}
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Visibility />}
                  onClick={() => handleNavigateToData(id ?? "" || "", currentInstance.data_type)}
                >
                  View Details
                </Button>
              </Grid>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Status
                </Typography>
                <Chip
                  label={currentInstance.status || "unknown"}
                  color={
                    currentInstance.status === "published"
                      ? "success"
                      : currentInstance.status === "staging"
                        ? "warning"
                        : "default"
                  }
                  size="small"
                  sx={{ mb: 2 }}
                />
                {currentInstance.created_at && (
                  <>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Created
                    </Typography>
                    <Typography variant="body2">
                      {new Date(currentInstance.created_at).toLocaleString()}
                    </Typography>
                  </>
                )}
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        {/* Tabs: Graph View | Processing Chain | Parameters */}
        <Paper>
          <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="Graph View" icon={<Timeline />} iconPosition="start" />
              <Tab label="Processing Chain" icon={<ArrowForward />} iconPosition="start" />
              <Tab label="Parameters" icon={<Settings />} iconPosition="start" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Box sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Data Lineage Graph
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Interactive visualization of data relationships. Click nodes to navigate.
              </Typography>
              <DataLineageGraph dataId={id || ""} />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Box sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Processing Chain
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Sequential view of data transformation pipeline
              </Typography>

              <Stack spacing={2}>
                {processingChain.map((item, index) => {
                  const isCurrent = item.direction === "current";
                  const isParent = item.direction === "parent";
                  const isLast = index === processingChain.length - 1;

                  return (
                    <Box key={`${item.id}-${index}`}>
                      <Card
                        sx={{
                          bgcolor: isCurrent ? "primary.dark" : "background.paper",
                          border: isCurrent ? 2 : 1,
                          borderColor: isCurrent ? "primary.main" : "divider",
                        }}
                      >
                        <CardContent>
                          <Stack direction="row" spacing={2} alignItems="center">
                            <Box sx={{ flexGrow: 1 }}>
                              <Typography
                                variant="subtitle1"
                                sx={{ fontWeight: isCurrent ? 700 : 400 }}
                              >
                                {isCurrent ? "Current" : isParent ? "Source" : "Product"}
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{
                                  fontFamily: "monospace",
                                  color: isCurrent ? "primary.contrastText" : "text.secondary",
                                  mt: 0.5,
                                }}
                              >
                                {item.id.slice(0, 16)}...
                              </Typography>
                              {item.relation !== "current" && (
                                <Chip
                                  label={item.relation}
                                  size="small"
                                  sx={{ mt: 1 }}
                                  color={isParent ? "info" : "success"}
                                />
                              )}
                            </Box>
                            <Button
                              variant={isCurrent ? "contained" : "outlined"}
                              size="small"
                              startIcon={<Visibility />}
                              onClick={() => {
                                // Try to determine data type from relation or instance
                                const dataType = isCurrent
                                  ? currentInstance.data_type
                                  : item.relation.includes("calib")
                                    ? "calib_ms"
                                    : item.relation.includes("image")
                                      ? "image"
                                      : "ms";
                                handleNavigateToData(item.id ?? "", dataType);
                              }}
                            >
                              View
                            </Button>
                          </Stack>
                        </CardContent>
                      </Card>
                      {!isLast && (
                        <Box sx={{ display: "flex", justifyContent: "center", my: 1 }}>
                          <ArrowDownward color="action" />
                        </Box>
                      )}
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Box sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Processing Parameters
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Parameters used to generate this data product
              </Typography>

              {currentInstance.processing_params ? (
                <Card>
                  <CardContent>
                    <Box
                      component="pre"
                      sx={{
                        fontFamily: "monospace",
                        fontSize: "0.875rem",
                        bgcolor: "background.default",
                        p: 2,
                        borderRadius: 1,
                        overflow: "auto",
                        maxHeight: 400,
                      }}
                    >
                      {JSON.stringify(currentInstance.processing_params, null, 2)}
                    </Box>
                  </CardContent>
                </Card>
              ) : (
                <Alert severity="info">
                  No processing parameters recorded for this data instance.
                </Alert>
              )}

              {lineage.processing_history && lineage.processing_history.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle1" gutterBottom>
                    Processing History
                  </Typography>
                  <Stack spacing={2}>
                    {lineage.processing_history.map((entry: any, idx: number) => (
                      <Card key={idx} variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle2">
                            {entry.step || `Step ${idx + 1}`}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {entry.timestamp
                              ? new Date(entry.timestamp).toLocaleString()
                              : "Unknown time"}
                          </Typography>
                          {entry.parameters && (
                            <Box
                              component="pre"
                              sx={{
                                fontFamily: "monospace",
                                fontSize: "0.75rem",
                                mt: 1,
                                p: 1,
                                bgcolor: "background.default",
                                borderRadius: 1,
                                overflow: "auto",
                              }}
                            >
                              {JSON.stringify(entry.parameters, null, 2)}
                            </Box>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </Stack>
                </Box>
              )}
            </Box>
          </TabPanel>
        </Paper>
      </Container>
    </>
  );
}
