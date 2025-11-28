/**
 * Related Products Panel
 * Displays products derived from the selected Measurement Set with thumbnails
 */
import {
  Alert,
  Typography,
  Grid,
  Card,
  CardMedia,
  CardContent,
  CardActionArea,
  Chip,
  Box,
  CircularProgress,
  Stack,
} from "@mui/material";
import { Image as ImageIcon, TableChart as CalTableIcon } from "@mui/icons-material";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import { useImages } from "../../api/queries";
import { useMemo } from "react";

interface RelatedProductsPanelProps {
  msPath: string;
}

export function RelatedProductsPanel({ msPath }: RelatedProductsPanelProps) {
  // Extract MS name for filtering
  const msName = useMemo(() => {
    if (!msPath) return null;
    return msPath.split("/").pop()?.replace(".ms", "");
  }, [msPath]);

  // Fetch images related to this MS
  const { data: imagesData, isLoading: imagesLoading } = useImages({
    limit: 50,
  });

  // Fetch calibration tables
  const { data: calTables, isLoading: calTablesLoading } = useQuery({
    queryKey: ["related-cal-tables", msPath],
    queryFn: async () => {
      if (!msPath) return [];
      try {
        const response = await apiClient.get(`/api/ms/${encodeURIComponent(msPath)}/cal_tables`);
        return response.data?.tables || [];
      } catch {
        return [];
      }
    },
    enabled: !!msPath,
    retry: false,
  });

  // Filter images that are related to this MS
  const relatedImages = useMemo(() => {
    if (!imagesData?.items || !msName) return [];
    return imagesData.items.filter(
      (img) =>
        img.fits_path?.includes(msName) ||
        img.source_ms?.includes(msName) ||
        img.fits_path?.includes(msPath)
    );
  }, [imagesData, msName, msPath]);

  const isLoading = imagesLoading || calTablesLoading;

  return (
    <>
      <Typography variant="h6" gutterBottom>
        Related Products
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Images, calibration tables, and logs derived from this MS
      </Typography>

      {!msPath ? (
        <Alert severity="info">Select an MS to view related products</Alert>
      ) : isLoading ? (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      ) : (
        <Stack spacing={3}>
          {/* Images */}
          {relatedImages.length > 0 && (
            <Box>
              <Typography
                variant="subtitle1"
                gutterBottom
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <ImageIcon /> Images ({relatedImages.length})
              </Typography>
              <Grid container spacing={2}>
                {relatedImages.slice(0, 8).map((img) => (
                  <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={img.image_id}>
                    <Card>
                      <CardActionArea>
                        {img.thumbnail_path ? (
                          <CardMedia
                            component="img"
                            height="140"
                            image={`/api/visualization/thumbnail?path=${encodeURIComponent(
                              img.thumbnail_path
                            )}`}
                            alt={img.fits_path?.split("/").pop() || "Image"}
                            sx={{ objectFit: "cover" }}
                          />
                        ) : (
                          <Box
                            sx={{
                              height: 140,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              bgcolor: "background.default",
                            }}
                          >
                            <ImageIcon sx={{ fontSize: 48, opacity: 0.3 }} />
                          </Box>
                        )}
                        <CardContent>
                          <Typography
                            variant="body2"
                            noWrap
                            title={img.fits_path?.split("/").pop()}
                            sx={{ fontWeight: 600, fontSize: "0.95rem" }}
                          >
                            {img.fits_path?.split("/").pop()}
                          </Typography>
                          <Stack direction="row" spacing={0.5} mt={1} flexWrap="wrap">
                            {img.image_type && (
                              <Chip label={img.image_type} size="small" color="primary" />
                            )}
                            {img.stokes && <Chip label={img.stokes} size="small" />}
                          </Stack>
                        </CardContent>
                      </CardActionArea>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          {/* Calibration Tables */}
          {calTables && calTables.length > 0 && (
            <Box>
              <Typography
                variant="subtitle1"
                gutterBottom
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <CalTableIcon /> Calibration Tables ({calTables.length})
              </Typography>
              <Grid container spacing={2}>
                {calTables.map((table: any, idx: number) => (
                  <Grid size={{ xs: 12, sm: 6, md: 4 }} key={idx}>
                    <Card>
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <CalTableIcon color="warning" />
                          <Typography variant="body2" fontWeight={600} noWrap>
                            {table.name || table.path?.split("/").pop()}
                          </Typography>
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {table.type || "Calibration Table"}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          {/* No products found */}
          {relatedImages.length === 0 && (!calTables || calTables.length === 0) && (
            <Alert severity="info">
              No related products found. Images and calibration tables will appear here once
              processing completes.
            </Alert>
          )}
        </Stack>
      )}
    </>
  );
}
