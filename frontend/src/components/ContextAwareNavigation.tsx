/**
 * Context-Aware Navigation Component
 * Shows suggested next steps and quick actions based on current workflow
 */
import React from "react";
import { Box, Paper, Typography, Button, Chip, Stack } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { ArrowForward, Lightbulb } from "@mui/icons-material";
import { useWorkflow } from "../contexts/WorkflowContext";

export default function ContextAwareNavigation() {
  const { suggestedNextSteps, quickActions, currentWorkflow } = useWorkflow();
  const navigate = useNavigate();

  // Don't show if no suggestions
  if (suggestedNextSteps.length === 0 && quickActions.length === 0) {
    return null;
  }

  return (
    <Paper
      sx={{
        p: 2,
        mb: 2,
        bgcolor: "background.paper",
        border: 1,
        borderColor: "divider",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
        <Lightbulb color="primary" fontSize="small" />
        <Typography variant="subtitle2" fontWeight={600}>
          Suggested Next Steps
        </Typography>
        {currentWorkflow && (
          <Chip
            label={currentWorkflow}
            size="small"
            sx={{ ml: "auto", textTransform: "capitalize" }}
          />
        )}
      </Box>
      <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
        {suggestedNextSteps.map((step) => {
          const Icon = step.icon || ArrowForward;
          return (
            <Button
              key={step.path}
              variant="outlined"
              size="small"
              startIcon={<Icon />}
              onClick={() => step.path && navigate(step.path)}
              sx={{ textTransform: "none" }}
            >
              {step.label}
              {step.description && (
                <Typography variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                  {step.description}
                </Typography>
              )}
            </Button>
          );
        })}
        {quickActions.map((action) => {
          const Icon = action.icon || ArrowForward;
          return (
            <Button
              key={action.id}
              variant="contained"
              size="small"
              startIcon={Icon ? <Icon /> : undefined}
              onClick={action.action}
              sx={{ textTransform: "none" }}
            >
              {action.label}
            </Button>
          );
        })}
      </Stack>
    </Paper>
  );
}
