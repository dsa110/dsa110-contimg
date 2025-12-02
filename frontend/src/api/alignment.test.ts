/**
 * API/Frontend Type Alignment Tests
 *
 * These tests validate that backend API responses match frontend TypeScript types.
 * They can be run in two modes:
 *
 * 1. Unit mode (default): Uses fixture data that mirrors real API responses
 * 2. Integration mode: Runs against real backend (set INTEGRATION_TEST=true)
 *
 * The fixtures are derived from actual API responses and should be updated
 * when the backend API changes.
 */

import { describe, it, expect } from "vitest";

// Import ALL types that correspond to API responses
import type {
  SystemHealthReport,
  ValidityTimeline,
  ValidityTimelineEntry,
  FluxMonitoringSummary,
  FluxMonitoringStatus,
  PointingStatus,
  AlertsResponse,
  ActiveValidityWindows,
  FluxHistory,
  ServiceHealthStatus,
} from "../types/health";

import type {
  Task,
  TaskListResponse,
  QueueStats,
  Worker,
  WorkerListResponse,
  WorkerMetrics,
  AbsurdMetrics,
  AbsurdHealth,
  Workflow,
  WorkflowDetail,
  Alert,
} from "../types/absurd";

import type {
  ImageSummary,
  ImageDetail,
  SourceSummary,
  SourceDetail,
  MSMetadata,
  JobSummary,
  JobDetail,
  JobStatus,
  ProvenanceStripProps,
} from "../types";

// Import calibrator imaging types (defined in hooks)
import type {
  CalibratorInfo,
  TransitInfo,
  ObservationInfo,
  MSGenerationResponse,
  CalibrationResponse,
  ImagingResponse,
  JobInfo,
  PhotometryResult,
  HealthStatus,
} from "../hooks/useCalibratorImaging";

// Import imaging session types (defined in hooks)
import type {
  ImagingSession,
  ImagingSessionsResponse,
  ImagingDefaults,
  InteractiveCleanResponse,
} from "../hooks/useQueries";

// =============================================================================
// Type-safe validation helpers
// =============================================================================

/**
 * Validates that an object has all required keys of a type.
 * Returns true if valid, throws descriptive error if not.
 */
function validateRequiredKeys<T extends object>(
  obj: unknown,
  requiredKeys: (keyof T)[],
  typeName: string
): obj is T {
  if (typeof obj !== "object" || obj === null) {
    throw new Error(`${typeName}: Expected object, got ${typeof obj}`);
  }

  for (const key of requiredKeys) {
    if (!(key in obj)) {
      throw new Error(
        `${typeName}: Missing required key "${String(
          key
        )}". Got keys: ${Object.keys(obj).join(", ")}`
      );
    }
  }

  return true;
}

/**
 * Validates array items against a validator function.
 */
function validateArray<T>(
  arr: unknown,
  itemValidator: (item: unknown, index: number) => item is T,
  typeName: string
): arr is T[] {
  if (!Array.isArray(arr)) {
    throw new Error(`${typeName}: Expected array, got ${typeof arr}`);
  }

  arr.forEach((item, index) => {
    itemValidator(item, index);
  });

  return true;
}

// =============================================================================
// Fixture data (mirrors actual API responses)
// Update these when backend changes!
// =============================================================================

