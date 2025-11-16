/**
 * Main Navigation Component
 * Flattened navigation - all primary sections visible directly
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
  Science,
  Visibility,
} from "@mui/icons-material";
import CommandPalette from "./CommandPalette";
import { useCommandPalette } from "../hooks/useCommandPalette";
import { useWorkflow } from "../contexts/WorkflowContext";
import { prefetchRoute } from "../utils/routePrefetch";

// Flattened navigation items - all primary sections visible
const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: Dashboard },
  { path: "/pipeline", label: "Pipeline", icon: AccountTree },
  { path: "/operations", label: "Operations", icon: Build },
  { path: "/control", label: "Control", icon: Settings },
  { path: "/calibration", label: "Calibration", icon: Build },
  { path: "/streaming", label: "Streaming", icon: PlayArrow },
  { path: "/data", label: "Data Browser", icon: Storage },
  { path: "/sources", label: "Sources", icon: TableChart },
  { path: "/mosaics", label: "Mosaics", icon: Image },
  { path: "/sky", label: "Sky View", icon: Public },
  { path: "/carta", label: "CARTA", icon: Visibility },
  { path: "/qa", label: "QA Tools", icon: Science },
  { path: "/health", label: "Health", icon: Assessment },
  { path: "/events", label: "Events", icon: EventNote },
  { path: "/cache", label: "Cache", icon: Cached },
];

export default function Navigation() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg")); // Changed from "md" to "lg" for better breakpoint
  const { open: commandPaletteOpen, setOpen: setCommandPaletteOpen } = useCommandPalette();
  const { currentWorkflow } = useWorkflow();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const isActive = (path: string) => {
    if (path === "/dashboard") {
      return location.pathname === "/dashboard";
    }
    // For other routes, check if pathname starts with the route
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const drawer = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: "center", pt: 2 }}>
      <Typography variant="h6" sx={{ my: 2 }}>
        DSA-110
      </Typography>
      <List>
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.path);

          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                component={RouterLink}
                to={item.path}
                selected={active}
                onMouseEnter={() => prefetchRoute(item.path)}
              >
                <ListItemIcon>
                  <Icon color={active ? "primary" : "inherit"} />
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
          maxWidth: "none",
          left: 0,
          right: 0,
          margin: 0,
          padding: 0,
          boxSizing: "border-box",
        }}
      >
        <Toolbar
          sx={{
            width: "100%",
            maxWidth: "100%",
            px: { xs: 1, sm: 2 },
            margin: 0,
          }}
        >
          {isMobile && (
            <IconButton color="inherit" edge="start" onClick={handleDrawerToggle} sx={{ mr: 2 }}>
              <MenuIcon />
            </IconButton>
          )}
          <ShowChart sx={{ mr: 2, display: { xs: "none", sm: "block" } }} />
          <Typography
            variant="h6"
            component="div"
            sx={{ flexGrow: 0, mr: { xs: 1, sm: 4 }, display: { xs: "none", sm: "block" } }}
          >
            DSA-110
          </Typography>

          {!isMobile && (
            <Box
              sx={{
                display: "flex",
                gap: 0.5,
                flexGrow: 1,
                alignItems: "center",
                flexWrap: "wrap",
                overflowX: "auto",
                "&::-webkit-scrollbar": { display: "none" },
                scrollbarWidth: "none",
              }}
            >
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);

                return (
                  <Button
                    key={item.path}
                    component={RouterLink}
                    to={item.path}
                    startIcon={<Icon />}
                    onMouseEnter={() => prefetchRoute(item.path)}
                    sx={{
                      color: active ? "primary.main" : "text.secondary",
                      bgcolor: active ? "rgba(144, 202, 249, 0.08)" : "transparent",
                      fontWeight: active ? 600 : 400,
                      fontSize: "0.875rem",
                      px: 1.5,
                      py: 0.75,
                      minWidth: "auto",
                      whiteSpace: "nowrap",
                      "&:hover": {
                        bgcolor: active ? "rgba(144, 202, 249, 0.12)" : "rgba(255, 255, 255, 0.05)",
                      },
                      transition: "all 0.2s ease-in-out",
                    }}
                  >
                    {item.label}
                  </Button>
                );
              })}
            </Box>
          )}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: "auto" }}>
            {currentWorkflow && !isMobile && (
              <Chip
                label={currentWorkflow}
                size="small"
                sx={{ textTransform: "capitalize", display: { xs: "none", md: "flex" } }}
              />
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
          display: { xs: "block", lg: "none" },
          "& .MuiDrawer-paper": { boxSizing: "border-box", width: 280 },
        }}
      >
        {drawer}
      </Drawer>
      <CommandPalette open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </>
  );
}
