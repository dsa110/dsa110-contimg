import React from "react";
import { Table, TableContainer, TableRow, Paper } from "@mui/material";
import { alpha } from "@mui/material/styles";

interface EnhancedTableProps {
  children: React.ReactNode;
  stickyHeader?: boolean;
  size?: "small" | "medium";
}

/**
 * Enhanced Table Container with hover effects and alternating rows
 */
export const EnhancedTable: React.FC<EnhancedTableProps> = ({
  children,
  stickyHeader = false,
  size = "medium",
}) => {
  return (
    <TableContainer
      component={Paper}
      sx={{
        "& .MuiTable-root": {
          "& .MuiTableHead-root .MuiTableRow-root": {
            backgroundColor: "background.paper",
            "& .MuiTableCell-head": {
              fontWeight: 600,
              backgroundColor: "action.hover",
            },
          },
          "& .MuiTableBody-root .MuiTableRow-root": {
            "&:nth-of-type(even)": {
              backgroundColor: alpha("#fff", 0.02),
            },
            "&:hover": {
              backgroundColor: "action.hover",
              cursor: "pointer",
              transform: "translateX(2px)",
              boxShadow: `0 2px 4px ${alpha("#000", 0.1)}`,
            },
            transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
          },
        },
      }}
    >
      <Table stickyHeader={stickyHeader} size={size}>
        {children}
      </Table>
    </TableContainer>
  );
};

/**
 * Enhanced Table Row with hover effects
 */
export const EnhancedTableRow: React.FC<{
  children: React.ReactNode;
  onClick?: () => void;
  selected?: boolean;
}> = ({ children, onClick, selected }) => {
  return (
    <TableRow
      onClick={onClick}
      selected={selected}
      sx={{
        "&:hover": {
          backgroundColor: "action.hover",
          cursor: onClick ? "pointer" : "default",
          transform: "translateX(2px)",
          boxShadow: `0 2px 4px ${alpha("#000", 0.1)}`,
        },
        backgroundColor: selected ? "action.selected" : "transparent",
        transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      {children}
    </TableRow>
  );
};
