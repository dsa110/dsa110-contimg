# Test Coverage Analysis

> **Generated:** This document is auto-generated from coverage reports. **Last
> Updated:** Run `scripts/analyze_coverage.py` to regenerate.

## Overall Coverage Summary

**Total Coverage:** 19.0%

- **Statements:** 2,170
- **Covered:** 420
- **Missing:** 1,750

## Coverage by Module

### Low Coverage Modules (< 50%)

| Module                                         | Statements | Missing | Coverage % |
| ---------------------------------------------- | ---------- | ------- | ---------- |
| `src/dsa110_contimg/pipeline/health.py`        | 91         | 91      | 0.0%       |
| `src/dsa110_contimg/pipeline/signals.py`       | 54         | 54      | 0.0%       |
| `src/dsa110_contimg/pipeline/timeout.py`       | 70         | 70      | 0.0%       |
| `src/dsa110_contimg/pipeline/stages_impl.py`   | 1138       | 1051    | 8.0%       |
| `src/dsa110_contimg/pipeline/adapter.py`       | 61         | 46      | 25.0%      |
| `src/dsa110_contimg/pipeline/resources.py`     | 71         | 53      | 25.0%      |
| `src/dsa110_contimg/pipeline/orchestrator.py`  | 162        | 120     | 26.0%      |
| `src/dsa110_contimg/pipeline/workflows.py`     | 41         | 28      | 32.0%      |
| `src/dsa110_contimg/pipeline/observability.py` | 80         | 51      | 36.0%      |
| `src/dsa110_contimg/pipeline/state.py`         | 129        | 70      | 46.0%      |
| `src/dsa110_contimg/pipeline/config.py`        | 175        | 89      | 49.0%      |

### Medium Coverage Modules (50-80%)

| Module                                      | Statements | Missing | Coverage % |
| ------------------------------------------- | ---------- | ------- | ---------- |
| `src/dsa110_contimg/pipeline/resilience.py` | 34         | 14      | 59.0%      |
| `src/dsa110_contimg/pipeline/context.py`    | 21         | 6       | 71.0%      |
| `src/dsa110_contimg/pipeline/__init__.py`   | 16         | 4       | 75.0%      |

### High Coverage Modules (>= 80%)

| Module                                  | Statements | Missing | Coverage % |
| --------------------------------------- | ---------- | ------- | ---------- |
| `src/dsa110_contimg/pipeline/stages.py` | 27         | 3       | 89.0%      |

## Recommendations

### Priority 1: Critical Modules with Low Coverage

The following critical modules have very low coverage and need immediate
attention:

- **`pipeline/stages_impl.py`** (8% coverage, 1,051 missing statements)
  - **Impact:** Core stage implementations - critical for pipeline functionality
  - **Action Items:**
    - Add unit tests for all 9 stage classes (ConversionStage, CalibrationStage,
      ImagingStage, etc.)
    - Test `validate()`, `execute()`, `cleanup()`, and `validate_outputs()`
      methods
    - Add integration tests for stage interactions
    - Focus on error handling and edge cases

- **`pipeline/orchestrator.py`** (26% coverage, 120 missing statements)
  - **Impact:** Pipeline orchestration and dependency management
  - **Action Items:**
    - Test dependency resolution logic
    - Test retry mechanisms and error handling
    - Test stage execution ordering
    - Test context propagation between stages

- **`pipeline/config.py`** (49% coverage, 89 missing statements)
  - **Impact:** Configuration validation and management
  - **Action Items:**
    - Test all configuration classes (PathsConfig, ConversionConfig, etc.)
    - Test validation logic
    - Test environment variable parsing
    - Test default value handling

- **`pipeline/health.py`** (0% coverage, 91 missing statements)
  - **Impact:** Health monitoring and diagnostics
  - **Action Items:**
    - Add comprehensive unit tests
    - Test health check endpoints
    - Test monitoring functionality

- **`pipeline/signals.py`** (0% coverage, 54 missing statements)
  - **Impact:** Signal handling for pipeline events
  - **Action Items:**
    - Add unit tests for signal handlers
    - Test event propagation
    - Test error handling in signal handlers

- **`pipeline/timeout.py`** (0% coverage, 70 missing statements)
  - **Impact:** Timeout management for long-running operations
  - **Action Items:**
    - Add unit tests for timeout logic
    - Test timeout expiration handling
    - Test timeout cancellation

### Priority 2: Improve Coverage for Medium Coverage Modules

Focus on modules with 50-80% coverage that are frequently used:

- `src/dsa110_contimg/pipeline/resilience.py` - Add tests for edge cases and
  error handling
- `src/dsa110_contimg/pipeline/context.py` - Add tests for edge cases and error
  handling
- `src/dsa110_contimg/pipeline/__init__.py` - Add tests for edge cases and error
  handling

## How to Improve Coverage

1. **Run coverage report:**

   ```bash
   pytest --cov=src/dsa110_contimg --cov-report=term-missing tests/
   ```

2. **View HTML report:**

   ```bash
   pytest --cov=src/dsa110_contimg --cov-report=html:tests/coverage_html tests/
   # Open tests/coverage_html/index.html in browser
   ```

3. **Focus on uncovered lines:**
   - Review uncovered lines in HTML report
   - Add tests for missing branches
   - Test error conditions and edge cases

4. **Use coverage markers:**
   ```python
   # Mark lines that don't need coverage
   if False:  # pragma: no cover
       debug_code()
   ```

## Related Documentation

- [Testing Guide](../how-to/testing.md)
- [Pipeline Stage Architecture](../concepts/pipeline_stage_architecture.md)
