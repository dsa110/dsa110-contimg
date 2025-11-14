/**
 * CasaTableViewer Component - View CASA Measurement Set tables
 */
import { useState, useEffect } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { ExpandMore, TableChart, Info, Refresh } from "@mui/icons-material";
import { useCasaTableInfo } from "../../api/queries";
import { apiClient } from "../../api/client";

interface CasaTableViewerProps {
  tablePath: string | null;
}

export default function CasaTableViewer({ tablePath }: CasaTableViewerProps) {
  const [viewerHtml, setViewerHtml] = useState<string | null>(null);
  const [loadingViewer, setLoadingViewer] = useState(false);
  const [viewerError, setViewerError] = useState<string | null>(null);
  const [maxRows, setMaxRows] = useState(10);
  const [maxCols, setMaxCols] = useState(10);

  const {
    data: tableInfo,
    isLoading: loadingInfo,
    error: infoError,
    refetch,
  } = useCasaTableInfo(tablePath);

  // Load table viewer HTML from API
  const loadViewer = () => {
    if (!tablePath) {
      setViewerHtml(null);
      return;
    }

    setLoadingViewer(true);
    setViewerError(null);

    apiClient
      .get(`/api/visualization/casatable/view`, {
        params: {
          path: tablePath,
          max_rows: maxRows,
          max_cols: maxCols,
        },
        responseType: "text",
      })
      .then((response) => {
        setViewerHtml(response.data);
        setLoadingViewer(false);
      })
      .catch((error) => {
        setViewerError(
          error.response?.data?.detail || error.message || "Failed to load table viewer"
        );
        setLoadingViewer(false);
      });
  };

  useEffect(() => {
    if (tablePath && tableInfo?.exists) {
      loadViewer();
    }
  }, [tablePath, maxRows, maxCols]);

  if (!tablePath) {
    return (
      <Paper sx={{ p: 3, bgcolor: "background.paper", height: "100%" }}>
        <Alert severity="info">Select a CASA table to view</Alert>
      </Paper>
    );
  }

  return (
    <Paper
      sx={{
        p: 2,
        bgcolor: "background.paper",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <TableChart />
        <Typography variant="h6">CASA Table Viewer</Typography>
        {tableInfo && (
          <Chip
            label={tableInfo.exists ? "Found" : "Not Found"}
            color={tableInfo.exists ? "success" : "error"}
            size="small"
          />
        )}
        <Button
          startIcon={<Refresh />}
          onClick={() => {
            refetch();
            loadViewer();
          }}
          disabled={loadingInfo || loadingViewer}
          size="small"
        >
          Refresh
        </Button>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontFamily: "monospace" }}>
        {tablePath}
      </Typography>

      <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
        <TextField
          label="Max Rows"
          type="number"
          value={maxRows}
          onChange={(e) => setMaxRows(parseInt(e.target.value) || 10)}
          size="small"
          inputProps={{ min: 1, max: 100 }}
          sx={{ width: 120 }}
        />
        <TextField
          label="Max Cols"
          type="number"
          value={maxCols}
          onChange={(e) => setMaxCols(parseInt(e.target.value) || 10)}
          size="small"
          inputProps={{ min: 1, max: 50 }}
          sx={{ width: 120 }}
        />
        <Button variant="outlined" onClick={loadViewer} disabled={loadingViewer}>
          Update View
        </Button>
      </Box>

      {infoError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error loading table info:{" "}
          {infoError instanceof Error ? infoError.message : "Unknown error"}
        </Alert>
      )}

      {loadingInfo && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {tableInfo && tableInfo.exists && (
        <>
          <Accordion defaultExpanded={false}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Info />
                <Typography>Table Information</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <Box>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    <strong>Rows:</strong> {tableInfo.nrows?.toLocaleString() || "N/A"}
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    <strong>Columns:</strong> {tableInfo.columns?.length || 0}
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    <strong>Subtables:</strong> {tableInfo.subtables?.length || 0}
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    <strong>Writable:</strong>{" "}
                    {tableInfo.is_writable !== null
                      ? tableInfo.is_writable
                        ? "Yes"
                        : "No"
                      : "N/A"}
                  </Typography>
                </Box>

                {tableInfo.columns && tableInfo.columns.length > 0 && (
                  <Box>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Columns ({tableInfo.columns.length}):</strong>
                    </Typography>
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {tableInfo.columns.map((col) => (
                        <Chip key={col} label={col} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </Box>
                )}

                {tableInfo.subtables && tableInfo.subtables.length > 0 && (
                  <Box>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Subtables ({tableInfo.subtables.length}):</strong>
                    </Typography>
                    <Box
                      sx={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 0.5,
                      }}
                    >
                      {tableInfo.subtables.slice(0, 10).map((subtable) => (
                        <Typography
                          key={subtable}
                          variant="caption"
                          sx={{ fontFamily: "monospace", fontSize: "0.75rem" }}
                        >
                          {subtable.split("/").pop()}
                        </Typography>
                      ))}
                      {tableInfo.subtables.length > 10 && (
                        <Typography variant="caption" color="text.secondary">
                          ... and {tableInfo.subtables.length - 10} more
                        </Typography>
                      )}
                    </Box>
                  </Box>
                )}

                {tableInfo.keywords && Object.keys(tableInfo.keywords).length > 0 && (
                  <Box>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <strong>Keywords ({Object.keys(tableInfo.keywords).length}):</strong>
                    </Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Key</TableCell>
                            <TableCell>Value</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {Object.entries(tableInfo.keywords)
                            .slice(0, 10)
                            .map(([key, value]) => (
                              <TableRow key={key}>
                                <TableCell>
                                  <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                                    {key}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Typography variant="caption">
                                    {typeof value === "string" && value.length > 50
                                      ? value.substring(0, 50) + "..."
                                      : String(value)}
                                  </Typography>
                                </TableCell>
                              </TableRow>
                            ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                    {Object.keys(tableInfo.keywords).length > 10 && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                        ... and {Object.keys(tableInfo.keywords).length - 10} more keywords
                      </Typography>
                    )}
                  </Box>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>

          {viewerError && (
            <Alert severity="error" sx={{ mb: 2, mt: 2 }}>
              {viewerError}
            </Alert>
          )}

          {loadingViewer && (
            <Box sx={{ display: "flex", justifyContent: "center", p: 4, mt: 2 }}>
              <CircularProgress />
              <Typography variant="body2" sx={{ ml: 2 }}>
                Loading table data...
              </Typography>
            </Box>
          )}

          {viewerHtml && !loadingViewer && (
            /* Security note: viewerHtml comes from our own backend API (/api/visualization/casatable/view),
               not from user input, so dangerouslySetInnerHTML is safe here. The backend generates trusted HTML. */
            <Box
              sx={{
                mt: 2,
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1,
                overflow: "auto",
                p: 2,
              }}
              dangerouslySetInnerHTML={{ __html: viewerHtml }}
            />
          )}
        </>
      )}

      {tableInfo && !tableInfo.exists && (
        <Alert severity="warning">Table not found or not accessible: {tablePath}</Alert>
      )}
    </Paper>
  );
}