const FIXTURES = {
  // --- Health API fixtures ---
  systemHealth: {
    overall_status: "healthy",
    services: [
      {
        name: "uvicorn-api",
        status: "running",
        message: "HTTP 200 in 50ms",
        response_time_ms: 50,
      },
      {
        name: "streaming-converter",
        status: "running",
        message: "Active",
      },
    ],
    docker_available: true,
    systemd_available: true,
    summary: {
      total: 2,
      running: 2,
      healthy: 2,
    },
    checked_at: "2025-06-02T12:00:00Z",
    timestamp: "2025-06-02T12:00:00Z",
  } satisfies SystemHealthReport,

  validityTimeline: {
    timeline_start: "2025-06-01T12:00:00Z",
    timeline_end: "2025-06-03T12:00:00Z",
    current_time: "2025-06-02T12:00:00Z",
    current_mjd: 60460.5,
    windows: [
      {
        set_name: "3C286_60459",
        table_type: "bandpass",
        cal_field: "3C286",
        refant: "2",
        start_mjd: 60459.0,
        end_mjd: 60461.0,
        start_iso: "2025-06-01T00:00:00Z",
        end_iso: "2025-06-03T00:00:00Z",
        duration_hours: 48.0,
        is_current: true,
      },
    ],
    total_windows: 1,
  } satisfies ValidityTimeline,

  fluxMonitoring: {
    calibrators: [
      {
        calibrator_name: "3C286",
        n_measurements: 100,
        latest_mjd: 60460.5,
        latest_flux_ratio: 0.98,
        mean_flux_ratio: 1.0,
        flux_ratio_std: 0.02,
        is_stable: true,
        alerts_count: 0,
      },
    ],
    total_measurements: 100,
    total_alerts: 0,
    last_check_time: "2025-06-02T12:00:00Z",
  } satisfies FluxMonitoringSummary,

  // Flux monitoring when table not initialized
  fluxMonitoringEmpty: {
    calibrators: [] as FluxMonitoringStatus[],
    message: "Flux monitoring table not initialized",
  } satisfies FluxMonitoringSummary,

  pointingStatus: {
    current_lst: 12.5,
    current_lst_deg: 187.5,
    active_calibrator: "3C286",
    upcoming_transits: [
      {
        calibrator: "3C286",
        ra_deg: 202.78,
        dec_deg: 30.51,
        transit_utc: "2025-06-02T14:00:00Z",
        time_to_transit_sec: 7200,
        lst_at_transit: 13.5,
        elevation_at_transit: 75.0,
        status: "upcoming",
      },
    ],
    timestamp: "2025-06-02T12:00:00Z",
  } satisfies PointingStatus,

  alerts: {
    alerts: [
      {
        id: 1,
        alert_type: "flux_deviation",
        severity: "warning",
        calibrator_name: "3C48",
        message: "Flux ratio deviation > 5%",
        triggered_at: "2025-06-02T11:00:00Z",
        acknowledged: false,
      },
    ],
    total_count: 1,
    unacknowledged_count: 1,
  } satisfies AlertsResponse,

  // Alerts when table not initialized
  alertsEmpty: {
    alerts: [],
    message: "Monitoring alerts table not initialized",
  } satisfies AlertsResponse,

  // --- Absurd API fixtures ---
  task: {
    task_id: "task-123",
    queue_name: "default",
    task_name: "process_image",
    params: { image_id: "img-456" },
    priority: 0,
    status: "completed",
    created_at: "2025-06-02T10:00:00Z",
    claimed_at: "2025-06-02T10:01:00Z",
    completed_at: "2025-06-02T10:05:00Z",
    result: { success: true },
    error: null,
    retry_count: 0,
  } satisfies Task,

  queueStats: {
    queue_name: "default",
    pending: 5,
    claimed: 2,
    completed: 100,
    failed: 3,
    cancelled: 1,
    total: 111,
  } satisfies QueueStats,

  worker: {
    worker_id: "worker-abc",
    state: "active",
    task_count: 50,
    current_task_id: "task-789",
    first_seen: "2025-06-01T00:00:00Z",
    last_seen: "2025-06-02T12:00:00Z",
    uptime_seconds: 129600,
  } satisfies Worker,

  // --- Additional Absurd API fixtures ---
  taskListResponse: {
    tasks: [
      {
        task_id: "task-123",
        queue_name: "default",
        task_name: "process_image",
        params: { image_id: "img-456" },
        priority: 0,
        status: "completed",
        created_at: "2025-06-02T10:00:00Z",
        claimed_at: "2025-06-02T10:01:00Z",
        completed_at: "2025-06-02T10:05:00Z",
        result: { success: true },
        error: null,
        retry_count: 0,
      },
    ],
    total: 1,
  } satisfies TaskListResponse,

  workerListResponse: {
    workers: [
      {
        worker_id: "worker-abc",
        state: "active",
        task_count: 50,
        current_task_id: "task-789",
        first_seen: "2025-06-01T00:00:00Z",
        last_seen: "2025-06-02T12:00:00Z",
        uptime_seconds: 129600,
      },
    ],
    total: 1,
    active: 1,
    idle: 0,
    stale: 0,
    crashed: 0,
  } satisfies WorkerListResponse,

  workerMetrics: {
    total_workers: 4,
    active_workers: 2,
    idle_workers: 2,
    crashed_workers: 0,
    timed_out_workers: 0,
    avg_tasks_per_worker: 25.0,
    avg_worker_uptime_sec: 3600.0,
  } satisfies WorkerMetrics,

  absurdMetrics: {
    total_spawned: 1000,
    total_claimed: 995,
    total_completed: 980,
    total_failed: 10,
    total_cancelled: 5,
    total_timed_out: 0,
    current_pending: 5,
    current_claimed: 10,
    avg_wait_time_sec: 0.5,
    avg_execution_time_sec: 30.0,
    p50_wait_time_sec: 0.3,
    p95_wait_time_sec: 1.0,
    p99_wait_time_sec: 2.0,
    p50_execution_time_sec: 25.0,
    p95_execution_time_sec: 60.0,
    p99_execution_time_sec: 120.0,
    throughput_1min: 10.0,
    throughput_5min: 8.0,
    throughput_15min: 7.5,
    success_rate_1min: 0.98,
    success_rate_5min: 0.97,
    success_rate_15min: 0.98,
    error_rate_1min: 0.02,
    error_rate_5min: 0.03,
    error_rate_15min: 0.02,
  } satisfies AbsurdMetrics,

  absurdHealth: {
    status: "healthy",
    message: "All systems operational",
    queue_depth: 5,
    database_available: true,
    worker_pool_healthy: true,
    alerts: [],
    warnings: [],
  } satisfies AbsurdHealth,

  workflow: {
    workflow_id: "wf-123",
    name: "calibration_pipeline",
    status: "completed",
    task_count: 3,
    completed_tasks: 3,
    failed_tasks: 0,
    created_at: "2025-06-02T09:00:00Z",
    started_at: "2025-06-02T09:01:00Z",
    completed_at: "2025-06-02T09:30:00Z",
    metadata: { calibrator: "3C286" },
  } satisfies Workflow,

  workflowDetail: {
    workflow_id: "wf-123",
    name: "calibration_pipeline",
    status: "completed",
    task_count: 3,
    completed_tasks: 3,
    failed_tasks: 0,
    created_at: "2025-06-02T09:00:00Z",
    started_at: "2025-06-02T09:01:00Z",
    completed_at: "2025-06-02T09:30:00Z",
    metadata: { calibrator: "3C286" },
    tasks: [
      {
        task_id: "task-1",
        task_name: "generate_ms",
        status: "completed",
        depends_on: [],
        result: { ms_path: "/data/ms/out.ms" },
        error: null,
      },
    ],
    dag_edges: [["task-1", "task-2"]],
  } satisfies WorkflowDetail,

  // --- Calibrator Imaging fixtures ---
  calibratorInfo: {
    id: 1,
    name: "3C286",
    ra_deg: 202.78,
    dec_deg: 30.51,
    flux_jy: 14.5,
    status: "active",
  } satisfies CalibratorInfo,

  transitInfo: {
    transit_time_iso: "2025-06-02T14:00:00Z",
    transit_time_mjd: 60460.5833,
    has_data: true,
    num_subband_groups: 1,
    observation_ids: ["obs_20250602_140000"],
  } satisfies TransitInfo,

  observationInfo: {
    observation_id: "obs_20250602_140000",
    start_time_iso: "2025-06-02T13:57:30Z",
    mid_time_iso: "2025-06-02T14:00:00Z",
    end_time_iso: "2025-06-02T14:02:30Z",
    num_subbands: 16,
    file_paths: ["/data/incoming/2025-06-02T14:00:00_sb00.hdf5"],
    delta_from_transit_min: 0.0,
  } satisfies ObservationInfo,

  msGenerationResponse: {
    job_id: "job-ms-001",
    status: "completed",
    ms_path: "/stage/dsa110-contimg/ms/3C286_20250602.ms",
  } satisfies MSGenerationResponse,

  calibrationResponse: {
    job_id: "job-cal-001",
    status: "completed",
    cal_table_path: "/stage/dsa110-contimg/cal/3C286_bp.caltable",
  } satisfies CalibrationResponse,

  imagingResponse: {
    job_id: "job-img-001",
    status: "completed",
    image_path: "/stage/dsa110-contimg/images/3C286_20250602.fits",
  } satisfies ImagingResponse,

  jobInfo: {
    job_id: "job-001",
    job_type: "imaging",
    status: "completed",
    created_at: "2025-06-02T10:00:00Z",
    started_at: "2025-06-02T10:01:00Z",
    completed_at: "2025-06-02T10:05:00Z",
    error_message: null,
    result: { image_path: "/data/images/out.fits" },
  } satisfies JobInfo,

  photometryResult: {
    source_name: "3C286",
    ra_deg: 202.78,
    dec_deg: 30.51,
    peak_flux_jy: 14.2,
    integrated_flux_jy: 14.5,
    rms_jy: 0.001,
    snr: 14200,
  } satisfies PhotometryResult,

  calibratorImagingHealthStatus: {
    status: "healthy",
    hdf5_db_exists: true,
    calibrators_db_exists: true,
    incoming_dir_exists: true,
    output_ms_dir_exists: true,
    output_images_dir_exists: true,
  } satisfies HealthStatus,

  // --- Interactive Imaging fixtures ---
  imagingSession: {
    id: "session-abc",
    port: 9100,
    url: "http://localhost:9100",
    ms_path: "/data/ms/observation.ms",
    imagename: "observation_interactive",
    created_at: "2025-06-02T10:00:00Z",
    age_hours: 1.5,
    is_alive: true,
  } satisfies ImagingSession,

  imagingSessionsResponse: {
    sessions: [
      {
        id: "session-abc",
        port: 9100,
        url: "http://localhost:9100",
        ms_path: "/data/ms/observation.ms",
        imagename: "observation_interactive",
        created_at: "2025-06-02T10:00:00Z",
        age_hours: 1.5,
        is_alive: true,
      },
    ],
    total: 1,
    available_ports: 9,
  } satisfies ImagingSessionsResponse,

  imagingDefaults: {
    imsize: [4096, 4096],
    cell: "1arcsec",
    specmode: "mfs",
    deconvolver: "mtmfs",
    weighting: "briggs",
    robust: 0.5,
    niter: 10000,
    threshold: "0.1mJy",
    nterms: 2,
    datacolumn: "data",
  } satisfies ImagingDefaults,

  interactiveCleanResponse: {
    session_id: "session-abc",
    url: "http://localhost:9100",
    status: "running",
    ms_path: "/data/ms/observation.ms",
    imagename: "observation_interactive",
  } satisfies InteractiveCleanResponse,

  // --- Provenance fixture ---
  provenanceStrip: {
    runId: "run-abc123",
    msPath: "/data/ms/observation.ms",
    calTable: "bandpass.caltable",
    qaGrade: "good",
    qaSummary: "RMS 0.35 mJy, DR 1200",
    createdAt: "2025-06-02T10:00:00Z",
  } satisfies ProvenanceStripProps,
};

