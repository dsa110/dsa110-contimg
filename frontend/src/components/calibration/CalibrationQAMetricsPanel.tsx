/**
 * Calibration QA Metrics Panel Component
 *
 * Displays calibration quality metrics with visual indicators.
 */

import React from "react";
import type {
  CalibrationQAMetrics,
  QualityThresholds,
} from "../../types/calibration";
import { DEFAULT_QUALITY_THRESHOLDS } from "../../types/calibration";

interface CalibrationQAMetricsPanelProps {
  metrics: CalibrationQAMetrics;
  thresholds?: QualityThresholds;
  showDetails?: boolean;
  className?: string;
}

const gradeColors: Record<CalibrationQAMetrics["quality_grade"], string> = {
  excellent:
    "text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30",
  good: "text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30",
  acceptable:
    "text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/30",
  poor: "text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30",
  failed: "text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30",
};

const gradeLabels: Record<CalibrationQAMetrics["quality_grade"], string> = {
  excellent: "Excellent",
  good: "Good",
  acceptable: "Acceptable",
  poor: "Poor",
  failed: "Failed",
};

function MetricGauge({
  label,
  value,
  unit,
  min,
  max,
  warningThreshold,
  criticalThreshold,
  invertThresholds = false,
}: {
  label: string;
  value: number;
  unit?: string;
  min: number;
  max: number;
  warningThreshold: number;
  criticalThreshold: number;
  invertThresholds?: boolean;
}) {
  const percent = Math.max(
    0,
    Math.min(100, ((value - min) / (max - min)) * 100)
  );

  let status: "good" | "warning" | "critical" = "good";
  if (invertThresholds) {
    // Higher is worse (e.g., flagging, phase RMS)
    if (value >= criticalThreshold) status = "critical";
    else if (value >= warningThreshold) status = "warning";
  } else {
    // Lower is worse (e.g., SNR)
    if (value <= criticalThreshold) status = "critical";
    else if (value <= warningThreshold) status = "warning";
  }

  const statusColors = {
    good: "bg-green-500",
    warning: "bg-yellow-500",
    critical: "bg-red-500",
  };

  const textColors = {
    good: "text-green-600 dark:text-green-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    critical: "text-red-600 dark:text-red-400",
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className={`font-mono font-medium ${textColors[status]}`}>
          {typeof value === "number" ? value.toFixed(1) : value}
          {unit && <span className="text-xs ml-0.5">{unit}</span>}
        </span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
        <div
          className={`h-full ${statusColors[status]} transition-all duration-300`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function IssuesList({ issues }: { issues: CalibrationQAMetrics["issues"] }) {
  if (issues.length === 0) return null;

  const severityColors = {
    info: "text-blue-600 dark:text-blue-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    critical: "text-red-600 dark:text-red-400",
  };

  const severityIcons = {
    info: "ℹ️",
    warning: "⚠️",
    critical: "🚨",
  };

  return (
    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
        Issues Detected
      </h4>
      <div className="space-y-2">
        {issues.map((issue, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 text-sm ${
              severityColors[issue.severity]
            }`}
          >
            <span>{severityIcons[issue.severity]}</span>
            <div>
              <span>{issue.message}</span>
              {issue.affected_antennas &&
                issue.affected_antennas.length > 0 && (
                  <span className="ml-1 text-xs opacity-75">
                    (Antennas: {issue.affected_antennas.join(", ")})
                  </span>
                )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecommendationsList({
  recommendations,
}: {
  recommendations: string[];
}) {
  if (recommendations.length === 0) return null;

  return (
    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
        Recommendations
      </h4>
      <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
        {recommendations.map((rec, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="text-blue-500">→</span>
            <span>{rec}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CalibrationQAMetricsPanel({
  metrics,
  thresholds = DEFAULT_QUALITY_THRESHOLDS,
  showDetails = true,
  className = "",
}: CalibrationQAMetricsPanelProps) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      {/* Header with grade */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Calibration Quality
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {metrics.calibrator_name} •{" "}
            {new Date(metrics.cal_timestamp).toLocaleString()}
          </p>
        </div>
        <div className="text-right">
          <span
            className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
              gradeColors[metrics.quality_grade]
            }`}
          >
            {gradeLabels[metrics.quality_grade]}
          </span>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Score: {metrics.quality_score}/100
          </div>
        </div>
      </div>

      {/* Main metrics grid */}
      <div className="grid grid-cols-2 gap-4">
        <MetricGauge
          label="SNR"
          value={metrics.snr}
          min={0}
          max={200}
          warningThreshold={thresholds.min_snr * 2}
          criticalThreshold={thresholds.min_snr}
          invertThresholds={false}
        />
        <MetricGauge
          label="Flagging"
          value={metrics.flagging_percent}
          unit="%"
          min={0}
          max={100}
          warningThreshold={thresholds.max_flagging_percent * 0.7}
          criticalThreshold={thresholds.max_flagging_percent}
          invertThresholds={true}
        />
        <MetricGauge
          label="Phase RMS"
          value={metrics.phase_rms_deg}
          unit="°"
          min={0}
          max={90}
          warningThreshold={thresholds.max_phase_rms_deg * 0.7}
          criticalThreshold={thresholds.max_phase_rms_deg}
          invertThresholds={true}
        />
        <MetricGauge
          label="Amp RMS"
          value={metrics.amp_rms * 100}
          unit="%"
          min={0}
          max={50}
          warningThreshold={thresholds.max_amp_rms * 100 * 0.7}
          criticalThreshold={thresholds.max_amp_rms * 100}
          invertThresholds={true}
        />
      </div>

      {/* Detailed info */}
      {showDetails && (
        <>
          <IssuesList issues={metrics.issues} />
          <RecommendationsList recommendations={metrics.recommendations} />
        </>
      )}
    </div>
  );
}

export default CalibrationQAMetricsPanel;
