import React, { useMemo, useState, useEffect } from "react";
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

const formatRelativeTime = (value?: string) => {
  if (!value) return "—";
  const date = new Date(value);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
};

const HomePage: React.FC = () => {
  const { data: images, dataUpdatedAt: imagesUpdatedAt } = useImages();
  const { data: sources } = useSources();
  const { data: jobs, isLoading: jobsLoading, dataUpdatedAt: jobsUpdatedAt } = useJobs();
  const pipelineStatusQuery = usePipelineStatus(30000);

  // Capture current time when data updates to avoid impure Date.now() in render
  const [currentTime, setCurrentTime] = useState(() => Date.now());
  
  useEffect(() => {
    // Update current time when data changes
    setCurrentTime(Date.now());
  }, [imagesUpdatedAt, jobsUpdatedAt]);

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

  // Calculate alerts
  const alerts = useMemo(() => {
    const alertList: {
      type: "error" | "warning" | "info";
      message: string;
      link?: string;
    }[] = [];

    // Failed jobs in last 24 hours
    const recentFailedJobs =
      jobs?.filter((job) => {
        if (job.status !== "failed") return false;
        const finishedAt = job.finished_at ? new Date(job.finished_at) : null;
        if (!finishedAt) return false;
        const hoursSinceFinished =
          (currentTime - finishedAt.getTime()) / (1000 * 60 * 60);
        return hoursSinceFinished < 24;
      }) ?? [];

    if (recentFailedJobs.length > 0) {
      alertList.push({
        type: "error",
        message: `${recentFailedJobs.length} job${
          recentFailedJobs.length > 1 ? "s" : ""
        } failed in the last 24 hours`,
        link: ROUTES.JOBS.LIST + "?status=failed",
      });
    }

    // Pipeline unhealthy
    if (pipelineStatusQuery.data && !pipelineStatusQuery.data.is_healthy) {
      alertList.push({
        type: "warning",
        message: "Pipeline requires attention",
        link: ROUTES.PIPELINE,
      });
    }

    // Stale data warning (no new images in 24 hours)
    if (images && images.length > 0) {
      const latestImage = images.reduce((latest, img) => {
        const imgDate = img.created_at ? new Date(img.created_at) : null;
        const latestDate = latest?.created_at
          ? new Date(latest.created_at)
          : null;
        if (!imgDate) return latest;
        if (!latestDate) return img;
        return imgDate > latestDate ? img : latest;
      }, images[0]);

      if (latestImage?.created_at) {
        const hoursSinceLatest =
          (currentTime - new Date(latestImage.created_at).getTime()) /
          (1000 * 60 * 60);
        if (hoursSinceLatest > 24) {
          alertList.push({
            type: "info",
            message: `No new images in ${Math.floor(
              hoursSinceLatest / 24
            )} days`,
          });
        }
      }
    }

    return alertList;
  }, [jobs, images, pipelineStatusQuery.data, currentTime]);

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
        description: "FITS images",
      },
      {
        label: "Sources",
        value: sourcesCount,
        description: "Radio sources",
      },
      {
        label: "Active",
        value: activeJobs,
        description: "Running jobs",
      },
      {
        label: "Completed",
        value: completedJobs,
        description: "Finished jobs",
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
      .slice(0, 8);
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

  const dataFreshness = imagesUpdatedAt
    ? formatRelativeTime(new Date(imagesUpdatedAt).toISOString())
    : "—";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-5">
      {/* Compact Hero Section */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-blue-900 to-slate-800 text-white shadow-lg">
        <div className="p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-[0.3em] text-slate-400">
                DSA-110 Continuum Imaging Pipeline
              </p>
              <h1 className="text-2xl font-semibold leading-tight">
                Operational Dashboard
              </h1>
              <p className="text-xs text-slate-300">
                Data refreshed {dataFreshness}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                to={ROUTES.IMAGES.LIST}
                className="btn btn-primary text-xs px-3 py-1.5"
              >
                Browse images
              </Link>
              <Link
                to={ROUTES.JOBS.LIST}
                className="btn btn-outline-primary text-xs px-3 py-1.5"
              >
                View jobs
              </Link>
              <a
                href="/api/health"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-slate-400 hover:text-white transition-colors"
              >
                API Health
              </a>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 mt-4">
            {heroMetrics.map((metric) => (
              <HeroMetricCard key={metric.label} {...metric} />
            ))}
          </div>
        </div>
      </section>

      {/* Alerts Banner */}
      {alerts.length > 0 && (
        <section className="space-y-2">
          {alerts.map((alert, idx) => (
            <div
              key={idx}
              className={`flex items-center justify-between rounded-lg px-4 py-2.5 text-sm ${
                alert.type === "error"
                  ? "bg-red-50 text-red-800 border border-red-200"
                  : alert.type === "warning"
                  ? "bg-amber-50 text-amber-800 border border-amber-200"
                  : "bg-blue-50 text-blue-800 border border-blue-200"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-medium">
                  {alert.type === "error"
                    ? "!"
                    : alert.type === "warning"
                    ? "!"
                    : "i"}
                </span>
                <span>{alert.message}</span>
              </div>
              {alert.link && (
                <Link
                  to={alert.link}
                  className="text-xs font-medium underline hover:no-underline"
                >
                  View details
                </Link>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Two-column layout: Pipeline Status + Infrastructure */}
      <div className="grid gap-5 lg:grid-cols-2">
        {/* Pipeline Status */}
        <section className="card p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2
              className="text-lg font-semibold"
              style={{ color: "var(--color-text-primary)" }}
            >
              Pipeline Status
            </h2>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${pipelineHealthVariant}`}
            >
              {pipelineHealthLabel}
            </span>
          </div>
          <PipelineStatusPanel pollInterval={30000} compact />
        </section>

        {/* Infrastructure Status */}
        <section className="card p-5 space-y-3">
          <h2
            className="text-lg font-semibold"
            style={{ color: "var(--color-text-primary)" }}
          >
            Infrastructure
          </h2>
          <ServiceStatusPanel compact />
        </section>
      </div>

      {/* Sky Coverage - Full Width */}
      <section className="card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2
            className="text-lg font-semibold"
            style={{ color: "var(--color-text-primary)" }}
          >
            Sky Coverage
          </h2>
          <span
            className="text-xs"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {pointings.length} pointings mapped
          </span>
        </div>
        {pointings.length > 0 ? (
          <div className="p-0">
            <SkyCoverageMapVAST
              pointings={pointings}
              height={400}
              totalImages={images?.length}
            />
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

      {/* Recent Jobs - Compact Table */}
      <section className="card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2
            className="text-lg font-semibold"
            style={{ color: "var(--color-text-primary)" }}
          >
            Recent Jobs
          </h2>
          <Link
            to={ROUTES.JOBS.LIST}
            className="text-xs font-medium"
            style={{ color: "var(--color-primary)" }}
          >
            View all →
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
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr
                  className="text-left text-xs"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  <th className="pb-2 font-medium">Job ID</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Started</th>
                  <th className="pb-2 font-medium text-right">Duration</th>
                </tr>
              </thead>
              <tbody
                className="divide-y"
                style={{ borderColor: "var(--color-border)" }}
              >
                {latestJobs.map((job) => {
                  const started = job.started_at
                    ? new Date(job.started_at)
                    : null;
                  const finished = job.finished_at
                    ? new Date(job.finished_at)
                    : null;
                  const durationMs =
                    started && finished
                      ? finished.getTime() - started.getTime()
                      : null;
                  const durationStr = durationMs
                    ? durationMs < 60000
                      ? `${Math.round(durationMs / 1000)}s`
                      : `${Math.round(durationMs / 60000)}m`
                    : job.status === "running"
                    ? "..."
                    : "—";

                  return (
                    <tr key={job.run_id} className="hover:bg-gray-50/50">
                      <td className="py-2">
                        <Link
                          to={ROUTES.JOBS.DETAIL(job.run_id)}
                          className="font-medium hover:underline"
                          style={{ color: "var(--color-primary)" }}
                        >
                          {job.run_id.length > 30
                            ? job.run_id.slice(0, 30) + "..."
                            : job.run_id}
                        </Link>
                      </td>
                      <td className="py-2">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            JOB_STATUS_STYLES[job.status]
                          }`}
                        >
                          {JOB_STATUS_LABELS[job.status]}
                        </span>
                      </td>
                      <td
                        className="py-2 text-xs"
                        style={{ color: "var(--color-text-secondary)" }}
                      >
                        {formatRelativeTime(job.started_at)}
                      </td>
                      <td
                        className="py-2 text-xs text-right tabular-nums"
                        style={{ color: "var(--color-text-secondary)" }}
                      >
                        {durationStr}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

const HeroMetricCard: React.FC<HeroMetric> = ({
  label,
  value,
  description,
}) => (
  <div className="rounded-xl border border-white/20 bg-white/5 px-4 py-3 backdrop-blur">
    <p className="text-[10px] uppercase tracking-[0.2em] text-white/60">
      {label}
    </p>
    <p className="text-2xl font-semibold text-white">{value}</p>
    <p className="text-xs text-white/70">{description}</p>
  </div>
);

export default HomePage;
