/**
 * Main Navigation Component
 */
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Dashboard,
  Image,
  TableChart,
  Public,
  ShowChart,
  Settings,
  PlayArrow,
} from '@mui/icons-material';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: Dashboard },
  { path: '/control', label: 'Control', icon: Settings },
  { path: '/streaming', label: 'Streaming', icon: PlayArrow },
  { path: '/mosaics', label: 'Mosaics', icon: Image },
  { path: '/sources', label: 'Sources', icon: TableChart },
  { path: '/sky', label: 'Sky View', icon: Public },
];

export default function Navigation() {
  const location = useLocation();

  return (
    <AppBar position="sticky" sx={{ bgcolor: '#1e1e1e' }}>
      <Toolbar>
        <ShowChart sx={{ mr: 2 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 0, mr: 4 }}>
          DSA-110
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

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
      </Toolbar>
    </AppBar>
  );
}

