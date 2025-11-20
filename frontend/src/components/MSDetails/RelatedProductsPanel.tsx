/**
 * Related Products Panel
 * Displays products derived from the selected Measurement Set
 */
import {
  Alert,
  Typography,
  Card,
  CardContent,
  CardMedia,
  CardActionArea,
  Chip,
  Stack,
  Box,
  CircularProgress,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { Image as ImageIcon, TableChart as TableIcon } from "@mui/icons-material";
import { useImages } from "../../api/queries";
import { apiClient } from "../../api/client";

interface RelatedProductsPanelProps {
  msPath: string;
}

export function RelatedProductsPanel({ msPath }: RelatedProductsPanelProps) {
  // Extract MS name from path
  const msName = msPath ? msPath.split("/").pop()?.replace(".ms", "") : "";

  // Fetch images related to this MS
  const { data: images, isLoading } = useImages({ ms_path: msPath });

  const derivedImages = images?.items.filter((img) => img.ms_path === msPath) || [];

  if (!msPath) {
    return <Alert severity="info">Select an MS to view related products</Alert>;
  }

  return (
    <>
      <Typography variant="h6" gutterBottom>
        Related Products
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Images and calibration tables derived from {msName}
      </Typography>

      {isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      ) : derivedImages.length > 0 ? (
        <Grid container spacing={2}>
          {/* Images */}
          {derivedImages.map((image) => (
            <Grid item xs={12} sm={6} md={4} key={image.id} {...({} as any)}>
              <Card>
                <CardActionArea
                  onClick={() => {
                    window.open(`/sky/${image.id}`, "_blank");
                  }}
                >
                  {image.path && (
                    <CardMedia
                      component="img"
                      height="140"
                      image={`${apiClient.defaults.baseURL}/api/images/${image.id}/thumbnail`}
                      alt={image.path.split("/").pop()}
                      sx={{ objectFit: "cover" }}
                      onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                        e.currentTarget.src =
                          "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect width='100' height='100' fill='%23333'/%3E%3Ctext x='50' y='50' text-anchor='middle' fill='%23666' font-size='12'%3ENo Preview%3C/text%3E%3C/svg%3E";
                      }}
                    />
                  )}
                  <CardContent>
                    <Stack spacing={1}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <ImageIcon fontSize="small" color="primary" />
                        <Typography variant="body2" noWrap title={image.path}>
                          {image.path.split("/").pop()}
                        </Typography>
                      </Box>
                      <Stack direction="row" spacing={1}>
                        <Chip label={image.type} size="small" color="primary" />
                        {image.pbcor && <Chip label="PBCor" size="small" />}
                        {image.calibrated && <Chip label="Cal" size="small" color="success" />}
                      </Stack>
                    </Stack>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}

          {/* Calibration Tables Placeholder */}
          <Grid item xs={12} sm={6} md={4} {...({} as any)}>
            <Card sx={{ opacity: 0.6 }}>
              <CardContent>
                <Stack spacing={1} alignItems="center" sx={{ py: 3 }}>
                  <TableIcon fontSize="large" color="action" />
                  <Typography variant="body2" color="text.secondary">
                    Calibration Tables
                  </Typography>
                  <Chip label="Coming Soon" size="small" variant="outlined" />
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      ) : (
        <Alert severity="info">
          No derived products found for this MS. Images will appear here after processing.
        </Alert>
      )}
    </>
  );
}
