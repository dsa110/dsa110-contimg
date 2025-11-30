import React, { Suspense, lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";

const HomePage = lazy(() => import("./pages/HomePage"));
const ImageDetailPage = lazy(() => import("./pages/ImageDetailPage"));
const MSDetailPage = lazy(() => import("./pages/MSDetailPage"));
const SourceDetailPage = lazy(() => import("./pages/SourceDetailPage"));
const JobDetailPage = lazy(() => import("./pages/JobDetailPage"));
const ImagesListPage = lazy(() => import("./pages/ImagesListPage"));
const SourcesListPage = lazy(() => import("./pages/SourcesListPage"));
const JobsListPage = lazy(() => import("./pages/JobsListPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));

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
        <Suspense fallback={<div className="p-6 text-gray-600">Loading...</div>}>
          <AppLayout />
        </Suspense>
      ),
      children: [
        {
          index: true,
          element: <HomePage />,
        },
        {
          path: "images",
          children: [
            {
              index: true,
              element: <ImagesListPage />,
            },
            {
              path: ":imageId",
              element: <ImageDetailPage />,
            },
          ],
        },
        {
          path: "ms/*",
          element: <MSDetailPage />,
        },
        {
          path: "sources",
          children: [
            {
              index: true,
              element: <SourcesListPage />,
            },
            {
              path: ":sourceId",
              element: <SourceDetailPage />,
            },
          ],
        },
        {
          path: "jobs",
          children: [
            {
              index: true,
              element: <JobsListPage />,
            },
            {
              path: ":runId",
              element: <JobDetailPage />,
            },
          ],
        },
        {
          path: "*",
          element: <NotFoundPage />,
        },
      ],
    },
  ],
  {
    basename: basename,
  }
);
