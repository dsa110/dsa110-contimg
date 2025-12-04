# Mock-Heavy Unit Test Audit

**Date**: 2025-02-12
**Phase**: 4 - Contract Testing Infrastructure

## Summary

This audit identifies unit test files with heavy mocking (>5 mock/patch calls)
that may be candidates for refactoring or replacement with contract tests.

## Audit Findings

### High Mocking (>50 instances)

These files rely heavily on mocking and may be providing limited value:

| File                     | Mock Count | Recommendation                                    |
| ------------------------ | ---------- | ------------------------------------------------- |
| test_batch_thumbnails.py | 75         | Review - may benefit from contract tests          |
| test_services_monitor.py | 73         | Review - consider integration tests               |
| test_websocket.py        | 70         | OK - WebSocket mocking often necessary            |
| test_services.py         | 64         | Review - consider end-to-end tests                |
| test_batch_qa.py         | 54         | Review - QA logic testable without mocking        |
| test_job_queue.py        | 53         | Review - queue behavior should be contract-tested |

### Medium Mocking (20-50 instances)

| File                                  | Mock Count | Recommendation                           |
| ------------------------------------- | ---------- | ---------------------------------------- |
| api/test_phase3_integration.py        | 34         | OK - API testing often needs mocking     |
| conversion/test_helpers_validation.py | 33         | Review - validation logic is pure        |
| api/test_ms_visualization.py          | 26         | OK - visualization endpoint tests        |
| api/test_imaging.py                   | 25         | OK - imaging API tests                   |
| test_rate_limit.py                    | 20         | OK - rate limiting requires mocking time |

### Low-Medium Mocking (10-20 instances)

| File                       | Mock Count | Notes                                             |
| -------------------------- | ---------- | ------------------------------------------------- |
| test_fits_service.py       | 17         | Review - FITS operations testable without mocking |
| test_cache.py              | 16         | OK - cache testing needs mocking                  |
| test_logging_config.py     | 15         | OK - logging config tests                         |
| conversion/test_writers.py | 15         | Review - could use real temp files                |
| test_unified_config.py     | 13         | OK - config testing                               |
| test_config.py             | 13         | OK - config testing                               |

## Recommendations

### 1. High-Value Refactoring Candidates

The following should be reviewed for potential simplification:

1. **test_batch_thumbnails.py** - Thumbnail generation can be tested with real
   temp files and synthetic FITS images. Create a contract test that verifies
   the output format.

2. **test_services_monitor.py** - Service monitoring logic should be tested
   against actual (or lightweight mock) services. Consider making the monitor
   more easily testable by dependency injection.

3. **test_batch_qa.py** - QA logic is largely pure computation. Extract pure
   functions and test without mocking.

4. **test_job_queue.py** - Queue behavior is already covered by
   test_database_contracts.py. Consider removing redundant tests.

### 2. Keep As-Is

The following are appropriate uses of mocking:

- WebSocket tests (protocol mocking)
- API endpoint tests (HTTP mocking)
- Rate limiting tests (time mocking)
- Cache tests (cache backend mocking)
- Config tests (environment mocking)

### 3. Action Items

- [x] Review test_batch_thumbnails.py for conversion to contract tests
      **DONE (2025-06-12)**: Created `test_thumbnail_contracts.py` with 15 contract tests
      that verify actual thumbnail generation behavior using synthetic FITS images.
      The pure function tests in test_batch_thumbnails.py remain valid; the mock-heavy
      directory tests are now supplemented by real-data contract tests.
- [x] Review test_services_monitor.py for conversion to integration tests
      **REVIEWED (2025-06-12)**: Mocking is APPROPRIATE here. The tests verify network
      monitoring logic (HTTP, Redis, TCP protocols). Testing against real services would
      require running all monitored services (Grafana, Redis, Prometheus, etc.) which
      makes tests flaky and slow. The current unit tests properly verify status detection,
      timeout handling, and error cases. No contract tests needed.
- [x] Extract pure functions from test_batch_qa.py for direct testing
      **REVIEWED (2025-06-12)**: Already done! The file has excellent pure function tests
      for `_calculate_overall_quality` and `_assess_image_quality` without mocking.
      The mock-heavy tests are for `extract_calibration_qa` which requires CASA's
      casatools.table - these mocks are appropriate for external dependencies.
- [x] Verify test_job_queue.py coverage is not redundant with contract tests
      **VERIFIED (2025-06-12)**: NOT redundant. test_job_queue.py tests the API-level
      job queue (Redis/in-memory fallback for async tasks), while test_database_contracts.py
      tests the processing_queue table (SQLite-based streaming conversion queue).
      These are distinct components. The in-memory fallback tests in TestJobQueueInMemory
      are appropriate unit tests for queue behavior. The mock-heavy TestRerunPipelineJob
      tests could benefit from integration tests but are acceptable as-is since they
      test complex async workflows that are difficult to test without mocking.
- [x] No immediate action needed for API tests (mocking is appropriate)

## Audit Complete

All action items have been reviewed. The testing strategy is now:

1. **Contract tests** (tests/contract/) - Real data, minimal mocking, verify actual behavior
2. **Unit tests** (tests/unit/) - Pure function tests without mocking, mock-based tests for
   external dependencies (CASA, network services, Redis)

The mock counts remain high in some files, but this is now understood to be appropriate
for testing external dependencies. The key improvement is the addition of contract tests
that verify actual pipeline behavior with synthetic data.

## Philosophy Reminder

From the complexity reduction guide:

> **Contract tests verify actual behavior** with real data structures and minimal
> mocking. They ensure interfaces work correctly at integration boundaries.
>
> **Unit tests with heavy mocking** verify that code calls expected methods in
> expected order, but don't verify actual behavior. These provide false confidence.

The goal is not to eliminate all mocking, but to ensure that:

1. Critical paths are tested with real behavior (contract tests)
2. Mocking is used only when necessary (external services, time, etc.)
3. Tests verify outcomes, not implementation details
