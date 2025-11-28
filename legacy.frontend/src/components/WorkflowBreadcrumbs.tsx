/**
 * Workflow Breadcrumbs Component
 * Shows current navigation path and allows quick navigation
 */
// import React from "react";
import { Breadcrumbs, Link, Typography, Box, Chip } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { NavigateNext, Home } from "@mui/icons-material";
import { useWorkflow } from "../contexts/WorkflowContext";

export default function WorkflowBreadcrumbs() {
  const { breadcrumbs, currentWorkflow } = useWorkflow();
  const navigate = useNavigate();

  if (breadcrumbs.length <= 1) {
    return null; // Don't show breadcrumbs if we're just on the dashboard
  }

  return (
    <Box
      sx={{
        px: 2,
        py: 1,
        bgcolor: "background.paper",
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Breadcrumbs separator={<NavigateNext fontSize="small" />} aria-label="breadcrumb navigation">
        {breadcrumbs.map((crumb, index) => {
          const isLast = index === breadcrumbs.length - 1;
          const Icon = crumb.icon || (index === 0 ? Home : undefined);

          if (isLast || !crumb.path) {
            return (
              <Box key={index} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                {Icon && <Icon fontSize="small" />}
                <Typography color="text.primary" sx={{ fontWeight: isLast ? 600 : 400 }}>
                  {crumb.label}
                </Typography>
              </Box>
            );
          }

          return (
            <Link
              key={index}
              component="button"
              variant="body2"
              onClick={() => crumb.path && navigate(crumb.path)}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                color: "text.secondary",
                textDecoration: "none",
                "&:hover": {
                  textDecoration: "underline",
                },
                cursor: "pointer",
                border: "none",
                background: "none",
                padding: 0,
              }}
            >
              {Icon && <Icon fontSize="small" />}
              {crumb.label}
            </Link>
          );
        })}
      </Breadcrumbs>
      {currentWorkflow && (
        <Box sx={{ mt: 0.5 }}>
          <Chip
            label={currentWorkflow.charAt(0).toUpperCase() + currentWorkflow.slice(1)}
            size="small"
            sx={{
              textTransform: "capitalize",
              fontSize: "0.7rem",
              height: 20,
            }}
          />
        </Box>
      )}
    </Box>
  );
}