// =============================================================================
// Health API Type Alignment Tests
// =============================================================================

describe("Health API Type Alignment", () => {
  describe("SystemHealthReport", () => {
    it("services should be an array, not a Record", () => {
      const data = FIXTURES.systemHealth;

      // Key insight: services is an ARRAY with name property, not Record<name, status>
      expect(Array.isArray(data.services)).toBe(true);
      expect(data.services[0]).toHaveProperty("name");
      expect(data.services[0]).toHaveProperty("status");
    });

    it("validates required fields", () => {
      const data = FIXTURES.systemHealth;

      validateRequiredKeys<SystemHealthReport>(
        data,
        ["overall_status", "services", "summary"],
        "SystemHealthReport"
      );

      // Validate each service in array
      data.services.forEach((svc, i) => {
        validateRequiredKeys<ServiceHealthStatus>(
          svc,
          ["name", "status"],
          `ServiceHealthStatus[${i}]`
        );
      });
    });

    it("summary has correct structure", () => {
      const { summary } = FIXTURES.systemHealth;

      expect(summary).toHaveProperty("total");
      expect(typeof summary.total).toBe("number");
    });
  });

  describe("ValidityTimeline", () => {
    it("uses correct field names (timeline_start, not window_start_iso)", () => {
      const data = FIXTURES.validityTimeline;

      // These are the CORRECT field names from the API
      expect(data).toHaveProperty("timeline_start");
      expect(data).toHaveProperty("timeline_end");
      expect(data).toHaveProperty("current_time");
      expect(data).toHaveProperty("current_mjd");
      expect(data).toHaveProperty("windows");
      expect(data).toHaveProperty("total_windows");

      // These would be WRONG (old field names that don't exist)
      expect(data).not.toHaveProperty("window_start_iso");
      expect(data).not.toHaveProperty("window_end_iso");
      expect(data).not.toHaveProperty("entries");
    });

    it("windows array entries have correct field names", () => {
      const entry = FIXTURES.validityTimeline.windows[0];

      // Correct field names
      expect(entry).toHaveProperty("start_iso");
      expect(entry).toHaveProperty("end_iso");
      expect(entry).toHaveProperty("start_mjd");
      expect(entry).toHaveProperty("end_mjd");
      expect(entry).toHaveProperty("duration_hours");

      // Wrong field names (what we had before)
      expect(entry).not.toHaveProperty("valid_start_iso");
      expect(entry).not.toHaveProperty("valid_end_iso");
    });
  });

  describe("FluxMonitoringSummary", () => {
    it("handles normal response with calibrators", () => {
      const data = FIXTURES.fluxMonitoring;

      expect(Array.isArray(data.calibrators)).toBe(true);
      expect(data.calibrators[0]).toHaveProperty("calibrator_name");
      expect(data.calibrators[0]).toHaveProperty("is_stable");
    });

    it("handles empty response with message", () => {
      const data = FIXTURES.fluxMonitoringEmpty;

      expect(data.calibrators).toEqual([]);
      expect(data.message).toBeDefined();
    });

    it("total_alerts may be undefined (optional)", () => {
      // This ensures we use nullish coalescing when accessing total_alerts
      const dataWithAlerts = FIXTURES.fluxMonitoring;
      const dataEmpty = FIXTURES.fluxMonitoringEmpty;

      expect(dataWithAlerts.total_alerts ?? 0).toBe(0);
      expect(dataEmpty.total_alerts ?? 0).toBe(0); // undefined coalesces to 0
    });
  });

  describe("PointingStatus", () => {
    it("has required fields", () => {
      const data = FIXTURES.pointingStatus;

      validateRequiredKeys<PointingStatus>(
        data,
        ["current_lst", "current_lst_deg", "upcoming_transits", "timestamp"],
        "PointingStatus"
      );
    });

    it("upcoming_transits is an array", () => {
      const data = FIXTURES.pointingStatus;

      expect(Array.isArray(data.upcoming_transits)).toBe(true);
    });
  });

  describe("AlertsResponse", () => {
    it("handles normal response with alerts", () => {
      const data = FIXTURES.alerts;

      expect(Array.isArray(data.alerts)).toBe(true);
      expect(data.alerts[0]).toHaveProperty("id");
      expect(data.alerts[0]).toHaveProperty("severity");
      expect(data.alerts[0]).toHaveProperty("acknowledged");
    });

    it("handles empty response with message", () => {
      const data = FIXTURES.alertsEmpty;

      expect(data.alerts).toEqual([]);
      expect(data.message).toBeDefined();
    });
  });
});

