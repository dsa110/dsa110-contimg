import React from "react";
import {
  Alert,
  Grid,
  Card,
  CardHeader,
  CardContent,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  Typography,
} from "@mui/material";
import { Assessment as AssessmentIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useESECandidates } from "../../api/queries";
import { formatDateTime } from "../../utils/dateUtils";

export const QADiagnosticsTab: React.FC = () => {
  const navigate = useNavigate();
  const { data: eseCandidates } = useESECandidates();

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Alert severity="info">
          QA diagnostics and gallery features are available on the{" "}
          <strong
            onClick={() => navigate("/qa")}
            style={{ cursor: "pointer", textDecoration: "underline" }}
          >
            QA Visualization page
          </strong>
          .
        </Alert>
      </Grid>

      <Grid size={12}>
        <Card>
          <CardHeader title="ESE Candidates" avatar={<AssessmentIcon />} />
          <CardContent>
            {eseCandidates?.candidates && eseCandidates.candidates.length > 0 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Source ID</TableCell>
                      <TableCell>Max σ</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Last Detection</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {eseCandidates.candidates.slice(0, 10).map((candidate) => (
                      <TableRow key={candidate.source_id}>
                        <TableCell>{candidate.source_id}</TableCell>
                        <TableCell>{(candidate.max_sigma_dev ?? 0).toFixed(2)}</TableCell>
                        <TableCell>
                          <Chip
                            label={candidate.status}
                            size="small"
                            color={
                              candidate.status === "active"
                                ? "error"
                                : candidate.status === "resolved"
                                  ? "success"
                                  : "default"
                            }
                          />
                        </TableCell>
                        <TableCell>{formatDateTime(candidate.last_detection_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No ESE candidates detected
              </Typography>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};
