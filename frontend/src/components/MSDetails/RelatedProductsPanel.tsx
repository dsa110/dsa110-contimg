/**
 * Related Products Panel
 * Displays products derived from the selected Measurement Set
 */
import { Alert, Typography } from "@mui/material";

interface RelatedProductsPanelProps {
  msPath: string;
}

export function RelatedProductsPanel({ msPath }: RelatedProductsPanelProps) {
  return (
    <>
      <Typography variant="h6" gutterBottom>
        Related Products
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Products derived from this Measurement Set
      </Typography>
      {msPath ? (
        <Alert severity="info">
          Related products (calibration tables, images, etc.) would be listed here. Navigate to the
          Data Browser to see all related products.
        </Alert>
      ) : (
        <Alert severity="info">Select an MS to view related products</Alert>
      )}
    </>
  );
}
