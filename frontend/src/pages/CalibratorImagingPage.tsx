import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, LoadingSpinner } from "../components/common";
import {
  useCalibratorList,
  useCalibratorTransits,
  useCalibratorObservations,
  useGenerateMS,
  useCalibrateMS,
  useCreateImage,
  useCalibratorJob,
  usePhotometry,
  useCalibratorImagingHealth,
  useDataCoverage,
} from "../hooks/useCalibratorImaging";

/**
 * Calibrator Imaging Test Page
 *
 * This page provides a workflow to:
 * 1. Select a time of day
 * 2. Find bandpass calibrators with observations around that time
 * 3. Select an observation
 * 4. Generate MS from HDF5 files
 * 5. Calibrate and image
 * 6. Display results
 *
 * Route: /calibrator-imaging
 */

type WorkflowStep =
  | "select-calibrator"
  | "select-transit"
  | "select-observation"
  | "generate-ms"
  | "calibrate"
  | "image"
  | "complete";

interface Transit {
  transit_time_iso: string;
  transit_time_mjd: number;
  has_data: boolean;
  num_subband_groups: number;
  observation_ids: string[];
}

interface Observation {
  observation_id: string;
  start_time_iso: string;
  mid_time_iso: string;
  end_time_iso: string;
  num_subbands: number;
  file_paths: string[];
  delta_from_transit_min: number;
}

interface Calibrator {
  id: number;
  name: string;
  ra_deg: number;
  dec_deg: number;
  flux_jy: number | null;
  status: string;
}

