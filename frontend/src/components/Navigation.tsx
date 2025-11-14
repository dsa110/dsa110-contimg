/**
 * Main Navigation Component
 * Uses grouped navigation to reduce clutter
 */
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Drawer,
  useMediaQuery,
  useTheme,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Chip,
} from "@mui/material";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { Menu as MenuIcon, Keyboard } from "@mui/icons-material";
import { useState } from "react";
import {
  Dashboard,
  Image,
  TableChart,
  Public,
  ShowChart,
  Settings,
  PlayArrow,
  Storage,
  Assessment,
  Build,
  AccountTree,
  EventNote,
  Cached,
} from "@mui/icons-material";
import CommandPalette from "./CommandPalette";
import { useCommandPalette } from "../hooks/useCommandPalette";
import { useWorkflow } from "../contexts/WorkflowContext";
import { NavigationGroup } from "./NavigationGroup";

// Navigation groups for consolidated pages
const navigationGroups = {
  pipeline: {
    label: "Pipeline Operations",
    icon: <AccountTree />,
    items: [
      {
        label: "Pipeline Monitoring",
        path: "/pipeline-operations",
        icon: <AccountTree />,
      },
      {
        label: "Operations (DLQ)",
        path: "/pipeline-operations",
        icon: <Build />,
      },
      { label: "Events", path: "/pipeline-operations", icon: <EventNote /> },
    ],
  },
  data: {
    label: "Data Explorer",
    icon: <Storage />,
    items: [
      { label: "Data Browser", path: "/data-explorer", icon: <Storage /> },
      { label: "Mosaics", path: "/data-explorer", icon: <Image /> },
      { label: "Sources", path: "/data-explorer", icon: <TableChart /> },
      { label: "Sky View", path: "/data-explorer", icon: <Public /> },
    ],
  },
  control: {
    label: "Pipeline Control",
    icon: <Settings />,
    items: [
      { label: "Control Panel", path: "/pipeline-control", icon: <Settings /> },
      {
        label: "Streaming Service",
        path: "/pipeline-control",
        icon: <PlayArrow />,
      },
      { label: "Observing", path: "/pipeline-control", icon: <Public /> },
    ],
  },
  diagnostics: {
    label: "System Diagnostics",
    icon: <Assessment />,
    items: [
      {
        label: "System Health",
        path: "/system-diagnostics",
        icon: <Assessment />,
      },
      { label: "QA Tools", path: "/system-diagnostics", icon: <Assessment /> },
      {
        label: "Cache Statistics",
        path: "/system-diagnostics",
        icon: <Cached />,
      },
    ],
  },
};

// Legacy nav items for mobile drawer (backward compatibility)
const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: Dashboard },
  {
    path: "/pipeline-operations",
    label: "Pipeline Operations",
    icon: AccountTree,
  },
  { path: "/data-explorer", label: "Data Explorer", icon: Storage },
  { path: "/pipeline-control", label: "Pipeline Control", icon: Settings },
  {
    path: "/system-diagnostics",
    label: "System Diagnostics",
    icon: Assessment,
  },
];

export default function Navigation() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const { open: commandPaletteOpen, setOpen: setCommandPaletteOpen } = useCommandPalette();
  const { currentWorkflow } = useWorkflow();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const drawer = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: "center", pt: 2 }}>
      <Typography variant="h6" sx={{ my: 2 }}>
        DSA-110
      </Typography>
      <List>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            location.pathname === item.path ||
            (item.path === "/data" && location.pathname.startsWith("/data")) ||
            (item.path === "/qa" && location.pathname.startsWith("/qa"));

          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton component={RouterLink} to={item.path} selected={isActive}>
                <ListItemIcon>
                  <Icon color={isActive ? "primary" : "inherit"} />
                </ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Box>
  );

  return (
    <>
      <AppBar
        position="sticky"
        sx={{
          bgcolor: "#1e1e1e",
          width: "100%",
          left: 0,
          right: 0,
        }}
      >
        <Toolbar sx={{ width: "100%", maxWidth: "100%" }}>
          {isMobile && (
            <IconButton color="inherit" edge="start" onClick={handleDrawerToggle} sx={{ mr: 2 }}>
              <MenuIcon />
            </IconButton>
          )}
          <ShowChart sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 0, mr: 4 }}>
            DSA-110
          </Typography>

          {!isMobile && (
            <Box
              sx={{
                display: "flex",
                gap: 1,
                flexGrow: 1,
                alignItems: "center",
              }}
            >
              {/* Dashboard - Always visible */}
              <Button
                component={RouterLink}
                to="/dashboard"
                startIcon={<Dashboard />}
                sx={{
                  color: location.pathname === "/dashboard" ? "primary.main" : "inherit",
                  bgcolor:
                    location.pathname === "/dashboard"
                      ? "rgba(144, 202, 249, 0.08)"
                      : "transparent",
                  fontWeight: location.pathname === "/dashboard" ? 600 : 400,
                  "&:hover": {
                    bgcolor: "rgba(144, 202, 249, 0.12)",
                  },
                }}
              >
                Dashboard
              </Button>

              {/* Grouped Navigation */}
              {Object.entries(navigationGroups).map(([key, group]) => (
                <NavigationGroup
                  key={key}
                  label={group.label}
                  icon={group.icon}
                  items={group.items}
                  currentPath={location.pathname}
                />
              ))}
            </Box>
          )}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {currentWorkflow && !isMobile && (
              <Chip label={currentWorkflow} size="small" sx={{ textTransform: "capitalize" }} />
            )}
            <IconButton
              color="inherit"
              onClick={() => setCommandPaletteOpen(true)}
              title="Open command palette (Cmd+K / Ctrl+K)"
              sx={{ ml: 1 }}
            >
              <Keyboard />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": { boxSizing: "border-box", width: 240 },
        }}
      >
        {drawer}
      </Drawer>
      <CommandPalette open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </>
  );
}
