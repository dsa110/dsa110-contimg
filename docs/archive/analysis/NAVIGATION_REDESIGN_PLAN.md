# Navigation Bar Redesign Plan

**Date:** 2025-11-13  
**Issue:** 14 navigation links in single row - too busy, barely fits  
**Goal:** User-friendly, consolidated navigation design

---

## Current State Analysis

### Current Navigation Links (14 total)

1. Dashboard
2. Control
3. Streaming
4. Data
5. QA Visualization
6. Mosaics
7. Sources
8. Sky View
9. Observing
10. Health
11. Operations
12. Pipeline
13. Events
14. Cache

### Problems

- Too many links for comfortable scanning
- No visual grouping or hierarchy
- Will wrap on smaller screens
- Cognitive overload
- No clear organization by function

---

## Proposed Navigation Structure

### Option 1: Grouped Navigation with Dropdowns (Recommended)

**Primary Navigation (5 items):**

1. **Dashboard** (always visible)
2. **Pipeline** (dropdown: Pipeline, Operations, Events)
3. **Data** (dropdown: Data Browser, Mosaics, Sources, Sky View)
4. **Control** (dropdown: Control, Streaming, Observing)
5. **Analysis** (dropdown: QA Visualization, Health, Cache)

**Visual Layout:**

```
[Dashboard] [Pipeline ▼] [Data ▼] [Control ▼] [Analysis ▼] [⚙️]
```

**Dropdown Contents:**

**Pipeline Menu:**

- Pipeline Monitoring
- Operations (DLQ, Circuit Breakers)
- Events

**Data Menu:**

- Data Browser
- Mosaics
- Sources
- Sky View

**Control Menu:**

- Control Panel
- Streaming Service
- Observing

**Analysis Menu:**

- QA Visualization
- System Health
- Cache Statistics

---

### Option 2: Sidebar Navigation (Alternative)

**Left Sidebar with Collapsible Sections:**

```
┌─────────────────────┐
│  DSA-110            │
├─────────────────────┤
│ 📊 Dashboard        │
├─────────────────────┤
│ 🔄 Pipeline         │
│   • Monitoring      │
│   • Operations      │
│   • Events          │
├─────────────────────┤
│ 💾 Data             │
│   • Browser         │
│   • Mosaics         │
│   • Sources         │
│   • Sky View        │
├─────────────────────┤
│ ⚙️ Control          │
│   • Control Panel   │
│   • Streaming       │
│   • Observing       │
├─────────────────────┤
│ 📈 Analysis         │
│   • QA              │
│   • Health          │
│   • Cache           │
└─────────────────────┘
```

---

### Option 3: Hybrid - Primary + Secondary Navigation

**Top Bar (5 primary items):**

- Dashboard
- Pipeline
- Data
- Control
- Analysis

**Secondary Navigation (below breadcrumbs):**

- Quick links to most-used pages
- Recent pages
- Favorites

---

## Recommended Solution: Option 1 (Grouped Navigation)

### Rationale

- Reduces visual clutter (14 → 5 items)
- Maintains horizontal layout (familiar)
- Groups related functionality
- Easy to scan and understand
- Works well on all screen sizes
- Can show active section in dropdown

### Implementation Plan

#### 1. Create NavigationGroup Component

```typescript
// frontend/src/components/NavigationGroup.tsx
import React, { useState } from 'react';
import {
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Chip
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import { ExpandMore, Check } from '@mui/icons-material';

interface NavItem {
  label: string;
  path: string;
  icon?: React.ReactNode;
  badge?: string | number;
}

interface NavigationGroupProps {
  label: string;
  icon?: React.ReactNode;
  items: NavItem[];
  currentPath: string;
}

export const NavigationGroup: React.FC<NavigationGroupProps> = ({
  label,
  icon,
  items,
  currentPath
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const navigate = useNavigate();
  const open = Boolean(anchorEl);

  const isActive = items.some(item => currentPath.startsWith(item.path));

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleItemClick = (path: string) => {
    navigate(path);
    handleClose();
  };

  return (
    <>
      <Button
        onClick={handleClick}
        startIcon={icon}
        endIcon={<ExpandMore />}
        color={isActive ? 'primary' : 'inherit'}
        sx={{
          textTransform: 'none',
          fontWeight: isActive ? 600 : 400,
          '&:hover': {
            backgroundColor: 'action.hover'
          }
        }}
      >
        {label}
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
      >
        {items.map((item) => {
          const itemIsActive = currentPath === item.path;
          return (
            <MenuItem
              key={item.path}
              onClick={() => handleItemClick(item.path)}
              selected={itemIsActive}
              sx={{
                minWidth: 200,
                '&.Mui-selected': {
                  backgroundColor: 'action.selected',
                  '&:hover': {
                    backgroundColor: 'action.selected',
                  }
                }
              }}
            >
              {item.icon && (
                <ListItemIcon sx={{ minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
              )}
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontWeight: itemIsActive ? 600 : 400
                }}
              />
              {itemIsActive && (
                <Check fontSize="small" color="primary" />
              )}
              {item.badge && (
                <Chip
                  label={item.badge}
                  size="small"
                  color="primary"
                  sx={{ ml: 1 }}
                />
              )}
            </MenuItem>
          );
        })}
      </Menu>
    </>
  );
};
```

