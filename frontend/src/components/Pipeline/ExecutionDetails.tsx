import React, { useState } from "react";
import {
  Box,
  Button,
  Collapse,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { PipelineExecutionResponse } from "../../api/types";
import { usePipelineExecution } from "../../api/queries";

interface ExecutionDetailsProps {
  execution: PipelineExecutionResponse;
}

export default function ExecutionDetails({ execution }: ExecutionDetailsProps) {
  const [expanded, setExpanded] = useState(false);
  const { data: detailedExecution } = usePipelineExecution(execution.id);

  const exec = detailedExecution || execution;

  return (
    <Box sx={{ mt: 2 }}>
      <Button
        size="small"
        onClick={() => setExpanded(!expanded)}
        endIcon={
          <ExpandMoreIcon sx={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)" }} />
        }
      >
        {expanded ? "Hide" : "Show"} Details
      </Button>

      <Collapse in={expanded}>
        <Box sx={{ mt: 2 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2">Execution Information</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <Typography variant="body2">
                  <strong>ID:</strong> {exec.id}
                </Typography>
                <Typography variant="body2">
                  <strong>Type:</strong> {exec.job_type}
                </Typography>
                <Typography variant="body2">
                  <strong>Status:</strong> {exec.status}
                </Typography>
                <Typography variant="body2">
                  <strong>Retry Count:</strong> {exec.retry_count}
                </Typography>
                {exec.error_message && (
                  <Typography variant="body2" color="error">
                    <strong>Error:</strong> {exec.error_message}
                  </Typography>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>

          {exec.stages && exec.stages.length > 0 && (
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="subtitle2">Stage Details</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {exec.stages.map((stage) => (
                    <Box
                      key={stage.name}
                      sx={{
                        p: 1,
                        bgcolor: "background.default",
                        borderRadius: 1,
                      }}
                    >
                      <Typography variant="body2">
                        <strong>{stage.name.replace(/_/g, " ")}</strong>
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Status: {stage.status} | Duration:{" "}
                        {stage.duration_seconds?.toFixed(1) || "N/A"}s | Attempt: {stage.attempt}
                      </Typography>
                      {stage.error_message && (
                        <Typography
                          variant="caption"
                          color="error"
                          display="block"
                          sx={{ mt: 0.5 }}
                        >
                          {stage.error_message}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}
