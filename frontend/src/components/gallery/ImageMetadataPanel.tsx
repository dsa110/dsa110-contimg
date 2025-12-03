/**
 * Image Metadata Panel Component
 *
 * Displays comprehensive metadata for a selected image including:
 * - Header information (coordinates, frequency, beam parameters)
 * - Quality metrics (RMS noise, dynamic range, beam efficiency)
 * - Processing parameters (pipeline version, calibration status)
 * - Related files and links
 */

import { useMemo } from "react";
import type { QAGrade } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ImageMetadata {
  id: string;
  path: string;

  // WCS / Pointing
  pointing_ra_deg?: number | null;
  pointing_dec_deg?: number | null;
  reference_frequency_hz?: number | null;
  bandwidth_hz?: number | null;
  integration_time_s?: number | null;

  // Beam Parameters
  beam_major_arcsec?: number | null;
  beam_minor_arcsec?: number | null;
  beam_pa_deg?: number | null;

  // Image Properties
  pixel_scale_arcsec?: number | null;
  image_size_x?: number | null;
  image_size_y?: number | null;

  // Quality Metrics
  qa_grade?: QAGrade;
  rms_noise_jy?: number | null;
  dynamic_range?: number | null;
  peak_flux_jy?: number | null;
  beam_efficiency?: number | null;
  sidelobe_ratio?: number | null;

  // Processing Info
  pipeline_version?: string | null;
  calibration_id?: string | null;
  ms_id?: string | null;
  processing_time_s?: number | null;
  created_at?: string | null;
  modified_at?: string | null;

  // File Info
  size_bytes?: number | null;
  checksum?: string | null;
  format?: string | null;

  // Related Files
  related_files?: RelatedFile[];
}

export interface RelatedFile {
  id: string;
  type:
    | "psf"
    | "residual"
    | "model"
    | "weights"
    | "primary_beam"
    | "mask"
    | "catalog";
  path: string;
  description?: string;
}

