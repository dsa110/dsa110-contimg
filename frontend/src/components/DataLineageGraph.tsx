/**
 * Data Lineage Graph Component
 * Visualizes data relationships as a graph
 */
import { useMemo } from "react";
import { Box, Paper, Typography, Chip, CircularProgress, Alert } from "@mui/material";
import { useDataLineage, useDataInstance } from "../api/queries";

interface LineageGraphProps {
  dataId: string;
}

const DATA_TYPE_COLORS: Record<string, string> = {
  ms: "#4CAF50",
  calib_ms: "#2196F3",
  caltable: "#FF9800",
  image: "#9C27B0",
  mosaic: "#E91E63",
  catalog: "#00BCD4",
  qa: "#607D8B",
  metadata: "#795548",
};

export default function DataLineageGraph({ dataId }: LineageGraphProps) {
  const { data: lineage, isLoading, error } = useDataLineage(dataId);
  const { data: currentInstance } = useDataInstance(dataId);

  const graphData = useMemo(() => {
    if (!lineage) return null;

    const nodes: Array<{
      id: string;
      label: string;
      type: string;
      color: string;
    }> = [];
    const edges: Array<{
      from: string;
      to: string;
      label: string;
      color: string;
    }> = [];

    // Add current node
    if (currentInstance) {
      nodes.push({
        id: dataId,
        label: `${currentInstance.data_type ?? "unknown"}\n${dataId.slice(0, 8)}...`,
        type: currentInstance.data_type ?? "unknown",
        color: DATA_TYPE_COLORS[currentInstance.data_type ?? "unknown"] || "#757575",
      });
    }

    // Add parent nodes
    Object.entries(lineage.parents).forEach(([relType, parentIds]) => {
      parentIds.forEach((parentId) => {
        if (!nodes.find((n) => n.id === parentId)) {
          nodes.push({
            id: parentId,
            label: `${parentId.slice(0, 8)}...`,
            type: "unknown",
            color: "#757575",
          });
        }
        edges.push({
          from: parentId,
          to: dataId,
          label: relType,
          color: "#4CAF50",
        });
      });
    });

    // Add child nodes
    Object.entries(lineage.children).forEach(([relType, childIds]) => {
      childIds.forEach((childId) => {
        if (!nodes.find((n) => n.id === childId)) {
          nodes.push({
            id: childId,
            label: `${childId.slice(0, 8)}...`,
            type: "unknown",
            color: "#757575",
          });
        }
        edges.push({
          from: dataId,
          to: childId,
          label: relType,
          color: "#2196F3",
        });
      });
    });

    return { nodes, edges };
  }, [lineage, dataId, currentInstance]);

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Failed to load lineage: {error.message}</Alert>;
  }

  if (!lineage || (!lineage.parents && !lineage.children)) {
    return <Alert severity="info">No lineage information available for this data instance.</Alert>;
  }

  if (!graphData || graphData.nodes.length === 0) {
    return <Alert severity="info">No relationships found.</Alert>;
  }

  // Simple graph visualization using CSS and flexbox
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Data Lineage Graph
      </Typography>

      <Box sx={{ mt: 2 }}>
        {/* Parents Section */}
        {Object.keys(lineage.parents).length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Parents (Derived From)
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}>
              {Object.entries(lineage.parents).map(([relType, parentIds]) =>
                parentIds.map((parentId) => (
                  <Box
                    key={`parent-${parentId}`}
                    sx={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      p: 1,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 1,
                      bgcolor: "background.paper",
                    }}
                  >
                    <Chip
                      label={parentId.slice(0, 12)}
                      size="small"
                      sx={{ mb: 0.5, fontFamily: "monospace" }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {relType}
                    </Typography>
                    <Box
                      sx={{
                        width: 2,
                        height: 20,
                        bgcolor: "primary.main",
                        my: 0.5,
                      }}
                    />
                  </Box>
                ))
              )}
            </Box>
          </Box>
        )}

        {/* Current Node */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            my: 2,
          }}
        >
          <Paper
            sx={{
              p: 2,
              bgcolor: currentInstance?.data_type
                ? DATA_TYPE_COLORS[currentInstance.data_type] || "primary.main"
                : "primary.main",
              color: "white",
              borderRadius: 2,
              minWidth: 200,
              textAlign: "center",
            }}
          >
            <Typography variant="subtitle2" fontWeight="bold">
              {currentInstance?.data_type?.toUpperCase() || "CURRENT"}
            </Typography>
            <Typography variant="body2" sx={{ fontFamily: "monospace", mt: 0.5 }}>
              {dataId.slice(0, 16)}...
            </Typography>
          </Paper>
        </Box>

        {/* Children Section */}
        {Object.keys(lineage.children).length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Children (Produced)
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
              {Object.entries(lineage.children).map(([relType, childIds]) =>
                childIds.map((childId) => (
                  <Box
                    key={`child-${childId}`}
                    sx={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      p: 1,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 1,
                      bgcolor: "background.paper",
                    }}
                  >
                    <Box
                      sx={{
                        width: 2,
                        height: 20,
                        bgcolor: "primary.main",
                        mb: 0.5,
                      }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {relType}
                    </Typography>
                    <Chip
                      label={childId.slice(0, 12)}
                      size="small"
                      sx={{ mt: 0.5, fontFamily: "monospace" }}
                    />
                  </Box>
                ))
              )}
            </Box>
          </Box>
        )}
      </Box>

      {/* Legend */}
      <Box sx={{ mt: 4, p: 2, bgcolor: "background.default", borderRadius: 1 }}>
        <Typography variant="caption" fontWeight="bold" gutterBottom>
          Relationship Types:
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1 }}>
          {[...new Set([...Object.keys(lineage.parents), ...Object.keys(lineage.children)])].map(
            (relType) => (
              <Chip key={relType} label={relType} size="small" variant="outlined" />
            )
          )}
        </Box>
      </Box>
    </Box>
  );
}
