/**
 * Calibration QA Metrics Types
 *
 * TypeScript interfaces for calibration quality assessment.
 */

// =============================================================================
// Calibration Quality Types
// =============================================================================

export interface CalibrationQAMetrics {
  /** Calibration set/table name */
  cal_set_name: string;
  /** Calibrator source name */
  calibrator_name: string;
  /** MJD of calibration */
  cal_mjd: number;
  /** ISO timestamp */
  cal_timestamp: string;
  /** Signal-to-noise ratio */
  snr: number;
  /** Overall flagging percentage (0-100) */
  flagging_percent: number;
  /** Per-antenna flagging percentages */
  antenna_flagging?: Record<string, number>;
  /** Phase RMS in degrees */
  phase_rms_deg: number;
  /** Amplitude RMS (fractional) */
  amp_rms: number;
  /** Bandwidth smearing indicator (0-1) */
  bandwidth_smearing?: number;
  /** Time smearing indicator (0-1) */
  time_smearing?: number;
  /** Quality grade */
  quality_grade: "excellent" | "good" | "acceptable" | "poor" | "failed";
  /** Quality score (0-100) */
  quality_score: number;
  /** Issues detected */
  issues: CalibrationIssue[];
  /** Recommendations */
  recommendations: string[];
}

export interface CalibrationIssue {
  /** Issue severity */
  severity: "info" | "warning" | "critical";
  /** Issue category */
  category: "snr" | "flagging" | "phase" | "amplitude" | "rfi" | "other";
  /** Issue message */
  message: string;
  /** Affected antennas (if applicable) */
  affected_antennas?: string[];
}

export interface CalibrationComparison {
  /** Current calibration metrics */
  current: CalibrationQAMetrics;
  /** Previous/reference calibration */
  reference?: CalibrationQAMetrics;
  /** Comparison summary */
  comparison_summary?: {
    snr_change: number;
    snr_change_percent: number;
    flagging_change: number;
    phase_rms_change: number;
    quality_improved: boolean;
  };
}

// =============================================================================
// Photometry Types (extending existing)
// =============================================================================

export interface PhotometryResult {
  /** Peak flux density in Jy */
  peak_flux_jy: number;
  /** Integrated flux density in Jy */
  integrated_flux_jy: number;
  /** RMS noise in Jy */
  rms_jy: number;
  /** Signal-to-noise ratio */
  snr: number;
  /** Peak position RA (degrees) */
  peak_ra_deg?: number;
  /** Peak position Dec (degrees) */
  peak_dec_deg?: number;
  /** Position offset from expected (arcsec) */
  position_offset_arcsec?: number;
  /** Flux ratio (observed/expected) */
  flux_ratio?: number;
  /** Flux ratio uncertainty */
  flux_ratio_error?: number;
}

// =============================================================================
// Quality Thresholds
// =============================================================================

export interface QualityThresholds {
  /** Minimum acceptable SNR */
  min_snr: number;
  /** Maximum acceptable flagging percent */
  max_flagging_percent: number;
  /** Maximum acceptable phase RMS (degrees) */
  max_phase_rms_deg: number;
  /** Maximum acceptable amplitude RMS */
  max_amp_rms: number;
  /** Maximum acceptable position offset (arcsec) */
  max_position_offset_arcsec: number;
  /** Minimum acceptable flux ratio */
  min_flux_ratio: number;
  /** Maximum acceptable flux ratio */
  max_flux_ratio: number;
}

export const DEFAULT_QUALITY_THRESHOLDS: QualityThresholds = {
  min_snr: 10,
  max_flagging_percent: 30,
  max_phase_rms_deg: 30,
  max_amp_rms: 0.1,
  max_position_offset_arcsec: 10,
  min_flux_ratio: 0.8,
  max_flux_ratio: 1.2,
};
