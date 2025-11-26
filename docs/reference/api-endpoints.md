# Reference: API (Verified)

## alerts

- `/api/alerts/history`

## available

- `/api/available`

## batch

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

## cache

- `/api/cache/stats`

## calibrator_matches

- `/api/calibrator_matches`

## caltables

- `/api/caltables`

## catalog

- `/api/catalog/overlay`

## clear

- `/api/clear`

## data

- `/api/data`
- `/api/data/{data_id:path}`
- `/api/data/{data_id:path}/auto-publish/disable`
- `/api/data/{data_id:path}/auto-publish/enable`
- `/api/data/{data_id:path}/auto-publish/status`
- `/api/data/{data_id:path}/finalize`
- `/api/data/{data_id:path}/lineage`
- `/api/data/{data_id:path}/publish`

## ese

- `/api/ese/candidates`
- `/api/ese/candidates/{source_id}/external_catalogs`
- `/api/ese/candidates/{source_id}/lightcurve`
- `/api/ese/candidates/{source_id}/postage_stamps`
- `/api/ese/candidates/{source_id}/variability`

## groups

- `/api/groups/{group_id}`

## health

- `/api/health`

## images

- `/api/images`
- `/api/images/{image_id}`
- `/api/images/{image_id}/fit`
- `/api/images/{image_id}/fits`
- `/api/images/{image_id}/measurements`
- `/api/images/{image_id}/profile`

## jobs

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

## keys

- `/api/keys`
- `/api/keys/{key:path}`

## legacy

- `/api/legacy/sources/search`
- `/api/legacy/sources/{source_id}`
- `/api/legacy/sources/{source_id}/detections`
- `/api/legacy/sources/{source_id}/external_catalogs`
- `/api/legacy/sources/{source_id}/lightcurve`
- `/api/legacy/sources/{source_id}/postage_stamps`
- `/api/legacy/sources/{source_id}/variability`

## metrics

- `/api/metrics`
- `/api/metrics/system`
- `/api/metrics/system/history`

## monitoring

- `/api/monitoring/publish/failed`
- `/api/monitoring/publish/retry-all`
- `/api/monitoring/publish/retry/{data_id:path}`
- `/api/monitoring/publish/status`

## mosaics

- `/api/mosaics` - GET: List recent mosaics with pagination
- `/api/mosaics/create` - POST: Create a new mosaic job
- `/api/mosaics/query` - POST: Query mosaics by time range
- `/api/mosaics/{mosaic_id}` - GET: Get mosaic by ID
- `/api/mosaics/{mosaic_id}/fits` - GET: Download mosaic FITS file

## ms

- `/api/ms`
- `/api/ms/discover`
- `/api/ms/{ms_path:path}/calibrator-matches`
- `/api/ms/{ms_path:path}/existing-caltables`
- `/api/ms/{ms_path:path}/metadata`
- `/api/ms/{ms_path:path}/validate-caltable`

## ms_index

- `/api/ms_index`

## observation_timeline

- `/api/observation_timeline`
- `/api/observation_timeline/plot`

## operations

- `/api/operations/circuit-breakers`
- `/api/operations/circuit-breakers/{name}`
- `/api/operations/circuit-breakers/{name}/reset`
- `/api/operations/dlq/items`
- `/api/operations/dlq/items/{item_id}`
- `/api/operations/dlq/items/{item_id}/fail`
- `/api/operations/dlq/items/{item_id}/resolve`
- `/api/operations/dlq/items/{item_id}/retry`
- `/api/operations/dlq/stats`

## dlq (Phase 2 - Enhanced DLQ API)

- `/api/dlq/items` - List DLQ items with filtering
- `/api/dlq/items/{item_id}` - Get specific DLQ item
- `/api/dlq/items/{item_id}/retry` - Retry with Absurd resubmission option
- `/api/dlq/items/{item_id}/resolve` - Mark as resolved
- `/api/dlq/items/{item_id}/fail` - Mark as permanently failed
- `/api/dlq/stats` - Statistics with by_component and by_error_type breakdowns
- `DELETE /api/dlq/items/{item_id}` - Delete item permanently

## absurd (Phase 2 & 3 - Workflow Manager)

- `/api/absurd/health` - Health check
- `/api/absurd/metrics` - Real-time metrics (JSON)
- `/api/absurd/metrics/prometheus` - Prometheus exposition format metrics
- `/api/absurd/tasks` - List/spawn tasks
- `/api/absurd/tasks/{task_id}` - Get/cancel task
- `/api/absurd/queues/{queue_name}/stats` - Queue statistics

## performance

- `/api/performance`

## photometry

- `/api/photometry/measure`
- `/api/photometry/measure-batch`
- `/api/photometry/normalize`

## pipeline

- `/api/pipeline/dependency-graph`
- `/api/pipeline/executions`
- `/api/pipeline/executions/active`
- `/api/pipeline/executions/{execution_id}`
- `/api/pipeline/executions/{execution_id}/stages`
- `/api/pipeline/metrics/summary`
- `/api/pipeline/stages/metrics`
- `/api/pipeline/stages/{stage_name}/metrics`
- `/api/pipeline/workflow-status`

## plots

- `/api/plots/caltable/{caltable_path:path}`

## pointing-monitor

- `/api/pointing-monitor/status`

## pointing_history

- `/api/pointing_history`

## products

- `/api/products`

## qa

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

## queues

- `/api/queues/{queue_name}/enqueue`
- `/api/queues/{queue_name}/stats`

## rate-limiting

- `/api/rate-limiting/stats`

## regions

- `/api/regions`
- `/api/regions/{region_id}`
- `/api/regions/{region_id}/statistics`

## reprocess

- `/api/reprocess/{group_id}`

## sources

- `/api/sources/search`
- `/api/sources/{source_id}`
- `/api/sources/{source_id}/detections`
- `/api/sources/{source_id}/external_catalogs`
- `/api/sources/{source_id}/lightcurve`
- `/api/sources/{source_id}/postage_stamps`
- `/api/sources/{source_id}/variability`

## sse

- `/api/sse/status`

## stats

- `/api/stats`

## status

- `/api/status`

## stream

- `/api/stream`

## streaming

- `/api/streaming/config`
- `/api/streaming/health`
- `/api/streaming/metrics`
- `/api/streaming/restart`
- `/api/streaming/start`
- `/api/streaming/status`
- `/api/streaming/stop`

## test

- `/api/test/streaming/broadcast`

## thumbnails

- `/api/thumbnails/{ms_path:path}.png`

## types

- `/api/types`

## ui

- `/api/ui/calibrators`

## uvh5

- `/api/uvh5`

## ws

- `/api/ws/status`
