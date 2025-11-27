/**
 * Data Sources Tab
 *
 * Source catalog with variability monitoring:
 * - Source search and filtering
 * - AG-Grid table view
 * - Light curve visualization
 */
import React from "react";
import SourceMonitoringPage from "../../pages/SourceMonitoringPage";

export default function SourcesTab() {
  // Reuse the existing SourceMonitoringPage component
  // It has its own search, filtering, and table functionality
  return <SourceMonitoringPage />;
}
