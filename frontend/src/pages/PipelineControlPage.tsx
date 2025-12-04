/**
 * PipelineControlPage - Central pipeline control dashboard.
 *
 * Provides UI to:
 * 1. Run full pipelines (conversion → calibration → imaging)
 * 2. Run individual pipeline stages on specific MS files
 * 3. Run registered pipelines (nightly_mosaic, on_demand_mosaic)
 * 4. View pipeline execution history and status
 *
 * Route: /pipeline
 */

import React, { useState } from "react";
import { Card, LoadingSpinner } from "../components/common";
import {
  useRegisteredPipelines,
  useAvailableStages,
  useRunPipeline,
  useRunFullPipeline,
  useRunStage,
  useCalibrateMS,
  useImageMS,
  useExecutions,
  type FullPipelineRequest,
} from "../hooks/usePipeline";

// =============================================================================
// Helper Components
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
    running: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
    completed:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
    queued:
      "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        colors[status] ||
        "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
      }`}
    >
      {status}
    </span>
  );
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
        {title}
      </h2>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {description}
        </p>
      )}
      {children}
    </Card>
  );
}

// =============================================================================
// Full Pipeline Section
// =============================================================================

function FullPipelineSection() {
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [runCalibration, setRunCalibration] = useState(true);
  const [runImaging, setRunImaging] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [inputDir, setInputDir] = useState("/data/incoming");
  const [outputDir, setOutputDir] = useState("/stage/dsa110-contimg/ms");

  const runFullPipeline = useRunFullPipeline();

  // Helper to set time range to last N hours
  const setLastHours = (hours: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - hours * 60 * 60 * 1000);
    setStartTime(start.toISOString().slice(0, 16));
    setEndTime(end.toISOString().slice(0, 16));
  };

  const handleSubmit = () => {
    if (!startTime || !endTime) {
      alert("Please specify start and end times");
      return;
    }

    const request: FullPipelineRequest = {
      start_time: new Date(startTime).toISOString(),
      end_time: new Date(endTime).toISOString(),
      input_dir: inputDir,
      output_dir: outputDir,
      run_calibration: runCalibration,
      run_imaging: runImaging,
    };

    runFullPipeline.mutate(request);
  };

  return (
    <SectionCard
      title="Run Full Pipeline"
      description="Process observations through conversion → calibration → imaging"
    >
      <div className="space-y-4">
        {/* Quick time selection */}
        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400 self-center">
            Quick select:
          </span>
          <button
            onClick={() => setLastHours(1)}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Last 1h
          </button>
          <button
            onClick={() => setLastHours(6)}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Last 6h
          </button>
          <button
            onClick={() => setLastHours(12)}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Last 12h
          </button>
          <button
            onClick={() => setLastHours(24)}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            Last 24h
          </button>
        </div>

        {/* Time range inputs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Start Time
            </label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              End Time
            </label>
            <input
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </div>
        </div>

        {/* Pipeline options */}
        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={runCalibration}
              onChange={(e) => setRunCalibration(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Run Calibration
            </span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={runImaging}
              onChange={(e) => setRunImaging(e.target.checked)}
              disabled={!runCalibration}
              className="h-4 w-4 text-blue-600 rounded disabled:opacity-50"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">
              Run Imaging
            </span>
          </label>
        </div>

        {/* Advanced options toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          {showAdvanced ? "Hide" : "Show"} advanced options
        </button>

        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-md">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Input Directory
              </label>
              <input
                type="text"
                value={inputDir}
                onChange={(e) => setInputDir(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Output Directory
              </label>
              <input
                type="text"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm"
              />
            </div>
          </div>
        )}

        {/* Submit button */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleSubmit}
            disabled={runFullPipeline.isPending || !startTime || !endTime}
            className="px-4 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {runFullPipeline.isPending && <LoadingSpinner size="sm" />}
            Run Pipeline
          </button>

          {runFullPipeline.isSuccess && (
            <span className="text-sm text-green-600 dark:text-green-400">
              ✓ Pipeline queued: {runFullPipeline.data.message}
            </span>
          )}

          {runFullPipeline.isError && (
            <span className="text-sm text-red-600 dark:text-red-400">
              Error: {(runFullPipeline.error as Error).message}
            </span>
          )}
        </div>
      </div>
    </SectionCard>
  );
}

// =============================================================================
// Individual Stages Section
// =============================================================================

function IndividualStagesSection() {
  const { data: stagesData, isLoading } = useAvailableStages();
  const [selectedStage, setSelectedStage] = useState<string>("");
  const [msPath, setMsPath] = useState("");
  const [applyOnly, setApplyOnly] = useState(true);

  // Imaging options
  const [imsize, setImsize] = useState(5040);
  const [cell, setCell] = useState("2.5arcsec");
  const [niter, setNiter] = useState(10000);
  const [threshold, setThreshold] = useState("0.5mJy");

  const calibrateMS = useCalibrateMS();
  const imageMS = useImageMS();
  const runStage = useRunStage();

  const handleRunStage = () => {
    if (!msPath) {
      alert("Please specify an MS path");
      return;
    }

    if (selectedStage === "calibration") {
      calibrateMS.mutate({ msPath, applyOnly });
    } else if (selectedStage === "imaging") {
      imageMS.mutate({
        msPath,
        options: { imsize, cell, niter, threshold },
      });
    } else if (selectedStage) {
      runStage.mutate({
        stage: selectedStage,
        params: { ms_path: msPath },
      });
    }
  };

  const isPending =
    calibrateMS.isPending || imageMS.isPending || runStage.isPending;
  const isSuccess =
    calibrateMS.isSuccess || imageMS.isSuccess || runStage.isSuccess;
  const error = calibrateMS.error || imageMS.error || runStage.error;

  if (isLoading) {
    return (
      <SectionCard title="Individual Stages">
        <LoadingSpinner />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title="Run Individual Stage"
      description="Run a specific pipeline stage on a Measurement Set"
    >
      <div className="space-y-4">
        {/* MS Path */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Measurement Set Path
          </label>
          <input
            type="text"
            value={msPath}
            onChange={(e) => setMsPath(e.target.value)}
            placeholder="/stage/dsa110-contimg/ms/2025-01-01T12:00:00.ms"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 font-mono text-sm"
          />
        </div>

        {/* Stage Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Stage
          </label>
          <select
            value={selectedStage}
            onChange={(e) => setSelectedStage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            <option value="">Select a stage...</option>
            <option value="calibration">Calibration</option>
            <option value="imaging">Imaging</option>
            {stagesData?.stages
              .filter(
                (s) =>
                  ![
                    "calibration-apply",
                    "calibration-solve",
                    "imaging",
                  ].includes(s.name)
              )
              .map((stage) => (
                <option key={stage.name} value={stage.name}>
                  {stage.name} - {stage.description}
                </option>
              ))}
          </select>
        </div>

        {/* Calibration options */}
        {selectedStage === "calibration" && (
          <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-md">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={applyOnly}
                onChange={(e) => setApplyOnly(e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Apply existing solutions (uncheck to solve new)
              </span>
            </label>
          </div>
        )}

        {/* Imaging options */}
        {selectedStage === "imaging" && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-md">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Image Size
              </label>
              <input
                type="number"
                value={imsize}
                onChange={(e) => setImsize(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Cell Size
              </label>
              <input
                type="text"
                value={cell}
                onChange={(e) => setCell(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Iterations
              </label>
              <input
                type="number"
                value={niter}
                onChange={(e) => setNiter(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Threshold
              </label>
              <input
                type="text"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>
        )}

        {/* Run button */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleRunStage}
            disabled={isPending || !msPath || !selectedStage}
            className="px-4 py-2 bg-green-600 text-white rounded-md font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isPending && <LoadingSpinner size="sm" />}
            Run Stage
          </button>

          {isSuccess && (
            <span className="text-sm text-green-600 dark:text-green-400">
              ✓ Task queued
            </span>
          )}

          {error && (
            <span className="text-sm text-red-600 dark:text-red-400">
              Error: {(error as Error).message}
            </span>
          )}
        </div>
      </div>
    </SectionCard>
  );
}

// =============================================================================
// Registered Pipelines Section
// =============================================================================

function RegisteredPipelinesSection() {
  const { data: pipelinesData, isLoading, error } = useRegisteredPipelines();
  const runPipeline = useRunPipeline();
  const [runningPipeline, setRunningPipeline] = useState<string | null>(null);

  const handleRunPipeline = (pipelineName: string) => {
    setRunningPipeline(pipelineName);
    runPipeline.mutate(
      { pipelineName },
      {
        onSettled: () => setRunningPipeline(null),
      }
    );
  };

  if (isLoading) {
    return (
      <SectionCard title="Registered Pipelines">
        <LoadingSpinner />
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title="Registered Pipelines">
        <p className="text-red-600 dark:text-red-400">
          Failed to load pipelines: {(error as Error).message}
        </p>
      </SectionCard>
    );
  }

  const pipelines = pipelinesData?.pipelines || [];

  return (
    <SectionCard
      title="Registered Pipelines"
      description="Pre-defined pipelines that can be triggered manually or run on schedule"
    >
      {pipelines.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400 italic">
          No pipelines registered. Import the mosaic module to register
          nightly_mosaic and on_demand_mosaic.
        </p>
      ) : (
        <div className="space-y-3">
          {pipelines.map((pipeline) => (
            <div
              key={pipeline.name}
              className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
            >
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100">
                    {pipeline.name}
                  </h3>
                  {pipeline.is_scheduled && (
                    <span className="px-2 py-0.5 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 rounded">
                      Scheduled
                    </span>
                  )}
                </div>
                {pipeline.schedule && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Schedule: {pipeline.schedule}
                  </p>
                )}
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                  {pipeline.description.split("\n")[0]}
                </p>
              </div>
              <button
                onClick={() => handleRunPipeline(pipeline.name)}
                disabled={runningPipeline === pipeline.name}
                className="px-4 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shrink-0"
              >
                {runningPipeline === pipeline.name && (
                  <LoadingSpinner size="sm" />
                )}
                Run Now
              </button>
            </div>
          ))}
        </div>
      )}

      {runPipeline.isSuccess && (
        <p className="mt-4 text-sm text-green-600 dark:text-green-400">
          ✓ Pipeline queued: {runPipeline.data.message}
        </p>
      )}

      {runPipeline.isError && (
        <p className="mt-4 text-sm text-red-600 dark:text-red-400">
          Error: {(runPipeline.error as Error).message}
        </p>
      )}
    </SectionCard>
  );
}

// =============================================================================
// Execution History Section
// =============================================================================

function ExecutionHistorySection() {
  const { data: executionsData, isLoading, error } = useExecutions(20);

  if (isLoading) {
    return (
      <SectionCard title="Recent Executions">
        <LoadingSpinner />
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title="Recent Executions">
        <p className="text-red-600 dark:text-red-400">
          Failed to load executions: {(error as Error).message}
        </p>
      </SectionCard>
    );
  }

  const executions = executionsData?.executions || [];

  return (
    <SectionCard
      title="Recent Executions"
      description="Pipeline execution history"
    >
      {executions.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400 italic">
          No pipeline executions found. Run a pipeline to see execution history.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">
                  Pipeline
                </th>
                <th className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">
                  Status
                </th>
                <th className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">
                  Started
                </th>
                <th className="text-left py-2 px-3 font-medium text-gray-700 dark:text-gray-300">
                  Jobs
                </th>
              </tr>
            </thead>
            <tbody>
              {executions.map((exec) => (
                <tr
                  key={exec.execution_id}
                  className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                >
                  <td className="py-2 px-3 font-mono text-xs">
                    {exec.pipeline_name}
                  </td>
                  <td className="py-2 px-3">
                    <StatusBadge status={exec.status} />
                  </td>
                  <td className="py-2 px-3 text-gray-600 dark:text-gray-400">
                    {exec.started_at
                      ? new Date(exec.started_at).toLocaleString()
                      : "-"}
                  </td>
                  <td className="py-2 px-3">
                    <span className="text-gray-600 dark:text-gray-400">
                      {exec.jobs.length} jobs
                    </span>
                    {exec.jobs.some((j) => j.status === "failed") && (
                      <span className="ml-2 text-red-600 dark:text-red-400">
                        ({exec.jobs.filter((j) => j.status === "failed").length}{" "}
                        failed)
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SectionCard>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

const PipelineControlPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Pipeline Control
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">
          Run and monitor DSA-110 data processing pipelines
        </p>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column - Actions */}
        <div className="space-y-6">
          <FullPipelineSection />
          <IndividualStagesSection />
        </div>

        {/* Right column - Pipelines and History */}
        <div className="space-y-6">
          <RegisteredPipelinesSection />
          <ExecutionHistorySection />
        </div>
      </div>
    </div>
  );
};

export default PipelineControlPage;
