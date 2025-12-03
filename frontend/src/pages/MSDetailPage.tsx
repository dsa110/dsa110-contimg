import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import {
  Card,
  CoordinateDisplay,
  QAMetrics,
  Modal,
} from "../components/common";
import { MsRasterPlot } from "../components/ms";
import { AntennaLayoutWidget } from "../components/antenna";
import { CalibrationComparisonPanel } from "../components/calibration";
import { mapProvenanceFromMSDetail } from "../utils/provenanceMappers";
import { relativeTime } from "../utils/relativeTime";
import type { ErrorResponse } from "../types/errors";
import { useMS } from "../hooks/useQueries";
import { config, FEATURES } from "../config";
import type { CalibrationQAMetrics } from "../types/calibration";

/**
 * Detail page for a Measurement Set.
 * Displays MS metadata, calibrator matches, provenance, and related images.
 *
 * Route: /ms/*
 * The "*" captures the full MS path which may contain slashes.
 */
const MSDetailPage: React.FC = () => {
  // React Router v6 captures the rest of the path with "*"
  const { "*": msPath } = useParams<{ "*": string }>();
  const { data: ms, isLoading, error, refetch } = useMS(msPath);

  // State for calibration comparison modal
  const [showComparisonModal, setShowComparisonModal] = useState(false);
  const [comparisonSets, setComparisonSets] = useState<{
    setA: CalibrationQAMetrics | null;
    setB: CalibrationQAMetrics | null;
  }>({ setA: null, setB: null });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-pulse text-gray-500">
          Loading Measurement Set details...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorDisplay
          error={error as unknown as ErrorResponse}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (!ms || !msPath) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card>
          <p className="text-gray-500 mb-4">Measurement Set not found.</p>
          <Link to="/images" className="link">
            Back to Images
          </Link>
        </Card>
      </div>
    );
  }

  // Map MS data to provenance format
  const provenance = mapProvenanceFromMSDetail({
    path: ms.path,
    pointing_ra_deg: ms.pointing_ra_deg,
    pointing_dec_deg: ms.pointing_dec_deg,
    created_at: ms.created_at,
    qa_grade: ms.qa_grade,
    calibrator_matches: ms.calibrator_matches,
  });

  const filename = ms.path.split("/").pop() || msPath;

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/images"
          className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block"
        >
          Back to Images
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{filename}</h1>
        <ProvenanceStrip {...provenance} />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column - Actions and quick info */}
        <div className="lg:col-span-1 space-y-6">
          {/* Status */}
          {ms.qa_grade && (
            <Card title="Quality">
              <QAMetrics
                grade={ms.qa_grade as "good" | "warn" | "fail" | undefined}
                summary={ms.qa_summary}
                compact
              />
            </Card>
          )}

          {/* Actions */}
          <Card title="Actions">
            <div className="flex flex-col gap-2">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() =>
                  window.open(
                    `${config.api.baseUrl}/ms/${encodeURIComponent(
                      msPath ?? ""
                    )}/download`,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                Download MS
              </button>
              <Link
                to="/imaging"
                state={{ ms_path: ms.path }}
                className="btn btn-secondary text-center flex items-center justify-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Interactive Clean
              </Link>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() =>
                  window.open(
                    `/viewer/carta?ms=${encodeURIComponent(msPath ?? "")}`,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                Open in CARTA
              </button>
              {ms.qa_grade && (
                <Link
                  to={`/qa/ms/${encodeURIComponent(msPath ?? "")}`}
                  className="btn btn-secondary text-center"
                >
                  View QA Report
                </Link>
              )}
              {/* Calibration Comparison button - only show if feature enabled and multiple calibrations */}
              {FEATURES.enableCalibrationComparison &&
                ms.calibrator_matches &&
                ms.calibrator_matches.length >= 2 && (
                  <button
                    type="button"
                    className="btn btn-secondary flex items-center justify-center gap-2"
                    onClick={() => {
                      // Create mock QA metrics from calibrator matches for demonstration
                      // In production, this would fetch real QA data from the API
                      const createMockQAMetrics = (
                        cal: { type: string; cal_table: string },
                        index: number
                      ): CalibrationQAMetrics => ({
                        cal_set_name:
                          cal.cal_table.split("/").pop() || cal.cal_table,
                        calibrator_name: cal.type,
                        cal_mjd: 60000 + index,
                        cal_timestamp: new Date().toISOString(),
                        snr: 50 + index * 10 + Math.random() * 20,
                        flagging_percent: 5 + Math.random() * 10,
                        phase_rms_deg: 10 + Math.random() * 5,
                        amp_rms: 0.05 + Math.random() * 0.03,
                        quality_grade: index === 0 ? "good" : "acceptable",
                        quality_score: 75 + index * 5 + Math.random() * 10,
                        issues: [],
                        recommendations: [],
                      });
                      setComparisonSets({
                        setA: createMockQAMetrics(ms.calibrator_matches![0], 0),
                        setB: createMockQAMetrics(ms.calibrator_matches![1], 1),
                      });
                      setShowComparisonModal(true);
                    }}
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                      />
                    </svg>
                    Compare Calibrations
                  </button>
                )}
            </div>
          </Card>

          {/* Quick stats */}
          <Card title="Quick Info">
            <dl className="space-y-3">
              {ms.created_at && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Created
                  </dt>
                  <dd className="text-sm text-gray-900">
                    {relativeTime(ms.created_at)}
                    <span className="text-gray-500 block text-xs">
                      {new Date(ms.created_at).toLocaleString()}
                    </span>
                  </dd>
                </div>
              )}
              {ms.run_id && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Pipeline Run
                  </dt>
                  <dd className="text-sm">
                    <Link
                      to={`/jobs/${ms.run_id}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {ms.run_id}
                    </Link>
                  </dd>
                </div>
              )}
            </dl>
          </Card>
        </div>

        {/* Right column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Pointing coordinates */}
          {ms.pointing_ra_deg !== undefined &&
            ms.pointing_ra_deg !== null &&
            ms.pointing_dec_deg !== undefined &&
            ms.pointing_dec_deg !== null && (
              <Card title="Pointing">
                <CoordinateDisplay
                  raDeg={ms.pointing_ra_deg}
                  decDeg={ms.pointing_dec_deg}
                  showDecimal
                />
              </Card>
            )}

          {/* Visibility Raster Plot */}
          <Card
            title="Visibility Plot"
            subtitle="Inspect visibility data quality"
          >
            <MsRasterPlot msPath={ms.path} width={700} height={450} />
          </Card>

          {/* Antenna Layout */}
          <Card
            title="Antenna Layout"
            subtitle="Array configuration and flagging status"
          >
            <AntennaLayoutWidget msPath={ms.path} height={250} showLegend />
          </Card>

          {/* Calibrator matches */}
          {ms.calibrator_matches && ms.calibrator_matches.length > 0 && (
            <Card
              title="Calibration Applied"
              subtitle={`${ms.calibrator_matches.length} calibration table${
                ms.calibrator_matches.length !== 1 ? "s" : ""
              }`}
            >
              <div className="space-y-3">
                {ms.calibrator_matches.map((cal, index) => (
                  <div
                    key={index}
                    className="p-3 rounded-lg border border-gray-200 bg-gray-50"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span
                          className={`badge ${
                            cal.type === "bandpass"
                              ? "badge-info"
                              : cal.type === "gain"
                              ? "badge-success"
                              : "badge-gray"
                          }`}
                        >
                          {cal.type}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 font-mono text-xs text-gray-600 break-all">
                      {cal.cal_table}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* No calibration applied */}
          {(!ms.calibrator_matches || ms.calibrator_matches.length === 0) && (
            <Card title="Calibration">
              <div className="text-center py-6 text-gray-500">
                <svg
                  className="w-10 h-10 mx-auto mb-2 text-gray-300"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p>No calibration tables applied yet.</p>
              </div>
            </Card>
          )}

          {/* Metadata */}
          <Card title="Metadata">
            <dl className="grid grid-cols-1 gap-4">
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">
                  Full Path
                </dt>
                <dd className="font-mono text-sm text-gray-900 break-all">
                  {ms.path}
                </dd>
              </div>
            </dl>
          </Card>
        </div>
      </div>

      {/* Calibration Comparison Modal */}
      {FEATURES.enableCalibrationComparison &&
        comparisonSets.setA &&
        comparisonSets.setB && (
          <Modal
            isOpen={showComparisonModal}
            onClose={() => setShowComparisonModal(false)}
            title="Compare Calibrations"
            size="xl"
          >
            <CalibrationComparisonPanel
              setA={comparisonSets.setA}
              setB={comparisonSets.setB}
              labels={{
                setA: comparisonSets.setA.cal_set_name,
                setB: comparisonSets.setB.cal_set_name,
              }}
              showDetails
            />
          </Modal>
        )}
    </div>
  );
};

export default MSDetailPage;
