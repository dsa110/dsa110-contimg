# System Status Page

## Overview

The System Status page provides a centralized dashboard for monitoring the
health and connectivity of all services, APIs, and external integrations in the
DSA-110 pipeline system.

## Location

- **Route**: `/system-status`
- **Navigation**: System → System Status
- **Breadcrumb**: Dashboard → System Status

## Features

### 1. Overall System Health

- At-a-glance health indicator showing overall system status
- Quick counts of healthy, degraded, and unhealthy services
- Last updated timestamp

### 2. Backend Services Monitoring

Automatically tests core API endpoints:

- Backend API Health (`/api/health`)
- Pipeline API (`/api/pipeline/metrics/summary`)
- Jobs API (`/api/jobs`)
- MS List API (`/api/ms`)

### 3. External Services Monitoring

Tests connectivity to external integrations:

- **CARTA Frontend** (port 9002)
- **ABSURD API** (`/api/absurd/health`)

### 4. Service Details

For each service, displays:

- Status indicator (healthy/unhealthy/degraded/unknown)
- Response time in milliseconds
- Endpoint URL
- Expandable details with:
  - Last check timestamp
  - HTTP status codes
  - Error messages (if applicable)

### 5. Auto-Refresh

- Auto-refresh toggle (default: ON)
- Refreshes every 30 seconds when enabled
- Manual refresh button available

### 6. Configuration Display

Shows current system configuration:

- API Base URL
- CARTA Backend URL
- CARTA Frontend URL

### 7. Troubleshooting Tips

Built-in help section with common fixes for service issues.

## Status Indicators

| Status      | Color  | Meaning                            |
| ----------- | ------ | ---------------------------------- |
| ✓ Healthy   | Green  | Service responding normally        |
| ⚠ Degraded | Yellow | Service responding but with issues |
| ✕ Unhealthy | Red    | Service not responding or erroring |
| ? Unknown   | Gray   | Status cannot be determined        |

## Use Cases

### 1. Quick Health Check

Navigate to System Status to see if all services are operational before starting
work.

### 2. Troubleshooting Connection Issues

When a page fails to load data:

1. Check System Status to identify which service is down
2. Expand service details to see specific error messages
3. Follow troubleshooting tips for the affected service

### 3. Post-Deployment Verification

After updating services or restarting containers:

1. Open System Status
2. Use manual refresh to test all connections
3. Verify all services show "healthy" status

### 4. Monitoring Service Performance

- Check response times to identify slow services
- Compare response times over multiple refreshes
- Identify services that may need optimization

## Technical Details

### Connection Testing

- Uses `fetch()` API for absolute URLs (CARTA)
- Uses `apiClient` (axios) for relative API endpoints
- 5-second timeout per request
- Tests run in parallel for faster results

### Error Handling

- Network errors caught and displayed
- HTTP status codes validated
- Detailed error messages preserved
- Services tested independently (one failure doesn't block others)

### Performance

- Lightweight checks (HEAD requests where possible)
- Parallel execution of all tests
- Results cached between auto-refresh cycles

## Comparison with System Diagnostics Page

| Feature          | System Status                | System Diagnostics                   |
| ---------------- | ---------------------------- | ------------------------------------ |
| Purpose          | Service connectivity testing | In-depth metrics and diagnostics     |
| Focus            | Health checks                | Performance metrics                  |
| Scope            | All services at once         | Tabbed interface for different areas |
| Update Frequency | 30 seconds                   | Varies by metric                     |
| Best For         | Quick status overview        | Deep troubleshooting                 |

## Integration Points

The System Status page consolidates information from:

- **Backend API** health endpoints
- **CARTA** Docker container
- **ABSURD** workflow manager
- **apiClient** connection status

## Future Enhancements

Potential additions:

- [ ] WebSocket connection testing
- [ ] Database connection pooling stats
- [ ] Historical uptime graphs
- [ ] Service dependency visualization
- [ ] Alert thresholds and notifications
- [ ] Export status report as JSON/CSV
- [ ] Service restart buttons (with auth)
