import { useMemo } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Stack,
  Chip,
  Button,
  Skeleton,
  Alert,
} from "@mui/material";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";
import { usePointingHistory } from "../api/queries";

const SIX_HOURS_MS = 6 * 60 * 60 * 1000;
const MJD_OFFSET = 40587; // Unix epoch to MJD offset
const MS_PER_DAY = 86400000;

function dateToMjd(date: Date) {
  return date.getTime() / MS_PER_DAY + MJD_OFFSET;
}

function mjdToDate(mjd: number) {
  const unixTs = (mjd - MJD_OFFSET) * MS_PER_DAY;
  return new Date(unixTs);
}

export function PointingSummaryCard() {
  const navigate = useNavigate();
  const now = new Date();
  const startMjd = dateToMjd(new Date(now.getTime() - SIX_HOURS_MS));
  const endMjd = dateToMjd(now);

  const { data, isLoading, error } = usePointingHistory(startMjd, endMjd);

  const currentPointing = useMemo(() => {
    if (!data?.items?.length) return null;
    const latest = data.items[data.items.length - 1];
    return {
      ra: latest.ra_deg,
      dec: latest.dec_deg,
      timestamp: latest.timestamp,
    };
  }, [data]);

  const lastUpdate = currentPointing ? mjdToDate(currentPointing.timestamp) : null;

  return (
    <Card>
      <CardHeader
        title="Current Pointing"
        subheader="Based on the last 6 hours of observations"
        action={
          <Button size="small" variant="outlined" onClick={() => navigate("/observing")}>
            Open Observing View
          </Button>
        }
      />
      <CardContent>
        {isLoading && <Skeleton variant="rectangular" height={96} />}
        {!isLoading && error && (
          <Alert severity="warning">Unable to load pointing data right now.</Alert>
        )}
        {!isLoading && !error && !currentPointing && (
          <Alert severity="info">No recent pointing samples in the last 6 hours.</Alert>
        )}
        {!isLoading && currentPointing && (
          <Stack spacing={1.5}>
            <Typography variant="body2" color="text.secondary">
              Last Update: {lastUpdate ? dayjs(lastUpdate).format("YYYY-MM-DD HH:mm:ss") : "N/A"}
            </Typography>
            <Stack direction="row" spacing={2} flexWrap="wrap">
              <Chip label={`RA: ${currentPointing.ra.toFixed(4)}°`} color="info" />
              <Chip label={`Dec: ${currentPointing.dec.toFixed(4)}°`} color="success" />
              <Chip label="History: 6h" color="default" />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Use the Observing view for full pointing history and calibrator diagnostics.
            </Typography>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
