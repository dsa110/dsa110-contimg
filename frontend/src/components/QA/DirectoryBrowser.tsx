/**
 * DirectoryBrowser Component - Browse and navigate directory structures
 */
import { useState, useEffect, useRef } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Checkbox,
  FormControlLabel,
  CircularProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  IconButton,
  Breadcrumbs,
  Link,
} from "@mui/material";
import {
  Folder,
  InsertDriveFile,
  Image as ImageIcon,
  TableChart,
  NavigateNext,
  Refresh,
  Home,
  ViewList,
  ViewModule,
} from "@mui/icons-material";
import { useDirectoryListing, useDirectoryThumbnails } from "../../api/queries";
import type { DirectoryEntry } from "../../api/types";
import DOMPurify from "dompurify";

/**
 * Check if a path looks complete (not being actively typed).
 */
function isPathComplete(path: string | null): boolean {
  if (!path || path.trim().length === 0) return false;

  const trimmed = path.trim();
  // Paths ending with these characters suggest incomplete typing
  const incompleteEndings = ["-", "_", ".", " "];
  // Allow root and common base paths
  if (trimmed === "/" || trimmed === "/data" || trimmed.startsWith("/data/")) {
    // Check if it ends with an incomplete segment
    const lastSegment = trimmed.split("/").pop() || "";
    return !incompleteEndings.some((ending) => lastSegment.endsWith(ending));
  }

  // For other paths, check if the last segment looks incomplete
  const lastSegment = trimmed.split("/").pop() || "";
  return (
    lastSegment.length > 0 && !incompleteEndings.some((ending) => lastSegment.endsWith(ending))
  );
}

interface DirectoryBrowserProps {
  initialPath?: string;
  onSelectFile?: (path: string, type: string) => void;
  onSelectDirectory?: (path: string) => void;
}