// =============================================================================
// Absurd API Type Alignment Tests
// =============================================================================

describe("Absurd API Type Alignment", () => {
  describe("Task", () => {
    it("validates required fields", () => {
      validateRequiredKeys<Task>(
        FIXTURES.task,
        [
          "task_id",
          "queue_name",
          "task_name",
          "params",
          "priority",
          "status",
          "retry_count",
        ],
        "Task"
      );
    });

    it("nullable fields can be null", () => {
      const task = FIXTURES.task;

      // These fields CAN be null according to the type
      const createdAtType =
        task.created_at === null ? "object" : typeof task.created_at;
      expect(["string", "object"]).toContain(createdAtType);
      expect(task.error).toBeNull(); // Explicitly null in fixture
    });
  });

  describe("QueueStats", () => {
    it("has all status counts", () => {
      const stats = FIXTURES.queueStats;

      expect(typeof stats.pending).toBe("number");
      expect(typeof stats.claimed).toBe("number");
      expect(typeof stats.completed).toBe("number");
      expect(typeof stats.failed).toBe("number");
      expect(typeof stats.cancelled).toBe("number");
      expect(typeof stats.total).toBe("number");
    });
  });

  describe("Worker", () => {
    it("validates required fields", () => {
      validateRequiredKeys<Worker>(
        FIXTURES.worker,
        ["worker_id", "state", "task_count", "uptime_seconds"],
        "Worker"
      );
    });
  });

  describe("WorkerListResponse", () => {
    it("has workers array and summary counts", () => {
      const data = FIXTURES.workerListResponse;

      expect(Array.isArray(data.workers)).toBe(true);
      expect(typeof data.total).toBe("number");
      expect(typeof data.active).toBe("number");
      expect(typeof data.idle).toBe("number");
    });
  });

  describe("WorkerMetrics", () => {
    it("has worker pool metrics", () => {
      validateRequiredKeys<WorkerMetrics>(
        FIXTURES.workerMetrics,
        ["total_workers", "active_workers", "idle_workers"],
        "WorkerMetrics"
      );
    });
  });

  describe("AbsurdMetrics", () => {
    it("has throughput and latency metrics", () => {
      const metrics = FIXTURES.absurdMetrics;

      expect(typeof metrics.throughput_1min).toBe("number");
      expect(typeof metrics.avg_execution_time_sec).toBe("number");
      expect(typeof metrics.success_rate_1min).toBe("number");
    });
  });

  describe("AbsurdHealth", () => {
    it("has health status and alerts array", () => {
      const health = FIXTURES.absurdHealth;

      expect(["healthy", "degraded", "unhealthy"]).toContain(health.status);
      expect(Array.isArray(health.alerts)).toBe(true);
      expect(Array.isArray(health.warnings)).toBe(true);
      expect(typeof health.database_available).toBe("boolean");
    });
  });

  describe("WorkflowDetail", () => {
    it("extends Workflow with tasks and dag_edges", () => {
      const detail = FIXTURES.workflowDetail;

      // Base workflow fields
      expect(detail).toHaveProperty("workflow_id");
      expect(detail).toHaveProperty("status");

      // Detail-specific fields
      expect(Array.isArray(detail.tasks)).toBe(true);
      expect(Array.isArray(detail.dag_edges)).toBe(true);
    });
  });

  describe("TaskListResponse", () => {
    it("has tasks array and total count", () => {
      const data = FIXTURES.taskListResponse;

      expect(Array.isArray(data.tasks)).toBe(true);
      expect(typeof data.total).toBe("number");
    });
  });
});