#### 2. Update Navigation Component

```typescript
// frontend/src/components/Navigation.tsx
import React from 'react';
import {
  AppBar,
  Toolbar,
  Box,
  IconButton,
  Chip,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  AccountTree as PipelineIcon,
  Storage as DataIcon,
  Settings as ControlIcon,
  Assessment as AnalysisIcon,
  Keyboard as KeyboardIcon
} from '@mui/icons-material';
import { useLocation } from 'react-router-dom';
import { useWorkflow } from '../contexts/WorkflowContext';
import { useCommandPalette } from '../hooks/useCommandPalette';
import { NavigationGroup } from './NavigationGroup';
import CommandPalette from './CommandPalette';
import { Link } from 'react-router-dom';

const navigationGroups = {
  pipeline: {
    label: 'Pipeline',
    icon: <PipelineIcon />,
    items: [
      { label: 'Pipeline Monitoring', path: '/pipeline', icon: <PipelineIcon /> },
      { label: 'Operations', path: '/operations', icon: <SettingsIcon /> },
      { label: 'Events', path: '/events', icon: <EventNoteIcon /> },
    ]
  },
  data: {
    label: 'Data',
    icon: <DataIcon />,
    items: [
      { label: 'Data Browser', path: '/data', icon: <StorageIcon /> },
      { label: 'Mosaics', path: '/mosaics', icon: <GridOnIcon /> },
      { label: 'Sources', path: '/sources', icon: <TableChartIcon /> },
      { label: 'Sky View', path: '/sky', icon: <PublicIcon /> },
    ]
  },
  control: {
    label: 'Control',
    icon: <ControlIcon />,
    items: [
      { label: 'Control Panel', path: '/control', icon: <ControlIcon /> },
      { label: 'Streaming Service', path: '/streaming', icon: <PlayArrowIcon /> },
      { label: 'Observing', path: '/observing', icon: <VisibilityIcon /> },
    ]
  },
  analysis: {
    label: 'Analysis',
    icon: <AnalysisIcon />,
    items: [
      { label: 'QA Visualization', path: '/qa', icon: <AssessmentIcon /> },
      { label: 'System Health', path: '/health', icon: <HealthIcon /> },
      { label: 'Cache Statistics', path: '/cache', icon: <CachedIcon /> },
    ]
  }
};

export default function Navigation() {
  const location = useLocation();
  const { currentWorkflow } = useWorkflow();
  const { open, setOpen } = useCommandPalette();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const isDashboard = location.pathname === '/dashboard';

  return (
    <>
      <AppBar position="static" elevation={1}>
        <Toolbar>
          {/* Logo */}
          <Box sx={{ display: 'flex', alignItems: 'center', mr: 3 }}>
            <Link to="/dashboard" style={{ textDecoration: 'none', color: 'inherit' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendingUpIcon />
                <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                  DSA-110
                </Typography>
              </Box>
            </Link>
          </Box>

          {/* Primary Navigation */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
            {/* Dashboard - Always visible */}
            <Button
              component={Link}
              to="/dashboard"
              startIcon={<DashboardIcon />}
              color={isDashboard ? 'primary' : 'inherit'}
              sx={{
                textTransform: 'none',
                fontWeight: isDashboard ? 600 : 400,
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

          {/* Right Side Actions */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {/* Workflow Chip */}
            {currentWorkflow && (
              <Chip
                label={currentWorkflow}
                size="small"
                sx={{ textTransform: 'capitalize' }}
              />
            )}

            {/* Command Palette */}
            <IconButton
              onClick={() => setOpen(true)}
              color="inherit"
              title="Open command palette (Cmd+K / Ctrl+K)"
            >
              <KeyboardIcon />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      <CommandPalette open={open} onClose={() => setOpen(false)} />
    </>
  );
}
```

#### 3. Add Badge Support for Notifications

```typescript
// Add badge counts to navigation items
const navigationGroups = {
  pipeline: {
    // ...
    items: [
      {
        label: 'Operations',
        path: '/operations',
        icon: <SettingsIcon />,
        badge: pendingDLQCount > 0 ? pendingDLQCount : undefined
      },
      // ...
    ]
  },
  // ...
};
```

