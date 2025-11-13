# Calibration Provenance Tracking - Risk Analysis

**Date**: 2025-01-XX  
**Status**: Pre-deployment Risk Assessment  
**Priority**: High

## Executive Summary

This document identifies potential risk points in the calibration provenance tracking implementation, categorizes them by severity and likelihood, and provides mitigation strategies.

## Risk Categories

### 1. Database Migration Risks

#### Risk 1.1: Concurrent Migration Conflicts
**Severity**: Medium  
**Likelihood**: Low  
**Description**: Multiple processes attempting to migrate the same database simultaneously could cause conflicts.

**Impact**:
- Database corruption
- Incomplete migrations
- Lock contention

**Mitigation**:
- SQLite handles concurrent access via file locking
- Migration uses `CREATE INDEX IF NOT EXISTS` (idempotent)
- `ALTER TABLE ADD COLUMN` is safe for concurrent reads
- Migration checks for existing columns before adding

**Status**: ✅ Mitigated - Migration is idempotent and safe

#### Risk 1.2: Migration Failure on Large Databases
**Severity**: Medium  
**Likelihood**: Low  
**Description**: Very large calibration registries (>10k entries) might experience slow migrations.

**Impact**:
- Slow first access after deployment
- Timeout issues
- User experience degradation

**Mitigation**:
- Migration only adds columns (fast operation)
- No data migration required (NULL values acceptable)
- Index creation is deferred and uses `IF NOT EXISTS`
- Consider running migration during maintenance window

**Status**: ⚠️ Monitor - Migration should be fast but monitor production databases

#### Risk 1.3: Rollback Complexity
**Severity**: Low  
**Likelihood**: Very Low  
**Description**: Removing provenance columns would require manual SQL operations.

**Impact**:
- Cannot easily rollback schema changes
- Data loss if rollback attempted incorrectly

**Mitigation**:
- Schema changes are additive only (no data loss)
- Old code continues to work with NULL provenance fields
- No rollback needed - backward compatible

**Status**: ✅ Low Risk - Backward compatible design

### 2. Integration Risks

#### Risk 2.1: Provenance Tracking Failure Breaks Calibration
**Severity**: High  
**Likelihood**: Low  
**Description**: If provenance tracking raises exceptions, calibration could fail.

**Impact**:
- Calibration pipeline failures
- Production outages
- Data processing delays

**Mitigation**:
- ✅ **IMPLEMENTED**: All provenance tracking wrapped in try/except
- ✅ **IMPLEMENTED**: Failures log warnings but don't raise exceptions
- ✅ **VERIFIED**: `_track_calibration_provenance()` catches all exceptions

**Code Verification**:
```python
try:
    track_calibration_provenance(...)
except Exception as e:
    logger.warning(f"Failed to track provenance: {e}. Calibration succeeded.")
    # No exception raised - calibration continues
```

**Status**: ✅ Mitigated - Non-blocking error handling implemented

#### Risk 2.2: Performance Impact on Calibration
**Severity**: Medium  
**Likelihood**: Low  
**Description**: Provenance tracking adds overhead to calibration solves.

**Impact**:
- Slower calibration execution
- Increased resource usage
- Timeout issues

**Mitigation**:
- Provenance tracking happens after solve (async-like)
- Quality metrics extraction uses efficient table reads
- Database operations are fast (single row updates)
- Estimated overhead: <100ms per solve

**Status**: ⚠️ Monitor - Should be negligible but measure in production

#### Risk 2.3: Missing Provenance for Existing Caltables
**Severity**: Low  
**Likelihood**: High  
**Description**: Existing calibration tables won't have provenance data.

**Impact**:
- Incomplete provenance records
- Cannot trace origin of old caltables
- Impact analysis incomplete

**Mitigation**:
- Expected behavior - only new calibrations tracked
- Can manually add provenance using `track_calibration_provenance()`
- NULL values are acceptable (backward compatible)
- Documentation explains this limitation

**Status**: ✅ Acceptable - By design, documented

### 3. Data Integrity Risks

#### Risk 3.1: JSON Serialization Failures
**Severity**: Medium  
**Likelihood**: Low  
**Description**: Invalid data types in `solver_params` or `quality_metrics` could cause JSON serialization errors.

