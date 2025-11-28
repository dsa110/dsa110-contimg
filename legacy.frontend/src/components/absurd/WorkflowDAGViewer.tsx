/**
 * WorkflowDAGViewer - Visualize workflow task dependencies as a DAG.
 *
 * Features:
 * - Visual representation of task dependency graph
 * - Task status indicators
 * - Interactive node selection
 * - Ready tasks highlighting
 * - Progress tracking
 */

import { useState, useMemo } from "react";
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  LinearProgress,
  useTheme,
  alpha,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Collapse,
} from "@mui/material";
import {
  AccountTree as DAGIcon,
  Circle as NodeIcon,
  CheckCircle as CompletedIcon,
  Error as FailedIcon,
  HourglassEmpty as PendingIcon,
  PlayCircle as RunningIcon,
  ArrowForward as ArrowIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
} from "@mui/icons-material";
import { useWorkflowDAG, useWorkflowStatus, useReadyTasks } from "../../api/absurdQueries";
import type { DAGNode, WorkflowDAG, WorkflowStatus } from "../../api/absurd";

interface WorkflowDAGViewerProps {
  workflowId: string;
}

// Get status icon
function getStatusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CompletedIcon color="success" fontSize="small" />;
    case "failed":
      return <FailedIcon color="error" fontSize="small" />;
    case "claimed":
      return <RunningIcon color="info" fontSize="small" />;
    default:
      return <PendingIcon color="disabled" fontSize="small" />;
  }
}

// Get status color
function getStatusColor(status: string, theme: any) {
  switch (status) {
    case "completed":
      return theme.palette.success.main;
    case "failed":
      return theme.palette.error.main;
    case "claimed":
      return theme.palette.info.main;
    default:
      return theme.palette.grey[400];
  }
}