// =============================================================================
// Calibrator Imaging API Type Alignment Tests
// =============================================================================

describe("Calibrator Imaging API Type Alignment", () => {
  describe("CalibratorInfo", () => {
    it("has required calibrator fields", () => {
      validateRequiredKeys<CalibratorInfo>(
        FIXTURES.calibratorInfo,
        ["id", "name", "ra_deg", "dec_deg", "status"],
        "CalibratorInfo"
      );
    });

    it("flux_jy can be null", () => {
      const cal = FIXTURES.calibratorInfo;
      expect(cal.flux_jy === null || typeof cal.flux_jy === "number").toBe(
        true
      );
    });
  });

  describe("TransitInfo", () => {
    it("has transit time and data availability", () => {
      validateRequiredKeys<TransitInfo>(
        FIXTURES.transitInfo,
        ["transit_time_iso", "transit_time_mjd", "has_data", "observation_ids"],
        "TransitInfo"
      );
      expect(Array.isArray(FIXTURES.transitInfo.observation_ids)).toBe(true);
    });
  });

  describe("ObservationInfo", () => {
    it("has observation time window and files", () => {
      validateRequiredKeys<ObservationInfo>(
        FIXTURES.observationInfo,
        [
          "observation_id",
          "start_time_iso",
          "mid_time_iso",
          "end_time_iso",
          "file_paths",
        ],
        "ObservationInfo"
      );
      expect(Array.isArray(FIXTURES.observationInfo.file_paths)).toBe(true);
    });
  });

  describe("Job Response Types", () => {
    it("MSGenerationResponse has job_id and status", () => {
      validateRequiredKeys<MSGenerationResponse>(
        FIXTURES.msGenerationResponse,
        ["job_id", "status"],
        "MSGenerationResponse"
      );
    });

    it("CalibrationResponse has job_id and status", () => {
      validateRequiredKeys<CalibrationResponse>(
        FIXTURES.calibrationResponse,
        ["job_id", "status"],
        "CalibrationResponse"
      );
    });

    it("ImagingResponse has job_id and status", () => {
      validateRequiredKeys<ImagingResponse>(
        FIXTURES.imagingResponse,
        ["job_id", "status"],
        "ImagingResponse"
      );
    });
  });

  describe("JobInfo", () => {
    it("has job status and timing fields", () => {
      validateRequiredKeys<JobInfo>(
        FIXTURES.jobInfo,
        ["job_id", "job_type", "status", "created_at"],
        "JobInfo"
      );
      expect(["pending", "running", "completed", "failed"]).toContain(
        FIXTURES.jobInfo.status
      );
    });
  });

  describe("PhotometryResult", () => {
    it("has source position and flux measurements", () => {
      validateRequiredKeys<PhotometryResult>(
        FIXTURES.photometryResult,
        [
          "source_name",
          "ra_deg",
          "dec_deg",
          "peak_flux_jy",
          "integrated_flux_jy",
          "snr",
        ],
        "PhotometryResult"
      );
    });
  });

  describe("HealthStatus", () => {
    it("has status and path existence flags", () => {
      const health = FIXTURES.calibratorImagingHealthStatus;

      expect(["healthy", "degraded"]).toContain(health.status);
      expect(typeof health.hdf5_db_exists).toBe("boolean");
      expect(typeof health.incoming_dir_exists).toBe("boolean");
    });
  });
});