**Impact**:
- Provenance tracking fails silently
- Missing provenance data
- Database corruption (unlikely)

**Mitigation**:
- ✅ **IMPLEMENTED**: `json.dumps()` with error handling
- ✅ **VERIFIED**: Tests cover edge cases
- Type validation in `_extract_quality_metrics()` (numpy types converted to Python)

**Potential Issues**:
- Complex nested structures in params
- Non-serializable objects (file handles, etc.)

**Status**: ⚠️ Monitor - Add validation if complex params encountered

#### Risk 3.2: Database Path Resolution Failures
**Severity**: Medium  
**Likelihood**: Low  
**Description**: Incorrect registry DB path resolution could write to wrong database.

**Impact**:
- Provenance stored in wrong location
- Missing provenance in correct database
- Data inconsistency

**Mitigation**:
- ✅ **IMPLEMENTED**: Uses same path resolution as registry
- ✅ **VERIFIED**: Tests cover path resolution
- Environment variable precedence documented

**Status**: ✅ Mitigated - Uses established path resolution logic

#### Risk 3.3: CASA Version Detection Failures
**Severity**: Low  
**Likelihood**: Medium  
**Description**: CASA version detection might fail in some environments.

**Impact**:
- `solver_version` field is NULL
- Incomplete provenance records
- Cannot reproduce exact CASA version

**Mitigation**:
- ✅ **IMPLEMENTED**: Multiple fallback methods
- ✅ **IMPLEMENTED**: Graceful degradation (returns None)
- ✅ **VERIFIED**: Tests cover all fallback paths
- NULL is acceptable (optional field)

**Status**: ✅ Acceptable - Graceful degradation implemented

### 4. Performance Risks

#### Risk 4.1: Quality Metrics Extraction Overhead
**Severity**: Low  
**Likelihood**: Medium  
**Description**: Reading calibration tables to extract metrics adds I/O overhead.

**Impact**:
- Slower provenance tracking
- Increased disk I/O
- Potential contention on large tables

**Mitigation**:
- Uses readonly table access
- Efficient numpy operations
- Only reads necessary columns
- Can be disabled if needed (set metrics=None)

**Status**: ⚠️ Monitor - Should be fast but measure in production

#### Risk 4.2: Index Creation on Large Tables
**Severity**: Low  
**Likelihood**: Low  
**Description**: Creating `idx_caltables_source` on existing large tables might be slow.

**Impact**:
- Slow migration on large databases
- Lock contention during index creation

**Mitigation**:
- Uses `CREATE INDEX IF NOT EXISTS` (idempotent)
- Index creation is fast for typical table sizes (<1k entries)
- Can be created during maintenance window

**Status**: ✅ Low Risk - Typical databases are small

### 5. Testing Coverage Gaps

#### Risk 5.1: Real CASA Environment Not Tested
**Severity**: Medium  
**Likelihood**: Medium  
**Description**: Tests use mocks - real CASA integration not fully tested.

**Impact**:
- Undiscovered integration issues
- Version detection failures in production
- Command string building errors

**Mitigation**:
- ✅ **IMPLEMENTED**: Smoke tests use real CASA when available
- ✅ **VERIFIED**: `test_get_casa_version_returns_string` uses real CASA
- Integration tests should be added for full workflow

**Status**: ⚠️ Partial - Add integration tests with real CASA

#### Risk 5.2: Concurrent Access Not Tested
**Severity**: Low  
**Likelihood**: Low  
**Description**: Tests don't verify concurrent database access.

**Impact**:
- Undiscovered race conditions
- Lock contention issues
- Data corruption under load

**Mitigation**:
- SQLite handles concurrency via file locking
- Migration is idempotent
- Consider adding concurrent access tests

**Status**: ⚠️ Monitor - SQLite handles this but could add tests

### 6. Production Deployment Risks

#### Risk 6.1: Registry DB Location Mismatch
**Severity**: High  
**Likelihood**: Low  
**Description**: If registry DB path differs between calibration and provenance tracking, provenance won't be stored.

**Impact**:
- Missing provenance data
- Silent failures
- Incomplete tracking

**Mitigation**:
- ✅ **IMPLEMENTED**: Uses same path resolution logic
- ✅ **VERIFIED**: Tests verify path resolution
- Environment variables must be consistent

**Status**: ✅ Mitigated - Uses same path resolution

