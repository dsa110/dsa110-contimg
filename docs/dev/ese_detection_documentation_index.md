# ESE Detection Documentation Index

This document provides an index of all documentation related to ESE (Extreme
Scattering Event) detection implementation.

## User Guides

### [ESE Detection Guide](../../how-to/ese_detection_guide.md)

**Location**: `docs/how-to/ese_detection_guide.md`

Comprehensive user guide covering:

- Quick start instructions
- CLI usage with examples
- API usage (single and batch jobs)
- Automated detection configuration
- Understanding results and troubleshooting

**Audience**: End users, operators, developers

## Architecture Documentation

### [ESE Detection Architecture](../../concepts/ese_detection_architecture.md)

**Location**: `docs/concepts/ese_detection_architecture.md`

Technical architecture documentation covering:

- System components and modules
- Data flow diagrams
- Database schema
- Variability metrics
- Source ID generation
- Performance considerations
- Testing strategy

**Audience**: Developers, architects, maintainers

## Implementation Summaries

### [ESE Detection Implementation Summary](../ese_detection_implementation_summary.md)

**Location**: `docs/dev/ese_detection_implementation_summary.md`

Summary of CLI and API implementation:

- Feature confirmation checklist
- Implementation details
- Test coverage
- Usage examples
- Status: Complete

**Audience**: Developers, project managers

### [Automated ESE Detection Pipeline Summary](../ese_automated_pipeline_summary.md)

**Location**: `docs/dev/ese_automated_pipeline_summary.md`

Summary of automated pipeline integration:

- Automatic variability stats computation
- Automatic ESE candidate detection
- Photometry pipeline integration
- Configuration options
- Data flow
- Status: Complete

**Audience**: Developers, project managers

## Task Tracking

### [Unaddressed Tasks Review](../analysis/unaddressed_tasks_review.md)

**Location**: `docs/dev/analysis/unaddressed_tasks_review.md`

Updated to reflect completion:

- Stage 8: ESE Detection CLI and Execution (100% complete)
- Stage 8: Automated ESE Detection Pipeline (100% complete)

**Audience**: Project managers, developers

## Code Documentation

### Core Modules

1. **ESE Detection Module**
   - File: `src/dsa110_contimg/photometry/ese_detection.py`
   - Function: `detect_ese_candidates()`
   - Documentation: Inline docstrings

2. **Pipeline Integration Module**
   - File: `src/dsa110_contimg/photometry/ese_pipeline.py`
   - Functions: `update_variability_stats_for_source()`,
     `auto_detect_ese_for_new_measurements()`
   - Documentation: Inline docstrings

3. **CLI Interface**
   - File: `src/dsa110_contimg/photometry/cli.py`
   - Command: `ese-detect`
   - Documentation: Inline docstrings and help text

4. **API Endpoints**
   - File: `src/dsa110_contimg/api/routes.py`
   - Endpoints: `POST /api/jobs/ese-detect`, `POST /api/batch/ese-detect`
   - Documentation: FastAPI docstrings

5. **Job Adapters**
   - File: `src/dsa110_contimg/api/job_adapters.py`
   - Functions: `run_ese_detect_job()`, `run_batch_ese_detect_job()`
   - Documentation: Inline docstrings

## Test Documentation

### Unit Tests

1. **Core Detection Tests**
   - File: `tests/unit/photometry/test_ese_detection.py`
   - Coverage: Core detection logic

2. **CLI Tests**
   - File: `tests/unit/photometry/test_ese_cli.py`
   - Coverage: CLI command interface

3. **API Endpoint Tests**
   - File: `tests/unit/api/test_ese_endpoints.py`
   - Coverage: REST API endpoints

4. **Job Adapter Tests**
   - File: `tests/unit/api/test_ese_job_adapters.py`
   - Coverage: Job execution logic

5. **Pipeline Integration Tests**
   - File: `tests/unit/photometry/test_ese_pipeline.py`
   - Coverage: Automated pipeline

6. **Smoke Tests**
   - File: `tests/unit/photometry/test_ese_smoke.py`
   - Coverage: End-to-end validation

## Quick Reference

### CLI Commands

```bash
# Basic detection
python -m dsa110_contimg.photometry.cli ese-detect

# With options
python -m dsa110_contimg.photometry.cli ese-detect \
  --min-sigma 6.0 \
  --source-id "J120000+450000" \
  --recompute
```

### API Endpoints

```bash
# Single job
POST /api/jobs/ese-detect

# Batch job
POST /api/batch/ese-detect
```

### Configuration

```python
{
    "auto_detect_ese": True,
    "ese_min_sigma": 5.0
}
```

## Related Documentation

- [Photometry Guide](../../how-to/photometry_guide.md) - Photometry measurement
  procedures
- [Database Schema](../../reference/database_schema.md) - Database structure
- [API Reference](../../reference/api_reference_generated.md) - Complete API
  documentation

## Documentation Maintenance

### Last Updated

- 2025-11-12: Initial documentation creation
- All ESE detection features marked complete

### Maintenance Notes

- Update this index when adding new documentation
- Keep implementation summaries synchronized with code
- Update user guides when adding new features
- Review architecture docs when making significant changes

## Contact

For questions or issues with ESE detection:

- Check user guide first:
  [ESE Detection Guide](../../how-to/ese_detection_guide.md)
- Review architecture:
  [ESE Detection Architecture](../../concepts/ese_detection_architecture.md)
- Check implementation summaries for technical details