// =============================================================================
// Interactive Imaging API Type Alignment Tests
// =============================================================================

describe("Interactive Imaging API Type Alignment", () => {
  describe("ImagingSession", () => {
    it("has session identifiers and state", () => {
      validateRequiredKeys<ImagingSession>(
        FIXTURES.imagingSession,
        ["id", "port", "url", "ms_path", "imagename", "is_alive"],
        "ImagingSession"
      );
    });
  });

  describe("ImagingSessionsResponse", () => {
    it("has sessions array and availability info", () => {
      const data = FIXTURES.imagingSessionsResponse;

      expect(Array.isArray(data.sessions)).toBe(true);
      expect(typeof data.total).toBe("number");
      expect(typeof data.available_ports).toBe("number");
    });
  });

  describe("ImagingDefaults", () => {
    it("has CASA tclean parameters", () => {
      const defaults = FIXTURES.imagingDefaults;

      expect(Array.isArray(defaults.imsize)).toBe(true);
      expect(typeof defaults.cell).toBe("string");
      expect(typeof defaults.niter).toBe("number");
      expect(typeof defaults.robust).toBe("number");
    });
  });

  describe("InteractiveCleanResponse", () => {
    it("has session_id and url", () => {
      validateRequiredKeys<InteractiveCleanResponse>(
        FIXTURES.interactiveCleanResponse,
        ["session_id", "url", "status", "ms_path", "imagename"],
        "InteractiveCleanResponse"
      );
    });
  });
});

// =============================================================================
// Provenance Type Alignment Tests
// =============================================================================

describe("Provenance API Type Alignment", () => {
  describe("ProvenanceStripProps", () => {
    it("has optional provenance fields", () => {
      const prov = FIXTURES.provenanceStrip;

      // All fields are optional, but if present should be correct types
      if (prov.runId) expect(typeof prov.runId).toBe("string");
      if (prov.msPath) expect(typeof prov.msPath).toBe("string");
      if (prov.qaGrade) {
        expect(["good", "warn", "fail", null]).toContain(prov.qaGrade);
      }
    });
  });
});

// =============================================================================
// Cross-cutting Type Patterns
// =============================================================================

