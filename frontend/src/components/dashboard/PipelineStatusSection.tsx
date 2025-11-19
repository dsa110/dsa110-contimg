import React from "react";
import { Box, Typography } from "@mui/material";
import CollapsibleSection from "../CollapsibleSection";
import { QueueOverviewCard } from "../QueueOverviewCard";
import { DeadLetterQueueStats } from "../DeadLetterQueue";
import type { PipelineStatus } from "../../api/types";

type QueueStatusType = "total" | "pending" | "in_progress" | "completed" | "failed" | "collecting";

interface PipelineStatusSectionProps {
  status?: PipelineStatus;
  selectedQueueStatus: QueueStatusType;
  onSelectQueueStatus: (status: QueueStatusType) => void;
}

export const PipelineStatusSection: React.FC<PipelineStatusSectionProps> = ({
  status,
  selectedQueueStatus,
  onSelectQueueStatus,
}) => {
  return (
    <CollapsibleSection title="Pipeline Status" defaultExpanded={true} variant="outlined">
      <Box sx={{ mt: 2 }}>
        <QueueOverviewCard
          queue={status?.queue}
          selectedStatus={selectedQueueStatus}
          onSelectStatus={onSelectQueueStatus}
          helperText="Select a queue state to filter the details panel."
          variant="inline"
        />

        <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
          Calibration Sets
        </Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          Active: <strong>{status?.calibration_sets?.length || 0}</strong>
        </Typography>

        {/* Dead Letter Queue Statistics */}
        <Box sx={{ mt: 3 }}>
          <DeadLetterQueueStats />
        </Box>
      </Box>
    </CollapsibleSection>
  );
};
