# DSA-110 Dashboard: Error Handling & Resilience

**Date:** 2025-11-12  
**Status:** Consolidated error handling documentation  
**Audience:** Frontend developers, backend developers

---

## Table of Contents

1. [Error Handling Architecture](#error-handling-architecture)
2. [Error Classification](#error-classification)
3. [Circuit Breaker Pattern](#circuit-breaker-pattern)
4. [Retry Logic](#retry-logic)
5. [Error Boundaries](#error-boundaries)
6. [User-Friendly Error Messages](#user-friendly-error-messages)
7. [Error Logging](#error-logging)
8. [Resilience Patterns](#resilience-patterns)

---

## Error Handling Architecture

### Multi-Layer Approach

**Three Layers:**

1. **API Client Layer** - Network errors, retries, circuit breaker
2. **React Query Layer** - Query errors, retry logic
3. **Component Layer** - Error boundaries, user feedback

### Error Flow

```
Network Error
    :arrow_down:
API Client Interceptor
    :arrow_down:
Error Classification
    :arrow_down:
Retry Logic (if retryable)
    :arrow_down:
Circuit Breaker Check
    :arrow_down:
React Query Error Handler
    :arrow_down:
Component Error Display
```

---

## Error Classification

### Error Types

**Network Errors:**

- Connection timeout
- DNS resolution failure
- Network unreachable
- CORS errors

**Server Errors:**

- 500 Internal Server Error
- 503 Service Unavailable
- 502 Bad Gateway
- 504 Gateway Timeout

**Client Errors:**

- 400 Bad Request
- 404 Not Found
- 422 Validation Error
- 401 Unauthorized

**Application Errors:**

- Invalid data format
- Missing required fields
- Business logic violations

### Classification Function

**Implementation (`errorUtils.ts`):**

```typescript
export function classifyError(error: AxiosError): ErrorClassification {
  if (!error.response) {
    // Network error
    return {
      type: "network",
      retryable: true,
      userMessage: "Network connection failed. Please check your connection.",
    };
  }

  const status = error.response.status;

  if (status >= 500) {
    // Server error - retryable
    return {
      type: "server",
      retryable: true,
      userMessage: "Server error. Please try again.",
    };
  }

  if (status === 429) {
    // Rate limit - retryable with backoff
    return {
      type: "rate_limit",
      retryable: true,
      userMessage: "Too many requests. Please wait a moment.",
    };
  }

  if (status >= 400 && status < 500) {
    // Client error - not retryable
    return {
      type: "client",
      retryable: false,
      userMessage: "Invalid request. Please check your input.",
    };
  }

  return {
    type: "unknown",
    retryable: false,
    userMessage: "An unexpected error occurred.",
  };
}
```

---

## Circuit Breaker Pattern

### Implementation

**Circuit Breaker (`circuitBreaker.ts`):**

```typescript
interface CircuitBreakerConfig {
  failureThreshold: number; // Open after N failures
  resetTimeout: number; // Try reset after timeout
  monitoringPeriod: number; // Monitoring window
}

class CircuitBreaker {
  private state: "closed" | "open" | "half-open" = "closed";
  private failures = 0;
  private lastFailureTime = 0;

  canAttempt(): boolean {
    if (this.state === "closed") return true;

    if (this.state === "open") {
      const timeSinceFailure = Date.now() - this.lastFailureTime;
      if (timeSinceFailure > this.resetTimeout) {
        this.state = "half-open";
        return true;
      }
      return false;
    }

    // half-open
    return true;
  }

  recordSuccess(): void {
    this.failures = 0;
    this.state = "closed";
  }

  recordFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();

    if (this.failures >= this.failureThreshold) {
      this.state = "open";
    }
  }
}
```

### Configuration

**Default Settings:**

- Failure threshold: 5 failures
- Reset timeout: 30 seconds
- Monitoring period: 60 seconds

**Usage:**

```typescript
const circuitBreaker = createCircuitBreaker({
  failureThreshold: 5,
  resetTimeout: 30000,
  monitoringPeriod: 60000,
});
```

---

## Retry Logic

### Exponential Backoff

**Strategy:**

```typescript
const retryDelay = (attemptIndex: number): number => {
  return Math.min(
    1000 * Math.pow(2, attemptIndex), // 1s, 2s, 4s, 8s...
    10000 // Max 10 seconds
  );
};
```

### Retry Configuration

**React Query:**

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (failureCount >= 3) return false;
        return isRetryableError(error);
      },
      retryDelay: (attemptIndex) => {
        return Math.min(1000 * Math.pow(2, attemptIndex), 10000);
      },
    },
  },
});
```

**API Client:**

```typescript
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as InternalAxiosRequestConfig & {
      _retryCount?: number;
    };
    const retryCount = config._retryCount || 0;
    const maxRetries = 3;

    if (isRetryableError(error) && retryCount < maxRetries) {
      config._retryCount = retryCount + 1;
      const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return apiClient.request(config);
    }

    return Promise.reject(error);
  }
);
```

---

## Error Boundaries

### Implementation

**Error Boundary Component:**

```typescript
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error('Error boundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box>
          <Alert severity="error">
            Something went wrong. Please refresh the page.
          </Alert>
          <Button onClick={() => window.location.reload()}>
            Reload Page
          </Button>
        </Box>
      );
    }

    return this.props.children;
  }
}
```

### Usage

**App-Level:**

```typescript
<ErrorBoundary>
  <AppContent />
