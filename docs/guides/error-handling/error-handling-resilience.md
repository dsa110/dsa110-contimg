# Error Handling & Resilience Guide

**Last Updated:** 2025-11-14  
**Status:** ✅ Implemented

## Overview

The DSA-110 frontend dashboard includes comprehensive error handling and
resilience patterns to ensure a robust user experience even when things go
wrong.

## Features

### 1. Error Tracking (Sentry Integration)

**Status:** ✅ Implemented (Optional)

Error tracking is integrated using Sentry. It's optional and only activates if a
Sentry DSN is provided.

**Setup:**

1. **Install Sentry** (optional - only if you want error tracking):

   ```bash
   cd frontend
   npm install @sentry/react
   ```

2. **Configure Sentry DSN**: Set the environment variable:

   ```bash
   VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
   ```

3. **Automatic Initialization**: Error tracking initializes automatically in
   `App.tsx` if `VITE_SENTRY_DSN` is set.

**Features:**

- Automatic error capture from ErrorBoundary
- Browser tracing for performance monitoring
- Session replay for debugging
- User context tracking
- Breadcrumb tracking

**Usage:**

```typescript
import {
  captureError,
  captureMessage,
  addBreadcrumb,
} from "../utils/errorTracking";

// Capture an error
captureError(error, { context: "additional info" });

// Capture a message
captureMessage("Something happened", "warning");

// Add breadcrumb
addBreadcrumb("User action", "navigation", "info");
```

### 2. Error Analytics Dashboard

**Status:** ✅ Implemented

A dedicated dashboard page displays error statistics and trends.

**Access:**

- Navigate to `/error-analytics` in the dashboard
- Or add link to navigation menu

**Features:**

- Total error count
- Error rate with trend indicators
- Errors by type (network, server, client, timeout, unknown)
- Errors by HTTP status code
- Recent errors table with details
- Time range selection (24h, 7d, 30d)

**Backend Endpoint Required:** The dashboard expects a backend endpoint:

```
GET /api/operations/error-analytics?time_range=24h
```

Response format:

```json
{
  "total_errors": 42,
  "errors_by_type": {
    "network": 10,
    "server": 20,
    "client": 12
  },
  "errors_by_status": {
    "500": 15,
    "404": 8,
    "503": 5
  },
  "recent_errors": [
    {
      "id": "error-123",
      "type": "network",
      "message": "Network error: Unable to reach server",
      "timestamp": "2025-11-14T10:30:00Z",
      "status_code": null,
      "retryable": true
    }
  ],
  "error_rate": {
    "current": 2.5,
    "previous": 3.1,
    "trend": "down"
  }
}
```

### 3. Error Recovery Suggestions

**Status:** ✅ Implemented

The ErrorBoundary component now displays actionable recovery suggestions based
on error type.

**Features:**

- Context-aware suggestions
- Actionable buttons (e.g., "Retry", "Go to Login")
- Multiple suggestions per error type
- User-friendly descriptions

**Error Types and Suggestions:**

- **Network Errors:**
  - Check internet connection
  - Verify server is running
  - Retry button

- **Timeout Errors:**
  - Server may be experiencing high load
  - Retry after delay

- **Server Errors (500):**
  - Server error logged
  - Refresh page option

- **Service Unavailable (503):**
  - Service temporarily unavailable
  - Retry option

- **Authentication (401):**
  - Session expired
  - Redirect to login

- **Permission Denied (403):**
  - Insufficient permissions
  - Contact administrator

- **Not Found (404):**
  - Resource not found
  - Redirect to dashboard

- **Rate Limited (429):**
  - Too many requests
  - Wait before retry

### 4. Offline Detection

**Status:** ✅ Implemented

The application detects when it goes offline and displays appropriate
notifications.

**Features:**

- Real-time online/offline detection
- Visual indicators (snackbar notifications)
- Connection restored notifications
- Automatic status updates

**Components:**

- `useOfflineDetection` hook
- `OfflineIndicator` component

**Usage:**

```typescript
import { useOfflineDetection } from "../hooks/useOfflineDetection";

function MyComponent() {
  const { isOnline, wasOffline, lastOnlineTime } = useOfflineDetection();

  if (!isOnline) {
    return <div>You are offline</div>;
  }

  return <div>You are online</div>;
}
```

### 5. Service Worker (Offline Support)

**Status:** ✅ Implemented

A service worker provides offline support by caching static assets.

**Features:**

- Automatic registration in production
- Static asset caching
- Offline fallback pages
- Cache versioning
- Automatic cache cleanup

**Service Worker Location:**

- `frontend/public/service-worker.js`