describe("Common API Response Patterns", () => {
  it("arrays are arrays, not Records (learned from services bug)", () => {
    // The services field was incorrectly typed as Record<string, T> but API returns T[]
    // This test documents the pattern to watch for

    // CORRECT: arrays with 'name' or 'id' property
    expect(Array.isArray(FIXTURES.systemHealth.services)).toBe(true);
    expect(Array.isArray(FIXTURES.validityTimeline.windows)).toBe(true);
    expect(Array.isArray(FIXTURES.fluxMonitoring.calibrators)).toBe(true);
    expect(Array.isArray(FIXTURES.alerts.alerts)).toBe(true);
    expect(Array.isArray(FIXTURES.pointingStatus.upcoming_transits)).toBe(true);
  });

  it("optional message field for uninitialized states", () => {
    // Many endpoints return {data: [], message: "Not initialized"} when DB not ready
    // Types should have optional message field

    expect(FIXTURES.fluxMonitoringEmpty).toHaveProperty("message");
    expect(FIXTURES.alertsEmpty).toHaveProperty("message");
  });

  it("ISO timestamps are strings, MJD values are numbers", () => {
    const timeline = FIXTURES.validityTimeline;

    // ISO timestamps
    expect(typeof timeline.timeline_start).toBe("string");
    expect(typeof timeline.current_time).toBe("string");

    // MJD values
    expect(typeof timeline.current_mjd).toBe("number");
    expect(typeof timeline.windows[0].start_mjd).toBe("number");
  });
});

// =============================================================================
// Integration Test Mode (run with INTEGRATION_TEST=true)
// =============================================================================

const INTEGRATION_MODE = process.env.INTEGRATION_TEST === "true";

describe.skipIf(!INTEGRATION_MODE)("Live API Integration Tests", () => {
  const API_BASE = "http://localhost:8000";

  it("GET /api/v1/health/system matches SystemHealthReport type", async () => {
    const res = await fetch(`${API_BASE}/api/v1/health/system`);
    const data = await res.json();

    expect(res.ok).toBe(true);
    validateRequiredKeys<SystemHealthReport>(
      data,
      ["overall_status", "services", "summary"],
      "SystemHealthReport"
    );
    expect(Array.isArray(data.services)).toBe(true);
  });

  it("GET /api/v1/health/validity-windows/timeline matches ValidityTimeline type", async () => {
    const res = await fetch(
      `${API_BASE}/api/v1/health/validity-windows/timeline`
    );
    const data = await res.json();

    expect(res.ok).toBe(true);
    validateRequiredKeys<ValidityTimeline>(
      data,
      [
        "timeline_start",
        "timeline_end",
        "current_time",
        "windows",
        "total_windows",
      ],
      "ValidityTimeline"
    );
  });

  it("GET /api/v1/health/flux-monitoring matches FluxMonitoringSummary type", async () => {
    const res = await fetch(`${API_BASE}/api/v1/health/flux-monitoring`);
    const data = await res.json();

    expect(res.ok).toBe(true);
    // Either has calibrators array or message for uninitialized
    expect("calibrators" in data || "message" in data).toBe(true);
  });

  it("GET /api/v1/health/pointing matches PointingStatus type", async () => {
    const res = await fetch(`${API_BASE}/api/v1/health/pointing`);
    const data = await res.json();

    expect(res.ok).toBe(true);
    validateRequiredKeys<PointingStatus>(
      data,
      ["current_lst", "current_lst_deg", "upcoming_transits", "timestamp"],
      "PointingStatus"
    );
  });

  it("GET /api/v1/health/alerts matches AlertsResponse type", async () => {
    const res = await fetch(`${API_BASE}/api/v1/health/alerts`);
    const data = await res.json();

    expect(res.ok).toBe(true);
    expect("alerts" in data || "message" in data).toBe(true);
  });
});

// =============================================================================
// Core Data Types - Images, Sources, MS, Jobs
// =============================================================================

