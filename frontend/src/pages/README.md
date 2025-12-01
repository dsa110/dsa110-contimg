# Pages

This directory contains top-level page components that correspond to routes.

## Available Pages

| File                   | Route          | Description                                            |
| ---------------------- | -------------- | ------------------------------------------------------ |
| `HomePage.tsx`         | `/`            | Dashboard with overview statistics and recent activity |
| `SourcesListPage.tsx`  | `/sources`     | Paginated list of detected sources with filtering      |
| `SourceDetailPage.tsx` | `/sources/:id` | Detailed view of a single source                       |
| `ImagesListPage.tsx`   | `/images`      | List of processed images                               |
| `ImageDetailPage.tsx`  | `/images/:id`  | Detailed image view with FITS viewer                   |
| `JobsListPage.tsx`     | `/jobs`        | Pipeline job monitoring                                |
| `JobDetailPage.tsx`    | `/jobs/:id`    | Job details and logs                                   |
| `MSDetailPage.tsx`     | `/ms/:id`      | Measurement Set details                                |
| `NotFoundPage.tsx`     | `*`            | 404 error page                                         |

## Routing

Routes are defined in `src/router.tsx`. Each page should:

1. Handle loading states (use `PageSkeleton` from `@/components/common`)
2. Handle error states (use error boundaries)
3. Have corresponding tests in `PageName.test.tsx`

## Data Fetching

Pages use React Query hooks from `src/hooks/useQueries.ts`:

```tsx
import { useImages, useSources, useJobs } from "@/hooks/useQueries";

function ImagesListPage() {
  const { data, isLoading, error } = useImages();
  // ...
}
```
