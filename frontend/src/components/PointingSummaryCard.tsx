// React import not needed with new JSX transform
import { Box, Typography, Card, CardContent, Chip } from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { AccessTime, LocationOn } from "@mui/icons-material";
import type { PointingHistoryEntry } from "../api/types";
import { formatDateTime } from "../utils/dateUtils";

interface PointingSummaryCardProps {
  currentPointing?: PointingHistoryEntry;
  lastUpdate?: string;
}

export default function PointingSummaryCard({
  currentPointing,
  lastUpdate,
}: PointingSummaryCardProps) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6" component="div">
            Current Pointing
          </Typography>
          <Chip
            label={lastUpdate ? `Updated: ${formatDateTime(lastUpdate)}` : "No Data"}
            size="small"
            color={lastUpdate ? "success" : "default"}
            variant="outlined"
          />
        </Box>

        {currentPointing ? (
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <LocationOn color="primary" />
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    RA (deg)
                  </Typography>
                  <Typography variant="h6">{currentPointing.ra_deg.toFixed(4)}°</Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <LocationOn color="primary" />
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Dec (deg)
                  </Typography>
                  <Typography variant="h6">{currentPointing.dec_deg.toFixed(4)}°</Typography>
                </Box>
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <AccessTime color="action" />
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Observation Time
                  </Typography>
                  <Typography variant="body1">
                    {formatDateTime(currentPointing.timestamp * 1000)}
                  </Typography>
                </Box>
              </Box>
            </Grid>
          </Grid>
        ) : (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <Typography color="text.secondary">No pointing data available</Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
