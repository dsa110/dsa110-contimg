import { createBrowserRouter, Navigate } from "react-router-dom";
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
 */
export const router = createBrowserRouter([
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
            element: <ImageDetailPageWrapper />,
          },
        ],
      },
      {
        path: "ms/*",
        element: <MSDetailPageWrapper />,
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
            element: <SourceDetailPageWrapper />,
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
]);

/**
 * Wrapper components to extract route params and pass to page components.
 */
import { useParams } from "react-router-dom";

function ImageDetailPageWrapper() {
  const { imageId } = useParams<{ imageId: string }>();
  if (!imageId) return <NotFoundPage />;
  return <ImageDetailPage imageId={imageId} />;
}

function MSDetailPageWrapper() {
  const { "*": msPath } = useParams<{ "*": string }>();
  if (!msPath) return <NotFoundPage />;
  // Decode the path - it may be URL-encoded
  const decodedPath = decodeURIComponent(msPath);
  return <MSDetailPage msPath={decodedPath} />;
}

function SourceDetailPageWrapper() {
  const { sourceId } = useParams<{ sourceId: string }>();
  if (!sourceId) return <NotFoundPage />;
  return <SourceDetailPage sourceId={sourceId} />;
}
