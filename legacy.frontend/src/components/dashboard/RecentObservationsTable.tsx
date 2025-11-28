import React from "react";
import { Box, Typography, alpha } from "@mui/material";
import CollapsibleSection from "../CollapsibleSection";
import type { PipelineStatus } from "../../api/types";

interface RecentObservationsTableProps {
  status?: PipelineStatus;
}

export const RecentObservationsTable: React.FC<RecentObservationsTableProps> = ({ status }) => {
  return (
    <CollapsibleSection title="Recent Observations" defaultExpanded={true} variant="outlined">
      <Box sx={{ mt: 2 }}>
        {status?.recent_groups &&
        Array.isArray(status.recent_groups) &&
        status.recent_groups.length > 0 ? (
          <Box sx={{ overflowX: "auto" }}>
            <Box
              component="table"
              sx={{
                width: "100%",
                borderCollapse: "collapse",
                "& thead tr": {
                  borderBottom: "1px solid",
                  borderColor: "divider",
                },
                "& th": {
                  textAlign: "left",
                  padding: "8px",
                  fontWeight: 600,
                  color: "text.secondary",
                },
                "& tbody tr": {
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
                  "&:hover": {
                    backgroundColor: "action.hover",
                    transform: "translateX(2px)",
                    boxShadow: (theme) => `0 2px 4px ${alpha(theme.palette.common.black, 0.1)}`,
                  },
                  "&:nth-of-type(even)": {
                    backgroundColor: alpha("#fff", 0.02),
                  },
                },
                "& td": {
                  padding: "8px",
                },
              }}
            >
              <thead>
                <tr>
                  <th>Group ID</th>
                  <th>State</th>
                  <th style={{ textAlign: "right" }}>Subbands</th>
                  <th>Calibrator</th>
                </tr>
              </thead>
              <tbody>
                {status.recent_groups.slice(0, 10).map((group) => (
                  <tr key={group.group_id}>
                    <td>{group.group_id}</td>
                    <td>{group.state}</td>
                    <td style={{ textAlign: "right" }}>
                      {group.subbands_present}/{group.expected_subbands}
                    </td>
                    <td>{group.has_calibrator ? "✓" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </Box>
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No recent observations
          </Typography>
        )}
      </Box>
    </CollapsibleSection>
  );
};
