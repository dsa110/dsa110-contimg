# API Client

This directory contains the HTTP client and resilience patterns for backend communication.

## Files

| File             | Purpose                                  |
| ---------------- | ---------------------------------------- |
| `client.ts`      | Axios-based API client with interceptors |
| `client.test.ts` | API client unit tests                    |
| `resilience/`    | Circuit breaker and retry logic          |

## Usage

```tsx
import apiClient from "@/api/client";

// GET request
const response = await apiClient.get("/sources");

// POST request
await apiClient.post("/images/123/rating", { tagId: "good" });

// DELETE request
await apiClient.delete("/images/123");
```

## Resilience Features

The API client includes built-in resilience patterns:

### Circuit Breaker

Prevents cascading failures when the backend is unhealthy:

```tsx
import { isCircuitOpen, getCircuitBreakerState } from "@/api/resilience";

if (isCircuitOpen()) {
  // Show fallback UI or cached data
}
```

### Automatic Retry

Retries failed requests with exponential backoff:

- Retries on 5xx errors and network failures
- Does NOT retry on 4xx client errors
- Configurable max retries and delays

### Disable Retry for Specific Requests

```tsx
import { noRetry } from "@/api/resilience";

// This request won't be retried on failure
await apiClient.post("/ratings", data, noRetry());
```

## Error Handling

All errors are normalized to `ErrorResponse` shape:

```tsx
import type { ErrorResponse } from "@/types";

try {
  await apiClient.get("/sources");
} catch (error) {
  const err = error as ErrorResponse;
  console.log(err.message); // User-friendly message
  console.log(err.status); // HTTP status code
  console.log(err.errorCode); // Application error code
}
```

## Configuration

The client is configured via `src/config/index.ts`:

- `config.api.baseUrl` - API base URL (default: `/api`)
- `config.api.timeout` - Request timeout in ms
