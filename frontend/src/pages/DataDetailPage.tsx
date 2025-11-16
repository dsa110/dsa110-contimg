/**
 * Data Detail Page - Detailed view of a single data instance
 */
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Paper,
  Chip,
  Button,
  Card,
  CardContent,
  Alert,
  Tabs,
  Tab,
  IconButton,
} from "@mui/material";
import { SkeletonLoader } from "../components/SkeletonLoader";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import {
  ArrowBack,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Pending,
  Publish,
} from "@mui/icons-material";
import { useDataInstance, useAutoPublishStatus } from "../api/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import DataLineageGraph from "../components/DataLineageGraph";

const DATA_TYPE_LABELS: Record<string, string> = {
  ms: "Measurement Set",
  calib_ms: "Calibrated Measurement Set",
  caltable: "Calibration Table",
  image: "Image",
  mosaic: "Mosaic",
  catalog: "Catalog",
  qa: "QA Report",
  metadata: "Metadata",
};

function formatDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString();
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function DataDetailPage() {
  const { id } = useParams<{ type: string; id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [tabValue, setTabValue] = useState(0);

  const { data: instance, isLoading, error } = useDataInstance(id!);
  const { data: autoPublishStatus } = useAutoPublishStatus(id!);

  const publishMutation = useMutation({
    mutationFn: async () => {
      const encodedId = encodeURIComponent(id!);
      const response = await apiClient.post(`/api/data/${encodedId}/publish`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["data", "instance", id] });
      queryClient.invalidateQueries({ queryKey: ["data", "instances"] });
    },
  });

  const finalizeMutation = useMutation({
    mutationFn: async (params: { qa_status?: string; validation_status?: string }) => {
      const encodedId = encodeURIComponent(id!);
      const response = await apiClient.post(`/api/data/${encodedId}/finalize`, params);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["data", "instance", id] });
      queryClient.invalidateQueries({ queryKey: ["data", "instances"] });
      queryClient.invalidateQueries({ queryKey: ["data", "auto-publish", id] });
    },
  });

  const toggleAutoPublishMutation = useMutation({
    mutationFn: async (enable: boolean) => {
      const encodedId = encodeURIComponent(id!);
      const endpoint = enable ? "enable" : "disable";
      const response = await apiClient.post(`/api/data/${encodedId}/auto-publish/${endpoint}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["data", "instance", id] });
      queryClient.invalidateQueries({ queryKey: ["data", "auto-publish", id] });
    },
  });

  if (isLoading) {
    return (
      <Box sx={{ p: 4 }}>
        <SkeletonLoader variant="cards" rows={3} />
      </Box>
    );
  }

  if (error || !instance) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          Failed to load data instance: {error?.message || "Not found"}
        </Alert>
        <Button startIcon={<ArrowBack />} onClick={() => navigate("/data")} sx={{ mt: 2 }}>
          Back to Data Browser
        </Button>
      </Box>
    );
  }

  const canPublish = instance.status === "staging" && instance.finalization_status === "finalized";
  const canFinalize = instance.status === "staging" && instance.finalization_status === "pending";

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
          <IconButton onClick={() => navigate("/data")} sx={{ mr: 1 }}>
            <ArrowBack />
          </IconButton>
          <Typography variant="h1" component="h1" sx={{ flexGrow: 1 }}>
            {(instance.data_type && DATA_TYPE_LABELS[instance.data_type]) || instance.data_type || "Unknown"}
          </Typography>
          {canPublish && (
            <Button
              variant="contained"
              startIcon={<Publish />}
              onClick={() => publishMutation.mutate()}
              disabled={publishMutation.isPending}
              sx={{ mr: 1 }}
            >
              Publish
            </Button>
          )}
          {canFinalize && (
            <Button
              variant="outlined"
              onClick={() =>
                finalizeMutation.mutate({
                  qa_status: instance.qa_status,
                  validation_status: instance.validation_status,
                })
              }
              disabled={finalizeMutation.isPending}
            >
              Finalize
            </Button>
          )}
        </Box>

        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            gap: 3,
          }}
        >
          <Box sx={{ flex: { xs: "1 1 100%", md: "2 1 66%" } }}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Basic Information
              </Typography>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                  gap: 2,
                }}
              >
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Data ID
                  </Typography>
                  <Typography variant="body1" sx={{ fontFamily: "monospace" }}>
                    {instance.id}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Type
                  </Typography>
                  <Chip
                    label={(instance.data_type && DATA_TYPE_LABELS[instance.data_type]) || instance.data_type || "Unknown"}
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Status
                  </Typography>
                  <Chip
                    label={instance.status}
                    color={instance.status === "published" ? "success" : "warning"}
                    size="small"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Created
                  </Typography>
                  <Typography variant="body1">
                    {formatDate(parseInt(instance.created_at, 10))}
                  </Typography>
                </Box>
                {instance.published_at && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Published
                    </Typography>
                    <Typography variant="body1">
                      {formatDate(parseInt(instance.published_at, 10))}
                    </Typography>
                  </Box>
                )}
                {instance.publish_mode && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Publish Mode
                    </Typography>
                    <Chip label={instance.publish_mode} size="small" sx={{ mt: 0.5 }} />
                  </Box>
                )}
              </Box>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
                <Tab label="Metadata" />
                <Tab label="Lineage" />
              </Tabs>
              <TabPanel value={tabValue} index={0}>
                {instance.metadata ? (
                  <Box sx={{ mt: 2 }}>
                    <pre
                      style={{
                        background: "#1e1e1e",
                        padding: "1rem",
                        borderRadius: "4px",
                        overflow: "auto",
                      }}
                    >
                      {JSON.stringify(instance.metadata, null, 2)}
                    </pre>
                  </Box>
                ) : (
                  <Typography color="text.secondary">No metadata available</Typography>
                )}
              </TabPanel>
              <TabPanel value={tabValue} index={1}>
                <DataLineageGraph dataId={id!} />
              </TabPanel>
            </Paper>
          </Box>

          <Box sx={{ flex: { xs: "1 1 100%", md: "1 1 33%" } }}>
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quality Status
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    QA Status
                  </Typography>
                  {instance.qa_status ? (
                    <Chip
                      label={instance.qa_status}
                      color={
                        instance.qa_status === "passed"
                          ? "success"
                          : instance.qa_status === "failed"
                            ? "error"
                            : instance.qa_status === "warning"
                              ? "warning"
                              : "default"
                      }
                      icon={
                        instance.qa_status === "passed" ? (
                          <CheckCircle />
                        ) : instance.qa_status === "failed" ? (
                          <ErrorIcon />
                        ) : instance.qa_status === "warning" ? (
                          <Warning />
                        ) : (
                          <Pending />
                        )
                      }
                    />
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      N/A
                    </Typography>
                  )}
                </Box>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Validation Status
                  </Typography>
                  <Chip
                    label={instance.validation_status || "pending"}
                    color={
                      instance.validation_status === "validated"
                        ? "success"
                        : instance.validation_status === "invalid"
                          ? "error"
                          : "default"
                    }
                  />
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Finalization Status
                  </Typography>
                  <Chip
                    label={instance.finalization_status}
                    color={
                      instance.finalization_status === "finalized"
                        ? "success"
                        : instance.finalization_status === "failed"
                          ? "error"
                          : "default"
                    }
                  />
                </Box>
              </CardContent>
            </Card>

            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Auto-Publish
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Chip
                    label={instance.auto_publish_enabled ? "Enabled" : "Disabled"}
                    color={instance.auto_publish_enabled ? "success" : "default"}
                    sx={{ mb: 2 }}
                  />
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => toggleAutoPublishMutation.mutate(!instance.auto_publish_enabled)}
                    disabled={toggleAutoPublishMutation.isPending}
                    fullWidth
                  >
                    {instance.auto_publish_enabled ? "Disable" : "Enable"} Auto-Publish
                  </Button>
                </Box>
                {autoPublishStatus && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Criteria Status
                    </Typography>
                    {autoPublishStatus.criteria_met ? (
                      <Alert severity="success" sx={{ mb: 1 }}>
                        All criteria met
                      </Alert>
                    ) : (
                      <Alert severity="warning" sx={{ mb: 1 }}>
                        Criteria not met
                        {autoPublishStatus.reasons && autoPublishStatus.reasons.length > 0 && (
                          <ul style={{ margin: "0.5rem 0 0 1.5rem", padding: 0 }}>
                            {autoPublishStatus.reasons.map((reason, idx) => (
                              <li key={idx}>{reason}</li>
                            ))}
                          </ul>
                        )}
                      </Alert>
                    )}
                  </Box>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  File Paths
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Staging Path
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ fontFamily: "monospace", wordBreak: "break-all" }}
                  >
                    {instance.stage_path}
                  </Typography>
                </Box>
                {instance.published_path && (
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Published Path
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ fontFamily: "monospace", wordBreak: "break-all" }}
                    >
                      {instance.published_path}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Box>
        </Box>
      </Box>
    </>
  );
}
