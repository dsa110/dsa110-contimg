/**
 * Main Navigation Component
 */
import { AppBar, Toolbar, Typography, Button, Box, IconButton, Drawer, useMediaQuery, useTheme, List, ListItem, ListItemButton, ListItemIcon, ListItemText } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Menu as MenuIcon } from '@mui/icons-material';
import { useState } from 'react';
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
} from '@mui/icons-material';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: Dashboard },
  { path: '/control', label: 'Control', icon: Settings },
  { path: '/streaming', label: 'Streaming', icon: PlayArrow },
  { path: '/data', label: 'Data', icon: Storage },
  { path: '/qa', label: 'QA Visualization', icon: Assessment },
  { path: '/mosaics', label: 'Mosaics', icon: Image },
  { path: '/sources', label: 'Sources', icon: TableChart },
  { path: '/sky', label: 'Sky View', icon: Public },
];

export default function Navigation() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const drawer = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: 'center', pt: 2 }}>
      <Typography variant="h6" sx={{ my: 2 }}>
        DSA-110
      </Typography>
      <List>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || 
            (item.path === '/data' && location.pathname.startsWith('/data')) ||
            (item.path === '/qa' && location.pathname.startsWith('/qa'));
          
          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                component={RouterLink}
                to={item.path}
                selected={isActive}
              >
                <ListItemIcon>
                  <Icon color={isActive ? 'primary' : 'inherit'} />
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
      <AppBar position="sticky" sx={{ bgcolor: '#1e1e1e' }}>
        <Toolbar>
          {isMobile && (
            <IconButton
              color="inherit"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}
          <ShowChart sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 0, mr: 4 }}>
            DSA-110
          </Typography>

          {!isMobile && (
            <Box sx={{ display: 'flex', gap: 1, flexGrow: 1 }}>
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path || 
                  (item.path === '/data' && location.pathname.startsWith('/data')) ||
                  (item.path === '/qa' && location.pathname.startsWith('/qa'));

                return (
                  <Button
                    key={item.path}
                    component={RouterLink}
                    to={item.path}
                    startIcon={<Icon />}
                    sx={{
                      color: isActive ? 'primary.main' : 'inherit',
                      bgcolor: isActive ? 'rgba(144, 202, 249, 0.08)' : 'transparent',
                      '&:hover': {
                        bgcolor: 'rgba(144, 202, 249, 0.12)',
                      },
                    }}
                  >
                    {item.label}
                  </Button>
                );
              })}
            </Box>
          )}
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
        display: { xs: 'block', md: 'none' },
        '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240 },
      }}
    >
      {drawer}
    </Drawer>
    </>
  );
}

