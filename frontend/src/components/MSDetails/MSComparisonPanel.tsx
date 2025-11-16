/**
 * MS Comparison Panel
 * Allows side-by-side comparison of two Measurement Sets
 */
import { useState } from "react";
import {
  Grid,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
} from "@mui/material";
import { useMSList, useMSMetadata } from "../../api/queries";
import MSTable from "../MSTable";
import type { MSListEntry } from "../../api/types";

interface MSComparisonPanelProps {
  selectedMS: string;
  onMSSelect: (ms: MSListEntry) => void;
}

export function MSComparisonPanel({ selectedMS, onMSSelect }: MSComparisonPanelProps) {
  const [compareMS, setCompareMS] = useState<string>("");

  const { data: msList, refetch: refetchMS } = useMSList({
    scan: true,
    scan_dir: "/scratch/dsa110-contimg/ms",
  });
  const { data: msMetadata } = useMSMetadata(selectedMS);
  const { data: compareMetadata } = useMSMetadata(compareMS);

  return (
    <>
      <Typography variant="h6" gutterBottom>
        Compare Measurement Sets
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Select two MSs to compare their properties side-by-side
      </Typography>
      <Grid container spacing={2}>
        <Grid
          size={{
            xs: 12,
            md: 6,
          }}
        >
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              MS 1
            </Typography>
            <MSTable
              data={msList?.items || []}
              total={msList?.total}
              filtered={msList?.filtered}
              selected={selectedMS ? [selectedMS] : []}
              onSelectionChange={(paths) => {
                if (paths.length > 0) {
                  // This will be handled by parent
                }
              }}
              onMSClick={onMSSelect}
              onRefresh={refetchMS}
            />
          </Paper>
        </Grid>
        <Grid
          size={{
            xs: 12,
            md: 6,
          }}
        >
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              MS 2 (for comparison)
            </Typography>
            <MSTable
              data={msList?.items || []}
              total={msList?.total}
              filtered={msList?.filtered}
              selected={compareMS ? [compareMS] : []}
              onSelectionChange={(paths) => {
                if (paths.length > 0) {
                  setCompareMS(paths[0]);
                }
              }}
              onMSClick={(ms) => setCompareMS(ms.path)}
              onRefresh={refetchMS}
            />
          </Paper>
        </Grid>
        {selectedMS && compareMS && (
          <Grid size={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Comparison
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Property</TableCell>
                      <TableCell align="right">MS 1</TableCell>
                      <TableCell align="right">MS 2</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Calibrated</TableCell>
                      <TableCell align="right">{msMetadata?.calibrated ? "Yes" : "No"}</TableCell>
                      <TableCell align="right">
                        {compareMetadata?.calibrated ? "Yes" : "No"}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Antennas</TableCell>
                      <TableCell align="right">
                        {msMetadata?.antennas?.length || msMetadata?.num_antennas || "N/A"}
                      </TableCell>
                      <TableCell align="right">
                        {compareMetadata?.antennas?.length ||
                          compareMetadata?.num_antennas ||
                          "N/A"}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Fields</TableCell>
                      <TableCell align="right">
                        {msMetadata?.fields?.length || msMetadata?.num_fields || "N/A"}
                      </TableCell>
                      <TableCell align="right">
                        {compareMetadata?.fields?.length || compareMetadata?.num_fields || "N/A"}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Frequency Range (GHz)</TableCell>
                      <TableCell align="right">
                        {msMetadata?.freq_min_ghz && msMetadata?.freq_max_ghz
                          ? `${msMetadata.freq_min_ghz.toFixed(3)} - ${msMetadata.freq_max_ghz.toFixed(3)}`
                          : "N/A"}
                      </TableCell>
                      <TableCell align="right">
                        {compareMetadata?.freq_min_ghz && compareMetadata?.freq_max_ghz
                          ? `${compareMetadata.freq_min_ghz.toFixed(3)} - ${compareMetadata.freq_max_ghz.toFixed(3)}`
                          : "N/A"}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Size (GB)</TableCell>
                      <TableCell align="right">
                        {msMetadata?.size_gb ? msMetadata.size_gb.toFixed(2) : "N/A"}
                      </TableCell>
                      <TableCell align="right">
                        {compareMetadata?.size_gb ? compareMetadata.size_gb.toFixed(2) : "N/A"}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        )}
        {(!selectedMS || !compareMS) && (
          <Grid size={12}>
            <Alert severity="info">Select both MS files above to see a detailed comparison</Alert>
          </Grid>
        )}
      </Grid>
    </>
  );
}
