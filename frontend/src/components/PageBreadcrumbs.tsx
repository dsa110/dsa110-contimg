/**
 * Universal Page Breadcrumbs Component
 * Shows consistent navigation path across all pages
 */
import React from "react";
import { Breadcrumbs, Link, Typography, Box } from "@mui/material";
import { useNavigate, useLocation } from "react-router-dom";
import { NavigateNext, Home } from "@mui/icons-material";

interface BreadcrumbItem {
  label: string;
  path?: string;
  icon?: React.ReactNode;
}

// Route to breadcrumb mapping
const routeBreadcrumbs: Record<string, BreadcrumbItem[]> = {
  "/dashboard": [{ label: "Dashboard" }],
  "/pipeline": [{ label: "Dashboard", path: "/dashboard" }, { label: "Pipeline" }],
  "/operations": [{ label: "Dashboard", path: "/dashboard" }, { label: "Operations" }],
  "/control": [{ label: "Dashboard", path: "/dashboard" }, { label: "Control Panel" }],
  "/streaming": [{ label: "Dashboard", path: "/dashboard" }, { label: "Streaming" }],
  "/data": [{ label: "Dashboard", path: "/dashboard" }, { label: "Data Browser" }],
  "/sources": [{ label: "Dashboard", path: "/dashboard" }, { label: "Sources" }],
  "/sources/:sourceId": [
    { label: "Dashboard", path: "/dashboard" },
    { label: "Sources", path: "/sources" },
    { label: "Source Details" },
  ],
  "/mosaics": [{ label: "Dashboard", path: "/dashboard" }, { label: "Mosaics" }],
  "/mosaics/:mosaicId": [
    { label: "Dashboard", path: "/dashboard" },
    { label: "Mosaics", path: "/mosaics" },
    { label: "Mosaic Details" },
  ],
  "/sky": [{ label: "Dashboard", path: "/dashboard" }, { label: "Sky View" }],
  "/qa": [{ label: "Dashboard", path: "/dashboard" }, { label: "QA Tools" }],
  "/qa/carta": [
    { label: "Dashboard", path: "/dashboard" },
    { label: "QA Tools", path: "/qa" },
    { label: "CARTA Viewer" },
  ],
  "/system-status": [{ label: "Dashboard", path: "/dashboard" }, { label: "System Status" }],
  "/health": [{ label: "Dashboard", path: "/dashboard" }, { label: "System Diagnostics" }],
  "/events": [{ label: "Dashboard", path: "/dashboard" }, { label: "Events" }],
  "/cache": [{ label: "Dashboard", path: "/dashboard" }, { label: "Cache Statistics" }],
  "/images/:imageId": [
    { label: "Dashboard", path: "/dashboard" },
    { label: "Images" },
    { label: "Image Details" },
  ],
  "/data/:type/:id": [
    { label: "Dashboard", path: "/dashboard" },
    { label: "Data Browser", path: "/data" },
    { label: "Data Details" },
  ],
};

function getBreadcrumbsForPath(pathname: string): BreadcrumbItem[] {
  // Try exact match first
  if (routeBreadcrumbs[pathname]) {
    return routeBreadcrumbs[pathname];
  }

  // Try pattern matching for dynamic routes
  for (const [pattern, breadcrumbs] of Object.entries(routeBreadcrumbs)) {
    const patternParts = pattern.split("/");
    const pathParts = pathname.split("/");

    if (patternParts.length === pathParts.length) {
      let matches = true;
      for (let i = 0; i < patternParts.length; i++) {
        if (!patternParts[i].startsWith(":") && patternParts[i] !== pathParts[i]) {
          matches = false;
          break;
        }
      }
      if (matches) {
        return breadcrumbs;
      }
    }
  }

  // Default: just show current page name
  const pageName = pathname.split("/").pop() || "Dashboard";
  return [
    { label: "Dashboard", path: "/dashboard" },
    { label: pageName.charAt(0).toUpperCase() + pageName.slice(1) },
  ];
}

interface PageBreadcrumbsProps {
  customBreadcrumbs?: BreadcrumbItem[];
}

export default function PageBreadcrumbs({ customBreadcrumbs }: PageBreadcrumbsProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const breadcrumbs = customBreadcrumbs || getBreadcrumbsForPath(location.pathname);

  // Don't show breadcrumbs if we're just on the dashboard
  if (breadcrumbs.length <= 1) {
    return null;
  }

  return (
    <Box
      sx={{
        px: 3,
        py: 1.5,
        bgcolor: "background.paper",
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Breadcrumbs
        separator={<NavigateNext fontSize="small" />}
        aria-label="breadcrumb navigation"
        sx={{
          "& .MuiBreadcrumbs-ol": {
            flexWrap: "nowrap",
          },
        }}
      >
        {breadcrumbs.map((crumb, index) => {
          const isLast = index === breadcrumbs.length - 1;

          if (isLast || !crumb.path) {
            return (
              <Box key={index} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                {index === 0 && <Home fontSize="small" sx={{ color: "text.secondary" }} />}
                <Typography
                  color="text.primary"
                  sx={{
                    fontWeight: isLast ? 600 : 400,
                    fontSize: "0.875rem",
                  }}
                >
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
                  color: "primary.main",
                },
                fontSize: "0.875rem",
              }}
            >
              {index === 0 && <Home fontSize="small" />}
              {crumb.label}
            </Link>
          );
        })}
      </Breadcrumbs>
    </Box>
  );
}
