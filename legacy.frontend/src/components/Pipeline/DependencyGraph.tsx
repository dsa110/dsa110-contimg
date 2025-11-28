// import React from "react";
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  Typography,
  Paper,
  Stack,
  Chip,
} from "@mui/material";
import { useDependencyGraph } from "../../api/queries";
// import ArrowForwardIcon from "@mui/icons-material/ArrowForward";

export default function DependencyGraph() {
  const { data: graph, isLoading, error } = useDependencyGraph();

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Error loading dependency graph: {error.message}</Typography>
      </Box>
    );
  }

  if (!graph || !graph.nodes || graph.nodes.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>No dependency graph available</Typography>
      </Box>
    );
  }

  // Build a map of dependencies for easier rendering
  const nodeMap = new Map(graph.nodes.map((node) => [node.id, node]));
  const edgesByTarget = new Map<string, string[]>();

  graph.edges.forEach((edge) => {
    if (!edgesByTarget.has(edge.to)) {
      edgesByTarget.set(edge.to, []);
    }
    edgesByTarget.get(edge.to)!.push(edge.from);
  });

  // Simple linear layout (can be enhanced with a proper graph library later)
  const renderNode = (nodeId: string, level: number = 0) => {
    const node = nodeMap.get(nodeId);
    if (!node) return null;

    const dependencies = edgesByTarget.get(nodeId) || [];

    return (
      <Box key={nodeId} sx={{ ml: level * 4 }}>
        <Paper
          elevation={2}
          sx={{
            p: 2,
            mb: 1,
            bgcolor: level === 0 ? "primary.light" : "background.paper",
            color: level === 0 ? "primary.contrastText" : "text.primary",
          }}
        >
          <Typography variant="body2" fontWeight={level === 0 ? "bold" : "normal"}>
            {node.label}
          </Typography>
          {dependencies.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" sx={{ opacity: 0.8 }}>
                Depends on: {dependencies.map((dep) => nodeMap.get(dep)?.label || dep).join(", ")}
              </Typography>
            </Box>
          )}
        </Paper>
        {dependencies.map((dep) => renderNode(dep, level + 1))}
      </Box>
    );
  };

  // Find root nodes (nodes with no dependencies)
  const rootNodes = graph.nodes.filter((node) => !edgesByTarget.has(node.id));

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Pipeline Dependency Graph
        </Typography>

        <Box sx={{ mt: 2 }}>
          {rootNodes.length > 0 ? (
            <Stack spacing={2}>
              {rootNodes.map((root) => (
                <Box key={root.id}>{renderNode(root.id, 0)}</Box>
              ))}
            </Stack>
          ) : (
            <Box>
              {graph.nodes.map((node) => (
                <Chip
                  key={node.id}
                  label={node.label}
                  sx={{ m: 0.5 }}
                  color="primary"
                  variant="outlined"
                />
              ))}
            </Box>
          )}
        </Box>

        <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: "divider" }}>
          <Typography variant="caption" color="text.secondary">
            Total Stages: {graph.nodes.length} | Dependencies: {graph.edges.length}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
