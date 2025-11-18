import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Stack,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Skeleton,
} from "@mui/material";
import type { ESECandidatesResponse, ESECandidate } from "../../api/types";

interface QASnapshotCardProps {
  data?: ESECandidatesResponse;
  isLoading?: boolean;
  onRefresh?: () => void;
  onOpenQA?: () => void;
}

const getSigmaValue = (candidate: ESECandidate) =>
  candidate.max_sigma_dev ?? candidate.variability_sigma ?? 0;

export function QASnapshotCard({ data, isLoading, onRefresh, onOpenQA }: QASnapshotCardProps) {
  const candidates = data?.candidates ?? [];
  const activeCount = candidates.filter((c) => c.status === "active").length;
  const resolvedCount = candidates.filter((c) => c.status === "resolved").length;
  const warningCount = candidates.filter((c) => c.status === "warning").length;
  const topCandidates = candidates.slice(0, 3);

  return (
    <Card>
      <CardHeader
        title="QA Snapshot"
        subheader="Latest ESE candidates and QA signals"
        action={
          <Stack direction="row" spacing={1}>
            <Button size="small" onClick={onRefresh} disabled={isLoading}>
              Refresh
            </Button>
            <Button size="small" variant="contained" onClick={onOpenQA}>
              Open QA Tools
            </Button>
          </Stack>
        }
      />
      <CardContent>
        {isLoading ? (
          <Skeleton variant="rectangular" height={140} />
        ) : candidates.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No QA anomalies detected. New candidates will appear here as variability is detected.
          </Typography>
        ) : (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip label={`Active: ${activeCount}`} color="error" variant="outlined" />
              <Chip label={`Resolved: ${resolvedCount}`} color="success" variant="outlined" />
              <Chip label={`Warnings: ${warningCount}`} color="warning" variant="outlined" />
              <Chip label={`Total: ${candidates.length}`} color="default" variant="outlined" />
            </Stack>

            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Source ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Max σ</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {topCandidates.map((candidate: ESECandidate) => (
                  <TableRow key={candidate.source_id}>
                    <TableCell>{candidate.source_id}</TableCell>
                    <TableCell>
                      <Chip
                        label={candidate.status || "pending"}
                        size="small"
                        color={
                          candidate.status === "active"
                            ? "error"
                            : candidate.status === "resolved"
                              ? "success"
                              : "warning"
                        }
                      />
                    </TableCell>
                    <TableCell>{getSigmaValue(candidate).toFixed(2)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
