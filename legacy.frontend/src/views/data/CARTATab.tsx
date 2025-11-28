/**
 * Data CARTA Tab
 *
 * Advanced radio astronomy visualization:
 * - CARTA iframe/WebSocket integration
 * - File browser for FITS selection
 */
import CARTAPage from "../../pages/CARTAPage";

export default function CARTATab() {
  // Reuse the existing CARTAPage with embedded mode
  return <CARTAPage embedded={true} />;
}
