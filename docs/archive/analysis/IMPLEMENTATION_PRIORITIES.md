# Implementation Priorities: VAST-Inspired Dashboard

## Overview

This document prioritizes VAST patterns for implementation, integrating them into the existing Phase 1-5 structure.

## Priority Matrix

### Critical Path (Must Have for MVP)

| Pattern | Phase | Priority | Dependencies | Effort |
|---------|-------|----------|--------------|--------|
| Generic Table Component | Phase 1 | P0 | None | Medium |
| State Management | Phase 1 | P0 | None | Medium |
| Detail Page Pattern | Phase 1 | P0 | Generic Table | Low |
| Source Statistics | Phase 2 | P0 | Data Model | High |
| Measurement Pair Metrics | Phase 2 | P0 | Data Model | High |
| Light Curve Visualization | Phase 3 | P0 | Measurement Pairs | Medium |
| Query Interface | Phase 3 | P0 | Generic Table | Medium |

### High Value (Important for Science)

| Pattern | Phase | Priority | Dependencies | Effort |
|---------|-------|----------|--------------|--------|
| Forced Extraction | Phase 2 | P1 | Data Model | High |
| Eta-V Plot | Phase 3 | P1 | Source Statistics | Low |
| Catalog Comparison | Phase 4 | P1 | Query Interface | Medium |
| Bulk Operations | Phase 2 | P1 | Data Model | Medium |

### Nice to Have (Enhancements)

| Pattern | Phase | Priority | Dependencies | Effort |
|---------|-------|----------|--------------|--------|
| Comments System | Phase 4 | P2 | Detail Pages | Low |
| Favorites/Bookmarks | Phase 4 | P2 | Detail Pages | Low |
| Configuration Management | Phase 2 | P2 | YAML Configs | Medium |
| Arrow Format Support | Phase 2 | P2 | Parquet Storage | Low |

## Phase 1 Implementation Plan (Weeks 1-2)

### Week 1: Foundation + Generic Table

**Day 1-2: State Management**
- [x] Install Zustand
- [ ] Create `dashboardStore.ts` with VAST-inspired state structure
- [ ] Implement basic state types (idle, autonomous, discovery, etc.)
- [ ] Create state transition functions