</ErrorBoundary>
```

**Page-Level:**

```typescript
<ErrorBoundary>
  <DashboardPage />
</ErrorBoundary>
```

---

## User-Friendly Error Messages

### Message Mapping

**User-Friendly Messages (`errorUtils.ts`):**

```typescript
export function getUserFriendlyMessage(error: AxiosError): string {
  if (!error.response) {
    return "Unable to connect to server. Please check your network connection.";
  }

  const status = error.response.status;
  const data = error.response.data as any;

  // Use server-provided message if available
  if (data?.error) {
    return data.error;
  }

  // Fallback to status-based messages
  switch (status) {
    case 400:
      return "Invalid request. Please check your input.";
    case 401:
      return "Authentication required. Please log in.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "The requested resource was not found.";
    case 422:
      return "Validation error. Please check your input.";
    case 500:
      return "Server error. Please try again later.";
    case 503:
      return "Service temporarily unavailable. Please try again later.";
    default:
      return "An unexpected error occurred. Please try again.";
  }
}
```

### Error Display

**Component Pattern:**

```typescript
const { data, error, isLoading } = useQuery(...);

if (error) {
  return (
    <Alert severity="error">
      {error.userMessage || 'An error occurred'}
    </Alert>
  );
}
```

---

## Error Logging

### Logging Utility

**Logger (`logger.ts`):**

```typescript
export const logger = {
  error: (message: string, error?: any, context?: any) => {
    console.error(message, error, context);
    // Send to error tracking service (e.g., Sentry)
  },
  warn: (message: string, context?: any) => {
    console.warn(message, context);
  },
  info: (message: string, context?: any) => {
    console.info(message, context);
  },
  apiError: (message: string, error: AxiosError) => {
    logger.error(message, {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      data: error.response?.data,
    });
  },
};
```

### Error Tracking

**Integration Points:**

- API client interceptors
- React Query error handlers
- Error boundaries
- WebSocket error handlers

---

## Resilience Patterns

### Graceful Degradation

**Pattern:**

```typescript
const { data, error } = useQuery({
  queryKey: ["non-critical", "data"],
  queryFn: fetchNonCriticalData,
  retry: false, // Don't retry non-critical data
  onError: () => {
    // Show warning but don't block UI
    showNotification("Some data unavailable", "warning");
  },
});
```

### Fallback Data

**Pattern:**

```typescript
const { data = defaultData } = useQuery({
  queryKey: ["data"],
  queryFn: fetchData,
  initialData: defaultData, // Use default if fetch fails
});
```

### Timeout Handling

**Pattern:**

```typescript
const apiClient = axios.create({
  timeout: 30000, // 30 second timeout
});

// Handle timeout specifically
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.code === "ECONNABORTED") {
      return Promise.reject({
        ...error,
        userMessage: "Request timed out. Please try again.",
      });
    }
    return Promise.reject(error);
  }
);
```

---

## See Also

- [Frontend Architecture](./dashboard_frontend_architecture.md) - Component
  architecture
- [Backend API & Integration](../../reference/dashboard_backend_api.md) - API error
  handling
- [State Management](./dashboard_architecture.md) - State error handling
