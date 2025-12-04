import React, { Suspense, lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import { PageSkeleton } from "./components/common";
import { ProtectedRoute } from "./components/common/auth";

const HomePage = lazy(() => import("./pages/HomePage"));
const HealthDashboardPage = lazy(() => import("./pages/HealthDashboardPage"));
const ImageDetailPage = lazy(() => import("./pages/ImageDetailPage"));
const MSDetailPage = lazy(() => import("./pages/MSDetailPage"));
const SourceDetailPage = lazy(() => import("./pages/SourceDetailPage"));
const JobDetailPage = lazy(() => import("./pages/JobDetailPage"));
const ImagesListPage = lazy(() => import("./pages/ImagesListPage"));
const SourcesListPage = lazy(() => import("./pages/SourcesListPage"));
const JobsListPage = lazy(() => import("./pages/JobsListPage"));
const InteractiveImagingPage = lazy(
  () => import("./pages/InteractiveImagingPage")
);
const CalibratorImagingPage = lazy(
  () => import("./pages/CalibratorImagingPage")
);
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const WorkflowsPage = lazy(() => import("./pages/WorkflowsPage"));
const RetentionPoliciesPage = lazy(
  () => import("./pages/RetentionPoliciesPage")
);
const LogsPage = lazy(() => import("./pages/LogsPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const DataCleanupWizardPage = lazy(
  () => import("./pages/DataCleanupWizardPage")
);
const BackupRestorePage = lazy(() => import("./pages/BackupRestorePage"));
const PipelineTriggersPage = lazy(() => import("./pages/PipelineTriggersPage"));
const VOExportPage = lazy(() => import("./pages/VOExportPage"));

/**
 * Application router configuration.
 *
 * Routes:
 * - / : Home/dashboard
 * - /health : Health monitoring dashboard
 * - /images : List of images
 * - /images/:imageId : Image detail
 * - /ms/* : Measurement set detail (path as wildcard)
 * - /sources : List of sources
 * - /sources/:sourceId : Source detail
 * - /jobs : List of jobs
 * - /jobs/:runId : Job detail/provenance
 *
 * All detail pages use useParams() internally to access route parameters.
 *
 * Note: basename is set for GitHub Pages deployment where the app
 * is served from /dsa110-contimg/ subdirectory.
 */

import { config } from "./config";

// Detect if running on GitHub Pages (production build with base path)
const basename = config.app.basePath;

export const router = createBrowserRouter(
  [
    {
      path: "/login",
      element: (
        <Suspense fallback={<PageSkeleton variant="detail" />}>
          <LoginPage />
        </Suspense>
      ),
    },
    {
      path: "/",
      element: (
        <Suspense fallback={<PageSkeleton variant="list" showHeader />}>
          <AppLayout />
        </Suspense>
      ),
      children: [
        {
          index: true,
          element: (
            <Suspense fallback={<PageSkeleton variant="cards" />}>
              <HomePage />
            </Suspense>
          ),
        },
        {
          path: "health",
          element: (
            <Suspense fallback={<PageSkeleton variant="cards" />}>
              <HealthDashboardPage />
            </Suspense>
          ),
        },
        {
          path: "images",
          children: [
            {
              index: true,
              element: (
                <Suspense fallback={<PageSkeleton variant="list" />}>
                  <ImagesListPage />
                </Suspense>
              ),
            },
            {
              path: ":imageId",
              element: (
                <Suspense fallback={<PageSkeleton variant="detail" />}>
                  <ImageDetailPage />
                </Suspense>
              ),
            },
          ],
        },
        {
          path: "ms/*",
          element: (
            <Suspense fallback={<PageSkeleton variant="detail" />}>
              <MSDetailPage />
            </Suspense>
          ),
        },
        {
          path: "imaging",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute
                permission="REIMAGE"
                requiredRoles={["operator", "admin"]}
              >
                <InteractiveImagingPage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "calibrator-imaging",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute
                permission="REIMAGE"
                requiredRoles={["operator", "admin"]}
              >
                <CalibratorImagingPage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "sources",
          children: [
            {
              index: true,
              element: (
                <Suspense fallback={<PageSkeleton variant="list" />}>
                  <SourcesListPage />
                </Suspense>
              ),
            },
            {
              path: ":sourceId",
              element: (
                <Suspense fallback={<PageSkeleton variant="detail" />}>
                  <SourceDetailPage />
                </Suspense>
              ),
            },
          ],
        },
        {
          path: "jobs",
          children: [
            {
              index: true,
              element: (
                <Suspense fallback={<PageSkeleton variant="list" />}>
                  <JobsListPage />
                </Suspense>
              ),
            },
            {
              path: ":runId",
              element: (
                <Suspense fallback={<PageSkeleton variant="detail" />}>
                  <JobDetailPage />
                </Suspense>
              ),
            },
          ],
        },
        {
          path: "logs",
          children: [
            {
              index: true,
              element: (
                <Suspense fallback={<PageSkeleton variant="list" />}>
                  <LogsPage />
                </Suspense>
              ),
            },
            {
              path: ":runId",
              element: (
                <Suspense fallback={<PageSkeleton variant="detail" />}>
                  <LogsPage />
                </Suspense>
              ),
            },
          ],
        },
        {
          path: "workflows",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute
                permission="CREATE_JOB"
                requiredRoles={["operator", "admin"]}
              >
                <WorkflowsPage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "retention",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute requiredRoles={["operator", "admin"]}>
                <RetentionPoliciesPage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "cleanup",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute requiredRoles={["operator", "admin"]}>
                <DataCleanupWizardPage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "backups",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute requiredRoles={["operator", "admin"]}>
                <BackupRestorePage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "triggers",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute requiredRoles={["operator", "admin"]}>
                <PipelineTriggersPage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "vo-export",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <ProtectedRoute requiredRoles={["viewer", "operator", "admin"]}>
                <VOExportPage />
              </ProtectedRoute>
            </Suspense>
          ),
        },
        {
          path: "*",
          element: (
            <Suspense fallback={<div className="p-6">Loading...</div>}>
              <NotFoundPage />
            </Suspense>
          ),
        },
      ],
    },
  ],
  {
    basename: basename,
  }
);
