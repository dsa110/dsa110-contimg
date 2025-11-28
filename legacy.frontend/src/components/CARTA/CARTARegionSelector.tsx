/**
 * CARTA Region Selector Component
 *
 * Provides UI for selecting and creating different region types.
 */

import { Box, ButtonGroup, Button, Tooltip } from "@mui/material";
import {
  CropFree as RectangleIcon,
  RadioButtonUnchecked as EllipseIcon,
  ChangeHistory as PolygonIcon,
  Adjust as PointIcon,
  Lens as AnnulusIcon,
} from "@mui/icons-material";
import { RegionType } from "../../services/cartaProtobuf";

interface CARTARegionSelectorProps {
  selectedType: RegionType;
  onTypeChange: (type: RegionType) => void;
  disabled?: boolean;
}

export default function CARTARegionSelector({
  selectedType,
  onTypeChange,
  disabled = false,
}: CARTARegionSelectorProps) {
  const regionTypes = [
    { type: RegionType.POINT, label: "Point", icon: PointIcon },
    { type: RegionType.RECTANGLE, label: "Rectangle", icon: RectangleIcon },
    { type: RegionType.ELLIPSE, label: "Ellipse", icon: EllipseIcon },
    { type: RegionType.POLYGON, label: "Polygon", icon: PolygonIcon },
    { type: RegionType.ANNULUS, label: "Annulus", icon: AnnulusIcon },
  ];

  return (
    <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
      <ButtonGroup size="small" disabled={disabled}>
        {regionTypes.map(({ type, label, icon: Icon }) => (
          <Tooltip key={type} title={label}>
            <Button
              variant={selectedType === type ? "contained" : "outlined"}
              onClick={() => onTypeChange(type)}
              sx={{ minWidth: 40 }}
            >
              <Icon />
            </Button>
          </Tooltip>
        ))}
      </ButtonGroup>
    </Box>
  );
}
