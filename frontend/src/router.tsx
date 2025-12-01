import React, { Suspense, lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import { PageSkeleton } from "./components/common";

const HomePage = lazy(() => import("./pages/HomePage"));
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

/**
 * Application router configuration.
 *
 * Routes:
 * - / : Home/dashboard
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
            <Suspense fallback={<PageSkeleton variant="dashboard" />}>
              <HomePage />
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
              <InteractiveImagingPage />
            </Suspense>
          ),
        },
        {
          path: "calibrator-imaging",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <CalibratorImagingPage />
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
          path: "workflows",
          element: (
            <Suspense fallback={<PageSkeleton variant="list" />}>
              <WorkflowsPage />
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