---

## Additional Improvements

### 1. Keyboard Shortcuts

- Add keyboard shortcuts for each main section
- `Cmd/Ctrl + 1` = Dashboard
- `Cmd/Ctrl + 2` = Pipeline
- `Cmd/Ctrl + 3` = Data
- etc.

### 2. Recent Pages

- Show recently visited pages in dropdown
- Add "Recently Visited" section at top of each menu

### 3. Favorites/Bookmarks

- Allow users to pin frequently used pages
- Show pinned items at top of dropdown

### 4. Search Integration

- Command palette already handles this
- Ensure all pages are searchable

### 5. Mobile Responsiveness

- On mobile, show hamburger menu
- Collapse all navigation into drawer

---

## Mobile Navigation Design

```typescript
// Mobile Navigation Drawer
const MobileNavigation = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <IconButton onClick={() => setDrawerOpen(true)}>
        <MenuIcon />
      </IconButton>

      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        <Box sx={{ width: 280, pt: 2 }}>
          <List>
            <ListItem>
              <ListItemIcon><DashboardIcon /></ListItemIcon>
              <ListItemText primary="Dashboard" />
            </ListItem>

            <Divider />

            <ListSubheader>Pipeline</ListSubheader>
            {navigationGroups.pipeline.items.map(item => (
              <ListItem
                key={item.path}
                component={Link}
                to={item.path}
                onClick={() => setDrawerOpen(false)}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItem>
            ))}

            {/* Repeat for other groups */}
          </List>
        </Box>
      </Drawer>
    </>
  );
};
```

---

## Consolidation Opportunities

### Pages That Could Be Combined

1. **Operations + Events**
   - Both are system monitoring/debugging
   - Could be tabs within a single "System" page
   - **Recommendation:** Keep separate but in same menu group

2. **Health + Cache**
   - Both are system diagnostics
   - Could be combined into "System Diagnostics"
   - **Recommendation:** Keep separate but in same menu group

3. **Mosaics + Sky View**
   - Both are visualization of sky data
   - Could be combined with tabs
   - **Recommendation:** Keep separate for now, but consider combining later

4. **Streaming + Observing**
   - Both are control/monitoring of observation
   - Could be combined
   - **Recommendation:** Keep separate - different purposes

### Pages That Could Be Removed/Deprecated

- None identified - all pages serve distinct purposes

---

## Visual Design Improvements

### 1. Active State Indication

- Highlight active section in dropdown
- Show checkmark next to active item
- Bold text for active item

### 2. Hover States

- Smooth transitions
- Clear visual feedback

### 3. Icons

- Consistent icon style
- Meaningful icons for each section
- Color coding for different groups

### 4. Spacing

- Better spacing between items
- Consistent padding

---

## Implementation Steps

### Phase 1: Basic Grouped Navigation (4-6 hours)

1. Create NavigationGroup component
2. Update Navigation component
3. Test all navigation paths
4. Update routing if needed

### Phase 2: Enhancements (3-4 hours)

1. Add badge support
2. Add keyboard shortcuts
3. Improve active state indication
4. Add hover effects

### Phase 3: Mobile Support (2-3 hours)

1. Create mobile drawer
2. Add responsive breakpoints
3. Test on mobile devices

### Phase 4: Advanced Features (4-6 hours)

1. Recent pages tracking
2. Favorites/bookmarks
3. Search integration improvements

**Total Estimated Time:** 13-19 hours

---

## Success Metrics

- Navigation bar fits comfortably on all screen sizes
- Users can find pages in 2 clicks or less
- Reduced cognitive load (5 items vs 14)
- Improved user satisfaction
- Faster navigation times

---

## Alternative: Sidebar Navigation

If the grouped dropdown approach doesn't work well, consider a sidebar:

### Benefits

- More space for labels
- Always visible navigation
- Better for power users
- Can show more context

### Drawbacks

- Takes up horizontal space
- Less familiar pattern
- May feel cluttered on small screens

### Implementation

- Collapsible sidebar
- Icon-only mode
- Responsive (drawer on mobile)

---

## Recommendation

**Go with Option 1 (Grouped Navigation with Dropdowns)** because:

1. Reduces items from 14 to 5
2. Maintains familiar horizontal layout
3. Groups related functionality logically
4. Easy to implement
5. Works well on all screen sizes
6. Can be enhanced with badges, recent items, etc.

The navigation will be:

```
[Dashboard] [Pipeline ▼] [Data ▼] [Control ▼] [Analysis ▼] [Workflow] [⌨️]
```

This is much cleaner and more scannable than 14 individual links.