export interface ImageMetadataPanelProps {
  /** Image metadata to display */
  metadata: ImageMetadata;
  /** Whether to show in compact mode */
  compact?: boolean;
  /** Callback when a related file is clicked */
  onRelatedFileClick?: (file: RelatedFile) => void;
  /** Callback when MS link is clicked */
  onMsClick?: (msId: string) => void;
  /** Callback when calibration link is clicked */
  onCalibrationClick?: (calibrationId: string) => void;
  /** Additional CSS class */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

/**
 * Format right ascension in HMS
 */
function formatRA(deg: number): string {
  const hours = deg / 15;
  const h = Math.floor(hours);
  const m = Math.floor((hours - h) * 60);
  const s = ((hours - h) * 60 - m) * 60;
  return `${h.toString().padStart(2, "0")}h ${m
    .toString()
    .padStart(2, "0")}m ${s.toFixed(2).padStart(5, "0")}s`;
}

/**
 * Format declination in DMS
 */
function formatDec(deg: number): string {
  const sign = deg >= 0 ? "+" : "-";
  const absDeg = Math.abs(deg);
  const d = Math.floor(absDeg);
  const m = Math.floor((absDeg - d) * 60);
  const s = ((absDeg - d) * 60 - m) * 60;
  return `${sign}${d.toString().padStart(2, "0")}° ${m
    .toString()
    .padStart(2, "0")}' ${s.toFixed(1).padStart(4, "0")}"`;
}

/**
 * Format frequency for display
 */
function formatFrequency(hz: number): string {
  if (hz >= 1e9) {
    return `${(hz / 1e9).toFixed(3)} GHz`;
  } else if (hz >= 1e6) {
    return `${(hz / 1e6).toFixed(3)} MHz`;
  } else if (hz >= 1e3) {
    return `${(hz / 1e3).toFixed(3)} kHz`;
  }
  return `${hz.toFixed(1)} Hz`;
}

/**
 * Format bandwidth for display
 */
function formatBandwidth(hz: number): string {
  if (hz >= 1e9) {
    return `${(hz / 1e9).toFixed(2)} GHz`;
  } else if (hz >= 1e6) {
    return `${(hz / 1e6).toFixed(2)} MHz`;
  } else if (hz >= 1e3) {
    return `${(hz / 1e3).toFixed(2)} kHz`;
  }
  return `${hz.toFixed(0)} Hz`;
}

/**
 * Format flux in appropriate units
 */
function formatFlux(jy: number): string {
  if (Math.abs(jy) >= 1) {
    return `${jy.toFixed(3)} Jy`;
  } else if (Math.abs(jy) >= 1e-3) {
    return `${(jy * 1e3).toFixed(3)} mJy`;
  } else if (Math.abs(jy) >= 1e-6) {
    return `${(jy * 1e6).toFixed(2)} µJy`;
  }
  return `${(jy * 1e9).toFixed(2)} nJy`;
}

/**
 * Format file size in human-readable form
 */
function formatFileSize(bytes: number): string {
  if (bytes >= 1e12) {
    return `${(bytes / 1e12).toFixed(2)} TB`;
  } else if (bytes >= 1e9) {
    return `${(bytes / 1e9).toFixed(2)} GB`;
  } else if (bytes >= 1e6) {
    return `${(bytes / 1e6).toFixed(2)} MB`;
  } else if (bytes >= 1e3) {
    return `${(bytes / 1e3).toFixed(2)} KB`;
  }
  return `${bytes} B`;
}

/**
 * Format duration in human-readable form
 */
function formatDuration(seconds: number): string {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  } else if (seconds >= 60) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s}s`;
  }
  return `${seconds.toFixed(1)}s`;
}

/**
 * Format date for display
 */
function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Get QA grade display color
 */
function getQAGradeColor(grade: QAGrade): string {
  switch (grade) {
    case "good":
      return "text-green-600 bg-green-100";
    case "warn":
      return "text-yellow-600 bg-yellow-100";
    case "fail":
      return "text-red-600 bg-red-100";
    default:
      return "text-gray-600 bg-gray-100";
  }
}

/**
 * Get related file type label
 */
function getRelatedFileLabel(type: RelatedFile["type"]): string {
  switch (type) {
    case "psf":
      return "PSF";
    case "residual":
      return "Residual";
    case "model":
      return "Model";
    case "weights":
      return "Weights";
    case "primary_beam":
      return "Primary Beam";
    case "mask":
      return "Mask";
    case "catalog":
      return "Source Catalog";
    default:
      return type;
  }
}

// ---------------------------------------------------------------------------
// Sub-Components
// ---------------------------------------------------------------------------

interface MetadataRowProps {
  label: string;
  value: React.ReactNode;
  compact?: boolean;
}

function MetadataRow({ label, value, compact }: MetadataRowProps) {
  if (value === null || value === undefined) {
    return null;
  }

  if (compact) {
    return (
      <div className="flex justify-between items-center py-1 border-b border-gray-100 last:border-b-0">
        <span className="text-xs text-gray-500">{label}</span>
        <span className="text-xs font-medium text-gray-900">{value}</span>
      </div>
    );
  }

  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-100 last:border-b-0">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

interface MetadataSectionProps {
  title: string;
  children: React.ReactNode;
  compact?: boolean;
}

function MetadataSection({ title, children, compact }: MetadataSectionProps) {
  return (
    <div className={compact ? "mb-3" : "mb-4"}>
      <h4
        className={`font-semibold text-gray-800 mb-2 ${
          compact ? "text-xs" : "text-sm"
        }`}
      >
        {title}
      </h4>
      <div className="space-y-0">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function ImageMetadataPanel({
  metadata,
  compact = false,
  onRelatedFileClick,
  onMsClick,
  onCalibrationClick,
  className = "",
}: ImageMetadataPanelProps) {
  // Compute derived values
  const computedValues = useMemo(() => {
    return {
      hasCoordinates:
        metadata.pointing_ra_deg != null && metadata.pointing_dec_deg != null,
      hasBeam:
        metadata.beam_major_arcsec != null &&
        metadata.beam_minor_arcsec != null,
      hasQuality:
        metadata.rms_noise_jy != null || metadata.dynamic_range != null,
      hasProcessing:
        metadata.pipeline_version != null || metadata.ms_id != null,
      hasRelatedFiles:
        metadata.related_files && metadata.related_files.length > 0,
    };
  }, [metadata]);

  return (
    <div
      className={`bg-white rounded-lg shadow-sm border border-gray-200 ${
        compact ? "p-3" : "p-4"
      } ${className}`}
      data-testid="image-metadata-panel"
    >
      {/* Header with QA Grade */}
      <div className="flex items-center justify-between mb-4">
        <h3
          className={`font-bold text-gray-900 ${
            compact ? "text-sm" : "text-base"
          }`}
        >
          Image Metadata
        </h3>
        {metadata.qa_grade && (
          <span
            className={`px-2 py-1 rounded text-xs font-bold ${getQAGradeColor(
              metadata.qa_grade
            )}`}
            data-testid="qa-grade-badge"
          >
            Grade: {metadata.qa_grade}
          </span>
        )}
      </div>

      {/* Coordinates Section */}
      {computedValues.hasCoordinates && (
        <MetadataSection title="Coordinates" compact={compact}>
          {metadata.pointing_ra_deg != null && (
            <MetadataRow
              label="RA"
              value={formatRA(metadata.pointing_ra_deg)}
              compact={compact}
            />
          )}
          {metadata.pointing_dec_deg != null && (
            <MetadataRow
              label="Dec"
              value={formatDec(metadata.pointing_dec_deg)}
              compact={compact}
            />
          )}
          {metadata.reference_frequency_hz != null && (
            <MetadataRow
              label="Frequency"
              value={formatFrequency(metadata.reference_frequency_hz)}
              compact={compact}
            />
          )}
          {metadata.bandwidth_hz != null && (
            <MetadataRow
              label="Bandwidth"
              value={formatBandwidth(metadata.bandwidth_hz)}
              compact={compact}
            />
          )}
        </MetadataSection>
      )}

      {/* Beam Parameters */}
      {computedValues.hasBeam && (
        <MetadataSection title="Beam" compact={compact}>
          {metadata.beam_major_arcsec != null && (
            <MetadataRow
              label="Major Axis"
              value={`${metadata.beam_major_arcsec.toFixed(2)}"`}
              compact={compact}
            />
          )}
          {metadata.beam_minor_arcsec != null && (
            <MetadataRow
              label="Minor Axis"
              value={`${metadata.beam_minor_arcsec.toFixed(2)}"`}
              compact={compact}
            />
          )}
          {metadata.beam_pa_deg != null && (
            <MetadataRow
              label="Position Angle"
              value={`${metadata.beam_pa_deg.toFixed(1)}°`}
              compact={compact}
            />
          )}
          {metadata.beam_efficiency != null && (
            <MetadataRow
              label="Beam Efficiency"
              value={`${(metadata.beam_efficiency * 100).toFixed(1)}%`}
              compact={compact}
            />
          )}
        </MetadataSection>
      )}

      {/* Image Properties */}
      {(metadata.pixel_scale_arcsec != null ||
        metadata.image_size_x != null) && (
        <MetadataSection title="Image Properties" compact={compact}>
          {metadata.pixel_scale_arcsec != null && (
            <MetadataRow
              label="Pixel Scale"
              value={`${metadata.pixel_scale_arcsec.toFixed(3)}"/px`}
              compact={compact}
            />
          )}
          {metadata.image_size_x != null && metadata.image_size_y != null && (
            <MetadataRow
              label="Image Size"
              value={`${metadata.image_size_x} × ${metadata.image_size_y} px`}
              compact={compact}
            />
          )}
          {metadata.integration_time_s != null && (
            <MetadataRow
              label="Integration Time"
              value={formatDuration(metadata.integration_time_s)}
              compact={compact}
            />
          )}
        </MetadataSection>
      )}

      {/* Quality Metrics */}
      {computedValues.hasQuality && (
        <MetadataSection title="Quality Metrics" compact={compact}>
          {metadata.rms_noise_jy != null && (
            <MetadataRow
              label="RMS Noise"
              value={formatFlux(metadata.rms_noise_jy)}
              compact={compact}
            />
          )}
          {metadata.peak_flux_jy != null && (
            <MetadataRow
              label="Peak Flux"
              value={formatFlux(metadata.peak_flux_jy)}
              compact={compact}
            />
          )}
          {metadata.dynamic_range != null && (
            <MetadataRow
              label="Dynamic Range"
              value={metadata.dynamic_range.toLocaleString()}
              compact={compact}
            />
          )}
          {metadata.sidelobe_ratio != null && (
            <MetadataRow
              label="Sidelobe Ratio"
              value={`${(metadata.sidelobe_ratio * 100).toFixed(1)}%`}
              compact={compact}
            />
          )}
        </MetadataSection>
      )}

      {/* Processing Information */}
      {computedValues.hasProcessing && (
        <MetadataSection title="Processing" compact={compact}>
          {metadata.pipeline_version && (
            <MetadataRow
              label="Pipeline Version"
              value={metadata.pipeline_version}
              compact={compact}
            />
          )}
          {metadata.ms_id && (
            <MetadataRow
              label="Source MS"
              value={
                onMsClick ? (
                  <button
                    onClick={() => onMsClick(metadata.ms_id!)}
                    className="text-blue-600 hover:text-blue-800 hover:underline"
                    data-testid="ms-link"
                  >
                    View MS
                  </button>
                ) : (
                  metadata.ms_id
                )
              }
              compact={compact}
            />
          )}
          {metadata.calibration_id && (
            <MetadataRow
              label="Calibration"
              value={
                onCalibrationClick ? (
                  <button
                    onClick={() => onCalibrationClick(metadata.calibration_id!)}
                    className="text-blue-600 hover:text-blue-800 hover:underline"
                    data-testid="calibration-link"
                  >
                    View Calibration
                  </button>
                ) : (
                  metadata.calibration_id
                )
              }
              compact={compact}
            />
          )}
          {metadata.processing_time_s != null && (
            <MetadataRow
              label="Processing Time"
              value={formatDuration(metadata.processing_time_s)}
              compact={compact}
            />
          )}
        </MetadataSection>
      )}

      {/* File Information */}
      <MetadataSection title="File Information" compact={compact}>
        <MetadataRow
          label="Path"
          value={
            <span
              className="font-mono text-xs truncate max-w-[200px] block"
              title={metadata.path}
            >
              {metadata.path.split("/").pop()}
            </span>
          }
          compact={compact}
        />
        {metadata.size_bytes != null && (
          <MetadataRow
            label="Size"
            value={formatFileSize(metadata.size_bytes)}
            compact={compact}
          />
        )}
        {metadata.format && (
          <MetadataRow
            label="Format"
            value={metadata.format}
            compact={compact}
          />
        )}
        {metadata.checksum && (
          <MetadataRow
            label="Checksum"
            value={
              <span
                className="font-mono text-xs truncate max-w-[120px] block"
                title={metadata.checksum}
              >
                {metadata.checksum.slice(0, 12)}...
              </span>
            }
            compact={compact}
          />
        )}
        {metadata.created_at && (
          <MetadataRow
            label="Created"
            value={formatDate(metadata.created_at)}
            compact={compact}
          />
        )}
        {metadata.modified_at && (
          <MetadataRow
            label="Modified"
            value={formatDate(metadata.modified_at)}
            compact={compact}
          />
        )}
      </MetadataSection>

      {/* Related Files */}
      {computedValues.hasRelatedFiles && (
        <MetadataSection title="Related Files" compact={compact}>
          <div className="flex flex-wrap gap-2 mt-1">
            {metadata.related_files!.map((file) => (
              <button
                key={file.id}
                onClick={() => onRelatedFileClick?.(file)}
                className={`
                  px-2 py-1 rounded text-xs font-medium
                  bg-gray-100 text-gray-700
                  hover:bg-blue-100 hover:text-blue-700
                  transition-colors
                  ${onRelatedFileClick ? "cursor-pointer" : "cursor-default"}
                `}
                title={file.description ?? file.path}
                data-testid={`related-file-${file.type}`}
              >
                {getRelatedFileLabel(file.type)}
              </button>
            ))}
          </div>
        </MetadataSection>
      )}
    </div>
  );
}

export default ImageMetadataPanel;
