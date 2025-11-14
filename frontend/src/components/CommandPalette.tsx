/**
 * Command Palette Component (Cmd+K / Ctrl+K)
 * Quick access to all pages, actions, and navigation
 */
import React, { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Chip,
  Paper,
  alpha,
} from "@mui/material";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Dashboard,
  Image,
  TableChart,
  Public,
  Settings,
  PlayArrow,
  Storage,
  Assessment,
  Build,
  AccountTree,
  EventNote,
  Cached,
  Search,
  ArrowForward,
} from "@mui/icons-material";
import { useWorkflow } from "../contexts/WorkflowContext";
import { WORKFLOW_TEMPLATES } from "../types/workflow";

interface Command {
  id: string;
  label: string;
  description?: string;
  icon?: React.ComponentType;
  path?: string;
  action?: () => void;
  category: "page" | "action" | "workflow" | "shortcut";
  keywords: string[];
}

const PAGE_COMMANDS: Command[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: Dashboard,
    path: "/dashboard",
    category: "page",
    keywords: ["dashboard", "home", "main"],
  },
  // Consolidated pages
  {
    id: "pipeline-operations",
    label: "Pipeline Operations",
    icon: AccountTree,
    path: "/pipeline-operations",
    category: "page",
    keywords: ["pipeline", "operations", "dlq", "events", "monitoring", "executions"],
  },
  {
    id: "data-explorer",
    label: "Data Explorer",
    icon: Storage,
    path: "/data-explorer",
    category: "page",
    keywords: ["data", "explorer", "browser", "mosaics", "sources", "sky", "images"],
  },
  {
    id: "pipeline-control",
    label: "Pipeline Control",
    icon: Settings,
    path: "/pipeline-control",
    category: "page",
    keywords: ["control", "pipeline", "streaming", "observing", "ms", "workflows"],
  },
  {
    id: "system-diagnostics",
    label: "System Diagnostics",
    icon: Assessment,
    path: "/system-diagnostics",
    category: "page",
    keywords: ["diagnostics", "health", "qa", "cache", "system", "monitoring"],
  },
  // Legacy routes (for backward compatibility)
  {
    id: "sources",
    label: "Sources",
    icon: TableChart,
    path: "/sources",
    category: "page",
    keywords: ["sources", "catalog", "ese"],
  },
  {
    id: "data",
    label: "Data Browser",
    icon: Storage,
    path: "/data",
    category: "page",
    keywords: ["data", "images", "browser"],
  },
  {
    id: "qa",
    label: "QA Visualization",
    icon: Assessment,
    path: "/qa",
    category: "page",
    keywords: ["qa", "quality", "visualization"],
  },
  {
    id: "control",
    label: "Control",
    icon: Settings,
    path: "/control",
    category: "page",
    keywords: ["control", "manual", "settings"],
  },
  {
    id: "streaming",
    label: "Streaming",
    icon: PlayArrow,
    path: "/streaming",
    category: "page",
    keywords: ["streaming", "ingest"],
  },
  {
    id: "operations",
    label: "Operations",
    icon: Build,
    path: "/operations",
    category: "page",
    keywords: ["operations", "dlq", "circuit"],
  },
  {
    id: "health",
    label: "Health",
    icon: Assessment,
    path: "/health",
    category: "page",
    keywords: ["health", "metrics", "system"],
  },
  {
    id: "pipeline",
    label: "Pipeline",
    icon: AccountTree,
    path: "/pipeline",
    category: "page",
    keywords: ["pipeline", "stages", "execution"],
  },
  {
    id: "sky",
    label: "Sky View",
    icon: Public,
    path: "/sky",
    category: "page",
    keywords: ["sky", "coverage", "pointing"],
  },
  {
    id: "events",
    label: "Events",
    icon: EventNote,
    path: "/events",
    category: "page",
    keywords: ["events", "event bus"],
  },
  {
    id: "cache",
    label: "Cache",
    icon: Cached,
    path: "/cache",
    category: "page",
    keywords: ["cache", "statistics"],
  },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export default function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const { currentWorkflow, suggestedNextSteps } = useWorkflow();

  // Combine all commands
  const allCommands = useMemo(() => {
    const commands: Command[] = [...PAGE_COMMANDS];

    // Add workflow templates
    WORKFLOW_TEMPLATES.forEach((template) => {
      commands.push({
        id: `workflow-${template.id}`,
        label: template.name,
        description: template.description,
        category: "workflow",
        keywords: ["workflow", "template", ...template.name.toLowerCase().split(" ")],
        action: () => {
          // Navigate to first step of workflow
          if (template.steps.length > 0) {
            navigate(template.steps[0].path);
          }
          onClose();
        },
      });
    });

    // Add suggested next steps
    suggestedNextSteps.forEach((step) => {
      commands.push({
        id: `suggested-${step.path}`,
        label: step.label,
        description: step.description,
        icon: step.icon,
        path: step.path,
        category: "action",
        keywords: ["suggested", "next", ...step.label.toLowerCase().split(" ")],
      });
    });

    return commands;
  }, [suggestedNextSteps, navigate, onClose]);

  // Filter commands based on search query
  const filteredCommands = useMemo(() => {
    if (!searchQuery.trim()) {
      return allCommands;
    }

    const query = searchQuery.toLowerCase();
    return allCommands.filter((cmd) => {
      const searchableText = [cmd.label, cmd.description, ...cmd.keywords].join(" ").toLowerCase();
      return searchableText.includes(query);
    });
  }, [allCommands, searchQuery]);

  // Reset selected index when filtered results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredCommands]);

  // Handle keyboard navigation
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          handleCommandSelect(filteredCommands[selectedIndex]);
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, filteredCommands, selectedIndex, onClose]);

  const handleCommandSelect = (command: Command) => {
    if (command.path) {
      navigate(command.path);
    } else if (command.action) {
      command.action();
    }
    onClose();
    setSearchQuery("");
  };

  const handleClose = () => {
    onClose();
    setSearchQuery("");
    setSelectedIndex(0);
  };

  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<string, Command[]> = {};
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.category]) {
        groups[cmd.category] = [];
      }
      groups[cmd.category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  const categoryLabels: Record<string, string> = {
    page: "Pages",
    action: "Suggested Actions",
    workflow: "Workflows",
    shortcut: "Shortcuts",
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          mt: "10vh",
          maxHeight: "70vh",
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Search />
          <TextField
            autoFocus
            fullWidth
            placeholder="Search pages, actions, workflows..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            variant="standard"
            InputProps={{
              disableUnderline: true,
            }}
            sx={{
              "& .MuiInputBase-input": {
                fontSize: "1.1rem",
              },
            }}
          />
        </Box>
      </DialogTitle>
      <DialogContent sx={{ p: 0 }}>
        {filteredCommands.length === 0 ? (
          <Box sx={{ p: 3, textAlign: "center" }}>
            <Typography color="text.secondary">No results found for "{searchQuery}"</Typography>
          </Box>
        ) : (
          <List sx={{ maxHeight: "50vh", overflow: "auto" }}>
            {Object.entries(groupedCommands).map(([category, commands]) => (
              <Box key={category}>
                <Box sx={{ px: 2, py: 1 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ textTransform: "uppercase", fontWeight: 600 }}
                  >
                    {categoryLabels[category] || category}
                  </Typography>
                </Box>
                {commands.map((command, index) => {
                  const globalIndex = filteredCommands.indexOf(command);
                  const isSelected = globalIndex === selectedIndex;
                  const Icon = command.icon || ArrowForward;

                  return (
                    <ListItem key={command.id} disablePadding>
                      <ListItemButton
                        selected={isSelected}
                        onClick={() => handleCommandSelect(command)}
                        sx={{
                          px: 2,
                          py: 1.5,
                          bgcolor: isSelected ? alpha("#90caf9", 0.1) : "transparent",
                          "&:hover": {
                            bgcolor: alpha("#90caf9", 0.15),
                          },
                        }}
                      >
                        <ListItemIcon>
                          <Icon color={isSelected ? "primary" : "action"} />
                        </ListItemIcon>
                        <ListItemText
                          primary={command.label}
                          secondary={command.description}
                          primaryTypographyProps={{
                            fontWeight: isSelected ? 600 : 400,
                          }}
                        />
                        {command.category === "workflow" && (
                          <Chip label="Workflow" size="small" sx={{ ml: 1 }} />
                        )}
                      </ListItemButton>
                    </ListItem>
                  );
                })}
              </Box>
            ))}
          </List>
        )}
        <Box
          sx={{
            px: 2,
            py: 1,
            borderTop: 1,
            borderColor: "divider",
            bgcolor: "background.default",
          }}
        >
          <Typography variant="caption" color="text.secondary">
            Use ↑↓ to navigate, Enter to select, Esc to close
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
