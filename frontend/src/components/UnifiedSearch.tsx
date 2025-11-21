/**
 * Unified Search Component
 * Search across all consolidated pages and their content using real API data
 */
import React, { useState, useMemo } from "react";
import {
  TextField,
  InputAdornment,
  Paper,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
  Chip,
  Divider,
  CircularProgress,
} from "@mui/material";
import {
  Search,
  Storage,
  AccountTree,
  Settings,
  Assessment,
  TableChart,
  Image,
  Public,
  EventNote,
  Build,
  WorkOutline,
  Science,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useJobs, useImages } from "../api/queries";
import { apiClient } from "../api/client";

interface SearchResult {
  id: string;
  title: string;
  description: string;
  category: "page" | "job" | "source" | "image" | "mosaic" | "event" | "execution";
  path: string;
  icon: React.ComponentType;
  keywords: string[];
  metadata?: any;
}

// Generate search results from API data and static pages
const generateSearchResults = (
  query: string,
  jobs: any[] = [],
  images: any[] = [],
  sources: any[] = [],
  mosaics: any[] = []
): SearchResult[] => {
  const lowerQuery = query.toLowerCase();
  const results: SearchResult[] = [];

  // Page results
  const pages: Omit<SearchResult, "keywords">[] = [
    {
      id: "data-explorer",
      title: "Data Explorer",
      description: "Browse data products, mosaics, sources, and sky view",
      category: "page",
      path: "/data-explorer",
      icon: Storage,
    },
    {
      id: "pipeline-operations",
      title: "Pipeline Operations",
      description: "Monitor pipeline executions, DLQ, and events",
      category: "page",
      path: "/pipeline-operations",
      icon: AccountTree,
    },
    {
      id: "pipeline-control",
      title: "Pipeline Control",
      description: "Control panel, streaming service, and observing",
      category: "page",
      path: "/pipeline-control",
      icon: Settings,
    },
    {
      id: "system-diagnostics",
      title: "System Diagnostics",
      description: "System health, QA tools, and cache statistics",
      category: "page",
      path: "/system-diagnostics",
      icon: Assessment,
    },
  ];

  // Add pages that match query
  pages.forEach((page) => {
    if (
      page.title.toLowerCase().includes(lowerQuery) ||
      page.description.toLowerCase().includes(lowerQuery) ||
      page.path.toLowerCase().includes(lowerQuery)
    ) {
      results.push({
        ...page,
        keywords: [page.title, page.description, page.path],
      });
    }
  });

  // Add category-specific results based on query
  if (
    lowerQuery.includes("source") ||
    lowerQuery.includes("ese") ||
    lowerQuery.includes("catalog")
  ) {
    results.push({
      id: "sources-tab",
      title: "Sources Tab",
      description: "View source catalog and ESE candidates",
      category: "source",
      path: "/data-explorer?tab=2",
      icon: TableChart,
      keywords: ["source", "catalog", "ese", "variability"],
    });
  }

  if (lowerQuery.includes("mosaic") || lowerQuery.includes("image")) {
    results.push({
      id: "mosaics-tab",
      title: "Mosaics Tab",
      description: "Browse and view mosaics",
      category: "mosaic",
      path: "/data-explorer?tab=1",
      icon: Image,
      keywords: ["mosaic", "image", "gallery"],
    });
  }

  if (lowerQuery.includes("event") || lowerQuery.includes("dlq")) {
    results.push({
      id: "events-tab",
      title: "Events Tab",
      description: "View event stream and statistics",
      category: "event",
      path: "/pipeline-operations?tab=2",
      icon: EventNote,
      keywords: ["event", "stream", "notification"],
    });
  }

  if (lowerQuery.includes("dlq") || lowerQuery.includes("dead letter")) {
    results.push({
      id: "operations-tab",
      title: "Operations Tab",
      description: "View dead letter queue and circuit breakers",
      category: "event",
      path: "/pipeline-operations?tab=1",
      icon: Build,
      keywords: ["dlq", "dead letter", "circuit breaker", "operations"],
    });
  }

  if (lowerQuery.includes("sky") || lowerQuery.includes("coverage")) {
    results.push({
      id: "sky-tab",
      title: "Sky View Tab",
      description: "Interactive sky map and image viewer",
      category: "page",
      path: "/data-explorer?tab=3",
      icon: Public,
      keywords: ["sky", "coverage", "pointing", "map"],
    });
  }

  // Search jobs (by job ID, type, MS path, status)
  jobs.forEach((job: any) => {
    const jobIdMatch = String(job.job_id || "").includes(lowerQuery);
    const jobTypeMatch = (job.job_type || "").toLowerCase().includes(lowerQuery);
    const msPathMatch = (job.ms_path || "").toLowerCase().includes(lowerQuery);
    const statusMatch = (job.status || "").toLowerCase().includes(lowerQuery);

    if (jobIdMatch || jobTypeMatch || msPathMatch || statusMatch) {
      results.push({
        id: `job-${job.job_id}`,
        title: `Job #${job.job_id} - ${job.job_type || "Unknown"}`,
        description: `${job.status || "Unknown status"} | ${job.ms_path?.split("/").pop() || "N/A"}`,
        category: "job",
        path: `/control?job=${job.job_id}`,
        icon: WorkOutline,
        keywords: [String(job.job_id), job.job_type, job.ms_path, job.status].filter(Boolean),
        metadata: job,
      });
    }
  });

  // Search images (by filename, type, MS source)
  images.forEach((img: any) => {
    const filename = img.fits_path?.split("/").pop() || "";
    const filenameMatch = filename.toLowerCase().includes(lowerQuery);
    const typeMatch = (img.image_type || "").toLowerCase().includes(lowerQuery);
    const msMatch = (img.source_ms || "").toLowerCase().includes(lowerQuery);
    const stokesMatch = (img.stokes || "").toLowerCase().includes(lowerQuery);

    if (filenameMatch || typeMatch || msMatch || stokesMatch) {
      results.push({
        id: `image-${img.image_id}`,
        title: filename,
        description: `${img.image_type || "Image"} | ${img.stokes || "N/A"} | ${
          img.freq_ghz ? `${img.freq_ghz.toFixed(2)} GHz` : ""
        }`,
        category: "image",
        path: `/data-explorer?tab=1&image=${img.image_id}`,
        icon: Image,
        keywords: [filename, img.image_type, img.stokes, img.source_ms].filter(Boolean),
        metadata: img,
      });
    }
  });

  // Search sources (by source name, coordinates, or ESE candidate)
  sources.forEach((src: any) => {
    const nameMatch = (src.source_name || "").toLowerCase().includes(lowerQuery);
    const idMatch = String(src.source_id || "").includes(lowerQuery);
    const catalogMatch = (src.catalog_name || "").toLowerCase().includes(lowerQuery);

    if (nameMatch || idMatch || catalogMatch) {
      results.push({
        id: `source-${src.source_id}`,
        title: src.source_name || `Source ${src.source_id}`,
        description: `RA: ${src.ra_deg?.toFixed(4)}° Dec: ${src.dec_deg?.toFixed(4)}° | ${
          src.catalog_name || "Unknown catalog"
        }`,
        category: "source",
        path: `/data-explorer?tab=2&source=${src.source_id}`,
        icon: Science,
        keywords: [src.source_name, String(src.source_id), src.catalog_name].filter(Boolean),
        metadata: src,
      });
    }
  });

  // Search mosaics (by mosaic ID, name, frequency)
  mosaics.forEach((mosaic: any) => {
    const idMatch = String(mosaic.mosaic_id || "").includes(lowerQuery);
    const nameMatch = (mosaic.mosaic_name || "").toLowerCase().includes(lowerQuery);
    const freqMatch = String(mosaic.freq_ghz || "").includes(lowerQuery);

    if (idMatch || nameMatch || freqMatch) {
      results.push({
        id: `mosaic-${mosaic.mosaic_id}`,
        title: mosaic.mosaic_name || `Mosaic ${mosaic.mosaic_id}`,
        description: `${mosaic.num_images || 0} images | ${
          mosaic.freq_ghz ? `${mosaic.freq_ghz.toFixed(2)} GHz` : "N/A"
        }`,
        category: "mosaic",
        path: `/data-explorer?tab=1&mosaic=${mosaic.mosaic_id}`,
        icon: TableChart,
        keywords: [String(mosaic.mosaic_id), mosaic.mosaic_name].filter(Boolean),
        metadata: mosaic,
      });
    }
  });

  return results;
};

