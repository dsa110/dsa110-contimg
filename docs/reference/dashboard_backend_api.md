# DSA-110 Dashboard: Backend API & Integration

This page lists the backend endpoints used by the dashboard. The list below is
generated from the code and is the single source of truth.

## API Overview

- Base URL (dev): `http://localhost:8000/api`
- Content-Type: `application/json`
- Auth: None (internal tool)
- Real-time updates: WebSocket `/api/ws/status`, SSE `/api/sse/status`

## Verified Endpoints (auto-generated)

<!-- BEGIN: VERIFIED-ENDPOINTS -->

## Verified Endpoints (auto-generated)

### alerts

- `/api/alerts`
- `/api/alerts/bulk-acknowledge`
- `/api/alerts/history`
- `/api/alerts/{alert_id}`
- `/api/alerts/{alert_id}/acknowledge`
- `/api/alerts/{alert_id}/follow-up`
- `/api/alerts/{alert_id}/notes`

### antenna-health

- `/api/antenna-health/metrics`
- `/api/antenna-health/plots/heatmap`
- `/api/antenna-health/plots/refant-report`
- `/api/antenna-health/plots/stability-trends`

### available

- `/api/available`

### batch

- `/api/batch`
- `/api/batch/apply`
- `/api/batch/calibrate`
- `/api/batch/convert`
- `/api/batch/ese-detect`
- `/api/batch/image`
- `/api/batch/photometry`
- `/api/batch/publish`
- `/api/batch/{batch_id}`
- `/api/batch/{batch_id}/cancel`

### cache

- `/api/cache/stats`

### calibration

- `/api/calibration/status`

### calibration-quality

- `/api/calibration-quality/metrics`
- `/api/calibration-quality/plots/snr-trends`

### calibrator_matches

- `/api/calibrator_matches`

### caltables

- `/api/caltables`

### candidates

- `/api/candidates`
- `/api/candidates/bulk-classify`
- `/api/candidates/{candidate_id}`
- `/api/candidates/{candidate_id}/classify`
- `/api/candidates/{candidate_id}/follow-up`
- `/api/candidates/{candidate_id}/notes`

### catalog

- `/api/catalog/overlay`

### clear

- `/api/clear`

### dashboard

- `/api/dashboard/summary`

### data

- `/api/data`
- `/api/data/{data_id:path}`
- `/api/data/{data_id:path}/auto-publish/disable`
- `/api/data/{data_id:path}/auto-publish/enable`
- `/api/data/{data_id:path}/auto-publish/status`
- `/api/data/{data_id:path}/finalize`
- `/api/data/{data_id:path}/lineage`
- `/api/data/{data_id:path}/publish`

### disk-usage

- `/api/disk-usage/current`
- `/api/disk-usage/plots/current`
- `/api/disk-usage/plots/projection`

### ese

- `/api/ese/candidates`
- `/api/ese/candidates/{source_id}/external_catalogs`
- `/api/ese/candidates/{source_id}/lightcurve`
- `/api/ese/candidates/{source_id}/postage_stamps`
- `/api/ese/candidates/{source_id}/variability`

### ese-candidates

- `/api/ese-candidates/list`
- `/api/ese-candidates/plots/flux-variations`
- `/api/ese-candidates/plots/sky-distribution`

### groups

- `/api/groups/{group_id}`

### health

- `/api/health`
- `/api/health/detailed`
- `/api/health/services`

### images

- `/api/images`
- `/api/images/{image_id}`
- `/api/images/{image_id}/fit`
- `/api/images/{image_id}/fits`
- `/api/images/{image_id}/measurements`
- `/api/images/{image_id}/profile`

### items

- `/api/items`
- `/api/items/{item_id}`
- `/api/items/{item_id}/fail`
- `/api/items/{item_id}/resolve`
- `/api/items/{item_id}/retry`

### jobs

- `/api/jobs`
- `/api/jobs/apply`
- `/api/jobs/calibrate`
- `/api/jobs/convert`
- `/api/jobs/ese-detect`
- `/api/jobs/healthz`
- `/api/jobs/id/{job_id}`
- `/api/jobs/id/{job_id}/logs`
- `/api/jobs/image`
- `/api/jobs/workflow`
- `/api/jobs/{job_id}`

### keys

- `/api/keys`
- `/api/keys/{key:path}`

### legacy

- `/api/legacy/sources/search`
- `/api/legacy/sources/{source_id}`
- `/api/legacy/sources/{source_id}/detections`
- `/api/legacy/sources/{source_id}/external_catalogs`
- `/api/legacy/sources/{source_id}/lightcurve`
- `/api/legacy/sources/{source_id}/postage_stamps`
- `/api/legacy/sources/{source_id}/variability`

### metrics

- `/api/metrics`
- `/api/metrics/database`
- `/api/metrics/history`
- `/api/metrics/prometheus`
- `/api/metrics/system`
- `/api/metrics/system/history`

### monitoring

- `/api/monitoring/publish/failed`
- `/api/monitoring/publish/retry-all`
- `/api/monitoring/publish/retry/{data_id:path}`
- `/api/monitoring/publish/status`

### mosaic-quality

- `/api/mosaic-quality/metrics`
- `/api/mosaic-quality/plots/dynamic-range`
- `/api/mosaic-quality/plots/rms-trends`

### mosaics

- `/api/mosaics`
- `/api/mosaics/create`
- `/api/mosaics/query`
- `/api/mosaics/{mosaic_id}`
- `/api/mosaics/{mosaic_id}/fits`

