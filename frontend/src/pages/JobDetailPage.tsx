import React from "react";
import { useParams, Link } from "react-router-dom";
import { useJobProvenance } from "../hooks/useQueries";
import ProvenanceStrip from "../components/provenance/ProvenanceStrip";
import ErrorDisplay from "../components/errors/ErrorDisplay";
import { Card, CoordinateDisplay, QAMetrics, LoadingSpinner } from "../components/common";
import type { ErrorResponse } from "../types/errors";
import { relativeTime } from "../utils/relativeTime";
import { usePreferencesStore } from "../stores/appStore";

type JobStatus = "pending" | "running" | "completed" | "failed";

const statusConfig: Record<JobStatus, { icon: string; bg: string; text: string }> = {
  pending: { icon: "⏳", bg: "bg-gray-100", text: "text-gray-700" },
  running: { icon: "🔄", bg: "bg-blue-100", text: "text-blue-700" },
  completed: { icon: "✓", bg: "bg-green-100", text: "text-green-700" },
  failed: { icon: "✗", bg: "bg-red-100", text: "text-red-700" },
};

/**
 * Job detail page showing provenance and job information.
 */
const JobDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const { data: provenance, isLoading, error, refetch } = useJobProvenance(runId);
  const addRecentJob = usePreferencesStore((state) => state.addRecentJob);

  // Track in recent items when job loads
  React.useEffect(() => {
    if (provenance && runId) {
      addRecentJob(runId);
    }
  }, [provenance, runId, addRecentJob]);

  if (isLoading) {
    return <LoadingSpinner label="Loading job details..." />;
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <ErrorDisplay error={error as unknown as ErrorResponse} onRetry={() => refetch()} />
      </div>
    );
  }

  if (!provenance) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Card>
          <p className="text-gray-500 mb-4">Job not found.</p>
          <Link to="/jobs" className="link">
            ← Back to Jobs
          </Link>
        </Card>
      </div>
    );
  }

  // Determine status from provenance data
  const status: JobStatus = provenance.qaGrade
    ? "completed"
    : provenance.createdAt
    ? "running"
    : "pending";
  const statusInfo = statusConfig[status];

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Link to="/jobs" className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block">
          ← Back to Jobs
        </Link>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-gray-900">Job: {runId}</h1>
          <span
            className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${statusInfo.bg} ${statusInfo.text}`}
          >
            <span>{statusInfo.icon}</span>
            <span className="capitalize">{status}</span>
          </span>
        </div>
        <ProvenanceStrip {...provenance} />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column - Status and actions */}
        <div className="lg:col-span-1 space-y-6">
          {/* Status card */}
          <Card title="Status">
            <div className="space-y-4">
              <div
                className={`p-4 rounded-lg ${statusInfo.bg} flex items-center justify-center gap-2`}
              >
                <span className="text-2xl">{statusInfo.icon}</span>
                <span className={`text-lg font-semibold ${statusInfo.text} capitalize`}>
                  {status}
                </span>
              </div>
              {provenance.createdAt && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">Started</dt>
                  <dd className="text-sm text-gray-900">
                    {new Date(provenance.createdAt).toLocaleString()}
                    <span className="text-gray-500 ml-1">
                      ({relativeTime(provenance.createdAt)})
                    </span>
                  </dd>
                </div>
              )}
            </div>
          </Card>

          {/* Actions */}
          <Card title="Actions">
            <div className="flex flex-col gap-2">
              {provenance.logsUrl && (
                <a
                  href={provenance.logsUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary text-center"
                >
                  📜 View Logs
                </a>
              )}
              {provenance.imageUrl && (
                <Link to={provenance.imageUrl} className="btn btn-primary text-center">
                  🖼️ View Output Image
                </Link>
              )}
              {provenance.qaUrl && (
                <a
                  href={provenance.qaUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary text-center"
                >
                  📊 QA Report
                </a>
              )}
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  // TODO: Implement re-run functionality
                  alert("Re-run functionality not yet implemented");
                }}
              >
                🔄 Re-run Job
              </button>
            </div>
          </Card>
        </div>

        {/* Right column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* QA Metrics */}
          {provenance.qaGrade && (
            <Card title="Quality Assessment">
              <QAMetrics
                grade={provenance.qaGrade as "good" | "warn" | "fail" | undefined}
                summary={provenance.qaSummary}
              />
            </Card>
          )}

          {/* Pointing coordinates */}
          {provenance.pointingRaDeg !== undefined && provenance.pointingDecDeg !== undefined && (
            <Card title="Pointing">
              <CoordinateDisplay
                raDeg={provenance.pointingRaDeg}
                decDeg={provenance.pointingDecDeg}
                showDecimal
              />
            </Card>
          )}

          {/* Input/Output details */}
          <Card title="Pipeline Details">
            <dl className="grid grid-cols-1 gap-4">
              <div>
                <dt className="text-xs text-gray-500 uppercase tracking-wide">Run ID</dt>
                <dd className="font-mono text-sm text-gray-900 break-all">
                  {provenance.runId || runId}
                </dd>
              </div>
              {provenance.msPath && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Input Measurement Set
                  </dt>
                  <dd className="font-mono text-sm break-all">
                    <Link
                      to={`/ms/${encodeURIComponent(provenance.msPath)}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {provenance.msPath}
                    </Link>
                  </dd>
                </div>
              )}
              {provenance.calTable && (
                <div>
                  <dt className="text-xs text-gray-500 uppercase tracking-wide">
                    Calibration Table
                  </dt>
                  <dd className="font-mono text-sm text-gray-900 break-all">
                    {provenance.calUrl ? (
                      <a
                        href={provenance.calUrl}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {provenance.calTable}
                      </a>
                    ) : (
                      provenance.calTable
                    )}
                  </dd>
                </div>
              )}
            </dl>
          </Card>

          {/* Related resources */}
          <Card title="Related Resources">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {provenance.msUrl && (
                <Link
                  to={provenance.msUrl}
                  className="p-3 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors flex items-center gap-3"
                >
                  <span className="text-2xl">📁</span>
                  <div>
                    <div className="font-medium text-gray-900">Measurement Set</div>
                    <div className="text-xs text-gray-500">View MS details</div>
                  </div>
                </Link>
              )}
              {provenance.imageUrl && (
                <Link
                  to={provenance.imageUrl}
                  className="p-3 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors flex items-center gap-3"
                >
                  <span className="text-2xl">🖼️</span>
                  <div>
                    <div className="font-medium text-gray-900">Output Image</div>
                    <div className="text-xs text-gray-500">View image details</div>
                  </div>
                </Link>
              )}
              {provenance.logsUrl && (
                <a
                  href={provenance.logsUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-3 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors flex items-center gap-3"
                >
                  <span className="text-2xl">📜</span>
                  <div>
                    <div className="font-medium text-gray-900">Logs</div>
                    <div className="text-xs text-gray-500">View job logs</div>
                  </div>
                </a>
              )}
              {provenance.qaUrl && (
                <a
                  href={provenance.qaUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-3 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors flex items-center gap-3"
                >
                  <span className="text-2xl">📊</span>
                  <div>
                    <div className="font-medium text-gray-900">QA Report</div>
                    <div className="text-xs text-gray-500">Quality assessment</div>
                  </div>
                </a>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default JobDetailPage;
