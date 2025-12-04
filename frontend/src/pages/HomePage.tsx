import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { SkyCoverageMapVAST, type Pointing } from "../components/skymap";
import { ServiceStatusPanel } from "../components/stats";
import { PipelineStatusPanel, usePipelineStatus } from "../components/pipeline";
import { useImages, useJobs, useSources } from "../hooks/useQueries";
import type { ImageSummary, JobStatus, JobSummary } from "../types";
import { ROUTES } from "../constants/routes";

interface HeroMetric {
  label: string;
  value: React.ReactNode;
  description: string;
  badge?: string;
}

const JOB_STATUS_STYLES: Record<JobStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

const formatDateTime = (value?: string) =>
  value ? new Date(value).toLocaleString() : "Not started";

const HomePage: React.FC = () => {
  const { data: images } = useImages();
  const { data: sources } = useSources();
  const { data: jobs, isLoading: jobsLoading } = useJobs();
  const pipelineStatusQuery = usePipelineStatus(30000);

  const pointings: Pointing[] = useMemo(() => {
    if (!images) return [];
    return images
      .filter(
        (img: ImageSummary) =>
          img.pointing_ra_deg != null && img.pointing_dec_deg != null
      )
      .map(
        (img: ImageSummary): Pointing => ({
          id: img.id,
          ra: img.pointing_ra_deg as number,
          dec: img.pointing_dec_deg as number,
          label: img.path?.split("/").pop() || img.id,
          status:
            img.qa_grade === "good"
              ? "completed"
              : img.qa_grade === "fail"
              ? "failed"
              : "scheduled",
        })
      );
  }, [images]);

  const heroMetrics = useMemo<HeroMetric[]>(() => {
    const totalImages = images?.length ?? 0;
    const activeJobs = jobs
      ? jobs.filter(
          (job) => job.status === "running" || job.status === "pending"
        ).length
      : 0;
    const completedJobs = jobs
      ? jobs.filter((job) => job.status === "completed").length
      : 0;
    const sourcesCount = sources?.length ?? 0;
    return [
      {
        label: "Images",
        value: totalImages,
        description: "FITS images in catalog",
      },
      {
        label: "Sources",
        value: sourcesCount,
        description: "Radio sources indexed",
      },
      {
        label: "Active jobs",
        value: activeJobs,
        description: "Running or pending",
      },
      {
        label: "Completed jobs",
        value: completedJobs,
        description: "Successfully finished",
      },
    ];
  }, [images, jobs, sources]);

  const latestJobs = useMemo(() => {
    if (!jobs) return [];
    return [...jobs]
      .sort((a, b) => {
        const toEpoch = (job: JobSummary) =>
          Date.parse(job.finished_at ?? job.started_at ?? "") || 0;
        return toEpoch(b) - toEpoch(a);
      })
      .slice(0, 4);
  }, [jobs]);

  const pipelineHealthLabel = pipelineStatusQuery.isPlaceholderData
    ? "Loading..."
    : pipelineStatusQuery.data?.is_healthy
    ? "Healthy"
    : "Attention needed";
  const pipelineHealthVariant = pipelineStatusQuery.isPlaceholderData
    ? "bg-slate-100 text-slate-800"
    : pipelineStatusQuery.data?.is_healthy
    ? "bg-emerald-100 text-emerald-800"
    : "bg-amber-100 text-amber-800";
  const pipelineLastUpdated = pipelineStatusQuery.isPlaceholderData
    ? "Loading..."
    : pipelineStatusQuery.data?.last_updated
    ? new Date(pipelineStatusQuery.data.last_updated).toLocaleTimeString()
    : "—";

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 text-white shadow-xl">
        <div className="p-8 space-y-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-300">
                DSA-110 Continuum Imaging
              </p>
              <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">
                Operational Dashboard
              </h1>
              <p className="max-w-2xl text-sm text-slate-200">
                Monitor sky coverage and pipeline activity across the imaging
                stack. Browse images, sources, or dive into job-level detail.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to={ROUTES.IMAGES.LIST} className="btn btn-primary text-sm">
                Browse images
              </Link>
              <Link
                to={ROUTES.JOBS.LIST}
                className="btn btn-outline-primary text-sm"
              >
                View jobs
              </Link>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {heroMetrics.map((metric) => (
              <HeroMetricCard key={metric.label} {...metric} />
            ))}
          </div>
        </div>
      </section>

      {/* Pipeline Status - Full Width */}
      <section className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2
              className="text-xl font-semibold"
              style={{ color: "var(--color-text-primary)" }}
            >
              Pipeline Status
            </h2>
            <p
              className="text-sm"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Worker state updates every 30 seconds.
            </p>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${pipelineHealthVariant}`}
          >
            {pipelineHealthLabel}
          </span>
        </div>
        <PipelineStatusPanel pollInterval={30000} />
      </section>

      {/* Sky Coverage - Full Width */}
      <section className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2
            className="text-xl font-semibold"
            style={{ color: "var(--color-text-primary)" }}
          >
            Sky Coverage
          </h2>
          <span
            className="text-sm"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {pointings.length} pointings mapped
          </span>
        </div>
        {pointings.length > 0 ? (
          <div className="card-body p-0">
            <SkyCoverageMapVAST pointings={pointings} height={450} />
          </div>
        ) : (
          <p
            className="text-sm"
            style={{ color: "var(--color-text-secondary)" }}
          >
            Pointings will appear here once image metadata is available.
          </p>
        )}
      </section>

      {/* Recent Jobs - Full Width */}
      <section className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2
              className="text-xl font-semibold"
              style={{ color: "var(--color-text-primary)" }}
            >
              Recent Jobs
            </h2>
            <p
              className="text-sm"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Latest pipeline runs.
            </p>
          </div>
          <Link
            to={ROUTES.JOBS.LIST}
            className="text-sm font-semibold"
            style={{ color: "var(--color-primary)" }}
          >
            View all
          </Link>
        </div>
        {jobsLoading ? (
          <p
            className="text-sm"
            style={{ color: "var(--color-text-secondary)" }}
          >
            Loading jobs...
          </p>
        ) : latestJobs.length === 0 ? (
          <p
            className="text-sm"
            style={{ color: "var(--color-text-secondary)" }}
          >
            Awaiting new pipeline submissions.
          </p>
        ) : (
          <div className="space-y-3">
            {latestJobs.map((job) => (
              <div
                key={job.run_id}
                className="flex items-center justify-between rounded-lg px-4 py-3"
                style={{
                  backgroundColor: "var(--color-bg-surface)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div>
                  <p
                    className="font-medium"
                    style={{ color: "var(--color-text-primary)" }}
                  >
                    {job.run_id}
                  </p>
                  <p
                    className="text-xs"
                    style={{ color: "var(--color-text-secondary)" }}
                  >
                    {formatDateTime(job.started_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      JOB_STATUS_STYLES[job.status]
                    }`}
                  >
                    {JOB_STATUS_LABELS[job.status]}
                  </span>
                  {job.finished_at && (
                    <p
                      className="text-[11px]"
                      style={{ color: "var(--color-text-secondary)" }}
                    >
                      Finished {formatDateTime(job.finished_at)}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card p-6 space-y-3">
        <h2
          className="text-xl font-semibold"
          style={{ color: "var(--color-text-primary)" }}
        >
          Quick Links
        </h2>
        <ul
          className="space-y-2 text-sm"
          style={{ color: "var(--color-text-secondary)" }}
        >
          <li>
            <a
              href="/docs/troubleshooting.md"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
              style={{ color: "var(--color-primary)" }}
            >
              Troubleshooting guide
            </a>
          </li>
          <li>
            <a
              href="/api/health"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:underline"
              style={{ color: "var(--color-primary)" }}
            >
              API health check
            </a>
          </li>
        </ul>
      </section>

      <section>
        <h2
          className="text-xl font-semibold mb-4"
          style={{ color: "var(--color-text-primary)" }}
        >
          Infrastructure Status
        </h2>
        <ServiceStatusPanel />
      </section>
    </div>
  );
};

const HeroMetricCard: React.FC<HeroMetric> = ({
  label,
  value,
  description,
  badge,
}) => (
  <div className="rounded-2xl border border-white/30 bg-white/5 p-4 backdrop-blur">
    <p className="text-xs uppercase tracking-[0.25em] text-white/70">{label}</p>
    <p className="text-3xl font-semibold text-white">{value}</p>
    <p className="text-sm text-white/80">{description}</p>
    {badge && (
      <span className="mt-2 inline-flex rounded-full border border-white/30 px-3 py-1 text-[11px] font-semibold">
        {badge}
      </span>
    )}
  </div>
);

export default HomePage;