### ms

- `/api/ms`
- `/api/ms/discover`
- `/api/ms/{ms_path:path}/calibrator-matches`
- `/api/ms/{ms_path:path}/existing-caltables`
- `/api/ms/{ms_path:path}/metadata`
- `/api/ms/{ms_path:path}/validate-caltable`

### ms_index

- `/api/ms_index`

### observation_timeline

- `/api/observation_timeline`
- `/api/observation_timeline/plot`

### operations

- `/api/operations/circuit-breakers`
- `/api/operations/circuit-breakers/{name}`
- `/api/operations/circuit-breakers/{name}/reset`
- `/api/operations/dlq/items`
- `/api/operations/dlq/items/{item_id}`
- `/api/operations/dlq/items/{item_id}/fail`
- `/api/operations/dlq/items/{item_id}/resolve`
- `/api/operations/dlq/items/{item_id}/retry`
- `/api/operations/dlq/stats`

### performance

- `/api/performance`
- `/api/performance/metrics`
- `/api/performance/plots/failure-rate`
- `/api/performance/plots/stage-duration`
- `/api/performance/plots/throughput`
- `/api/performance/plots/writer-comparison`

### photometry

- `/api/photometry/measure`
- `/api/photometry/measure-batch`
- `/api/photometry/normalize`

### pipeline

- `/api/pipeline/dependency-graph`
- `/api/pipeline/executions`
- `/api/pipeline/executions/active`
- `/api/pipeline/executions/{execution_id}`
- `/api/pipeline/executions/{execution_id}/stages`
- `/api/pipeline/metrics/summary`
- `/api/pipeline/stages/metrics`
- `/api/pipeline/stages/{stage_name}/metrics`
- `/api/pipeline/workflow-status`

### plots

- `/api/plots/caltable/{caltable_path:path}`

### pointing

- `/api/pointing/history`
- `/api/pointing/mollweide-sky-map`
- `/api/pointing/mollweide-sky-map-data`
- `/api/pointing/sky-map`
- `/api/pointing/sky-map-data`

### pointing-monitor

- `/api/pointing-monitor/status`

### pointing_history

- `/api/pointing_history`

### products

- `/api/products`

### qa

- `/api/qa`
- `/api/qa/calibration/{ms_path:path}`
- `/api/qa/calibration/{ms_path:path}/bandpass-plots`
- `/api/qa/calibration/{ms_path:path}/bandpass-plots/{filename}`
- `/api/qa/calibration/{ms_path:path}/caltable-completeness`
- `/api/qa/calibration/{ms_path:path}/spw-plot`
- `/api/qa/file/{group}/{name}`
- `/api/qa/image/{ms_path:path}`
- `/api/qa/images/{image_id}/catalog-overlay`
- `/api/qa/images/{image_id}/catalog-validation`
- `/api/qa/images/{image_id}/catalog-validation/run`
- `/api/qa/images/{image_id}/validation-report.html`
- `/api/qa/images/{image_id}/validation-report/generate`
- `/api/qa/thumbs`
- `/api/qa/{ms_path:path}`

### queue-health

- `/api/queue-health/metrics`
- `/api/queue-health/plots/depth-trends`
- `/api/queue-health/plots/processing-rate`
- `/api/queue-health/plots/state-transitions`
- `/api/queue-health/plots/time-to-completion`

### queues

- `/api/queues`
- `/api/queues/stats`
- `/api/queues/{queue_name}/enqueue`
- `/api/queues/{queue_name}/stats`

### rate-limiting

- `/api/rate-limiting/stats`

### regions

- `/api/regions`
- `/api/regions/{region_id}`
- `/api/regions/{region_id}/statistics`

### reprocess

- `/api/reprocess/{group_id}`

### schedules

- `/api/schedules`
- `/api/schedules/{name}`
- `/api/schedules/{name}/trigger`

### sources

- `/api/sources`
- `/api/sources/search`
- `/api/sources/{source_id}`
- `/api/sources/{source_id}/detections`
- `/api/sources/{source_id}/external_catalogs`
- `/api/sources/{source_id}/lightcurve`
- `/api/sources/{source_id}/postage_stamps`
- `/api/sources/{source_id}/variability`

### sse

- `/api/sse/status`

### stats

- `/api/stats`

### status

- `/api/status`

### stream

- `/api/stream`

### streaming

- `/api/streaming/config`
- `/api/streaming/health`
- `/api/streaming/metrics`
- `/api/streaming/mosaic-queue`
- `/api/streaming/restart`
- `/api/streaming/start`
- `/api/streaming/status`
- `/api/streaming/stop`

### tasks

- `/api/tasks`
- `/api/tasks/with-deps`
- `/api/tasks/{task_id}`

### templates

- `/api/templates`
- `/api/templates/{template_name}`
- `/api/templates/{template_name}/run`

### test

- `/api/test/streaming/broadcast`

### thumbnails

- `/api/thumbnails/{ms_path:path}.png`

### types

- `/api/types`

### ui

- `/api/ui/calibrators`

### uvh5

- `/api/uvh5`

### visualization

- `/api/visualization/casatable/info`

### workers

- `/api/workers`
- `/api/workers/metrics`
- `/api/workers/{worker_id}/heartbeat`

### workflows

- `/api/workflows`
- `/api/workflows/{workflow_id}`
- `/api/workflows/{workflow_id}/dag`
- `/api/workflows/{workflow_id}/ready`

### ws

- `/api/ws/status`

<!-- END: VERIFIED-ENDPOINTS -->
