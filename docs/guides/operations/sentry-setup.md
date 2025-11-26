# Sentry Setup Guide

**Last Updated:** 2025-11-14  
**Status:** ✅ Configured for Free Tier

## Overview

Sentry error tracking is integrated into the DSA-110 frontend dashboard. The
configuration is optimized for the **free tier** (5,000 errors/month, 10,000
performance units/month).

## Installation

Sentry has been installed:

```bash
cd frontend
npm install @sentry/react
```

**Package:** `@sentry/react@10.25.0`

## Setup Steps

### 1. Create Sentry Account

1. Go to [https://sentry.io/signup/](https://sentry.io/signup/)
2. Sign up for a free account
3. Create a new project:
   - Platform: **React**
   - Project name: `dsa110-dashboard` (or your preferred name)

### 2. Get Your DSN

After creating the project, Sentry will show you a DSN (Data Source Name). It
looks like:

```
https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx@o1234567.ingest.sentry.io/1234567
```

### 3. Configure Environment Variable

Set the `VITE_SENTRY_DSN` environment variable:

**For Development:**

Create or update `.env.local` in the `frontend/` directory:

```bash
VITE_SENTRY_DSN=https://your-dsn@sentry.io/project-id
```

**For Production:**

Set the environment variable in your deployment configuration:

```bash
export VITE_SENTRY_DSN=https://your-dsn@sentry.io/project-id
```

**For Docker:**

Update `docker-compose.yml`:

```yaml
services:
  dashboard:
    environment:
      - VITE_SENTRY_DSN=${VITE_SENTRY_DSN}
```

### 4. Verify Setup

1. Start the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

2. Check the browser console - you should see:

   ```
   Sentry error tracking initialized (free tier)
   ```

3. Trigger a test error (e.g., navigate to a non-existent route)
4. Check your Sentry dashboard - the error should appear within seconds

## Free Tier Configuration

The Sentry integration is configured to stay within free tier limits:

### Error Limits

- **5,000 errors/month** - All errors are captured
- Monitor usage in Sentry dashboard
- Add filtering in `beforeSend` if needed

### Performance Limits

- **10,000 performance units/month**
- **Traces Sample Rate:** 5% in production, 10% in development
- **Replay Session Rate:** 5% of sessions
- **Replay Error Rate:** 100% of error sessions (most important)

### Configuration Details

Located in `frontend/src/utils/errorTracking.ts`:

```typescript
Sentry.init({
  dsn,
  environment: import.meta.env.MODE || "development",
  integrations: [
    Sentry.browserTracingIntegration({...}),
    Sentry.replayIntegration({...}),
  ],
  tracesSampleRate: import.meta.env.MODE === "production" ? 0.05 : 0.1,
  replaysSessionSampleRate: 0.05,
  replaysOnErrorSampleRate: 1.0,
});
```

## Features

### Automatic Error Capture

Errors are automatically captured from:

- **ErrorBoundary** - React component errors
- **API Client** - Network and API errors
- **Unhandled Promise Rejections** - Async errors

### Manual Error Capture

You can manually capture errors:

```typescript
import { captureError, captureMessage } from "../utils/errorTracking";

// Capture an error
try {
  // some code
} catch (error) {
  captureError(error, { context: "additional info" });
}

// Capture a message
captureMessage("Something happened", "warning");
```

### User Context

Set user context for better error tracking:

```typescript
import { setUserContext, clearUserContext } from "../utils/errorTracking";

// On login
setUserContext(userId, email, username);

// On logout
clearUserContext();
```

### Breadcrumbs

Add breadcrumbs to track user actions:

```typescript
import { addBreadcrumb } from "../utils/errorTracking";

addBreadcrumb("User clicked button", "user-action", "info");
addBreadcrumb("API request started", "http", "info");
```

## Monitoring Usage

### Check Error Count

1. Go to your Sentry dashboard
2. Navigate to **Settings** → **Usage**
3. Check **Errors** count (should be under 5,000/month)

### Check Performance Units

1. Go to **Settings** → **Usage**
2. Check **Performance Units** (should be under 10,000/month)

### If Approaching Limits

1. **Reduce Sample Rates:**
   - Lower `tracesSampleRate` (currently 5% in prod)
   - Lower `replaysSessionSampleRate` (currently 5%)

2. **Filter Noisy Errors:**
   - Add filtering in `beforeSend` hook
   - Example: Filter out specific error types

3. **Upgrade Plan:**
   - Consider upgrading to Team plan ($26/month)
   - Or self-host Sentry (open source)

## Troubleshooting

### Sentry Not Initializing

**Check:**

1. `VITE_SENTRY_DSN` is set correctly
2. DSN format is correct (starts with `https://`)
3. Browser console for initialization messages
4. Network tab for Sentry API calls

**Common Issues:**

- DSN not set → Check console for "Sentry DSN not provided"
- Invalid DSN → Verify DSN format
- Network blocked → Check firewall/proxy settings

### Errors Not Appearing

**Check:**

1. Sentry dashboard (may take a few seconds)
2. Browser console for errors
3. Network tab for Sentry API calls
4. Sentry project settings (correct project selected)

### High Usage

**If approaching limits:**

1. Review error frequency in Sentry
2. Add filtering for noisy errors
3. Reduce sample rates
4. Consider upgrading plan

## Best Practices

1. **Don't Capture Sensitive Data:**
   - Sentry automatically masks common sensitive fields
   - Review `beforeSend` hook for additional masking

2. **Use Tags for Filtering:**
   - Add tags to errors for better organization
   - Example: `{ tags: { source: "frontend", page: "dashboard" } }`

3. **Set User Context:**
   - Helps identify affected users
   - Set on login, clear on logout

4. **Monitor Usage:**
   - Check Sentry dashboard regularly
   - Set up alerts for high error rates

5. **Review Errors Regularly:**
   - Fix high-frequency errors first
   - Group similar errors
   - Prioritize user-impacting errors

## Integration Points

### ErrorBoundary

Errors caught by ErrorBoundary are automatically sent to Sentry:

```typescript
// frontend/src/components/ErrorBoundary.tsx
componentDidCatch(error: Error, errorInfo: ErrorInfo) {
  captureError(error, {
    componentStack: errorInfo.componentStack,
    errorBoundary: true,
  });
}
```

### API Client

API errors can be captured (currently logged to console):

```typescript
// Add to frontend/src/api/client.ts if needed
catch (error) {
  captureError(error, { endpoint: url });
}
```

## See Also

- [Error Handling & Resilience Guide](../error-handling/error-handling-resilience.md)
- [Sentry Documentation](https://docs.sentry.io/platforms/javascript/guides/react/)
- [Sentry Free Tier Limits](https://sentry.io/pricing/)