const CalibratorImagingPage: React.FC = () => {
  // Workflow state
  const [step, setStep] = useState<WorkflowStep>("select-calibrator");
  const [selectedCalibrator, setSelectedCalibrator] =
    useState<Calibrator | null>(null);
  const [selectedTransit, setSelectedTransit] = useState<Transit | null>(null);
  const [selectedObservation, setSelectedObservation] =
    useState<Observation | null>(null);

  // Job tracking
  const [msJobId, setMsJobId] = useState<string | null>(null);
  const [calJobId, setCalJobId] = useState<string | null>(null);
  const [imageJobId, setImageJobId] = useState<string | null>(null);

  // Results
  const [msPath, setMsPath] = useState<string | null>(null);
  const [calTablePath, setCalTablePath] = useState<string | null>(null);
  const [imagePath, setImagePath] = useState<string | null>(null);

  // Health check - runs on mount
  const {
    data: healthStatus,
    isLoading: healthLoading,
    error: healthError,
    refetch: refetchHealth,
  } = useCalibratorImagingHealth();

  // Data coverage - determine appropriate time range for queries
  const { data: dataCoverage } = useDataCoverage();
  const recommendedDaysBack = dataCoverage?.recommended_days_back ?? 7;

  // API hooks
  const {
    data: calibrators,
    isLoading: calibratorsLoading,
    error: calibratorsError,
  } = useCalibratorList();

  const {
    data: transits,
    isLoading: transitsLoading,
    refetch: refetchTransits,
  } = useCalibratorTransits(
    selectedCalibrator?.name ?? null,
    recommendedDaysBack,
    2
  );

  const {
    data: observations,
    isLoading: observationsLoading,
    refetch: refetchObservations,
  } = useCalibratorObservations(
    selectedCalibrator?.name ?? null,
    selectedTransit?.transit_time_iso ?? null
  );

  // Mutations
  const generateMS = useGenerateMS();
  const calibrateMS = useCalibrateMS();
  const createImage = useCreateImage();

  // Job polling
  const { data: msJob } = useCalibratorJob(msJobId);
  const { data: calJob } = useCalibratorJob(calJobId);
  const { data: imageJob } = useCalibratorJob(imageJobId);

  // Photometry
  const { data: photometry, isLoading: photometryLoading } = usePhotometry(
    imagePath,
    selectedCalibrator?.name ?? null
  );

  // Effect to handle job completion
  useEffect(() => {
    if (msJob?.status === "completed" && msJob.result) {
      const msPath = msJob.result.ms_path as string | undefined;
      if (msPath) {
        setMsPath(msPath);
        setStep("calibrate");
      }
    }
  }, [msJob]);

  useEffect(() => {
    if (calJob?.status === "completed" && calJob.result) {
      const calPath = calJob.result.cal_table_path as string | undefined;
      if (calPath) {
        setCalTablePath(calPath);
        setStep("image");
      }
    }
  }, [calJob]);

  useEffect(() => {
    if (imageJob?.status === "completed" && imageJob.result) {
      const imgPath = imageJob.result.image_path as string | undefined;
      if (imgPath) {
        setImagePath(imgPath);
        setStep("complete");
      }
    }
  }, [imageJob]);

  // Handlers
  const handleSelectCalibrator = (cal: Calibrator) => {
    setSelectedCalibrator(cal);
    setSelectedTransit(null);
    setSelectedObservation(null);
    setStep("select-transit");
  };

  const handleSelectTransit = (transit: Transit) => {
    setSelectedTransit(transit);
    setSelectedObservation(null);
    setStep("select-observation");
  };

  const handleSelectObservation = (obs: Observation) => {
    setSelectedObservation(obs);
    setStep("generate-ms");
  };

  const handleGenerateMS = async () => {
    if (!selectedCalibrator || !selectedObservation) return;

    try {
      const result = await generateMS.mutateAsync({
        calibrator_name: selectedCalibrator.name,
        observation_id: selectedObservation.observation_id,
      });
      setMsJobId(result.job_id);
    } catch (error) {
      console.error("Failed to start MS generation:", error);
    }
  };

  const handleCalibrate = async () => {
    if (!msPath || !selectedCalibrator) return;

    try {
      const result = await calibrateMS.mutateAsync({
        ms_path: msPath,
        calibrator_name: selectedCalibrator.name,
      });
      setCalJobId(result.job_id);
    } catch (error) {
      console.error("Failed to start calibration:", error);
    }
  };

  const handleCreateImage = async () => {
    if (!msPath) return;

    try {
      const result = await createImage.mutateAsync({
        ms_path: msPath,
        imsize: 2048,
        cell: "2.5arcsec",
        niter: 5000,
        threshold: "1mJy",
      });
      setImageJobId(result.job_id);
    } catch (error) {
      console.error("Failed to start imaging:", error);
    }
  };

  const handleReset = () => {
    setStep("select-calibrator");
    setSelectedCalibrator(null);
    setSelectedTransit(null);
    setSelectedObservation(null);
    setMsJobId(null);
    setCalJobId(null);
    setImageJobId(null);
    setMsPath(null);
    setCalTablePath(null);
    setImagePath(null);
  };

  // Render step indicator
  const renderStepIndicator = () => {
    const steps = [
      { key: "select-calibrator", label: "1. Calibrator" },
      { key: "select-transit", label: "2. Transit" },
      { key: "select-observation", label: "3. Observation" },
      { key: "generate-ms", label: "4. Generate MS" },
      { key: "calibrate", label: "5. Calibrate" },
      { key: "image", label: "6. Image" },
      { key: "complete", label: "7. Results" },
    ];

    const currentIdx = steps.findIndex((s) => s.key === step);

    return (
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        {steps.map((s, idx) => (
          <React.Fragment key={s.key}>
            <div
              className={`px-3 py-1 rounded-full text-sm font-medium whitespace-nowrap ${
                idx <= currentIdx
                  ? "bg-blue-600 text-white"
                  : "bg-gray-700 text-gray-400"
              }`}
            >
              {s.label}
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`w-8 h-0.5 ${
                  idx < currentIdx ? "bg-blue-600" : "bg-gray-700"
                }`}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    );
  };

  // Render connection status panel
  const renderConnectionStatus = () => {
    // Show loading state
    if (healthLoading) {
      return (
        <div className="mb-6 p-4 bg-gray-800 border border-gray-700 rounded-lg">
          <div className="flex items-center gap-3">
            <LoadingSpinner size="sm" />
            <span className="text-gray-300">Checking system status...</span>
          </div>
        </div>
      );
    }

    // Show error if API is unreachable
    if (healthError || calibratorsError) {
      const error = healthError || calibratorsError;
      return (
        <div className="mb-6 p-4 bg-red-900/50 border border-red-700 rounded-lg">
          <div className="flex items-start gap-3">
            <span className="text-red-400 text-xl">⚠️</span>
            <div>
              <h3 className="font-bold text-red-300">API Connection Failed</h3>
              <p className="text-red-400 text-sm mt-1">
                Unable to connect to the calibrator imaging API. Please check
                that the backend server is running.
              </p>
              <p className="text-red-500 text-xs mt-2 font-mono">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
              <button
                onClick={() => refetchHealth()}
                className="mt-3 px-3 py-1 bg-red-800 hover:bg-red-700 text-red-200 rounded text-sm"
              >
                Retry Connection
              </button>
            </div>
          </div>
        </div>
      );
    }

    // Show status if available
    if (!healthStatus) {
      return null;
    }

    const issues: { label: string; message: string }[] = [];

    if (!healthStatus.hdf5_db_exists) {
      issues.push({
        label: "HDF5 Database",
        message: "HDF5 file index database not found",
      });
    }
    if (!healthStatus.calibrators_db_exists) {
      issues.push({
        label: "Calibrators Database",
        message: "Calibrators database not found",
      });
    }
    if (!healthStatus.incoming_dir_exists) {
      issues.push({
        label: "Incoming Directory",
        message: "HDF5 input directory does not exist",
      });
    }
    if (!healthStatus.output_ms_dir_exists) {
      issues.push({
        label: "MS Output Directory",
        message: "Measurement Set output directory does not exist",
      });
    }
    if (!healthStatus.output_images_dir_exists) {
      issues.push({
        label: "Images Output Directory",
        message: "Images output directory does not exist",
      });
    }

    // All healthy - show compact success indicator with stats
    if (issues.length === 0) {
      const config = healthStatus.configuration;
      const hdf5Count = config?.incoming_dir?.hdf5_file_count;
      const msCount = config?.output_ms_dir?.ms_file_count;

      return (
        <div className="mb-6 p-3 bg-green-900/30 border border-green-800 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-green-400">✓</span>
                <span className="text-green-300 text-sm">
                  All systems operational
                </span>
              </div>
              {(hdf5Count !== undefined || msCount !== undefined) && (
                <div className="flex items-center gap-3 text-xs text-gray-400 border-l border-gray-700 pl-4">
                  {hdf5Count !== undefined && (
                    <span>{hdf5Count.toLocaleString()} HDF5 files indexed</span>
                  )}
                  {msCount !== undefined && (
                    <span>{msCount} MS files available</span>
                  )}
                </div>
              )}
            </div>
            <button
              onClick={() => refetchHealth()}
              className="text-green-500 hover:text-green-400 text-xs"
            >
              Refresh
            </button>
          </div>
        </div>
      );
    }

    // Show warnings for each issue
    return (
      <div className="mb-6 p-4 bg-yellow-900/30 border border-yellow-700 rounded-lg">
        <div className="flex items-start gap-3">
          <span className="text-yellow-400 text-xl">⚠️</span>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-yellow-300">
                System Status: Degraded
              </h3>
              <button
                onClick={() => refetchHealth()}
                className="text-yellow-500 hover:text-yellow-400 text-xs"
              >
                Refresh
              </button>
            </div>
            <p className="text-yellow-400 text-sm mt-1">
              Some dependencies are unavailable. The workflow may not complete
              successfully.
            </p>
            <ul className="mt-3 space-y-1">
              {issues.map((issue) => (
                <li key={issue.label} className="text-sm">
                  <span className="text-yellow-500">✗</span>{" "}
                  <span className="text-yellow-300 font-medium">
                    {issue.label}:
                  </span>{" "}
                  <span className="text-yellow-400/80">{issue.message}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            to="/"
            className="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block"
          >
            ← Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-white">
            Calibrator Imaging Test
          </h1>
          <p className="text-gray-400 mt-1">
            Test the full pipeline: HDF5 → MS → Calibration → Imaging
          </p>
        </div>
        <button
          onClick={handleReset}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
        >
          Reset
        </button>
      </div>

      {/* Connection status */}
      {renderConnectionStatus()}

      {/* Step indicator */}
      {renderStepIndicator()}

      {/* Step 1: Select Calibrator */}
      {step === "select-calibrator" && (
        <Card title="Step 1: Select Bandpass Calibrator">
          {calibratorsLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="lg" />
            </div>
          ) : calibrators && calibrators.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {calibrators.map((cal) => (
                <button
                  key={cal.id}
                  onClick={() => handleSelectCalibrator(cal)}
                  className="p-4 bg-gray-800 hover:bg-gray-700 rounded-lg text-left transition-colors border border-gray-700 hover:border-blue-500"
                >
                  <div className="font-bold text-white text-lg">{cal.name}</div>
                  <div className="text-gray-400 text-sm mt-1">
                    RA: {cal.ra_deg.toFixed(4)}° Dec: {cal.dec_deg.toFixed(4)}°
                  </div>
                  {cal.flux_jy && (
                    <div className="text-gray-400 text-sm">
                      Flux: {cal.flux_jy.toFixed(2)} Jy
                    </div>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p>No calibrators found in database.</p>
              <p className="text-sm mt-2">
                Make sure calibrators are registered in the calibrators
                database.
              </p>
            </div>
          )}
        </Card>
      )}

      {/* Step 2: Select Transit */}
      {step === "select-transit" && selectedCalibrator && (
        <Card
          title={`Step 2: Select Transit for ${selectedCalibrator.name}`}
          subtitle="Choose a transit time with available HDF5 data"
        >
          {transitsLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="lg" />
            </div>
          ) : transits && transits.length > 0 ? (
            <div className="space-y-2">
              {transits.map((transit, idx) => (
                <button
                  key={idx}
                  onClick={() =>
                    transit.has_data && handleSelectTransit(transit)
                  }
                  disabled={!transit.has_data}
                  className={`w-full p-4 rounded-lg text-left transition-colors border ${
                    transit.has_data
                      ? "bg-gray-800 hover:bg-gray-700 border-gray-700 hover:border-blue-500"
                      : "bg-gray-900 border-gray-800 opacity-50 cursor-not-allowed"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-white">
                        {new Date(transit.transit_time_iso).toLocaleString()}
                      </div>
                      <div className="text-sm text-gray-400">
                        MJD: {transit.transit_time_mjd.toFixed(4)}
                      </div>
                    </div>
                    <div className="text-right">
                      {transit.has_data ? (
                        <span className="px-3 py-1 bg-green-900 text-green-300 rounded-full text-sm">
                          {transit.num_subband_groups} groups available
                        </span>
                      ) : (
                        <span className="px-3 py-1 bg-gray-800 text-gray-500 rounded-full text-sm">
                          No data
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <p>No transit times found.</p>
              <button
                onClick={() => refetchTransits()}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              >
                Refresh
              </button>
            </div>
          )}

          <div className="mt-4">
            <button
              onClick={() => setStep("select-calibrator")}
              className="text-blue-400 hover:text-blue-300"
            >
              ← Change calibrator
            </button>
          </div>
        </Card>
      )}

      {/* Step 3: Select Observation */}
      {step === "select-observation" &&
        selectedCalibrator &&
        selectedTransit && (
          <Card
            title="Step 3: Select Observation"
            subtitle={`Observations around transit at ${new Date(
              selectedTransit.transit_time_iso
            ).toLocaleString()}`}
          >
            {observationsLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner size="lg" />
              </div>
            ) : observations && observations.length > 0 ? (
              <div className="space-y-2">
                {observations.map((obs, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelectObservation(obs)}
                    className="w-full p-4 bg-gray-800 hover:bg-gray-700 rounded-lg text-left transition-colors border border-gray-700 hover:border-blue-500"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-white">
                          {obs.observation_id}
                        </div>
                        <div className="text-sm text-gray-400">
                          {new Date(obs.start_time_iso).toLocaleString()} -{" "}
                          {new Date(obs.end_time_iso).toLocaleTimeString()}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-400">
                          {obs.num_subbands} subbands
                        </div>
                        <div
                          className={`text-sm ${
                            obs.delta_from_transit_min < 5
                              ? "text-green-400"
                              : obs.delta_from_transit_min < 15
                              ? "text-yellow-400"
                              : "text-gray-400"
                          }`}
                        >
                          {obs.delta_from_transit_min.toFixed(1)} min from
                          transit
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-400">
                <p>No observations found for this transit.</p>
                <button
                  onClick={() => refetchObservations()}
                  className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                >
                  Refresh
                </button>
              </div>
            )}

            <div className="mt-4">
              <button
                onClick={() => setStep("select-transit")}
                className="text-blue-400 hover:text-blue-300"
              >
                ← Change transit
              </button>
            </div>
          </Card>
        )}

      {/* Step 4: Generate MS */}
      {step === "generate-ms" && selectedObservation && (
        <Card title="Step 4: Generate Measurement Set">
          <div className="space-y-4">
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="font-medium text-white mb-2">
                Selected Observation
              </h3>
              <div className="text-sm text-gray-400 space-y-1">
                <div>Calibrator: {selectedCalibrator?.name}</div>
                <div>Observation: {selectedObservation.observation_id}</div>
                <div>Subbands: {selectedObservation.num_subbands}</div>
                <div>
                  Distance from transit:{" "}
                  {selectedObservation.delta_from_transit_min.toFixed(1)} min
                </div>
              </div>
            </div>

            {msJobId && msJob ? (
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  {msJob.status === "running" || msJob.status === "pending" ? (
                    <LoadingSpinner size="sm" />
                  ) : msJob.status === "completed" ? (
                    <span className="text-green-400">✓</span>
                  ) : (
                    <span className="text-red-400">✗</span>
                  )}
                  <span className="text-white">
                    MS Generation: {msJob.status}
                  </span>
                </div>
                {msJob.error_message && (
                  <div className="mt-2 text-red-400 text-sm">
                    {msJob.error_message}
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={handleGenerateMS}
                disabled={generateMS.isPending}
                className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg font-medium"
              >
                {generateMS.isPending ? "Starting..." : "Generate MS from HDF5"}
              </button>
            )}
          </div>

          <div className="mt-4">
            <button
              onClick={() => setStep("select-observation")}
              className="text-blue-400 hover:text-blue-300"
            >
              ← Change observation
            </button>
          </div>
        </Card>
      )}

      {/* Step 5: Calibrate */}
      {step === "calibrate" && msPath && (
        <Card title="Step 5: Calibrate MS">
          <div className="space-y-4">
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="font-medium text-white mb-2">MS Generated</h3>
              <div className="text-sm text-gray-400 font-mono">{msPath}</div>
            </div>

            {calJobId && calJob ? (
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  {calJob.status === "running" ||
                  calJob.status === "pending" ? (
                    <LoadingSpinner size="sm" />
                  ) : calJob.status === "completed" ? (
                    <span className="text-green-400">✓</span>
                  ) : (
                    <span className="text-red-400">✗</span>
                  )}
                  <span className="text-white">
                    Calibration: {calJob.status}
                  </span>
                </div>
                {calJob.error_message && (
                  <div className="mt-2 text-red-400 text-sm">
                    {calJob.error_message}
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={handleCalibrate}
                disabled={calibrateMS.isPending}
                className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg font-medium"
              >
                {calibrateMS.isPending
                  ? "Starting..."
                  : `Calibrate with ${selectedCalibrator?.name} model`}
              </button>
            )}
          </div>
        </Card>
      )}

      {/* Step 6: Image */}
      {step === "image" && msPath && (
        <Card title="Step 6: Create Image">
          <div className="space-y-4">
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="font-medium text-white mb-2">Calibration Table</h3>
              <div className="text-sm text-gray-400 font-mono">
                {calTablePath}
              </div>
            </div>

            {imageJobId && imageJob ? (
              <div className="bg-gray-800 p-4 rounded-lg">
                <div className="flex items-center gap-3">
                  {imageJob.status === "running" ||
                  imageJob.status === "pending" ? (
                    <LoadingSpinner size="sm" />
                  ) : imageJob.status === "completed" ? (
                    <span className="text-green-400">✓</span>
                  ) : (
                    <span className="text-red-400">✗</span>
                  )}
                  <span className="text-white">Imaging: {imageJob.status}</span>
                </div>
                {imageJob.error_message && (
                  <div className="mt-2 text-red-400 text-sm">
                    {imageJob.error_message}
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={handleCreateImage}
                disabled={createImage.isPending}
                className="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg font-medium"
              >
                {createImage.isPending ? "Starting..." : "Create Image"}
              </button>
            )}
          </div>
        </Card>
      )}

      {/* Step 7: Results */}
      {step === "complete" && imagePath && (
        <Card title="Step 7: Results">
          <div className="space-y-6">
            {/* Summary */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="font-medium text-white mb-3">
                Processing Summary
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Calibrator:</span>
                  <span className="text-white">{selectedCalibrator?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Observation:</span>
                  <span className="text-white">
                    {selectedObservation?.observation_id}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">MS Path:</span>
                  <span className="text-white font-mono text-xs">{msPath}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Image Path:</span>
                  <span className="text-white font-mono text-xs">
                    {imagePath}
                  </span>
                </div>
              </div>
            </div>

            {/* Photometry */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="font-medium text-white mb-3">
                Photometry Results
              </h3>
              {photometryLoading ? (
                <div className="flex justify-center py-4">
                  <LoadingSpinner size="sm" />
                </div>
              ) : photometry ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-900 p-3 rounded">
                    <div className="text-gray-400 text-xs uppercase">
                      Peak Flux
                    </div>
                    <div className="text-white text-xl font-bold">
                      {photometry.peak_flux_jy.toFixed(3)} Jy
                    </div>
                  </div>
                  <div className="bg-gray-900 p-3 rounded">
                    <div className="text-gray-400 text-xs uppercase">
                      Integrated Flux
                    </div>
                    <div className="text-white text-xl font-bold">
                      {photometry.integrated_flux_jy.toFixed(3)} Jy
                    </div>
                  </div>
                  <div className="bg-gray-900 p-3 rounded">
                    <div className="text-gray-400 text-xs uppercase">RMS</div>
                    <div className="text-white text-xl font-bold">
                      {(photometry.rms_jy * 1000).toFixed(2)} mJy
                    </div>
                  </div>
                  <div className="bg-gray-900 p-3 rounded">
                    <div className="text-gray-400 text-xs uppercase">SNR</div>
                    <div className="text-white text-xl font-bold">
                      {photometry.snr.toFixed(1)}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-gray-400">
                  Photometry data not available
                </div>
              )}
            </div>

            {/* Image Preview Placeholder */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <h3 className="font-medium text-white mb-3">Image Preview</h3>
              <div className="bg-gray-900 rounded-lg aspect-square flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <div className="text-4xl mb-2">🔭</div>
                  <div>Image preview would appear here</div>
                  <div className="text-sm mt-1 font-mono">{imagePath}</div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-4">
              <button
                onClick={handleReset}
                className="flex-1 px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium"
              >
                Start New Test
              </button>
              <Link
                to={`/images/${encodeURIComponent(imagePath)}`}
                className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium text-center"
              >
                View Image Details
              </Link>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default CalibratorImagingPage;
