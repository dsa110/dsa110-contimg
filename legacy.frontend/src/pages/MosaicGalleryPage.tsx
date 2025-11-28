import React from "react";
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  CardActionArea,
  Stack,
  Alert,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import {
  Image as ImageIcon,
  Storage,
  Settings,
  Science,
  ViewModule,
  Visibility,
  Assessment,
  Build,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { usePipelineStatus } from "../api/queries";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { SkeletonLoader } from "../components/SkeletonLoader";

// Map features to relevant dashboard links
const features = [
  {
    title: "Recent Images",
    description: "Browse recent continuum images and mosaics",
    icon: ImageIcon,
    path: "/mosaics",
    color: "#2196f3",
  },
  {
    title: "Source Catalog",
    description: "Search and monitor detected radio sources",
    icon: Storage,
    path: "/sources",
    color: "#4caf50",
  },
  {
    title: "Pipeline Status",
    description: "Monitor pipeline queues and processing state",
    icon: Settings,
    path: "/pipeline",
    color: "#ff9800",
  },
  {
    title: "QA Tools",
    description: "Quality assurance and diagnostic plots",
    icon: Science,
    path: "/qa",
    color: "#f44336",
  },
  {
    title: "Sky View",
    description: "Interactive sky map of observations",
    icon: ViewModule,
    path: "/sky",
    color: "#9c27b0",
  },
  {
    title: "CARTA",
    description: "Remote CARTA visualization sessions",
    icon: Visibility,
    path: "/carta",
    color: "#00bcd4",
  },
  {
    title: "Health",
    description: "System health and performance metrics",
    icon: Assessment,
    path: "/health",
    color: "#607d8b",
  },
  {
    title: "Calibration",
    description: "Calibration tables and workflows",
    icon: Build,
    path: "/calibration",
    color: "#795548",
  },
];

export default function MosaicGalleryPage() {
  const navigate = useNavigate();
  const { data: status, isLoading } = usePipelineStatus();

  if (isLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={2} />
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <PageBreadcrumbs />
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Feature Gallery
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Overview of all available dashboard tools and visualizations
        </Typography>
      </Box>

      {status && !(status as any).running && (
        <Alert severity="warning" sx={{ mb: 4 }}>
          Pipeline service appears to be stopped. Some features may show stale data.
        </Alert>
      )}

      <Grid container spacing={3}>
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <Grid item xs={12} sm={6} md={4} lg={3} key={feature.path}>
              <Card
                sx={{
                  height: "100%",
                  transition: "transform 0.2s",
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: 4,
                  },
                }}
              >
                <CardActionArea
                  onClick={() => navigate(feature.path)}
                  sx={{ height: "100%", p: 2 }}
                >
                  <CardContent>
                    <Stack spacing={2} alignItems="center" textAlign="center">
                      <Box
                        sx={{
                          p: 2,
                          borderRadius: "50%",
                          bgcolor: `${feature.color}15`,
                          color: feature.color,
                        }}
                      >
                        <Icon fontSize="large" />
                      </Box>
                      <Typography variant="h6" component="h2">
                        {feature.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {feature.description}
                      </Typography>
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Container>
  );
}