#### Risk 6.2: Missing Dependencies
**Severity**: Medium  
**Likelihood**: Low  
**Description**: New dependencies (json module) might not be available.

**Impact**:
- Import errors
- Runtime failures

**Mitigation**:
- `json` is part of Python standard library
- No external dependencies added
- ✅ **VERIFIED**: No new dependencies

**Status**: ✅ Low Risk - Standard library only

#### Risk 6.3: Disk Space for Provenance Data
**Severity**: Low  
**Likelihood**: Low  
**Description**: JSON fields could consume significant disk space.

**Impact**:
- Database growth
- Disk space issues

**Mitigation**:
- JSON fields are typically small (<1KB per entry)
- SQLite compresses data
- Can archive old provenance data if needed

**Status**: ✅ Low Risk - Minimal storage overhead

### 7. Error Handling Risks

#### Risk 7.1: Silent Failures Mask Issues
**Severity**: Medium  
**Likelihood**: Medium  
**Description**: Non-blocking error handling might hide real problems.

**Impact**:
- Missing provenance without awareness
- Difficult to debug
- Incomplete data collection

**Mitigation**:
- ✅ **IMPLEMENTED**: Errors logged as warnings
- ✅ **VERIFIED**: Logging includes full error messages
- Monitoring should alert on warning frequency
- Consider metrics/alerting for provenance failures

**Status**: ⚠️ Monitor - Add monitoring/alerting

#### Risk 7.2: Partial Provenance Updates
**Severity**: Low  
**Likelihood**: Low  
**Description**: Database transaction failures could leave partial provenance data.

**Impact**:
- Inconsistent provenance records
- Missing fields

**Mitigation**:
- ✅ **IMPLEMENTED**: Uses database transactions
- ✅ **VERIFIED**: `register_set()` uses `with conn:` context
- SQLite ensures atomicity

**Status**: ✅ Mitigated - Transactional updates

## Risk Summary Matrix

| Risk | Severity | Likelihood | Status | Priority |
|------|----------|------------|--------|----------|
| Concurrent Migration Conflicts | Medium | Low | ✅ Mitigated | Low |
| Migration Performance | Medium | Low | ⚠️ Monitor | Medium |
| Provenance Tracking Breaks Calibration | High | Low | ✅ Mitigated | High |
| Performance Impact | Medium | Low | ⚠️ Monitor | Medium |
| JSON Serialization Failures | Medium | Low | ⚠️ Monitor | Medium |
| CASA Version Detection | Low | Medium | ✅ Acceptable | Low |
| Real CASA Testing | Medium | Medium | ⚠️ Partial | Medium |
| Registry DB Path Mismatch | High | Low | ✅ Mitigated | High |
| Silent Failures | Medium | Medium | ⚠️ Monitor | Medium |

## Recommended Actions

### Before Production Deployment

1. **High Priority**:
   - ✅ Verify non-blocking error handling (DONE)
   - ✅ Test migration on production-like database (DONE)
   - ⚠️ Add monitoring/alerting for provenance failures
   - ⚠️ Measure performance overhead in staging

2. **Medium Priority**:
   - ⚠️ Add integration tests with real CASA
   - ⚠️ Add concurrent access tests
   - ⚠️ Monitor JSON serialization edge cases
   - ⚠️ Document monitoring/alerting setup

3. **Low Priority**:
   - Consider archiving strategy for old provenance
   - Add metrics dashboard for provenance coverage
   - Consider provenance validation checks

### Monitoring Recommendations

1. **Metrics to Track**:
   - Provenance tracking success rate
   - Provenance tracking latency
   - Database migration duration
   - CASA version detection success rate

2. **Alerts to Configure**:
   - High frequency of provenance tracking failures
   - Migration failures
   - Database path resolution errors

3. **Dashboards**:
   - Provenance coverage (% of caltables with provenance)
   - Provenance tracking performance
   - CASA version distribution

## Critical Risk Verification

### Verified Protections

1. **Error Handling**: ✅ Verified
   - All provenance tracking wrapped in try/except
   - Errors logged as warnings, never raise exceptions
   - Calibration continues even if provenance fails

2. **Migration Safety**: ✅ Verified
   - Migration preserves existing data
   - Concurrent migrations handled gracefully (duplicate column errors caught)
   - Idempotent operations (safe to run multiple times)

