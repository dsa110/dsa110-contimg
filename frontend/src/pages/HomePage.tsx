import React from "react";
import { Link } from "react-router-dom";

/**
 * Home page / dashboard.
 * Shows overview of pipeline status and quick links.
 */
const HomePage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">DSA-110 Continuum Imaging Pipeline</h1>

      <p className="text-gray-600 mb-8">
        Monitor and manage the radio imaging pipeline for the Deep Synoptic Array.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <DashboardCard
          title="Images"
          description="Browse processed FITS images and view QA assessments."
          link="/images"
          icon="🖼️"
        />
        <DashboardCard
          title="Sources"
          description="Explore detected radio sources and lightcurves."
          link="/sources"
          icon="⭐"
        />
        <DashboardCard
          title="Jobs"
          description="Monitor pipeline jobs and view provenance."
          link="/jobs"
          icon="⚙️"
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
              📖 Troubleshooting Guide
            </a>
          </li>
          <li>
            <a
              href="/api/health"
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 hover:text-blue-800 hover:underline"
            >
              🔧 API Health Check
            </a>
          </li>
        </ul>
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