**Day 3-4: Generic Table Component (VAST Pattern #1)**
- [ ] Create `GenericTable.tsx` component
- [ ] Implement server-side pagination
- [ ] Add column configuration system
- [ ] Add search/filter functionality
- [ ] Add export functionality (CSV, Excel)
- [ ] Add column visibility toggle
- [ ] Reference: VAST's `generic_table.html` and `datatables-pipeline.js`

**Day 5: Integration**
- [ ] Integrate GenericTable into existing views
- [ ] Test with real API endpoints
- [ ] Add TypeScript types

### Week 2: Detail Pages + State Transitions

**Day 1-2: Detail Page Pattern (VAST Pattern #2)**
- [ ] Create `SourceDetailPage.tsx` with three-column layout
- [ ] Create `ImageDetailPage.tsx` with three-column layout
- [ ] Implement collapsible sections
- [ ] Add Previous/Next navigation
- [ ] Reference: VAST's `source_detail.html` and `image_detail.html`

**Day 3-4: State Transitions**
- [ ] Implement `useStateTransitions.ts` hook
- [ ] Add `useStreamingPipelineMonitor.ts` hook
- [ ] Integrate with streaming pipeline API
- [ ] Test state transitions

**Day 5: Polish & Testing**
- [ ] Add loading states
- [ ] Add error handling
- [ ] Write basic tests
- [ ] Document components

## Phase 2 Implementation Plan (Weeks 3-4)

### Week 3: Pipeline Processing (VAST Patterns #4, #5, #6)

**Day 1-2: Measurement Pair Metrics (VAST Pattern #4)**
- [ ] Create `src/dsa110_contimg/pipeline/pairs.py`
- [ ] Implement `calculate_vs_metric()`
- [ ] Implement `calculate_m_metric()`
- [ ] Implement `calculate_measurement_pair_metrics()`
- [ ] Add Dask parallelization
- [ ] Reference: VAST's `vast_pipeline/pipeline/pairs.py`

**Day 3-4: Source Statistics (VAST Pattern #6)**
- [ ] Create `src/dsa110_contimg/pipeline/finalise.py`
- [ ] Implement weighted averages calculation
- [ ] Implement aggregate flux metrics
- [ ] Implement variability metrics (v, eta)
- [ ] Implement nearest neighbor calculation
- [ ] Reference: VAST's `vast_pipeline/pipeline/finalise.py`

**Day 5: Forced Extraction (VAST Pattern #5)**
- [ ] Create `src/dsa110_contimg/pipeline/forced_extraction.py`
- [ ] Implement basic forced extraction
- [ ] Add edge detection
- [ ] Add NaN handling
- [ ] Reference: VAST's `vast_pipeline/pipeline/forced_extraction.py`

### Week 4: Bulk Operations + Pre-fetching

**Day 1-2: Bulk Operations (VAST Pattern #9)**
- [ ] Create `src/dsa110_contimg/pipeline/loading.py`
- [ ] Implement `bulk_upload_detections()`
- [ ] Implement `bulk_upload_sources()`
- [ ] Add batch processing
- [ ] Reference: VAST's `vast_pipeline/pipeline/loading.py`

**Day 3-5: Pre-fetching Engine**
- [ ] Create `useAnticipatoryPrefetch.ts`
- [ ] Implement preload target calculator
- [ ] Add pre-fetch to React Query
- [ ] Test pre-fetch performance

## Phase 3 Implementation Plan (Weeks 5-6)

### Week 5: Query Interface + Visualizations

**Day 1-2: Query Interface (VAST Pattern #3)**
- [ ] Create `SourceQueryBuilder.tsx`
- [ ] Implement filter UI (position, flux, variability, ESE flag)
- [ ] Add saved queries functionality
- [ ] Add export results
- [ ] Reference: VAST's `sources_query.html`

**Day 3-4: Light Curve Visualization (VAST Pattern #7)**
- [ ] Create `SourceLightCurve.tsx`
- [ ] Implement Plotly.js visualization
- [ ] Add forced vs detected differentiation
- [ ] Add interactive hover with cutouts
- [ ] Reference: VAST's source detail light curve

**Day 5: Eta-V Plot (VAST Pattern #7)**
- [ ] Create `EtaVPlot.tsx`
- [ ] Implement Plotly.js visualization
- [ ] Color by ESE probability
- [ ] Add interactive selection
- [ ] Reference: VAST's `sources_etav_plot.html`

### Week 6: Contextual Intelligence

**Day 1-3: Action Suggestions**
- [ ] Create `suggestActions.ts` engine
- [ ] Implement workflow state machine
- [ ] Add workflow manager component

**Day 4-5: Integration**
- [ ] Integrate with dashboard state
- [ ] Test action suggestions
- [ ] Polish UI

## Implementation Order Summary

### Phase 1 (Weeks 1-2): Foundation
1. ✅ State Management (Zustand)
2. ✅ Generic Table Component (VAST Pattern #1)
3. ✅ Detail Page Pattern (VAST Pattern #2)
4. ✅ State Transitions

### Phase 2 (Weeks 3-4): Pipeline Processing
1. ✅ Measurement Pair Metrics (VAST Pattern #4)
2. ✅ Source Statistics (VAST Pattern #6)
3. ✅ Forced Extraction (VAST Pattern #5)
4. ✅ Bulk Operations (VAST Pattern #9)
5. ✅ Pre-fetching Engine

### Phase 3 (Weeks 5-6): Query & Visualization
1. ✅ Query Interface (VAST Pattern #3)
2. ✅ Light Curve Visualization (VAST Pattern #7)
3. ✅ Eta-V Plot (VAST Pattern #7)
4. ✅ Contextual Intelligence

### Phase 4 (Weeks 7-8): UI Components
1. ✅ All view components (using VAST patterns)
2. ✅ Analysis workspace foundation

### Phase 5 (Weeks 9-12): Analysis Tools
1. ✅ Catalog Comparison (VAST-inspired)
2. ✅ Other analysis tools
3. ✅ Reproducibility system

## VAST Code References

### Frontend Components
- `archive/references/vast/vast-pipeline/templates/generic_table.html` - Generic table template
- `archive/references/vast/vast-pipeline/templates/source_detail.html` - Source detail page
- `archive/references/vast/vast-pipeline/templates/image_detail.html` - Image detail page
- `archive/references/vast/vast-pipeline/templates/sources_query.html` - Query interface
- `archive/references/vast/vast-pipeline/static/js/datatables-pipeline.js` - DataTables configuration

### Backend Processing
- `archive/references/vast/vast-pipeline/vast_pipeline/pipeline/pairs.py` - Measurement pairs
- `archive/references/vast/vast-pipeline/vast_pipeline/pipeline/finalise.py` - Source statistics
- `archive/references/vast/vast-pipeline/vast_pipeline/pipeline/forced_extraction.py` - Forced extraction
- `archive/references/vast/vast-pipeline/vast_pipeline/pipeline/loading.py` - Bulk operations

### Visualization
- `archive/references/vast/vast-pipeline/vast_pipeline/plots.py` - Bokeh plots (adapt to Plotly)
- `archive/references/vast/vast-pipeline/templates/sources_etav_plot.html` - Eta-V plot

## Success Criteria

### Phase 1 Complete When:
- [ ] Generic table component works with real API
- [ ] Source detail page displays correctly
- [ ] Image detail page displays correctly
- [ ] State transitions work smoothly
- [ ] All components have TypeScript types
- [ ] Basic tests pass

### Phase 2 Complete When:
- [ ] Measurement pair metrics calculate correctly
- [ ] Source statistics calculate correctly
- [ ] Forced extraction works for test cases
- [ ] Bulk operations are faster than individual inserts
- [ ] Pre-fetching reduces perceived load time

### Phase 3 Complete When:
- [ ] Query interface filters sources correctly
- [ ] Light curves display with forced/detected distinction
- [ ] Eta-V plot displays correctly
- [ ] Action suggestions appear contextually

## Notes

- All VAST patterns should be adapted for React/TypeScript/FastAPI
- Use existing DSA-110 API endpoints where possible
- Maintain consistency with existing codebase style
- Document all components with JSDoc
- Write tests for critical functionality

