# Prometheus Monitoring

The DSA-110 API exposes Prometheus metrics for monitoring request performance
and system health.

## Metrics Endpoint

**URL:** `http://localhost:8000/metrics`

> **Note:** When accessed through Nginx, the `/metrics` endpoint is restricted
> to localhost only for security.

## Available Metrics

### HTTP Request Metrics

| Metric                          | Type      | Description                  |
| ------------------------------- | --------- | ---------------------------- |
| `http_requests_total`           | Counter   | Total HTTP requests          |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `http_requests_in_progress`     | Gauge     | Current in-flight requests   |

Labels:

- `method`: HTTP method (GET, POST, etc.)
- `handler`: Endpoint path
- `status`: HTTP status code

### Python Runtime Metrics

| Metric                                  | Type    | Description             |
| --------------------------------------- | ------- | ----------------------- |
| `python_gc_objects_collected_total`     | Counter | Objects collected by GC |
| `python_gc_objects_uncollectable_total` | Counter | Uncollectable objects   |
| `python_gc_collections_total`           | Counter | GC collection counts    |
| `python_info`                           | Gauge   | Python version info     |

### Process Metrics

| Metric                          | Type    | Description                     |
| ------------------------------- | ------- | ------------------------------- |
| `process_virtual_memory_bytes`  | Gauge   | Virtual memory size             |
| `process_resident_memory_bytes` | Gauge   | Resident memory size (RSS)      |
| `process_cpu_seconds_total`     | Counter | Total CPU time                  |
| `process_open_fds`              | Gauge   | Open file descriptors           |
| `process_start_time_seconds`    | Gauge   | Process start time (Unix epoch) |

## Querying Metrics

### Direct Access

```bash
curl http://localhost:8000/metrics
```

### Through Nginx (localhost only)

```bash
curl http://localhost/metrics
```

### Example Queries

Request rate (last 5 minutes):

```promql
rate(http_requests_total[5m])
```

95th percentile latency:

```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

Error rate:

```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
/ sum(rate(http_requests_total[5m]))
```

## Prometheus Configuration

Add this scrape config to your Prometheus server:

```yaml
scrape_configs:
  - job_name: "dsa110-api"
    static_configs:
      - targets: ["dsa110-host:8000"]
    metrics_path: /metrics
    scrape_interval: 15s
```

## Grafana Dashboard

### Recommended Panels

1. **Request Rate** - Requests per second by endpoint
2. **Latency Heatmap** - Request duration distribution
3. **Error Rate** - 4xx and 5xx responses
4. **Memory Usage** - Process memory over time
5. **Active Connections** - In-progress requests

### Example Dashboard JSON

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total{job=\"dsa110-api\"}[5m])",
          "legendFormat": "{{handler}}"
        }
      ]
    }
  ]
}
```

## Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: dsa110-api
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on DSA-110 API"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, 
            rate(http_request_duration_seconds_bucket[5m])
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on DSA-110 API"

      - alert: APIDown
        expr: up{job="dsa110-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "DSA-110 API is down"
```

## Excluded Endpoints

The following endpoints are excluded from metrics to reduce noise:

- `/metrics` - Prometheus scrape endpoint
- `/api/health` - Health check endpoint
