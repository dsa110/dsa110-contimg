/**
 * Calibration Comparison Hook
 *
 * React Query hook for fetching and comparing calibration QA metrics.
 * Enables side-by-side comparison of calibration quality between two
 * calibration tables/sets.
 */

import { useQuery } from "@tanstack/react-query";
import apiClient from "../api/client";
import type {
  CalibrationQAMetrics,
  CalibrationComparison,
} from "../types/calibration";

const BASE_PATH = "/health/calibration";

// =============================================================================
// Query Keys
// =============================================================================

export const calibrationComparisonKeys = {
  all: ["calibration-comparison"] as const,
  qa: (calTablePath: string) =>
    [...calibrationComparisonKeys.all, "qa", calTablePath] as const,
  compare: (pathA: string, pathB: string) =>
    [...calibrationComparisonKeys.all, "compare", pathA, pathB] as const,
  recent: (calibratorName: string, limit?: number) =>
    [
      ...calibrationComparisonKeys.all,
      "recent",
      calibratorName,
      { limit },
    ] as const,
};

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetch QA metrics for a calibration table.
 */
export async function getCalibrationQA(
  calTablePath: string
): Promise<CalibrationQAMetrics> {
  const response = await apiClient.get<CalibrationQAMetrics>(
    `${BASE_PATH}/qa/${encodeURIComponent(calTablePath)}`
  );
  return response.data;
}

/**
 * Compare two calibration tables.
 * Returns metrics for both and a comparison summary.
 */
export async function compareCalibrations(
  pathA: string,
  pathB: string
): Promise<CalibrationComparison> {
  const response = await apiClient.get<CalibrationComparison>(
    `${BASE_PATH}/compare`,
    {
      params: {
        current_path: pathA,
        reference_path: pathB,
      },
    }
  );
  return response.data;
}

/**
 * Get recent calibration sets for a calibrator.
 * Useful for selecting a reference calibration to compare against.
 */
export async function getRecentCalibrations(
  calibratorName: string,
  limit = 10
): Promise<CalibrationQAMetrics[]> {
  const response = await apiClient.get<CalibrationQAMetrics[]>(
    `${BASE_PATH}/recent/${encodeURIComponent(calibratorName)}`,
    { params: { limit } }
  );
  return response.data;
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook to fetch calibration QA metrics for a single calibration table.
 *
 * @param calTablePath - Path to the calibration table
 * @param enabled - Whether to enable the query
 */
export function useCalibrationQA(calTablePath: string, enabled = true) {
  return useQuery({
    queryKey: calibrationComparisonKeys.qa(calTablePath),
    queryFn: () => getCalibrationQA(calTablePath),
    enabled: enabled && !!calTablePath,
    staleTime: 5 * 60 * 1000, // 5 minutes - calibration QA doesn't change often
  });
}

/**
 * Hook to compare two calibration tables.
 * Returns QA metrics for both tables and a comparison summary.
 *
 * @param pathA - Path to the first (current) calibration table
 * @param pathB - Path to the second (reference) calibration table
 * @param enabled - Whether to enable the query
 */
export function useCalibrationComparison(
  pathA: string,
  pathB: string,
  enabled = true
) {
  return useQuery({
    queryKey: calibrationComparisonKeys.compare(pathA, pathB),
    queryFn: () => compareCalibrations(pathA, pathB),
    enabled: enabled && !!pathA && !!pathB,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch recent calibrations for a calibrator.
 * Useful for populating a dropdown to select reference calibrations.
 *
 * @param calibratorName - Name of the calibrator
 * @param limit - Maximum number of recent calibrations to return
 * @param enabled - Whether to enable the query
 */
export function useRecentCalibrations(
  calibratorName: string,
  limit = 10,
  enabled = true
) {
  return useQuery({
    queryKey: calibrationComparisonKeys.recent(calibratorName, limit),
    queryFn: () => getRecentCalibrations(calibratorName, limit),
    enabled: enabled && !!calibratorName,
    staleTime: 2 * 60 * 1000, // 2 minutes - new calibrations may appear
  });
}

// =============================================================================
// Helper Types
// =============================================================================

export interface CalibrationComparisonResult {
  /** Current calibration metrics */
  current: CalibrationQAMetrics;
  /** Reference calibration metrics (if comparing) */
  reference?: CalibrationQAMetrics;
  /** Whether current is better than reference */
  isImproved?: boolean;
  /** Comparison deltas */
  deltas?: {
    snr: number;
    snrPercent: number;
    flagging: number;
    phaseRms: number;
    ampRms: number;
    qualityScore: number;
  };
}

/**
 * Calculate comparison deltas between two calibration sets.
 * Positive values indicate improvement (better current than reference).
 */
export function calculateComparisonDeltas(
  current: CalibrationQAMetrics,
  reference: CalibrationQAMetrics
): CalibrationComparisonResult["deltas"] {
  return {
    // Higher SNR is better
    snr: current.snr - reference.snr,
    snrPercent:
      reference.snr > 0
        ? ((current.snr - reference.snr) / reference.snr) * 100
        : 0,
    // Lower flagging is better (negate so positive = improvement)
    flagging: -(current.flagging_percent - reference.flagging_percent),
    // Lower phase RMS is better (negate so positive = improvement)
    phaseRms: -(current.phase_rms_deg - reference.phase_rms_deg),
    // Lower amp RMS is better (negate so positive = improvement)
    ampRms: -(current.amp_rms - reference.amp_rms),
    // Higher quality score is better
    qualityScore: current.quality_score - reference.quality_score,
  };
}

/**
 * Determine if current calibration is overall better than reference.
 */
export function isCalibrationImproved(
  current: CalibrationQAMetrics,
  reference: CalibrationQAMetrics
): boolean {
  // Simple heuristic: use quality score as primary indicator
  return current.quality_score > reference.quality_score;
}
