import { createBrowserRouter } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import HomePage from "./pages/HomePage";
import ImageDetailPage from "./pages/ImageDetailPage";
import MSDetailPage from "./pages/MSDetailPage";
import SourceDetailPage from "./pages/SourceDetailPage";
import JobDetailPage from "./pages/JobDetailPage";
import ImagesListPage from "./pages/ImagesListPage";
import SourcesListPage from "./pages/SourcesListPage";
import JobsListPage from "./pages/JobsListPage";
import NotFoundPage from "./pages/NotFoundPage";

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

// Detect if running on GitHub Pages (production build with base path)
const basename = import.meta.env.BASE_URL;

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppLayout />,
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
