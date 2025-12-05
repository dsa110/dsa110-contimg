import React, { Suspense, lazy, type ComponentType } from "react";
import { createBrowserRouter } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import { PageSkeleton } from "./components/common";
import type { PageSkeletonProps } from "./components/common";
import { ProtectedRoute } from "./components/common/auth";
import type { UserRole, Permission } from "./types/auth";

// =============================================================================
// Lazy Page Imports
// =============================================================================

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
const ConversionPage = lazy(() => import("./pages/ConversionPage"));
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
const JupyterPage = lazy(() => import("./pages/JupyterPage"));
const QARatingsPage = lazy(() => import("./pages/QARatingsPage"));
const CommentsPage = lazy(() => import("./pages/CommentsPage"));
const SharedQueriesPage = lazy(() => import("./pages/SharedQueriesPage"));
const PipelineControlPage = lazy(() => import("./pages/PipelineControlPage"));
const CARTAViewerPage = lazy(() => import("./pages/CARTAViewerPage"));

// =============================================================================
// Route Helper Functions
// =============================================================================

type SkeletonVariant = PageSkeletonProps["variant"];

/**
 * Wrap a lazy-loaded page component with Suspense and PageSkeleton fallback.
 */
function lazyPage(
  Component: ComponentType,
  variant: SkeletonVariant = "list"
): React.ReactNode {
  return (
    <Suspense fallback={<PageSkeleton variant={variant} />}>
      <Component />
    </Suspense>
  );
}

/**
 * Wrap a lazy-loaded page with Suspense and ProtectedRoute.
 */
function protectedPage(
  Component: ComponentType,
  options: {
    variant?: SkeletonVariant;
    roles?: UserRole[];
    permission?: Permission;
  } = {}
): React.ReactNode {
  const {
    variant = "list",
    roles = ["operator", "admin"],
    permission,
  } = options;
  return (
    <Suspense fallback={<PageSkeleton variant={variant} />}>
      <ProtectedRoute requiredRoles={roles} permission={permission}>
        <Component />
      </ProtectedRoute>
    </Suspense>
  );
}

// =============================================================================
// Router Configuration
// =============================================================================

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
      element: lazyPage(LoginPage, "detail"),
    },
    {
      path: "/",
      element: (
        <Suspense fallback={<PageSkeleton variant="list" showHeader />}>
          <AppLayout />
        </Suspense>
      ),
      children: [
        // Public pages
        { index: true, element: lazyPage(HomePage, "cards") },
        { path: "health", element: lazyPage(HealthDashboardPage, "cards") },

        // Images
        {
          path: "images",
          children: [
            { index: true, element: lazyPage(ImagesListPage, "list") },
            { path: ":imageId", element: lazyPage(ImageDetailPage, "detail") },
          ],
        },

        // MS (Measurement Sets)
        { path: "ms/*", element: lazyPage(MSDetailPage, "detail") },

        // Sources
        {
          path: "sources",
          children: [
            { index: true, element: lazyPage(SourcesListPage, "list") },
            {
              path: ":sourceId",
              element: lazyPage(SourceDetailPage, "detail"),
            },
          ],
        },

        // Jobs
        {
          path: "jobs",
          children: [
            { index: true, element: lazyPage(JobsListPage, "list") },
            { path: ":runId", element: lazyPage(JobDetailPage, "detail") },
          ],
        },

        // Logs
        {
          path: "logs",
          children: [
            { index: true, element: lazyPage(LogsPage, "list") },
            { path: ":runId", element: lazyPage(LogsPage, "detail") },
          ],
        },

        // Protected operator/admin pages
        {
          path: "imaging",
          element: protectedPage(InteractiveImagingPage, {
            permission: "REIMAGE",
          }),
        },
        {
          path: "calibrator-imaging",
          element: protectedPage(CalibratorImagingPage, {
            permission: "REIMAGE",
          }),
        },
        {
          path: "conversion",
          element: protectedPage(ConversionPage, { permission: "CREATE_JOB" }),
        },
        {
          path: "pipeline",
          element: protectedPage(PipelineControlPage, {
            permission: "CREATE_JOB",
          }),
        },
        {
          path: "workflows",
          element: protectedPage(WorkflowsPage, { permission: "CREATE_JOB" }),
        },
        { path: "retention", element: protectedPage(RetentionPoliciesPage) },
        { path: "cleanup", element: protectedPage(DataCleanupWizardPage) },
        { path: "backups", element: protectedPage(BackupRestorePage) },
        { path: "triggers", element: protectedPage(PipelineTriggersPage) },
        { path: "jupyter", element: protectedPage(JupyterPage) },

        // CARTA viewer (accessible to all authenticated users)
        {
          path: "viewer/carta",
          element: protectedPage(CARTAViewerPage, {
            variant: "detail",
            roles: ["viewer", "operator", "admin"],
          }),
        },

        // Pages accessible to all authenticated users
        {
          path: "vo-export",
          element: protectedPage(VOExportPage, {
            roles: ["viewer", "operator", "admin"],
          }),
        },
        {
          path: "ratings",
          element: protectedPage(QARatingsPage, {
            roles: ["viewer", "operator", "admin"],
          }),
        },
        {
          path: "comments",
          element: protectedPage(CommentsPage, {
            roles: ["viewer", "operator", "admin"],
          }),
        },
        {
          path: "queries",
          element: protectedPage(SharedQueriesPage, {
            roles: ["viewer", "operator", "admin"],
          }),
        },

        // 404 fallback
        { path: "*", element: lazyPage(NotFoundPage, "list") },
      ],
    },
  ],
  {
    basename: basename,
  }
);
