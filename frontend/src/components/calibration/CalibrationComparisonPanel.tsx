/**
 * Calibration Comparison Panel Component
 *
 * Allows side-by-side comparison of two calibration sets to help
 * astronomers identify quality differences and choose the best calibration.
 */

import React, { useMemo } from "react";
import type {
  CalibrationQAMetrics,
  CalibrationComparison,
} from "../../types/calibration";

// =============================================================================
// Types
// =============================================================================

export interface CalibrationComparisonPanelProps {
  /** First calibration set (e.g., current/new) */
  setA: CalibrationQAMetrics;
  /** Second calibration set (e.g., reference/old) */
  setB: CalibrationQAMetrics;
  /** Labels for the comparison */
  labels?: {
    setA: string;
    setB: string;
  };
  /** Show detailed metrics breakdown */
  showDetails?: boolean;
  /** Callback when user selects a preferred set */
  onSelectPreferred?: (selected: "A" | "B") => void;
  /** Additional CSS classes */
  className?: string;
}

interface MetricDelta {
  value: number;
  percent: number;
  improved: boolean;
}

interface ComparisonMetrics {
  snr: MetricDelta;
  flagging: MetricDelta;
  phaseRms: MetricDelta;
  ampRms: MetricDelta;
  qualityScore: MetricDelta;
  overallImproved: boolean;
  recommendation: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function calculateDelta(
  valueA: number,
  valueB: number,
  higherIsBetter: boolean
): MetricDelta {
  const diff = valueA - valueB;
  const percent = valueB !== 0 ? (diff / valueB) * 100 : diff > 0 ? 100 : -100;
  const improved = higherIsBetter ? diff > 0 : diff < 0;

  return {
    value: diff,
    percent,
    improved,
  };
}

function computeComparison(
  setA: CalibrationQAMetrics,
  setB: CalibrationQAMetrics
): ComparisonMetrics {
  const snr = calculateDelta(setA.snr, setB.snr, true);
  const flagging = calculateDelta(
    setA.flagging_percent,
    setB.flagging_percent,
    false
  );
  const phaseRms = calculateDelta(
    setA.phase_rms_deg,
    setB.phase_rms_deg,
    false
  );
  const ampRms = calculateDelta(setA.amp_rms, setB.amp_rms, false);
  const qualityScore = calculateDelta(
    setA.quality_score,
    setB.quality_score,
    true
  );

  // Weighted improvement assessment
  const improvements = [
    snr.improved ? 1 : -1,
    flagging.improved ? 1 : -1,
    phaseRms.improved ? 1 : -1,
    qualityScore.improved ? 2 : -2, // Double weight for overall score
  ];
  const overallScore = improvements.reduce((a, b) => a + b, 0);
  const overallImproved = overallScore > 0;

  // Generate recommendation
  let recommendation: string;
  if (Math.abs(qualityScore.percent) < 5) {
    recommendation = "Both calibrations are comparable in quality";
  } else if (overallImproved) {
    recommendation = `Set A shows ${Math.abs(qualityScore.percent).toFixed(
      0
    )}% improvement in overall quality`;
  } else {
    recommendation = `Set B shows ${Math.abs(qualityScore.percent).toFixed(
      0
    )}% better quality`;
  }

  return {
    snr,
    flagging,
    phaseRms,
    ampRms,
    qualityScore,
    overallImproved,
    recommendation,
  };
}

// =============================================================================
// Sub-components
// =============================================================================

const gradeColors: Record<CalibrationQAMetrics["quality_grade"], string> = {
  excellent:
    "text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30",
  good: "text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30",
  acceptable:
    "text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30",
  poor: "text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30",
  failed: "text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30",
};

function DeltaIndicator({
  delta,
  unit = "",
  precision = 1,
}: {
  delta: MetricDelta;
  unit?: string;
  precision?: number;
}) {
  const sign = delta.value >= 0 ? "+" : "";
  const color = delta.improved
    ? "text-green-600 dark:text-green-400"
    : delta.value === 0
    ? "text-gray-500"
    : "text-red-600 dark:text-red-400";
  const icon = delta.improved ? "↑" : delta.value === 0 ? "=" : "↓";

  return (
    <span className={`text-xs font-medium ${color}`}>
      {icon} {sign}
      {delta.value.toFixed(precision)}
      {unit} ({sign}
      {delta.percent.toFixed(0)}%)
    </span>
  );
}

function ComparisonRow({
  label,
  valueA,
  valueB,
  delta,
  unit = "",
  precision = 1,
}: {
  label: string;
  valueA: number;
  valueB: number;
  delta: MetricDelta;
  unit?: string;
  precision?: number;
}) {
  return (
    <div className="grid grid-cols-4 gap-4 py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <div className="text-sm text-gray-600 dark:text-gray-400">{label}</div>
      <div className="text-sm font-mono text-center">
        {valueA.toFixed(precision)}
        {unit}
      </div>
      <div className="text-sm font-mono text-center">
        {valueB.toFixed(precision)}
        {unit}
      </div>
      <div className="text-center">
        <DeltaIndicator delta={delta} unit={unit} precision={precision} />
      </div>
    </div>
  );
}

function CalSetSummary({
  metrics,
  label,
  isPreferred,
  onSelect,
}: {
  metrics: CalibrationQAMetrics;
  label: string;
  isPreferred?: boolean;
  onSelect?: () => void;
}) {
  return (
    <div
      className={`p-4 rounded-lg border-2 transition-colors ${
        isPreferred
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
          : "border-gray-200 dark:border-gray-700"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="font-medium text-gray-900 dark:text-gray-100">
            {label}
          </h4>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {metrics.cal_set_name}
          </p>
        </div>
        <span
          className={`px-2 py-1 text-xs font-medium rounded-full ${
            gradeColors[metrics.quality_grade]
          }`}
        >
          {metrics.quality_grade.charAt(0).toUpperCase() +
            metrics.quality_grade.slice(1)}
        </span>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Calibrator</span>
          <span className="font-medium">{metrics.calibrator_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">MJD</span>
          <span className="font-mono">{metrics.cal_mjd.toFixed(3)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Quality Score</span>
          <span className="font-mono font-medium">
            {metrics.quality_score}/100
          </span>
        </div>
      </div>

      {onSelect && (
        <button
          onClick={onSelect}
          className={`mt-3 w-full py-2 px-3 text-sm font-medium rounded-md transition-colors ${
            isPreferred
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          }`}
        >
          {isPreferred ? "✓ Selected" : "Select this set"}
        </button>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function CalibrationComparisonPanel({
  setA,
  setB,
  labels = { setA: "Set A (New)", setB: "Set B (Reference)" },
  showDetails = true,
  onSelectPreferred,
  className = "",
}: CalibrationComparisonPanelProps) {
  const [selectedSet, setSelectedSet] = React.useState<"A" | "B" | null>(null);

  const comparison = useMemo(() => computeComparison(setA, setB), [setA, setB]);

  const handleSelect = (set: "A" | "B") => {
    setSelectedSet(set);
    onSelectPreferred?.(set);
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Calibration Comparison
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Compare quality metrics between two calibration sets
        </p>
      </div>

      {/* Summary Cards */}
      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <CalSetSummary
            metrics={setA}
            label={labels.setA}
            isPreferred={selectedSet === "A"}
            onSelect={onSelectPreferred ? () => handleSelect("A") : undefined}
          />
          <CalSetSummary
            metrics={setB}
            label={labels.setB}
            isPreferred={selectedSet === "B"}
            onSelect={onSelectPreferred ? () => handleSelect("B") : undefined}
          />
        </div>

        {/* Recommendation Banner */}
        <div
          className={`p-3 rounded-lg mb-6 ${
            comparison.overallImproved
              ? "bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
              : "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800"
          }`}
        >
          <div className="flex items-center gap-2">
            <span
              className={`text-lg ${
                comparison.overallImproved
                  ? "text-green-600 dark:text-green-400"
                  : "text-blue-600 dark:text-blue-400"
              }`}
            >
              {comparison.overallImproved ? "📈" : "📊"}
            </span>
            <span
              className={`font-medium ${
                comparison.overallImproved
                  ? "text-green-800 dark:text-green-200"
                  : "text-blue-800 dark:text-blue-200"
              }`}
            >
              {comparison.recommendation}
            </span>
          </div>
        </div>

        {/* Detailed Metrics Comparison */}
        {showDetails && (
          <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Detailed Metrics Comparison
            </h4>

            {/* Header Row */}
            <div className="grid grid-cols-4 gap-4 pb-2 border-b border-gray-200 dark:border-gray-600 mb-2">
              <div className="text-xs font-medium text-gray-500 uppercase">
                Metric
              </div>
              <div className="text-xs font-medium text-gray-500 uppercase text-center">
                {labels.setA}
              </div>
              <div className="text-xs font-medium text-gray-500 uppercase text-center">
                {labels.setB}
              </div>
              <div className="text-xs font-medium text-gray-500 uppercase text-center">
                Change
              </div>
            </div>

            {/* Metric Rows */}
            <ComparisonRow
              label="SNR"
              valueA={setA.snr}
              valueB={setB.snr}
              delta={comparison.snr}
              precision={0}
            />
            <ComparisonRow
              label="Flagging"
              valueA={setA.flagging_percent}
              valueB={setB.flagging_percent}
              delta={comparison.flagging}
              unit="%"
              precision={1}
            />
            <ComparisonRow
              label="Phase RMS"
              valueA={setA.phase_rms_deg}
              valueB={setB.phase_rms_deg}
              delta={comparison.phaseRms}
              unit="°"
              precision={1}
            />
            <ComparisonRow
              label="Amp RMS"
              valueA={setA.amp_rms}
              valueB={setB.amp_rms}
              delta={comparison.ampRms}
              precision={3}
            />
            <ComparisonRow
              label="Quality Score"
              valueA={setA.quality_score}
              valueB={setB.quality_score}
              delta={comparison.qualityScore}
              precision={0}
            />
          </div>
        )}

        {/* Issues Comparison */}
        {(setA.issues.length > 0 || setB.issues.length > 0) && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <IssuesSection
              title={`${labels.setA} Issues`}
              issues={setA.issues}
            />
            <IssuesSection
              title={`${labels.setB} Issues`}
              issues={setB.issues}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function IssuesSection({
  title,
  issues,
}: {
  title: string;
  issues: CalibrationQAMetrics["issues"];
}) {
  const severityColors = {
    info: "text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/30",
    warning:
      "text-yellow-600 bg-yellow-50 dark:text-yellow-400 dark:bg-yellow-900/30",
    critical: "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/30",
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-3">
      <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {title} ({issues.length})
      </h5>
      {issues.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 italic">
          No issues detected
        </p>
      ) : (
        <div className="space-y-1">
          {issues.slice(0, 5).map((issue, i) => (
            <div
              key={i}
              className={`text-xs px-2 py-1 rounded ${
                severityColors[issue.severity]
              }`}
            >
              {issue.message}
            </div>
          ))}
          {issues.length > 5 && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              +{issues.length - 5} more issues
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default CalibrationComparisonPanel;
