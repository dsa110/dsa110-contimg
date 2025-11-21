# API Documentation - Catalog Coverage Status

## Overview

The pipeline status API endpoint now includes catalog coverage information,
providing real-time status of catalog databases for the current telescope
declination.

## Endpoint

### GET `/api/status`

Returns comprehensive pipeline status including catalog coverage.

#### Response Model

```json
{
  "queue": {
    "total": 10,
    "pending": 2,
    "in_progress": 1,
    "failed": 0,
    "completed": 7,
    "collecting": 0
  },
  "recent_groups": [...],
  "calibration_sets": [...],
  "matched_recent": 5,
  "catalog_coverage": {
    "dec_deg": 54.6,
    "nvss": {
      "exists": true,
      "within_coverage": true,
      "db_path": "/data/dsa110-contimg/state/catalogs/nvss_dec+54.6.sqlite3"
    },
    "first": {
      "exists": false,
      "within_coverage": true,
      "db_path": null
    },
    "rax": {
      "exists": false,
      "within_coverage": false,
      "db_path": null
    }
  }
}
```

#### Catalog Coverage Status Fields

**`catalog_coverage`** (optional)

- Type: `CatalogCoverageStatus | null`
- Description: Catalog database coverage status for current declination
- Returns `null` if:
  - Ingest database not found
  - Pointing history is empty
  - Error retrieving declination

**`dec_deg`**

- Type: `float | null`
- Description: Current telescope declination in degrees
- Source: Most recent entry in `pointing_history` table

**`nvss`, `first`, `rax`**

- Type: `Dict[str, Union[bool, str]]`
- Fields:
  - `exists` (bool): Whether database exists for this declination
  - `within_coverage` (bool): Whether declination is within catalog's coverage
    limits
  - `db_path` (str | null): Path to database file if exists, null otherwise

#### Coverage Limits

- **NVSS**: -40.0° to +90.0°
- **FIRST**: -40.0° to +90.0°
- **RACS (RAX)**: -90.0° to +49.9°

#### Example Usage

**Using curl:**

```bash
curl http://localhost:8000/api/status | jq .catalog_coverage
```

**Using Python:**

```python
import requests

response = requests.get("http://localhost:8000/api/status")
status = response.json()

if status.get("catalog_coverage"):
    coverage = status["catalog_coverage"]
    print(f"Current declination: {coverage['dec_deg']}°")
    print(f"NVSS database exists: {coverage['nvss']['exists']}")
    print(f"FIRST database exists: {coverage['first']['exists']}")
    print(f"RAX database exists: {coverage['rax']['exists']}")
else:
    print("No catalog coverage information available")
```

**Using JavaScript (fetch):**

```javascript
fetch("http://localhost:8000/api/status")
  .then((response) => response.json())
  .then((data) => {
    if (data.catalog_coverage) {
      const coverage = data.catalog_coverage;
      console.log(`Current declination: ${coverage.dec_deg}°`);
      console.log(`NVSS: ${coverage.nvss.exists ? "Ready" : "Missing"}`);
      console.log(`FIRST: ${coverage.first.exists ? "Ready" : "Missing"}`);
      console.log(`RAX: ${coverage.rax.exists ? "Ready" : "Missing"}`);
    }
  });
```

## Status Interpretation

### Database Status

- **`exists: true`**: Database is available and ready for queries
- **`exists: false`**: Database is missing (may be auto-built if within
  coverage)

### Coverage Status

- **`within_coverage: true`**: Declination is within catalog's coverage limits
- **`within_coverage: false`**: Declination is outside catalog's coverage
  (database not expected)

### Common Scenarios

**Scenario 1: All databases exist**

```json
{
  "nvss": { "exists": true, "within_coverage": true, "db_path": "..." },
  "first": { "exists": true, "within_coverage": true, "db_path": "..." },
  "rax": { "exists": false, "within_coverage": false, "db_path": null }
}
```

_Interpretation: NVSS and FIRST are ready. RAX is outside coverage (expected)._

**Scenario 2: Missing database within coverage**

```json
{
  "nvss": { "exists": true, "within_coverage": true, "db_path": "..." },
  "first": { "exists": false, "within_coverage": true, "db_path": null },
  "rax": { "exists": false, "within_coverage": false, "db_path": null }
}
```

_Interpretation: FIRST database is missing but should exist. May be auto-built
on next NVSS query._

**Scenario 3: Outside coverage**

```json
{
  "nvss": { "exists": false, "within_coverage": false, "db_path": null },
  "first": { "exists": false, "within_coverage": false, "db_path": null },
  "rax": { "exists": true, "within_coverage": true, "db_path": "..." }
}
```

_Interpretation: Declination is below -40°, only RAX has coverage. NVSS/FIRST
databases not expected._

## Error Handling

The endpoint handles errors gracefully:

- **Missing ingest database**: Returns `catalog_coverage: null`
- **Empty pointing history**: Returns `catalog_coverage: null`
- **Database access errors**: Logs warning, returns `catalog_coverage: null`
- **Invalid declination**: Handled by coverage limit checks

## Performance Considerations

- Status is computed on-demand (not cached)
- Database existence checks are lightweight (file system checks)
- Pointing history query is fast (single row, indexed by timestamp)
- Typical response time: < 50ms

## Integration with Auto-Build

When `catalog_coverage` shows missing databases:

1. Databases may be auto-built on next NVSS query
2. Manual build: Use `auto_build_missing_catalog_databases()`
3. Pipeline build: `CatalogSetupStage` builds databases during pipeline
   execution

## Monitoring

Use this endpoint to:

- Monitor catalog database availability
- Detect missing databases before pipeline execution
- Track declination changes and coverage transitions
- Generate status reports and dashboards

## Related Endpoints

- `GET /api/health`: Basic health check
- `GET /api/status/stream`: Real-time status updates (SSE)

## Version History

- **v1.0** (2024): Initial implementation
  - Added `catalog_coverage` field to status endpoint
  - Support for NVSS, FIRST, and RAX catalog status
