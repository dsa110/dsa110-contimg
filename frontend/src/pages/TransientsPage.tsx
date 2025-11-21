import { useState } from "react";
import { Box, Tabs, Tab, Typography } from "@mui/material";
import { TransientAlertsTable } from "../components/Transients/TransientAlertsTable";
import { TransientCandidatesTable } from "../components/Transients/TransientCandidatesTable";

export default function TransientsPage() {
  const [tabValue, setTabValue] = useState(0);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Transient Detection
      </Typography>

      <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)} sx={{ mb: 3 }}>
        <Tab label="Alerts" />
        <Tab label="Candidates" />
      </Tabs>

      <Box role="tabpanel" hidden={tabValue !== 0}>
        {tabValue === 0 && <TransientAlertsTable />}
      </Box>

      <Box role="tabpanel" hidden={tabValue !== 1}>
        {tabValue === 1 && <TransientCandidatesTable />}
      </Box>
    </Box>
  );
}
