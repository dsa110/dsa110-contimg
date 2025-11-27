/**
 * Main Navigation Component
 * Simplified two-view navigation: Pipeline | Data
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
  Divider,
} from "@mui/material";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { Menu as MenuIcon, Keyboard } from "@mui/icons-material";
import { useState } from "react";
import {
  AccountTree,
  Storage,
  ShowChart,
} from "@mui/icons-material";
import CommandPalette from "./CommandPalette";
import { useCommandPalette } from "../hooks/useCommandPalette";
import { useWorkflow } from "../contexts/WorkflowContext";
import { prefetchRoute } from "../utils/routePrefetch";

// Simplified navigation - just two main views
const navItems = [
  { path: "/pipeline", label: "Pipeline", icon: AccountTree, description: "Execute & Monitor" },
  { path: "/data", label: "Data", icon: Storage, description: "Browse & Analyze" },
];

export default function Navigation() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("lg"));
  const { open: commandPaletteOpen, setOpen: setCommandPaletteOpen } = useCommandPalette();
  const { currentWorkflow } = useWorkflow();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const isActive = (path: string) => {
    if (path === "/dashboard") {
      return location.pathname === "/dashboard";
    }
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const drawer = (
    <Box
      sx={{ textAlign: "center", pt: 2, height: "100%", display: "flex", flexDirection: "column" }}
    >
      <Typography variant="h6" sx={{ my: 2 }}>
        DSA-110
      </Typography>
      <Box sx={{ overflowY: "auto", flexGrow: 1 }}>
        <List>
          {navGroups.map((group, index) => (
            <Box key={group.title}>
              {index > 0 && <Divider />}
              <ListSubheader sx={{ bgcolor: "transparent", lineHeight: "32px", pt: 1 }}>
                {group.title}
              </ListSubheader>
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);

                return (
                  <ListItem key={item.path} disablePadding>
                    <ListItemButton
                      component={RouterLink}
                      to={item.path}
                      selected={active}
                      onClick={handleDrawerToggle}
                      onMouseEnter={() => prefetchRoute(item.path)}
                      sx={{ pl: 4 }}
                    >
                      <ListItemIcon>
                        <Icon color={active ? "primary" : "inherit"} />
                      </ListItemIcon>
                      <ListItemText primary={item.label} />
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </Box>
          ))}
        </List>
      </Box>
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
                flexWrap: "nowrap",
                overflowX: "auto",
                "&::-webkit-scrollbar": { display: "none" },
                scrollbarWidth: "none",
              }}
            >
              {navGroups.map((group, groupIndex) => (
                <Box key={group.title} sx={{ display: "flex", alignItems: "center" }}>
                  {groupIndex > 0 && (
                    <Divider
                      orientation="vertical"
                      flexItem
                      sx={{ mx: 1, height: 24, borderColor: "rgba(255,255,255,0.2)" }}
                    />
                  )}
                  {group.items.map((item) => {
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
                            bgcolor: active
                              ? "rgba(144, 202, 249, 0.12)"
                              : "rgba(255, 255, 255, 0.05)",
                          },
                          transition: "all 0.2s ease-in-out",
                        }}
                      >
                        {item.label}
                      </Button>
                    );
                  })}
                </Box>
              ))}
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
