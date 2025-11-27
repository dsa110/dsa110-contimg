/**
 * Pipeline Streaming Tab
 *
 * Real-time data ingest management:
 * - Streaming service status
 * - Queue statistics
 * - Resource usage
 * - Configuration
 */
import React from "react";
import StreamingPage from "../../pages/StreamingPage";

export default function StreamingTab() {
  // Reuse the existing StreamingPage component with embedded mode
  return <StreamingPage embedded={true} />;
}
