# Task 3: Architecture & Code Organization - Implementation Plan

**Date:** 2025-11-13  
**Status:** in-progress  
**Related:** [Task 3 Progress](task3_progress.md), [Dashboard Remodeling](../dev/analysis/dashboard_remodeling.md)

---

## Overview

This document outlines the refactoring plan for improving code architecture and
organization in the DSA-110 dashboard project.

## Current State

### Frontend

- **140 TypeScript/TSX files**
- **81 components, 27 pages**
- **18 test files (~13% coverage)**
- **ControlPage.tsx: 2,439 lines** (too large, needs splitting)
- **9 console.log statements** (should use logger)

### Backend

- **routes.py: 6,522 lines** (too large, needs modularization)
- **FastAPI app** with proper routing
- **No API versioning** strategy visible
- **No rate limiting** implemented
- **OpenAPI docs** should be available at `/docs` (FastAPI default)

## Implementation Plan

### Phase 1: Quick Wins ✅ (In Progress)

#### 1.1 Replace console.log with logger ✅

- [x] Replace all `console.log` in QACartaPage.tsx
- [x] Replace all `console.warn` and `console.error`
- [ ] Add ESLint rule to prevent future console.log usage
- [ ] Audit other files for console.log usage

**Status:** QACartaPage.tsx completed (9 instances replaced)

### Phase 2: Frontend Refactoring

#### 2.1 Split ControlPage.tsx

**Target Components:**

- `CalibrationWorkflow.tsx` - Calibration job creation and management
- `ImagingWorkflow.tsx` - Imaging job creation and management
- `ConversionWorkflow.tsx` - Conversion job creation and management
- `JobManagement.tsx` - Job list, status, logs, and controls

**Approach:**

1. Extract state management into custom hooks
2. Create focused workflow components
3. Update ControlPage to compose these components
4. Maintain existing functionality

**Estimated Impact:**

- ControlPage: ~2,439 lines → ~300 lines (orchestration)
- 4 new components: ~500-600 lines each
- Better maintainability and testability

#### 2.2 Increase Test Coverage

**Target:** 70%+ coverage

**Strategy:**

- Add unit tests for new workflow components
- Add integration tests for ControlPage composition
- Add tests for custom hooks
- Focus on critical paths first

### Phase 3: Backend Refactoring

#### 3.1 Modularize routes.py

**Target Structure:**

```
src/dsa110_contimg/api/
├── routes/
│   ├── __init__.py
│   ├── images.py      # Image-related endpoints
│   ├── calibration.py # Calibration endpoints
│   ├── pipeline.py    # Pipeline/job management
│   ├── qa.py          # QA endpoints
│   ├── sources.py     # Source catalog endpoints
│   └── system.py      # Health, metrics, system info
├── __init__.py
└── main.py           # App factory, middleware setup
```

**Approach:**

1. Group endpoints by domain
2. Create router modules using FastAPI's `APIRouter`
3. Register routers in main app
4. Maintain backward compatibility

#### 3.2 Add API Versioning

**Strategy:**

- Use `/api/v1/` prefix for all endpoints
- Keep `/api/` as alias to `/api/v1/` for backward compatibility
- Plan for future `/api/v2/` migration

**Implementation:**

```python
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
app.include_router(v1_router)
```

#### 3.3 Implement Rate Limiting

**Strategy:**

- Use `slowapi` or `fastapi-limiter`
- Configure per-endpoint limits
- Different limits for authenticated vs anonymous
- Return 429 Too Many Requests with Retry-After header

#### 3.4 Verify OpenAPI Documentation

**Check:**

- `/docs` endpoint accessible
- `/redoc` endpoint accessible
- OpenAPI schema properly generated
- Add API descriptions and examples

## Progress Tracking

### Completed ✅

- [x] Replace console.log in QACartaPage.tsx (9 instances)

### In Progress 🚧

- [ ] Add ESLint rule for console.log prevention
- [ ] Audit remaining console.log usage

### Pending 📋

- [ ] Split ControlPage.tsx into workflow components
- [ ] Increase test coverage to 70%+
- [ ] Modularize routes.py
- [ ] Add API versioning
- [ ] Implement rate limiting
- [ ] Verify OpenAPI docs

## Files to Modify

### Frontend

- `frontend/src/pages/ControlPage.tsx` - Split into components
- `frontend/src/components/workflows/` - New directory for workflow components
- `frontend/src/hooks/useCalibrationWorkflow.ts` - New hook
- `frontend/src/hooks/useImagingWorkflow.ts` - New hook
- `frontend/src/hooks/useConversionWorkflow.ts` - New hook
- `frontend/src/hooks/useJobManagement.ts` - New hook
- `.eslintrc.js` - Add console.log rule

### Backend

- `src/dsa110_contimg/api/routes.py` - Split into modules
- `src/dsa110_contimg/api/routes/` - New directory structure
- `src/dsa110_contimg/api/main.py` - App factory (if needed)
- `requirements.txt` - Add rate limiting library

## Testing Strategy

1. **Unit Tests:** Test each new component/hook in isolation
2. **Integration Tests:** Test component composition and API routes
3. **E2E Tests:** Verify end-to-end workflows still work
4. **Backward Compatibility:** Ensure existing API clients still work

## Risk Mitigation

1. **Incremental Refactoring:** Make small, testable changes
2. **Feature Flags:** Use feature flags for new API versions
3. **Comprehensive Testing:** Test before and after each change
4. **Documentation:** Update API docs and component docs

## Success Criteria

- [ ] ControlPage.tsx < 500 lines
- [ ] Test coverage > 70%
- [ ] Zero console.log in production code
- [ ] routes.py split into < 1,000 line modules
- [ ] API versioning implemented
- [ ] Rate limiting active
- [ ] OpenAPI docs accessible and complete
