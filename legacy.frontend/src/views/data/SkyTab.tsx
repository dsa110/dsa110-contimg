/**
 * Data Sky View Tab
 *
 * Sky visualization with JS9:
 * - Image browser
 * - Sky viewer (JS9)
 * - Image controls and metadata
 * - Catalog overlays
 * - Region tools
 * - Analysis plugins
 */
import SkyViewPage from "../../pages/SkyViewPage";

export default function SkyTab() {
  // Reuse the existing SkyViewPage component
  // It has comprehensive JS9 integration and tools
  return <SkyViewPage />;
}