export function WorkflowDAGViewer({ workflowId }: WorkflowDAGViewerProps) {
  const theme = useTheme();
  const [expandedLevels, setExpandedLevels] = useState<Set<number>>(new Set([0, 1, 2]));
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Fetch workflow data
  const { data: dagData, isLoading: dagLoading, refetch: refetchDAG } = useWorkflowDAG(workflowId);
  const { data: statusData, isLoading: statusLoading } = useWorkflowStatus(workflowId);
  const { data: readyData } = useReadyTasks(workflowId);

  const readyTaskIds = new Set(readyData?.ready_tasks || []);

  // Group nodes by depth level
  const nodesByLevel = useMemo(() => {
    if (!dagData?.nodes) return new Map<number, DAGNode[]>();

    const levels = new Map<number, DAGNode[]>();
    for (const node of dagData.nodes) {
      const level = node.depth;
      if (!levels.has(level)) {
        levels.set(level, []);
      }
      levels.get(level)!.push(node);
    }

    // Sort by depth
    return new Map([...levels.entries()].sort((a, b) => a[0] - b[0]));
  }, [dagData]);

  // Toggle level expansion
  const toggleLevel = (level: number) => {
    const newExpanded = new Set(expandedLevels);
    if (newExpanded.has(level)) {
      newExpanded.delete(level);
    } else {
      newExpanded.add(level);
    }
    setExpandedLevels(newExpanded);
  };

  if (dagLoading || statusLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography>Loading workflow...</Typography>
        <LinearProgress sx={{ mt: 2 }} />
      </Paper>
    );
  }

  if (!dagData || !statusData) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography color="error">Failed to load workflow data</Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Workflow Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <DAGIcon sx={{ fontSize: 28, color: theme.palette.primary.main }} />
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {statusData.name}
              </Typography>
              {statusData.description && (
                <Typography variant="body2" color="text.secondary">
                  {statusData.description}
                </Typography>
              )}
            </Box>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              label={statusData.status}
              color={
                statusData.status === "completed"
                  ? "success"
                  : statusData.status === "failed"
                    ? "error"
                    : statusData.status === "running"
                      ? "info"
                      : "default"
              }
              size="small"
            />
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={() => refetchDAG()}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>

        {/* Progress Bar */}
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              Progress
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {statusData.tasks.completed}/{statusData.tasks.total} completed
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={statusData.progress}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: alpha(theme.palette.primary.main, 0.1),
            }}
          />
        </Box>

        {/* Task Stats */}
        <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
          <Chip
            icon={<CompletedIcon fontSize="small" />}
            label={`${statusData.tasks.completed} completed`}
            size="small"
            color="success"
            variant="outlined"
          />
          <Chip
            icon={<RunningIcon fontSize="small" />}
            label={`${statusData.tasks.running} running`}
            size="small"
            color="info"
            variant="outlined"
          />
          <Chip
            icon={<PendingIcon fontSize="small" />}
            label={`${statusData.tasks.pending} pending`}
            size="small"
            variant="outlined"
          />
          {statusData.tasks.blocked > 0 && (
            <Chip
              label={`${statusData.tasks.blocked} blocked`}
              size="small"
              color="warning"
              variant="outlined"
            />
          )}
          {statusData.tasks.failed > 0 && (
            <Chip
              icon={<FailedIcon fontSize="small" />}
              label={`${statusData.tasks.failed} failed`}
              size="small"
              color="error"
              variant="outlined"
            />
          )}
        </Stack>
      </Paper>

      {/* DAG Visualization */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
          Task Dependency Graph
        </Typography>

        {dagData.total_depth === 0 ? (
          <Typography color="text.secondary">No tasks in workflow</Typography>
        ) : (
          <Box>
            {/* Ready Tasks Highlight */}
            {readyTaskIds.size > 0 && (
              <Box
                sx={{
                  mb: 2,
                  p: 1.5,
                  bgcolor: alpha(theme.palette.success.main, 0.1),
                  borderRadius: 1,
                  border: `1px solid ${alpha(theme.palette.success.main, 0.3)}`,
                }}
              >
                <Typography variant="body2" color="success.main" sx={{ fontWeight: 500 }}>
                  {readyTaskIds.size} task(s) ready to execute
                </Typography>
              </Box>
            )}

            {/* Levels */}
            {Array.from(nodesByLevel.entries()).map(([level, nodes]) => (
              <Box key={level} sx={{ mb: 2 }}>
                {/* Level Header */}
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    cursor: "pointer",
                    py: 0.5,
                    "&:hover": { bgcolor: alpha(theme.palette.primary.main, 0.05) },
                    borderRadius: 1,
                    px: 1,
                  }}
                  onClick={() => toggleLevel(level)}
                >
                  {expandedLevels.has(level) ? (
                    <CollapseIcon fontSize="small" />
                  ) : (
                    <ExpandIcon fontSize="small" />
                  )}
                  <Typography variant="subtitle2" color="text.secondary">
                    Level {level}
                    {level === 0 && " (Root)"}
                    {level === dagData.total_depth && level > 0 && " (Leaf)"}
                  </Typography>
                  <Chip label={nodes.length} size="small" />
                </Box>

                {/* Level Nodes */}
                <Collapse in={expandedLevels.has(level)}>
                  <Box sx={{ pl: 4, display: "flex", flexWrap: "wrap", gap: 1, mt: 1 }}>
                    {nodes.map((node) => {
                      const isReady = readyTaskIds.has(node.task_id);
                      const isSelected = selectedNode === node.task_id;

                      return (
                        <Box
                          key={node.task_id}
                          sx={{
                            p: 1.5,
                            border: `2px solid ${
                              isSelected
                                ? theme.palette.primary.main
                                : isReady
                                  ? theme.palette.success.main
                                  : getStatusColor(node.status, theme)
                            }`,
                            borderRadius: 2,
                            bgcolor: isSelected
                              ? alpha(theme.palette.primary.main, 0.05)
                              : isReady
                                ? alpha(theme.palette.success.main, 0.05)
                                : "background.paper",
                            cursor: "pointer",
                            transition: "all 0.2s",
                            "&:hover": {
                              transform: "translateY(-2px)",
                              boxShadow: 2,
                            },
                            minWidth: 180,
                          }}
                          onClick={() => setSelectedNode(isSelected ? null : node.task_id)}
                        >
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                            {getStatusIcon(node.status)}
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {node.task_name}
                            </Typography>
                          </Box>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{
                              display: "block",
                              fontFamily: "monospace",
                              fontSize: "0.65rem",
                            }}
                          >
                            {node.task_id.substring(0, 8)}...
                          </Typography>

                          {/* Dependencies info */}
                          {node.depends_on.length > 0 && (
                            <Typography variant="caption" color="text.secondary">
                              ← {node.depends_on.length} dep{node.depends_on.length > 1 ? "s" : ""}
                            </Typography>
                          )}
                          {node.dependents.length > 0 && (
                            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                              → {node.dependents.length} dependent
                              {node.dependents.length > 1 ? "s" : ""}
                            </Typography>
                          )}

                          {isReady && (
                            <Chip
                              label="Ready"
                              size="small"
                              color="success"
                              sx={{ mt: 0.5, height: 18, fontSize: "0.65rem" }}
                            />
                          )}
                        </Box>
                      );
                    })}
                  </Box>
                </Collapse>

                {level < dagData.total_depth && (
                  <Box sx={{ display: "flex", justifyContent: "center", my: 1 }}>
                    <ArrowIcon sx={{ color: theme.palette.grey[400] }} />
                  </Box>
                )}
              </Box>
            ))}
          </Box>
        )}

        {/* Selected Node Details */}
        {selectedNode && (
          <Box sx={{ mt: 3 }}>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Selected Task Details
            </Typography>
            {(() => {
              const node = dagData.nodes.find((n) => n.task_id === selectedNode);
              if (!node) return null;

              return (
                <Box sx={{ pl: 2 }}>
                  <Typography variant="body2">
                    <strong>Task ID:</strong> {node.task_id}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Type:</strong> {node.task_name}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Status:</strong> {node.status}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Depth:</strong> {node.depth}
                  </Typography>
                  {node.depends_on.length > 0 && (
                    <Typography variant="body2">
                      <strong>Depends on:</strong> {node.depends_on.join(", ")}
                    </Typography>
                  )}
                  {node.dependents.length > 0 && (
                    <Typography variant="body2">
                      <strong>Dependents:</strong> {node.dependents.join(", ")}
                    </Typography>
                  )}
                </Box>
              );
            })()}
          </Box>
        )}
      </Paper>
    </Box>
  );
}

export default WorkflowDAGViewer;