const CORE_FIXTURES = {
  imageSummary: {
    id: "img-12345",
    path: "/data/images/2025-06-02/observation_001.fits",
    qa_grade: "good",
    created_at: "2025-06-02T10:00:00Z",
    run_id: "run-abc123",
    pointing_ra_deg: 202.78,
    pointing_dec_deg: 30.51,
  } satisfies ImageSummary,

  imageDetail: {
    id: "img-12345",
    path: "/data/images/2025-06-02/observation_001.fits",
    qa_grade: "good",
    created_at: "2025-06-02T10:00:00Z",
    run_id: "run-abc123",
    pointing_ra_deg: 202.78,
    pointing_dec_deg: 30.51,
    ms_path: "/data/ms/2025-06-02/observation_001.ms",
    cal_table: "/data/cal/bandpass.caltable",
    qa_summary: "Clean image with no artifacts",
    noise_jy: 0.0001,
    dynamic_range: 10000,
    beam_major_arcsec: 15.0,
    beam_minor_arcsec: 10.0,
    beam_pa_deg: 45.0,
    peak_flux_jy: 1.5,
  } satisfies ImageDetail,

  sourceSummary: {
    id: "src-001",
    name: "3C286",
    ra_deg: 202.78,
    dec_deg: 30.51,
    num_images: 5,
    eta: 0.95,
    v: 0.02,
    peak_flux_jy: 14.5,
  } satisfies SourceSummary,

  sourceDetail: {
    id: "src-001",
    name: "3C286",
    ra_deg: 202.78,
    dec_deg: 30.51,
    num_images: 5,
    eta: 0.95,
    v: 0.02,
    peak_flux_jy: 14.5,
    flux_jy: 14.5,
    integrated_flux: 14.8,
    contributing_images: [
      {
        image_id: "img-001",
        path: "/data/images/obs1.fits",
        qa_grade: "good",
        flux_jy: 14.5,
      },
    ],
    latest_image_id: "img-001",
  } satisfies SourceDetail,

  msMetadata: {
    path: "/data/ms/2025-06-02/observation.ms",
    cal_table: "/data/cal/bandpass.caltable",
    scan_id: "scan_001",
    num_channels: 16384,
    integration_time_s: 12.88,
    pointing_ra_deg: 202.78,
    pointing_dec_deg: 30.51,
    run_id: "run-abc",
    qa_grade: "good",
    calibrator_matches: [
      { type: "bandpass", cal_table: "3C286_bp.caltable" },
      { type: "gain", cal_table: "3C286_gain.caltable" },
    ],
  } satisfies MSMetadata,

  jobSummary: {
    run_id: "run-abc123",
    status: "completed",
    started_at: "2025-06-02T09:00:00Z",
    finished_at: "2025-06-02T10:00:00Z",
  } satisfies JobSummary,

  jobDetail: {
    run_id: "run-abc123",
    status: "completed",
    started_at: "2025-06-02T09:00:00Z",
    finished_at: "2025-06-02T10:00:00Z",
    logs_url: "/api/jobs/run-abc123/logs",
    config: { wsclean_args: ["-niter", "10000"] },
  } satisfies JobDetail,
};

describe("Core Data API Type Alignment", () => {
  describe("ImageSummary / ImageDetail", () => {
    it("ImageSummary has required fields", () => {
      validateRequiredKeys<ImageSummary>(
        CORE_FIXTURES.imageSummary,
        ["id", "path", "qa_grade", "created_at"],
        "ImageSummary"
      );
    });

    it("ImageDetail extends ImageSummary with detail fields", () => {
      const detail = CORE_FIXTURES.imageDetail;

      // Has all summary fields
      validateRequiredKeys<ImageSummary>(
        detail,
        ["id", "path", "qa_grade", "created_at"],
        "ImageDetail (summary fields)"
      );

      // Has optional detail fields
      expect(detail).toHaveProperty("noise_jy");
      expect(detail).toHaveProperty("dynamic_range");
      expect(detail).toHaveProperty("beam_major_arcsec");
    });

    it("qa_grade can be null", () => {
      const validGrades: ImageSummary["qa_grade"][] = [
        "good",
        "warn",
        "fail",
        null,
      ];
      expect(validGrades).toContain(CORE_FIXTURES.imageSummary.qa_grade);
    });
  });

  describe("SourceSummary / SourceDetail", () => {
    it("SourceSummary has required coordinate fields", () => {
      validateRequiredKeys<SourceSummary>(
        CORE_FIXTURES.sourceSummary,
        ["id", "ra_deg", "dec_deg"],
        "SourceSummary"
      );
    });

    it("SourceDetail has contributing_images array", () => {
      const detail = CORE_FIXTURES.sourceDetail;

      expect(Array.isArray(detail.contributing_images)).toBe(true);
      expect(detail.contributing_images?.[0]).toHaveProperty("image_id");
      expect(detail.contributing_images?.[0]).toHaveProperty("path");
    });

    it("variability metrics are numbers", () => {
      const src = CORE_FIXTURES.sourceSummary;

      expect(typeof src.eta).toBe("number");
      expect(typeof src.v).toBe("number");
    });
  });

  describe("MSMetadata", () => {
    it("has required path field", () => {
      validateRequiredKeys<MSMetadata>(
        CORE_FIXTURES.msMetadata,
        ["path"],
        "MSMetadata"
      );
    });

    it("calibrator_matches is array of {type, cal_table}", () => {
      const ms = CORE_FIXTURES.msMetadata;

      expect(Array.isArray(ms.calibrator_matches)).toBe(true);
      expect(ms.calibrator_matches?.[0]).toHaveProperty("type");
      expect(ms.calibrator_matches?.[0]).toHaveProperty("cal_table");
    });
  });

  describe("JobSummary / JobDetail", () => {
    it("JobSummary has required fields", () => {
      validateRequiredKeys<JobSummary>(
        CORE_FIXTURES.jobSummary,
        ["run_id", "status"],
        "JobSummary"
      );
    });

    it("status is valid JobStatus value", () => {
      const validStatuses: JobStatus[] = [
        "pending",
        "running",
        "completed",
        "failed",
      ];
      expect(validStatuses).toContain(CORE_FIXTURES.jobSummary.status);
    });

    it("JobDetail extends JobSummary", () => {
      const detail = CORE_FIXTURES.jobDetail;

      validateRequiredKeys<JobSummary>(
        detail,
        ["run_id", "status"],
        "JobDetail (summary fields)"
      );
    });
  });
});
