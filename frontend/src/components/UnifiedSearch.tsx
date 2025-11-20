/**
 * Unified Search Component
 * Search across all consolidated pages and their content
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
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useJobs, useImages } from "../api/queries";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

interface SearchResult {
  id: string;
  title: string;
  description: string;
  category: "page" | "data" | "source" | "image" | "mosaic" | "event" | "execution";
  path: string;
  icon: React.ComponentType;
  keywords: string[];
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
      id: "absurd",
      title: "Absurd",
      description: "Pipeline automation, task queues, and workflow builder",
      category: "page",
      path: "/absurd",
      icon: AccountTree,
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

  // Add API data results
  jobs.forEach((job) => {
    if (
      job.id?.toLowerCase().includes(lowerQuery) ||
      job.type?.toLowerCase().includes(lowerQuery)
    ) {
      results.push({
        id: `job-${job.id}`,
        title: `Job: ${job.type}`,
        description: `Status: ${job.status} | ID: ${job.id.substring(0, 8)}`,
        category: "execution",
        path: `/pipeline-operations?tab=0&job=${job.id}`,
        icon: AccountTree,
        keywords: [job.id, job.type, job.status],
      });
    }
  });

  images.forEach((img) => {
    const filename = img.path?.split("/").pop() || "";
    if (
      filename.toLowerCase().includes(lowerQuery) ||
      img.ms_path?.toLowerCase().includes(lowerQuery)
    ) {
      results.push({
        id: `image-${img.id}`,
        title: filename,
        description: `${img.type} | MS: ${img.ms_path?.split("/").pop() || "N/A"}`,
        category: "image",
        path: `/sky/${img.id}`,
        icon: Image,
        keywords: [filename, img.ms_path || "", img.type],
      });
    }
  });

  sources.forEach((src: any) => {
    if (src.name?.toLowerCase().includes(lowerQuery)) {
      results.push({
        id: `source-${src.id}`,
        title: src.name,
        description: `RA: ${src.ra_deg?.toFixed(4)}° Dec: ${src.dec_deg?.toFixed(4)}°`,
        category: "source",
        path: `/data-explorer?tab=2&source=${src.id}`,
        icon: TableChart,
        keywords: [src.name, String(src.ra_deg), String(src.dec_deg)],
      });
    }
  });

  mosaics.forEach((mosaic: any) => {
    const filename = mosaic.path?.split("/").pop() || "";
    if (filename.toLowerCase().includes(lowerQuery)) {
      results.push({
        id: `mosaic-${mosaic.id}`,
        title: filename,
        description: `Mosaic | ${mosaic.num_images || 0} images`,
        category: "mosaic",
        path: `/data-explorer?tab=1&mosaic=${mosaic.id}`,
        icon: Public,
        keywords: [filename, "mosaic"],
      });
    }
  });

  return results.slice(0, 15); // Limit to 15 results
};

interface UnifiedSearchProps {
  onResultSelect?: (result: SearchResult) => void;
  placeholder?: string;
}

export default function UnifiedSearch({
  onResultSelect,
  placeholder = "Search pages, data, sources...",
}: UnifiedSearchProps) {
  const [query, setQuery] = useState("");
  const [showResults, setShowResults] = useState(false);
  const navigate = useNavigate();

  // Fetch data for search
  const { data: jobsData } = useJobs(50);
  const { data: imagesData } = useImages({ limit: 50 });
  const { data: sourcesData } = useQuery({
    queryKey: ["sources", "search"],
    queryFn: async () => {
      const response = await apiClient.get("/api/sources?limit=50");
      return response.data;
    },
    enabled: query.trim().length >= 2,
  });
  const { data: mosaicsData } = useQuery({
    queryKey: ["mosaics", "search"],
    queryFn: async () => {
      const response = await apiClient.get("/api/mosaics?limit=50");
      return response.data;
    },
    enabled: query.trim().length >= 2,
  });

  const results = useMemo(() => {
    if (query.trim().length < 2) return [];
    return generateSearchResults(
      query,
      jobsData?.items || [],
      imagesData?.items || [],
      sourcesData?.items || [],
      mosaicsData?.items || []
    );
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
  ): "default" | "primary" | "secondary" => {
    switch (category) {
      case "page":
        return "primary";
      case "data":
      case "image":
      case "mosaic":
        return "secondary";
      default:
        return "default";
    }
  };

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

      {showResults && results.length > 0 && (
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
                    <ListItemText primary={result.title} secondary={result.description} />
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
        </Paper>
      )}

      {showResults && query.trim().length >= 2 && results.length === 0 && (
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
        </Paper>
      )}
    </Box>
  );
}
