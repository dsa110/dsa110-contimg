import { useState } from "react";
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Typography,
  IconButton,
  Tooltip,
} from "@mui/material";
import LabelIcon from "@mui/icons-material/Label";
import NoteAddIcon from "@mui/icons-material/NoteAdd";
import AssignmentIcon from "@mui/icons-material/Assignment";
import { useTransientCandidates, useClassifyCandidate } from "../../api/queries";
import { ClassifyDialog } from "./ClassifyDialog";
import type { TransientCandidate } from "../../api/types";

export function TransientCandidatesTable() {
  const [classification, setClassification] = useState<string>("");
  const [followUpStatus, setFollowUpStatus] = useState<string>("");
  const [selectedCandidate, setSelectedCandidate] = useState<TransientCandidate | null>(null);
  const [classifyDialogOpen, setClassifyDialogOpen] = useState(false);

  const {
    data: candidates,
    isLoading,
    error,
    refetch,
  } = useTransientCandidates(classification || undefined, followUpStatus || undefined, 50);

  const classifyMutation = useClassifyCandidate();

  const handleClassify = (candidate: TransientCandidate) => {
    setSelectedCandidate(candidate);
    setClassifyDialogOpen(true);
  };

  const handleClassifyConfirm = async (
    classification: string,
    classifiedBy: string,
    notes?: string
  ) => {
    if (!selectedCandidate) return;

    try {
      await classifyMutation.mutateAsync({
        candidateId: String(selectedCandidate.id),
        data: { classification, classified_by: classifiedBy, notes },
      });
      setClassifyDialogOpen(false);
      setSelectedCandidate(null);
      refetch();
    } catch (error) {
      console.error("Failed to classify candidate:", error);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Failed to load candidates: {String(error)}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 2, display: "flex", gap: 2, alignItems: "center" }}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Classification</InputLabel>
          <Select
            value={classification}
            label="Classification"
            onChange={(e) => setClassification(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="real">Real</MenuItem>
            <MenuItem value="artifact">Artifact</MenuItem>
            <MenuItem value="variable">Variable</MenuItem>
            <MenuItem value="uncertain">Uncertain</MenuItem>
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Follow-up Status</InputLabel>
          <Select
            value={followUpStatus}
            label="Follow-up Status"
            onChange={(e) => setFollowUpStatus(e.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="required">Required</MenuItem>
            <MenuItem value="in_progress">In Progress</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="not_needed">Not Needed</MenuItem>
          </Select>
        </FormControl>

        <Typography sx={{ ml: "auto" }}>
          {candidates?.length || 0} candidate{candidates?.length !== 1 ? "s" : ""}
        </Typography>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>RA</TableCell>
              <TableCell>Dec</TableCell>
              <TableCell>Significance</TableCell>
              <TableCell>Classification</TableCell>
              <TableCell>Follow-up</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {candidates?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="textSecondary">No candidates found</Typography>
                </TableCell>
              </TableRow>
            ) : (
              candidates?.map((candidate) => (
                <TableRow key={candidate.id}>
                  <TableCell>{candidate.id}</TableCell>
                  <TableCell>{candidate.ra_deg?.toFixed(5) ?? "N/A"}</TableCell>
                  <TableCell>{candidate.dec_deg?.toFixed(5) ?? "N/A"}</TableCell>
                  <TableCell>{candidate.significance_sigma?.toFixed(2) ?? "N/A"}</TableCell>
                  <TableCell>
                    {candidate.classification ? (
                      <Chip
                        label={candidate.classification}
                        color={
                          candidate.classification === "real"
                            ? "success"
                            : candidate.classification === "artifact"
                              ? "error"
                              : candidate.classification === "variable"
                                ? "warning"
                                : "default"
                        }
                        size="small"
                      />
                    ) : (
                      <Chip label="Unclassified" size="small" color="default" />
                    )}
                  </TableCell>
                  <TableCell>
                    {candidate.follow_up_status ? (
                      <Chip
                        label={candidate.follow_up_status.replace("_", " ")}
                        size="small"
                        color={
                          candidate.follow_up_status === "completed"
                            ? "success"
                            : candidate.follow_up_status === "in_progress"
                              ? "primary"
                              : "default"
                        }
                      />
                    ) : (
                      <Chip label="None" size="small" color="default" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 1 }}>
                      <Tooltip title="Classify">
                        <IconButton
                          size="small"
                          onClick={() => handleClassify(candidate)}
                          color="primary"
                        >
                          <LabelIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Follow-up Status">
                        <IconButton size="small" color="default">
                          <AssignmentIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Add Notes">
                        <IconButton size="small" color="default">
                          <NoteAddIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <ClassifyDialog
        open={classifyDialogOpen}
        onClose={() => {
          setClassifyDialogOpen(false);
          setSelectedCandidate(null);
        }}
        onConfirm={handleClassifyConfirm}
        candidateId={selectedCandidate?.id}
        currentClassification={selectedCandidate?.classification}
      />
    </Box>
  );
}
