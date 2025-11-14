/**
 * Operations Page
 * Dead Letter Queue management and circuit breaker monitoring
 */
import { useState } from "react";
import {
  Container,
  Typography,
  Paper,
  Box,
  Grid,
  Tabs,
  Tab,
  Stack,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import { DeadLetterQueueTable, DeadLetterQueueStats } from "../components/DeadLetterQueue";
import { CircuitBreakerStatus } from "../components/CircuitBreaker/CircuitBreakerStatus";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export function OperationsPage() {
  const [tabValue, setTabValue] = useState(0);
  const [componentFilter, setComponentFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("pending");

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Operations Management
      </Typography>

      <Paper sx={{ mt: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Dead Letter Queue" />
          <Tab label="Circuit Breakers" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Stack spacing={3}>
            <DeadLetterQueueStats />

            <Box>
              <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel>Component</InputLabel>
                  <Select
                    value={componentFilter}
                    label="Component"
                    onChange={(e) => setComponentFilter(e.target.value)}
                  >
                    <MenuItem value="">All</MenuItem>
                    <MenuItem value="ese_detection">ESE Detection</MenuItem>
                    <MenuItem value="calibration">Calibration</MenuItem>
                    <MenuItem value="photometry">Photometry</MenuItem>
                    <MenuItem value="pipeline">Pipeline</MenuItem>
                  </Select>
                </FormControl>

                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={statusFilter}
                    label="Status"
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="retrying">Retrying</MenuItem>
                    <MenuItem value="resolved">Resolved</MenuItem>
                    <MenuItem value="failed">Failed</MenuItem>
                  </Select>
                </FormControl>
              </Stack>

              <DeadLetterQueueTable
                component={componentFilter || undefined}
                status={statusFilter}
                limit={100}
              />
            </Box>
          </Stack>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <CircuitBreakerStatus />
        </TabPanel>
      </Paper>
    </Container>
  );
}
