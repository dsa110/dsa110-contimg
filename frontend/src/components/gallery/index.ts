/**
 * Gallery Components
 *
 * Components for browsing, viewing, and managing astronomical images.
 */

// Main Gallery Grid
export { default as ImageGalleryGrid } from "./ImageGalleryGrid";
export type {
  ImageGalleryFilters,
  ImageGalleryImage,
  ImageGalleryGridProps,
} from "./ImageGalleryGrid";

// Image Viewer Modal
export { default as ImageViewerModal } from "./ImageViewerModal";
export type {
  ImageViewerModalProps,
  ImageViewerSettings,
  ColorMap,
  ScaleType,
} from "./ImageViewerModal";

// Image Metadata Panel
export { default as ImageMetadataPanel } from "./ImageMetadataPanel";
export type {
  ImageMetadata,
  ImageMetadataPanelProps,
  RelatedFile,
} from "./ImageMetadataPanel";

// CARTA Integration
export {
  CARTAIntegration,
  CARTAActions,
  CARTASAMPButton,
  useCARTAStatus,
  type CARTAIntegrationProps,
  type CARTAStatus,
  type CARTASAMPIntegrationProps,
  type CARTAActionsProps,
} from "./CARTAIntegration";

// Download Options
export {
  DownloadOptions,
  type DownloadOptionsProps,
  type DownloadConfig,
  type CutoutConfig,
  type ImageFormat,
  type CutoutUnit,
} from "./DownloadOptions";
