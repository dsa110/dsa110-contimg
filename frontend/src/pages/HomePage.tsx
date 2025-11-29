import React from "react";
import { Link } from "react-router-dom";

/**
 * Home page / dashboard.
 * Shows overview of pipeline status and quick links.
 */
const HomePage: React.FC = () => {
  return (
    <div className="home-page">
      <h1 style={{ marginTop: 0 }}>DSA-110 Continuum Imaging Pipeline</h1>

      <p style={{ color: "#666", marginBottom: "24px" }}>
        Monitor and manage the radio imaging pipeline for the Deep Synoptic Array.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "20px",
          marginBottom: "32px",
        }}
      >
        <DashboardCard
          title="Images"
          description="Browse processed FITS images and view QA assessments."
          link="/images"
          count={null}
        />
        <DashboardCard
          title="Sources"
          description="Explore detected radio sources and lightcurves."
          link="/sources"
          count={null}
        />
        <DashboardCard
          title="Jobs"
          description="Monitor pipeline jobs and view provenance."
          link="/jobs"
          count={null}
        />
      </div>

      <section style={{ marginTop: "32px" }}>
        <h2>Quick Links</h2>
        <ul style={{ lineHeight: "1.8" }}>
          <li>
            <a href="/docs/troubleshooting.md" target="_blank" rel="noreferrer">
              Troubleshooting Guide
            </a>
          </li>
          <li>
            <a href="/api/health" target="_blank" rel="noreferrer">
              API Health Check
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
  count: number | null;
}

const DashboardCard: React.FC<DashboardCardProps> = ({ title, description, link, count }) => (
  <Link
    to={link}
    style={{
      display: "block",
      backgroundColor: "white",
      padding: "20px",
      borderRadius: "8px",
      boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
      textDecoration: "none",
      color: "inherit",
      transition: "box-shadow 0.2s",
    }}
  >
    <h3 style={{ margin: "0 0 8px", color: "#1a1a2e" }}>{title}</h3>
    <p style={{ margin: "0 0 12px", color: "#666", fontSize: "0.9rem" }}>{description}</p>
    {count !== null && (
      <span style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#4fc3f7" }}>{count}</span>
    )}
  </Link>
);

export default HomePage;
