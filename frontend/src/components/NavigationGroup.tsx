import React, { useState } from "react";
import { Button, Menu, MenuItem, ListItemIcon, ListItemText, Chip } from "@mui/material";
import { ExpandMore, CheckCircle as Check } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";

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
  currentPath,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const navigate = useNavigate();
  const open = Boolean(anchorEl);

  const isActive = items.some((item) => {
    if (item.path === currentPath) return true;
    // Check if current path starts with any item path (for nested routes)
    return currentPath.startsWith(item.path + "/");
  });

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
        color={isActive ? "primary" : "inherit"}
        sx={{
          textTransform: "none",
          fontWeight: isActive ? 600 : 400,
          "&:hover": {
            backgroundColor: "action.hover",
          },
        }}
      >
        {label}
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
        PaperProps={{
          sx: { minWidth: 220 },
        }}
      >
        {items.map((item) => {
          const itemIsActive = currentPath === item.path || currentPath.startsWith(item.path + "/");

          // Handle icon: can be a React element (JSX) or a component type
          const renderIcon = () => {
            if (!item.icon) return null;

            // If it's already a React element (JSX), render it directly
            if (React.isValidElement(item.icon)) {
              return (
                <ListItemIcon sx={{ minWidth: 40 }}>
                  {React.cloneElement(item.icon, { fontSize: "small" })}
                </ListItemIcon>
              );
            }

            // If it's a component type, use it as a component
            const IconComponent = item.icon as React.ElementType;
            return (
              <ListItemIcon sx={{ minWidth: 40 }}>
                <IconComponent fontSize="small" />
              </ListItemIcon>
            );
          };

          return (
            <MenuItem
              key={item.path}
              onClick={() => handleItemClick(item.path)}
              selected={itemIsActive}
              sx={{
                minWidth: 200,
                "&.Mui-selected": {
                  backgroundColor: "action.selected",
                  "&:hover": {
                    backgroundColor: "action.selected",
                  },
                },
              }}
            >
              {renderIcon()}
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontWeight: itemIsActive ? 600 : 400,
                }}
              />
              {itemIsActive && <Check fontSize="small" color="primary" />}
              {item.badge && (
                <Chip label={item.badge} size="small" color="primary" sx={{ ml: 1 }} />
              )}
            </MenuItem>
          );
        })}
      </Menu>
    </>
  );
};
