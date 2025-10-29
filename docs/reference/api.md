# Reference: API

- `/api/status` – queue stats + recent groups
- `/api/products` – recent images
- `/api/calibrator_matches` – recent calibrator matches (limit, matched_only)
- `/api/ms_index` – filter ms_index by stage/status
- `/api/reprocess/{group_id}` – set a group back to pending
- `/api/qa` – recent QA artifacts (DB-backed or filesystem fallback)
- `/api/qa/file/{group}/{name}` – serve a specific QA artifact
- `/api/metrics/system` – current system metrics snapshot
- `/api/metrics/system/history` – last N system metrics samples