interface UnifiedSearchProps {
  onResultSelect?: (result: SearchResult) => void;
  placeholder?: string;
}

export default function UnifiedSearch({
  onResultSelect,
  placeholder = "Search pages, jobs, images, sources...",
}: UnifiedSearchProps) {
  const [query, setQuery] = useState("");
  const [showResults, setShowResults] = useState(false);
  const navigate = useNavigate();

  // Fetch data for search - only when user is actively searching
  const shouldFetch = query.trim().length >= 2;

  const { data: jobsData } = useJobs(50);
  const { data: imagesData } = useImages({ limit: 100 });

  // Fetch sources
  const { data: sourcesData } = useQuery({
    queryKey: ["sources-search", query],
    queryFn: async () => {
      try {
        const response = await apiClient.get("/api/sources", {
          params: { limit: 50, search: query },
        });
        return response.data;
      } catch {
        return { items: [] };
      }
    },
    enabled: shouldFetch,
  });

  // Fetch mosaics
  const { data: mosaicsData } = useQuery({
    queryKey: ["mosaics-search", query],
    queryFn: async () => {
      try {
        const response = await apiClient.get("/api/mosaics", {
          params: { limit: 50 },
        });
        return response.data;
      } catch {
        return { items: [] };
      }
    },
    enabled: shouldFetch,
  });

  const results = useMemo(() => {
    if (query.trim().length < 2) return [];

    const jobs = jobsData?.items || [];
    const images = imagesData?.items || [];
    const sources = sourcesData?.items || [];
    const mosaics = mosaicsData?.items || [];

    return generateSearchResults(query, jobs, images, sources, mosaics);
  }, [query, jobsData, imagesData, sourcesData, mosaicsData]);

  const handleResultClick = (result: SearchResult) => {
    navigate(result.path);
    setShowResults(false);
    setQuery("");
    if (onResultSelect) {
      onResultSelect(result);
    }
  };

  const getCategoryColor = (
    category: SearchResult["category"]
  ): "default" | "primary" | "secondary" | "success" | "warning" | "info" => {
    switch (category) {
      case "page":
        return "primary";
      case "job":
        return "info";
      case "image":
      case "mosaic":
        return "secondary";
      case "source":
        return "success";
      default:
        return "default";
    }
  };

  const isLoading = shouldFetch && (!jobsData || !imagesData || !sourcesData || !mosaicsData);

  return (
    <Box sx={{ position: "relative", width: "100%", maxWidth: 600 }}>
      <TextField
        fullWidth
        placeholder={placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setShowResults(e.target.value.trim().length >= 2);
        }}
        onFocus={() => {
          if (results.length > 0) setShowResults(true);
        }}
        onBlur={() => {
          // Delay hiding to allow clicks
          setTimeout(() => setShowResults(false), 200);
        }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search />
            </InputAdornment>
          ),
        }}
        sx={{ bgcolor: "background.paper" }}
      />

      {showResults && isLoading && (
        <Paper
          sx={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            mt: 1,
            p: 2,
            zIndex: 1000,
            boxShadow: 3,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <CircularProgress size={24} />
          <Typography variant="body2" sx={{ ml: 2 }}>
            Searching...
          </Typography>
        </Paper>
      )}

      {showResults && !isLoading && results.length > 0 && (
        <Paper
          sx={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            mt: 1,
            maxHeight: 400,
            overflow: "auto",
            zIndex: 1000,
            boxShadow: 3,
          }}
        >
          <List dense>
            {results.map((result, index) => (
              <React.Fragment key={result.id}>
                <ListItem disablePadding>
                  <ListItemButton onClick={() => handleResultClick(result)}>
                    <ListItemIcon>
                      <result.icon />
                    </ListItemIcon>
                    <ListItemText
                      primary={result.title}
                      secondary={result.description}
                      primaryTypographyProps={{
                        noWrap: true,
                        sx: { fontWeight: 500 },
                      }}
                      secondaryTypographyProps={{
                        noWrap: true,
                      }}
                    />
                    <Chip
                      label={result.category}
                      size="small"
                      color={getCategoryColor(result.category)}
                      sx={{ ml: 1 }}
                    />
                  </ListItemButton>
                </ListItem>
                {index < results.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
          {results.length > 10 && (
            <Box sx={{ p: 1, textAlign: "center", bgcolor: "background.default" }}>
              <Typography variant="caption" color="text.secondary">
                Showing first {Math.min(results.length, 20)} results
              </Typography>
            </Box>
          )}
        </Paper>
      )}

      {showResults && !isLoading && query.trim().length >= 2 && results.length === 0 && (
        <Paper
          sx={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            mt: 1,
            p: 2,
            zIndex: 1000,
            boxShadow: 3,
          }}
        >
          <Typography variant="body2" color="text.secondary" align="center">
            No results found for "{query}"
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            align="center"
            display="block"
            sx={{ mt: 1 }}
          >
            Try searching for job IDs, image names, source names (e.g., "3C286"), or page names
          </Typography>
        </Paper>
      )}
    </Box>
  );
}