3. **JSON Serialization**: ✅ Verified
   - Standard types serialize correctly
   - Non-serializable types fail gracefully (TypeError)
   - None values handled correctly

4. **Path Resolution**: ✅ Verified
   - Uses same logic as registry module
   - Environment variable precedence documented
   - Tests verify path resolution

### Remaining Concerns

1. **Non-Serializable Parameters**: ⚠️ Unhandled
   - If `solver_params` contains non-serializable objects (e.g., file handles), JSON serialization will fail
   - **Mitigation**: Current code catches exceptions, but params dict should be sanitized
   - **Recommendation**: Add parameter sanitization to convert non-serializable types

2. **Large JSON Fields**: ⚠️ Unhandled
   - Very large parameter dictionaries could cause issues
   - **Mitigation**: SQLite handles large TEXT fields, but performance may degrade
   - **Recommendation**: Monitor JSON field sizes, consider truncation for very large params

3. **CASA Command String Length**: ⚠️ Unhandled
   - Very long command strings might exceed database limits
   - **Mitigation**: SQLite TEXT has no practical limit, but very long strings are inefficient
   - **Recommendation**: Truncate extremely long command strings (>10KB)

## Edge Cases Identified

### Edge Case 1: Empty Parameter Dictionary
**Status**: ✅ Handled - `json.dumps({})` returns `"{}"`, correctly deserialized

### Edge Case 2: None Values in Parameters
**Status**: ✅ Handled - `None` values filtered out before JSON serialization

### Edge Case 3: Nested Structures
**Status**: ✅ Handled - JSON supports nested dictionaries/lists

### Edge Case 4: Unicode Characters
**Status**: ✅ Handled - JSON supports Unicode, SQLite TEXT supports UTF-8

### Edge Case 5: Very Large Calibration Tables
**Status**: ⚠️ Monitor - Quality metrics extraction reads entire table columns
   - **Impact**: Could be slow for tables with >100k solutions
   - **Mitigation**: Current implementation is efficient, but monitor in production

## Code Quality Risks

### Risk: Missing Type Validation
**Severity**: Low  
**Likelihood**: Low  
**Description**: No explicit type checking for provenance parameters.

**Impact**: Wrong types could cause runtime errors.

**Mitigation**:
- Python's dynamic typing handles most cases
- JSON serialization provides implicit validation
- Tests cover type scenarios

**Status**: ✅ Acceptable - Dynamic typing sufficient

### Risk: Incomplete Test Coverage
**Severity**: Medium  
**Likelihood**: Medium  
**Description**: Some edge cases not covered by tests.

**Impact**: Undiscovered bugs in production.

**Mitigation**:
- 35 tests covering main scenarios
- Smoke tests verify integration
- Consider adding:
  - Very large parameter dictionaries
  - Unicode in command strings
  - Concurrent provenance updates

**Status**: ⚠️ Partial - Good coverage but could be expanded

## Deployment Checklist

Before deploying to production:

- [x] Error handling verified (non-blocking)
- [x] Migration tested on production-like data
- [x] Backward compatibility verified
- [ ] Performance baseline established
- [ ] Monitoring/alerting configured
- [ ] Integration tests with real CASA run
- [ ] Documentation reviewed
- [ ] Rollback plan documented (not needed - backward compatible)

## Conclusion

The implementation has **strong error handling** and **backward compatibility**, with most critical risks mitigated. The main areas requiring attention are:

1. **Monitoring**: Add alerting for provenance failures
2. **Performance**: Measure overhead in production
3. **Testing**: Add integration tests with real CASA
4. **Parameter Sanitization**: Add validation for non-serializable types

Overall risk level: **LOW-MEDIUM** - Safe for deployment with monitoring.

### Risk Acceptance

**Accepted Risks** (by design):
- Missing provenance for existing caltables (expected)
- NULL solver_version if CASA detection fails (acceptable)
- Silent failures logged as warnings (by design)

**Mitigated Risks**:
- Provenance tracking breaking calibration (non-blocking)
- Migration failures (idempotent, tested)
- Database path mismatches (uses same logic)

**Monitoring Required**:
- Provenance tracking success rate
- Performance overhead
- JSON serialization failures
- CASA version detection failures

