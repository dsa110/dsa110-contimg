import React, { useState } from "react";
import { Link } from "react-router-dom";
import { StatCardGrid } from "../components/summary";
import { SkyCoverageMap } from "../components/skymap";
import { StatsDashboard, ServiceStatusPanel } from "../components/stats";
import { useImages, useSources, useJobs } from "../hooks/useQueries";

/**
 * Home page / dashboard.
 * Shows overview of pipeline status, stats, and sky coverage.
 */
const HomePage: React.FC = () => {
  const { data: images, isLoading: imagesLoading } = useImages();
  const { data: sources, isLoading: sourcesLoading } = useSources();
  const { data: jobs, isLoading: jobsLoading } = useJobs();
  const [showStatsDashboard, setShowStatsDashboard] = useState(false);

  // Build rating stats for StatsDashboard from image QA grades
  const ratingStats = React.useMemo(() => {
    if (!images) return { byUser: [], byTag: [], tagDistribution: [], total: 0, rated: 0 };

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
        { label: "Good", trueCount: gradeCount.good, falseCount: 0, unsureCount: 0 },
        { label: "Warning", trueCount: 0, falseCount: 0, unsureCount: gradeCount.warn },
        { label: "Fail", trueCount: 0, falseCount: gradeCount.fail, unsureCount: 0 },
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

  // Build stats for StatCardGrid
  const stats = [
    {
      label: "Total Images",
      value: images?.length ?? 0,
      icon: "IMG",
      href: "/images",
      variant: "primary" as const,
    },
    {
      label: "Detected Sources",
      value: sources?.length ?? 0,
      icon: "SRC",
      href: "/sources",
      variant: "success" as const,
    },
    {
      label: "Pipeline Jobs",
      value: jobs?.length ?? 0,
      icon: "JOB",
      href: "/jobs",
      variant: "info" as const,
    },
  ];

  // Build pointing data for sky coverage from images
  const pointings = React.useMemo(() => {
    if (!images) return [];
    // TODO: Import and use Image type from api/client.ts instead of 'any'
    // The images array should be typed as Image[] from the useImages hook
    return images
      .filter((img: any) => img.pointing_ra_deg != null && img.pointing_dec_deg != null)
      .map((img: any) => ({
        id: img.id,
        ra: img.pointing_ra_deg,
        dec: img.pointing_dec_deg,
        label: img.path?.split("/").pop() || img.id,
        status:
          img.qa_grade === "good" ? "completed" : img.qa_grade === "fail" ? "failed" : "scheduled",
      }));
  }, [images]);

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">DSA-110 Continuum Imaging Pipeline</h1>

      <p className="text-gray-600 mb-8">
        Monitor and manage the radio imaging pipeline for the Deep Synoptic Array.
      </p>

      {/* Stats overview */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Pipeline Overview</h2>
          <button
            onClick={() => setShowStatsDashboard(!showStatsDashboard)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showStatsDashboard ? "Hide Details" : "Show Detailed Stats"}
          </button>
        </div>
        <StatCardGrid cards={stats} isLoading={imagesLoading || sourcesLoading || jobsLoading} />
      </section>

      {/* Detailed Stats Dashboard */}
      {showStatsDashboard && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">QA Rating Statistics</h2>
          <div className="card p-4">
            <StatsDashboard
              byUser={ratingStats.byUser}
              byTag={ratingStats.byTag}
              tagDistribution={ratingStats.tagDistribution}
              totalCandidates={ratingStats.total}
              ratedCandidates={ratingStats.rated}
              isLoading={imagesLoading}
            />
          </div>
        </section>
      )}

      {/* Sky Coverage Map */}
      {pointings.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Sky Coverage</h2>
          <div className="card p-4">
            {/* TODO: Fix pointings type to match SkyCoverageMapProps['pointings'] */}
            <SkyCoverageMap
              pointings={pointings as any}
              height={350}
              showGalacticPlane
              showEcliptic
              colorScheme="status"
            />
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <DashboardCard
          title="Images"
          description="Browse processed FITS images and view QA assessments."
          link="/images"
          icon="IMG"
        />
        <DashboardCard
          title="Sources"
          description="Explore detected radio sources and lightcurves."
          link="/sources"
          icon="SRC"
        />
        <DashboardCard
          title="Jobs"
          description="Monitor pipeline jobs and view provenance."
          link="/jobs"
          icon="JOB"
        />
      </div>

      <section className="card p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Links</h2>
        <ul className="space-y-2">
          <li>
            <a
              href="/docs/troubleshooting.md"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline"
            >
              Troubleshooting Guide
            </a>
          </li>
          <li>
            <a
              href="/api/health"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline"
            >
              API Health Check
            </a>
          </li>
        </ul>
      </section>

      {/* Service Status Panel */}
      <section className="mt-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Infrastructure Status</h2>
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

const DashboardCard: React.FC<DashboardCardProps> = ({ title, description, link, icon }) => (
  <Link to={link} className="card p-6 hover:shadow-lg transition-shadow group">
    <div className="text-3xl mb-3">{icon}</div>
    <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors mb-2">
      {title}
    </h3>
    <p className="text-gray-600 text-sm">{description}</p>
  </Link>
);

export default HomePage;
