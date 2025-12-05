/**
 * Components Index
 *
 * Re-exports commonly used components from their respective modules.
 * For specialized components, import directly from their subdirectory.
 *
 * @example
 * ```tsx
 * // Common components
 * import { Card, Modal, LoadingSpinner } from '../components';
 *
 * // Specialized components (import from subdirectory)
 * import { FitsViewer } from '../components/fits';
 * import { SkyCoverageMap } from '../components/skymap';
 * ```
 */

// =============================================================================
// Common UI Components
// =============================================================================

export {
  Card,
  ConnectionStatus,
  CoordinateDisplay,
  ImageThumbnail,
  LoadingSpinner,
  Modal,
  PageSkeleton,
  Skeleton,
  QAMetrics,
  SortableTableHeader,
  useTableSort,
} from "./common";
export type {
  CardProps,
  CoordinateDisplayProps,
  ImageThumbnailProps,
  LoadingSpinnerProps,
  ModalProps,
  PageSkeletonProps,
  SkeletonProps,
  QAMetricsProps,
  SortableTableHeaderProps,
  SortDirection,
} from "./common";

// =============================================================================
// Error Handling
// =============================================================================

export {
  ErrorBoundary,
  WidgetErrorBoundary,
  AppErrorBoundary,
  SimpleErrorAlert,
} from "./errors";
export type {
  ErrorBoundaryProps,
  WidgetErrorBoundaryProps,
  SimpleErrorAlertProps,
} from "./errors";

// =============================================================================
// Layout
// =============================================================================

export { default as AppLayout } from "./layout/AppLayout";
export { default as ProtectedRoute } from "./layout/ProtectedRoute";

// =============================================================================
// Log Viewer
// =============================================================================

export { LogViewer } from "./logs";
export type { LogViewerProps } from "./logs";
