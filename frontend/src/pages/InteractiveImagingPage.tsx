import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, LoadingSpinner } from "../components/common";
import {
  useImagingSessions,
  useStartInteractiveClean,
  useStopSession,
  useImagingDefaults,
} from "../hooks/useQueries";

/**
 * TypeScript interfaces for imaging session data
 */
interface SessionInfo {
  id: string;
  port: number;
  url: string;
  ms_path: string;
  imagename: string;
  created_at: string;
  age_hours: number;
  is_alive: boolean;
  user_id?: string;
}

interface ImagingDefaults {
  imsize: number[];
  cell: string;
  specmode: string;
  deconvolver: string;
  weighting: string;
  robust: number;
  niter: number;
  threshold: string;
  nterms: number;
  datacolumn: string;
}

/**
 * Interactive Imaging Sessions Page.
 *
 * Displays active InteractiveClean sessions and allows users to:
 * - View all active sessions
 * - Launch new sessions (if MS path provided via state)
 * - Stop/cleanup sessions
 *
 * Route: /imaging
 */
const InteractiveImagingPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: sessions, isLoading, error, refetch } = useImagingSessions();
  const { data: defaults } = useImagingDefaults();
  const startSession = useStartInteractiveClean();
  const stopSession = useStopSession();

  // Form state for launching new session
  const [showNewSessionForm, setShowNewSessionForm] = useState(false);
  const [formData, setFormData] = useState({
    ms_path: "",
    imagename: "",
    imsize: [5040, 5040],
    cell: "2.5arcsec",
    niter: 10000,
    threshold: "0.5mJy",
    weighting: "briggs",
    robust: 0.5,
  });

  // Handle form field changes
  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    if (name === "imsize") {
      const size = parseInt(value, 10) || 5040;
      setFormData((prev) => ({ ...prev, imsize: [size, size] }));
    } else if (name === "robust" || name === "niter") {
      setFormData((prev) => ({ ...prev, [name]: parseFloat(value) || 0 }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  // Launch new session
  const handleLaunchSession = async () => {
    if (!formData.ms_path || !formData.imagename) {
      alert("Please provide both MS path and output image name");
      return;
    }

    try {
      const result = await startSession.mutateAsync({
        ms_path: formData.ms_path,
        imagename: formData.imagename,
        imsize: formData.imsize,
        cell: formData.cell,
        niter: formData.niter,
        threshold: formData.threshold,
        weighting: formData.weighting,
        robust: formData.robust,
      });

      // Open the Bokeh session in a new tab
      window.open(result.url, "_blank", "noopener,noreferrer");
      setShowNewSessionForm(false);
      refetch();
    } catch (err) {
      console.error("Failed to launch session:", err);
      alert(`Failed to launch session: ${err}`);
    }
  };

  // Stop session
  const handleStopSession = async (sessionId: string) => {
    if (!confirm("Are you sure you want to stop this session?")) {
      return;
    }

    try {
      await stopSession.mutateAsync(sessionId);
      refetch();
    } catch (err) {
      console.error("Failed to stop session:", err);
      alert(`Failed to stop session: ${err}`);
    }
  };

  // Format age for display
  const formatAge = (hours: number): string => {
    if (hours < 1) {
      return `${Math.round(hours * 60)} minutes`;
    }
    return `${hours.toFixed(1)} hours`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            to="/"
            className="text-sm text-gray-500 hover:text-gray-700 mb-2 inline-block"
          >
            ← Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">
            Interactive Imaging Sessions
          </h1>
          <p className="text-gray-600 mt-1">
            Manage InteractiveClean Bokeh sessions for MS visualization and
            imaging
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowNewSessionForm(!showNewSessionForm)}
          className="btn btn-primary"
        >
          {showNewSessionForm ? "Cancel" : "New Session"}
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">
            Failed to load sessions: {String(error)}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-2 text-sm text-red-600 hover:text-red-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* New Session Form */}
      {showNewSessionForm && (
        <Card title="Launch New Interactive Clean Session" className="mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* MS Path */}
            <div className="md:col-span-2">
              <label
                htmlFor="ms_path"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Measurement Set Path *
              </label>
              <input
                type="text"
                id="ms_path"
                name="ms_path"
                value={formData.ms_path}
                onChange={handleInputChange}
                placeholder="/data/ms/2025-10-05T12:00:00.ms"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Output Image Name */}
            <div className="md:col-span-2">
              <label
                htmlFor="imagename"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Output Image Name Prefix *
              </label>
              <input
                type="text"
                id="imagename"
                name="imagename"
                value={formData.imagename}
                onChange={handleInputChange}
                placeholder="/stage/dsa110-contimg/images/interactive_clean"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Image Size */}
            <div>
              <label
                htmlFor="imsize"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Image Size (pixels)
              </label>
              <input
                type="number"
                id="imsize"
                name="imsize"
                value={formData.imsize[0]}
                onChange={handleInputChange}
                min={256}
                max={8192}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Cell Size */}
            <div>
              <label
                htmlFor="cell"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Cell Size
              </label>
              <input
                type="text"
                id="cell"
                name="cell"
                value={formData.cell}
                onChange={handleInputChange}
                placeholder="2.5arcsec"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Max Iterations */}
            <div>
              <label
                htmlFor="niter"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Max Iterations
              </label>
              <input
                type="number"
                id="niter"
                name="niter"
                value={formData.niter}
                onChange={handleInputChange}
                min={0}
                max={1000000}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Threshold */}
            <div>
              <label
                htmlFor="threshold"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Threshold
              </label>
              <input
                type="text"
                id="threshold"
                name="threshold"
                value={formData.threshold}
                onChange={handleInputChange}
                placeholder="0.5mJy"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Weighting */}
            <div>
              <label
                htmlFor="weighting"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Weighting
              </label>
              <select
                id="weighting"
                name="weighting"
                value={formData.weighting}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="briggs">Briggs</option>
                <option value="natural">Natural</option>
                <option value="uniform">Uniform</option>
              </select>
            </div>

            {/* Robust */}
            <div>
              <label
                htmlFor="robust"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Robust Parameter
              </label>
              <input
                type="number"
                id="robust"
                name="robust"
                value={formData.robust}
                onChange={handleInputChange}
                min={-2}
                max={2}
                step={0.1}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Launch button */}
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={handleLaunchSession}
              disabled={startSession.isPending}
              className="btn btn-primary"
            >
              {startSession.isPending ? (
                <>
                  <span className="mr-2 inline-block">
                    <LoadingSpinner size="sm" centered={false} />
                  </span>
                  Launching...
                </>
              ) : (
                <>
                  <svg
                    className="w-4 h-4 mr-2"
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
                  Launch Session
                </>
              )}
            </button>
          </div>
        </Card>
      )}

      {/* Active Sessions */}
      <Card
        title={`Active Sessions (${sessions?.total ?? 0})`}
        subtitle={`${sessions?.available_ports ?? 0} ports available`}
      >
        {!sessions?.sessions?.length ? (
          <div className="text-center py-8 text-gray-500">
            <svg
              className="w-12 h-12 mx-auto mb-4 text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
            <p>No active sessions</p>
            <p className="text-sm mt-1">
              Click "New Session" to launch InteractiveClean
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {sessions.sessions.map((session: SessionInfo) => (
              <div
                key={session.id}
                className="py-4 first:pt-0 last:pb-0 flex items-start justify-between"
              >
                <div className="flex-1 min-w-0">
                  {/* Session header */}
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        session.is_alive ? "bg-green-500" : "bg-red-500"
                      }`}
                    />
                    <span className="font-mono text-sm text-gray-600">
                      {session.id.slice(0, 8)}...
                    </span>
                    <span className="text-xs text-gray-400">
                      Port {session.port}
                    </span>
                  </div>

                  {/* MS Path */}
                  <div className="mt-1">
                    <span className="text-xs text-gray-500">MS: </span>
                    <span className="text-sm text-gray-900 font-mono truncate">
                      {session.ms_path.split("/").pop()}
                    </span>
                  </div>

                  {/* Output name */}
                  <div>
                    <span className="text-xs text-gray-500">Output: </span>
                    <span className="text-sm text-gray-700 font-mono truncate">
                      {session.imagename.split("/").pop()}
                    </span>
                  </div>

                  {/* Age */}
                  <div className="mt-1 text-xs text-gray-500">
                    Running for {formatAge(session.age_hours)}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 ml-4">
                  {session.is_alive && (
                    <a
                      href={session.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-sm btn-primary"
                    >
                      Open
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => handleStopSession(session.id)}
                    disabled={stopSession.isPending}
                    className="btn btn-sm btn-danger"
                  >
                    Stop
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* DSA-110 Defaults Reference */}
      {defaults && (
        <Card title="DSA-110 Default Parameters" className="mt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">Image Size</dt>
              <dd className="font-mono">{defaults.imsize.join("×")}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Cell Size</dt>
              <dd className="font-mono">{defaults.cell}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Deconvolver</dt>
              <dd className="font-mono">{defaults.deconvolver}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Weighting</dt>
              <dd className="font-mono">{defaults.weighting}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Robust</dt>
              <dd className="font-mono">{defaults.robust}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Max Iterations</dt>
              <dd className="font-mono">{defaults.niter}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Threshold</dt>
              <dd className="font-mono">{defaults.threshold}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Data Column</dt>
              <dd className="font-mono">{defaults.datacolumn}</dd>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default InteractiveImagingPage;