export default function DirectoryBrowser({
  initialPath = "/data/dsa110-contimg/state/qa",
  onSelectFile,
  onSelectDirectory,
}: DirectoryBrowserProps) {
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [debouncedPath, setDebouncedPath] = useState(initialPath);
  const [recursive, setRecursive] = useState(false);
  const [includePattern, setIncludePattern] = useState("");
  const [excludePattern, setExcludePattern] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "thumbnails">("list");
  const [thumbnailCols] = useState<number | undefined>(undefined);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce path changes - only update debouncedPath after user stops typing for 500ms
  useEffect(() => {
    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedPath(currentPath);
    }, 500);

    // Cleanup on unmount or when currentPath changes
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [currentPath]);

  // Use debouncedPath for API calls to avoid fetching on every keystroke
  const { data, isLoading, error, refetch } = useDirectoryListing(
    debouncedPath,
    recursive,
    includePattern || undefined,
    excludePattern || undefined,
    false
  );

  // Thumbnail catalog query
  const { data: thumbnailHtml, isLoading: thumbnailsLoading } = useDirectoryThumbnails(
    viewMode === "thumbnails" ? debouncedPath : null,
    recursive,
    includePattern || undefined,
    excludePattern || undefined,
    thumbnailCols,
    0,
    8,
    true,
    undefined
  );

  const handlePathClick = (path: string, isDir: boolean) => {
    if (isDir) {
      // Immediately update both currentPath and debouncedPath when clicking
      setCurrentPath(path);
      setDebouncedPath(path);
      onSelectDirectory?.(path);
    } else {
      const entry = data?.entries?.find((e) => e.path === path);
      if (entry) {
        onSelectFile?.(path, entry.type);
      }
    }
  };

  const handleBreadcrumbClick = (path: string) => {
    // Immediately update both currentPath and debouncedPath when clicking breadcrumb
    setCurrentPath(path);
    setDebouncedPath(path);
  };

  const handleGoClick = () => {
    // Immediately update debouncedPath when user clicks "Go" button
    setDebouncedPath(currentPath);
  };

  const getIcon = (type: string) => {
    switch (type) {
      case "directory":
        return <Folder />;
      case "fits":
        return <ImageIcon />;
      case "casatable":
        return <TableChart />;
      default:
        return <InsertDriveFile />;
    }
  };

  const getTypeColor = (
    type: string
  ): "default" | "primary" | "secondary" | "success" | "warning" => {
    switch (type) {
      case "directory":
        return "primary";
      case "fits":
        return "success";
      case "casatable":
        return "warning";
      default:
        return "default";
    }
  };

  // Use debouncedPath for breadcrumbs to show the actual loaded path
  const pathParts = debouncedPath.split("/").filter(Boolean);
  const breadcrumbs = pathParts.map((_, index) => {
    const path = "/" + pathParts.slice(0, index + 1).join("/");
    return { name: pathParts[index], path };
  });

  return (
    <Paper
      sx={{
        p: 2,
        bgcolor: "background.paper",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="h6">Directory Browser</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant={viewMode === "list" ? "contained" : "outlined"}
            startIcon={<ViewList />}
            onClick={() => setViewMode("list")}
            size="small"
          >
            List
          </Button>
          <Button
            variant={viewMode === "thumbnails" ? "contained" : "outlined"}
            startIcon={<ViewModule />}
            onClick={() => setViewMode("thumbnails")}
            size="small"
          >
            Thumbnails
          </Button>
          <Button
            startIcon={<Refresh />}
            onClick={() => {
              refetch();
              if (viewMode === "thumbnails") {
                // Thumbnails will refetch automatically via query invalidation
              }
            }}
            disabled={isLoading || thumbnailsLoading}
            size="small"
          >
            Refresh
          </Button>
        </Box>
      </Box>

      <Box sx={{ mb: 2 }}>
        <Breadcrumbs separator={<NavigateNext fontSize="small" />} aria-label="breadcrumb">
          <Link
            component="button"
            variant="body1"
            onClick={() => handleBreadcrumbClick("/")}
            sx={{ cursor: "pointer" }}
          >
            <Home fontSize="small" sx={{ mr: 0.5, verticalAlign: "middle" }} />
            Root
          </Link>
          {breadcrumbs.map((crumb, index) => (
            <Link
              key={crumb.path}
              component="button"
              variant="body1"
              onClick={() => handleBreadcrumbClick(crumb.path)}
              sx={{ cursor: "pointer" }}
            >
              {crumb.name}
            </Link>
          ))}
        </Breadcrumbs>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <TextField
          label="Current Path"
          value={currentPath}
          onChange={(e) => setCurrentPath(e.target.value)}
          size="small"
          fullWidth
          sx={{ flex: 1, minWidth: 300 }}
        />
        <Button
          variant="contained"
          onClick={handleGoClick}
          disabled={isLoading || currentPath === debouncedPath}
        >
          Go
        </Button>
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <TextField
          label="Include Pattern"
          value={includePattern}
          onChange={(e) => setIncludePattern(e.target.value)}
          size="small"
          placeholder="*.fits"
          sx={{ flex: 1, minWidth: 200 }}
        />
        <TextField
          label="Exclude Pattern"
          value={excludePattern}
          onChange={(e) => setExcludePattern(e.target.value)}
          size="small"
          placeholder="*.tmp"
          sx={{ flex: 1, minWidth: 200 }}
        />
        <FormControlLabel
          control={
            <Checkbox checked={recursive} onChange={(e) => setRecursive(e.target.checked)} />
          }
          label="Recursive"
        />
      </Box>

      {data && (
        <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
          <Chip label={`${data.total_files} Files`} size="small" />
          <Chip label={`${data.total_dirs} Directories`} size="small" color="primary" />
          <Chip label={`${data.fits_count} FITS`} size="small" color="success" />
          <Chip label={`${data.casatable_count} CASA Tables`} size="small" color="warning" />
        </Box>
      )}

      {error && isPathComplete(debouncedPath) && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error loading directory: {error instanceof Error ? error.message : "Unknown error"}
        </Alert>
      )}

      {isLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {viewMode === "list" && data && !isLoading && (
        <List sx={{ flex: 1, overflow: "auto", bgcolor: "background.paper" }}>
          {!data.entries || data.entries.length === 0 ? (
            <Alert severity="info">No entries found</Alert>
          ) : (
            data.entries.map((entry: DirectoryEntry) => (
              <ListItem
                key={entry.path}
                disablePadding
                sx={{
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <ListItemButton
                  onClick={() => handlePathClick(entry.path ?? "", entry.is_dir)}
                  sx={{
                    bgcolor: "background.paper",
                    "&:hover": { bgcolor: "action.hover" },
                    flexDirection: "column",
                    alignItems: "flex-start",
                    py: 1.5,
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      width: "100%",
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40 }}>{getIcon(entry.type)}</ListItemIcon>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                          mb: 0.5,
                        }}
                      >
                        <Typography variant="body1" component="span" sx={{ fontWeight: 500 }}>
                          {entry.name}
                        </Typography>
                        <Chip label={entry.type} size="small" color={getTypeColor(entry.type)} />
                      </Box>
                      <Box sx={{ display: "flex", gap: 2 }}>
                        {!entry.is_dir && (
                          <Typography variant="caption" color="text.secondary" component="span">
                            {entry.size || "N/A"}
                          </Typography>
                        )}
                        {entry.modified_time && (
                          <Typography variant="caption" color="text.secondary" component="span">
                            {new Date(entry.modified_time).toLocaleString()}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                    {entry.is_dir && (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePathClick(entry.path ?? "", true);
                        }}
                        sx={{ ml: "auto" }}
                      >
                        <NavigateNext />
                      </IconButton>
                    )}
                  </Box>
                </ListItemButton>
              </ListItem>
            ))
          )}
        </List>
      )}

      {viewMode === "thumbnails" && (
        <Box sx={{ flex: 1, overflow: "auto", bgcolor: "background.paper", p: 2 }}>
          {thumbnailsLoading ? (
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                minHeight: 200,
              }}
            >
              <CircularProgress />
            </Box>
          ) : thumbnailHtml ? (
            // Security: HTML is sanitized with DOMPurify before rendering to prevent XSS attacks.
            // The HTML comes from our trusted backend API (/api/visualization/directory/thumbnails),
            // but we sanitize it as a defense-in-depth measure. DOMPurify removes any potentially
            // dangerous scripts, event handlers, and unsafe attributes while preserving safe HTML
            // elements needed for thumbnail display.
            <Box
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(thumbnailHtml, {
                  // Allow common HTML elements and attributes needed for thumbnails
                  ALLOWED_TAGS: [
                    "div",
                    "img",
                    "a",
                    "span",
                    "p",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                    "ul",
                    "ol",
                    "li",
                    "table",
                    "tr",
                    "td",
                    "th",
                    "tbody",
                    "thead",
                  ],
                  ALLOWED_ATTR: [
                    "class",
                    "id",
                    "style",
                    "src",
                    "alt",
                    "href",
                    "target",
                    "title",
                    "width",
                    "height",
                  ],
                  // Allow safe CSS in style attributes
                  ALLOW_DATA_ATTR: false,
                }),
              }}
              sx={{
                "& .qa-thumb-item": {
                  cursor: "pointer",
                },
                "& .qa-thumb-item:hover": {
                  transform: "scale(1.05)",
                  transition: "transform 0.2s",
                },
              }}
            />
          ) : (
            <Alert severity="info">No thumbnails available</Alert>
          )}
        </Box>
      )}
    </Paper>
  );
}
