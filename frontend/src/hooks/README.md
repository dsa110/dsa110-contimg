# Hooks

Custom React hooks for managing state and data.

## Available Hooks

### Data Fetching (React Query)

| Hook                  | Purpose                     |
| --------------------- | --------------------------- |
| `useImages()`         | Fetch list of images        |
| `useSources()`        | Fetch list of sources       |
| `useJobs()`           | Fetch pipeline jobs         |
| `useImageDetail(id)`  | Fetch single image details  |
| `useSourceDetail(id)` | Fetch single source details |

### Error Handling

| Hook                        | Purpose                          |
| --------------------------- | -------------------------------- |
| `useErrorHandler()`         | Manage error states              |
| `useErrorMapping()`         | Map error codes to user messages |
| `useNetworkNotifications()` | Show network status toasts       |
| `useNetworkStatus()`        | Track online/offline state       |

### Filtering & URL State

| Hook                   | Purpose                      |
| ---------------------- | ---------------------------- |
| `useSourceFiltering()` | Source list filter state     |
| `useUrlFilterState()`  | Sync filters with URL params |

### Other

| Hook               | Purpose                         |
| ------------------ | ------------------------------- |
| `useProvenance()`  | Fetch provenance/QA data        |
| `useImageDetail()` | Image detail with FITS metadata |

## Usage Example

```tsx
import { useImages } from "@/hooks/useQueries";
import { useErrorHandler } from "@/hooks/useErrorHandler";

function MyComponent() {
  const { data: images, isLoading, error } = useImages();
  const { handleError } = useErrorHandler();

  if (error) {
    handleError(error);
  }

  // ...
}
```
