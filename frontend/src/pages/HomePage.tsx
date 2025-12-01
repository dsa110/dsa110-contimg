import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { SkyCoverageMap, type Pointing } from "../components/skymap";
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

  const ratingStats = useMemo(() => {
    if (!images)
      return { byUser: [], byTag: [], tagDistribution: [], total: 0, rated: 0 };

    const imgArr = images as Array<{ qa_grade?: string; run_id?: string }>;
    const gradeCount = { good: 0, warn: 0, fail: 0 };
    imgArr.forEach((img) => {
      if (img.qa_grade === "good") gradeCount.good++;
      else if (img.qa_grade === "warn") gradeCount.warn++;
      else if (img.qa_grade === "fail") gradeCount.fail++;
    });

    const rated = gradeCount.good + gradeCount.warn + gradeCount.fail;
    const total = imgArr.length;

    return {
      byUser: [
        {
          label: "Pipeline",
          trueCount: gradeCount.good,
          falseCount: gradeCount.fail,
          unsureCount: gradeCount.warn,
        },
      ],
      byTag: [
        {
          label: "Good",
          trueCount: gradeCount.good,
          falseCount: 0,
          unsureCount: 0,
        },
        {
          label: "Warning",
          trueCount: 0,
          falseCount: 0,
          unsureCount: gradeCount.warn,
        },
        {
          label: "Fail",
          trueCount: 0,
          falseCount: gradeCount.fail,
          unsureCount: 0,
        },
      ],
      tagDistribution: [
        {
          tag: "Good",
          count: gradeCount.good,
          percentage: total > 0 ? (gradeCount.good / total) * 100 : 0,
        },
        {
          tag: "Warning",
          count: gradeCount.warn,
          percentage: total > 0 ? (gradeCount.warn / total) * 100 : 0,
        },
        {
          tag: "Fail",
          count: gradeCount.fail,
          percentage: total > 0 ? (gradeCount.fail / total) * 100 : 0,
        },
      ],
      total,
      rated,
    };
  }, [images]);

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
    const totalImages = ratingStats.total;
    const rated = ratingStats.rated;
    const ratedPct =
      totalImages > 0 ? Math.round((rated / totalImages) * 100) : 0;
    const activeJobs = jobs
      ? jobs.filter(
          (job) => job.status === "running" || job.status === "pending"
        ).length
      : 0;
    const sourcesCount = sources?.length ?? 0;
    return [
      {
        label: "Images processed",
        value: totalImages,
        description: "All FITS outputs tracked in the catalog",
      },
      {
        label: "QA rated",
        value: `${rated}/${totalImages}`,
        description: `${ratedPct}% of candidates reviewed`,
      },
      {
        label: "Active jobs",
        value: activeJobs,
        description: "Running or pending pipeline tasks",
      },
      {
        label: "Sources tracked",
        value: sourcesCount,
        description: "Unique radio sources indexed",
      },
    ];
  }, [ratingStats, jobs, sources]);

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

  const showSummaryCards = !showStatsDashboard && ratingStats.total > 0;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
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
                Monitor quality assurance, sky coverage, and pipeline activity
                across the entire imaging stack. Dive into job-level detail or
                explore catalogs with a single click.
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
                View pipeline jobs
              </Link>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {heroMetrics.map((metric) => (
              <HeroMetricCard key={metric.label} {...metric} />
            ))}
          </div>
        </div>
        <div className="border-t border-white/20 bg-white/5 px-8 py-4 text-xs uppercase tracking-widest text-white/70">
          {`Pipeline health: ${pipelineHealthLabel} • Workers: ${
            pipelineStatusQuery.data?.worker_count ?? "—"
          } • Last sync: ${pipelineLastUpdated}`}
        </div>
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
            <SkyCoverageMap
              pointings={pointings}
              height={400}
              showGalacticPlane
              showEcliptic
              colorScheme="status"
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

      {/* QA Rating Overview - Full Width */}
      <section className="card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2
              className="text-xl font-semibold"
              style={{ color: "var(--color-text-primary)" }}
            >
              QA Rating Overview
            </h2>
            <p
              className="text-sm"
              style={{ color: "var(--color-text-secondary)" }}
            >
              Track how many candidates were graded by the pipeline team.
            </p>
          </div>
          <button
            onClick={() => setShowStatsDashboard((prev) => !prev)}
            className="text-sm transition-colors"
            style={{ color: "var(--color-primary)" }}
          >
            {showStatsDashboard ? "Hide charts" : "Show charts"}
          </button>
        </div>

        {showSummaryCards && (
          <div className="grid grid-cols-3 gap-4 text-sm">
            {ratingStats.tagDistribution.map((entry) => (
              <div
                key={entry.tag}
                className="rounded-lg p-3"
                style={{
                  backgroundColor: "var(--color-bg-surface)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p
                  className="text-xs uppercase tracking-widest"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {entry.tag}
                </p>
                <p
                  className="text-2xl font-semibold"
                  style={{ color: "var(--color-text-primary)" }}
                >
                  {entry.count}
                </p>
                <p
                  className="text-xs"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {entry.percentage.toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        )}

        {showStatsDashboard && (
          <div className="card-body p-0">
            <StatsDashboard
              byUser={ratingStats.byUser}
              byTag={ratingStats.byTag}
              tagDistribution={ratingStats.tagDistribution}
              totalCandidates={ratingStats.total}
              ratedCandidates={ratingStats.rated}
              isLoading={imagesLoading}
            />
          </div>
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="card p-6 space-y-4">
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
                ABSURD worker state updates every 30 seconds.
              </p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${pipelineHealthVariant}`}
            >
              {pipelineHealthLabel}
            </span>
          </div>
          <PipelineStatusPanel pollInterval={30000} />
        </div>
        <div className="card p-6 space-y-4">
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
                Snapshot of the latest pipeline runs.
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
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <DashboardCard
          title="Images"
          description="Browse processed FITS images and view QA assessments."
          link={ROUTES.IMAGES.LIST}
          icon="IMG"
        />
        <DashboardCard
          title="Sources"
          description="Explore detected radio sources and lightcurves."
          link={ROUTES.SOURCES.LIST}
          icon="SRC"
        />
        <DashboardCard
          title="Jobs"
          description="Monitor pipeline jobs and view provenance."
          link={ROUTES.JOBS.LIST}
          icon="JOB"
        />
      </div>

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
              rel="noreferrer"
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
              rel="noreferrer"
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

interface DashboardCardProps {
  title: string;
  description: string;
  link: string;
  icon: string;
}

const DashboardCard: React.FC<DashboardCardProps> = ({
  title,
  description,
  link,
  icon,
}) => (
  <Link to={link} className="card p-6 hover:shadow-lg transition-shadow group">
    <div className="text-3xl mb-3" style={{ color: "var(--color-primary)" }}>
      {icon}
    </div>
    <h3
      className="text-lg font-semibold transition-colors mb-2"
      style={{ color: "var(--color-text-primary)" }}
    >
      {title}
    </h3>
    <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
      {description}
    </p>
  </Link>
);

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