**Registration:**

- Automatically registered in `App.tsx` for production builds
- Uses `registerServiceWorker()` utility

**Caching Strategy:**

- **Static Assets:** Cached on install
- **API Requests:** Not cached (fail gracefully)
- **Navigation:** Falls back to cached index page when offline

**Manual Cache Management:**

```typescript
import { unregisterServiceWorker } from "../utils/serviceWorker";

// Unregister service worker (for testing)
unregisterServiceWorker();
```

### 6. Retry UI for Failed Operations

**Status:** ✅ Implemented

A reusable `RetryButton` component provides retry functionality for failed
operations.

**Features:**

- Loading state during retry
- Disabled state while retrying
- Customizable labels
- Icon support

**Usage:**

```typescript
import { RetryButton } from "../components/RetryButton";

function MyComponent() {
  const handleRetry = async () => {
    await refetch();
  };

  return (
    <RetryButton
      onRetry={handleRetry}
      retryLabel="Retry Operation"
      variant="contained"
    />
  );
}
```

## Architecture

### Error Flow

1. **Error Occurs:**
   - Caught by ErrorBoundary (React errors)
   - Caught by API client (network errors)
   - Caught by retry logic (transient errors)

2. **Error Classification:**
   - `classifyError()` determines error type
   - `isRetryableError()` checks if retryable

3. **Error Tracking:**
   - Sentry captures error (if configured)
   - Error logged to console
   - Error added to analytics (if backend available)

4. **User Notification:**
   - ErrorBoundary displays user-friendly message
   - Recovery suggestions shown
   - Retry options provided

5. **Recovery:**
   - User can retry operation
   - User can navigate away
   - User can refresh page

### Resilience Patterns

1. **Circuit Breaker:**
   - Prevents cascading failures
   - Automatically opens on repeated failures
   - Half-open state for testing recovery

2. **Retry with Exponential Backoff:**
   - Automatic retries for retryable errors
   - Exponential delay between retries
   - Maximum retry limit

3. **WebSocket Reconnection:**
   - Automatic reconnection on disconnect
   - Exponential backoff for reconnection
   - Fallback to polling if WebSocket fails

4. **Offline Support:**
   - Service worker caches static assets
   - Offline detection and notifications
   - Graceful degradation

## Configuration

### Environment Variables

```bash
# Sentry DSN (optional)
VITE_SENTRY_DSN=https://your-dsn@sentry.io/project-id

# Error Analytics (backend endpoint)
# Configured in API client: /api/operations/error-analytics
```

### Error Tracking Configuration

Error tracking is configured in `frontend/src/utils/errorTracking.ts`:

- **Environment:** Set from `import.meta.env.MODE`
- **Traces Sample Rate:** 10% in production, 100% in development
- **Replay Sample Rate:** 10% for sessions, 100% for errors

## Testing

### Testing Error Handling

1. **Trigger Network Error:**
   - Disconnect network
   - Make API request
   - Verify error message and recovery suggestions

2. **Trigger Server Error:**
   - Mock 500 response
   - Verify error handling
   - Check Sentry capture (if configured)

3. **Test Offline Detection:**
   - Toggle network in browser DevTools
   - Verify offline indicator appears
   - Verify connection restored notification

4. **Test Service Worker:**
   - Go offline
   - Navigate to cached pages
   - Verify offline functionality

## Best Practices

1. **Always Use ErrorBoundary:**
   - Wrap route components in ErrorBoundary
   - Provide fallback UI for critical sections

2. **Classify Errors:**
   - Use `classifyError()` for all errors
   - Check `retryable` property before retrying

3. **Provide Recovery Options:**
   - Always show retry button for retryable errors
   - Provide navigation options
   - Show helpful error messages

4. **Track Errors:**
   - Use Sentry for production error tracking
   - Add context to error captures
   - Monitor error analytics dashboard

5. **Handle Offline State:**
   - Check `isOnline` before making requests
   - Show offline indicators
   - Cache critical data

## Troubleshooting

### Sentry Not Working

1. Check `VITE_SENTRY_DSN` is set
2. Verify Sentry package is installed
3. Check browser console for initialization errors
4. Verify network connectivity to Sentry

### Service Worker Not Registering

1. Check browser supports service workers
2. Verify HTTPS (or localhost)
3. Check service worker file exists at `/service-worker.js`
4. Check browser console for registration errors

### Error Analytics Not Loading

1. Verify backend endpoint exists
2. Check API client configuration
3. Verify authentication (if required)
4. Check network tab for request/response

## See Also

- Error Utils
- Circuit Breaker Pattern
- Retry Logic
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
