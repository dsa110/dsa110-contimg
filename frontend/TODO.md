# TODO: Outstanding Feature Work

---

## ✅ COMPLETED FEATURES

These features have been fully implemented but were not previously marked complete.

### Configurable alerts ✅
- Implemented: AlertPolicyList/Editor modal, silence creation, NotificationBell integration
- Files: `src/api/alertPolicies.ts`, alert components in `src/components/`
- All implementation steps complete

### Log aggregation UI ✅
- Implemented: LogViewer with virtualized list, live tail, syntax highlighting
- Files: `src/api/logs.ts`, log viewer components
- All implementation steps complete

### Resource utilization (CPU/memory/disk) ✅
- Implemented: Full Prometheus metrics integration with ECharts visualization
- Files:
  - `src/api/metrics.ts` - `useMetricsDashboard` hook
  - `src/components/metrics/MetricsDashboardPanel.tsx` - Tabbed panel (Overview/Resources/Pipeline/Custom)
  - `src/components/metrics/ResourceMetricsPanel.tsx` - CPU/memory/disk/network gauges
  - `src/components/metrics/ServiceDrilldownModal.tsx` - Per-service drill-down with time range selector (1h/6h/24h) and CSV/PNG export
  - `src/pages/HealthDashboardPage.tsx` - Integrated into dashboard
- All implementation steps complete

### Data cleanup UI (archival/deletion) ✅
- Implemented: Multi-step wizard with dry-run preview and audit notes
- Files:
  - `src/api/cleanup.ts` - API hooks for dry-run and execution
  - `src/pages/DataCleanupWizardPage.tsx` (903 lines) - Full wizard implementation
  - `src/pages/DataCleanupWizardPage.test.tsx` - Comprehensive tests
- All implementation steps complete

### Backup status ✅
- Implemented: Full backup/restore management with history and validation
- Files:
  - `src/api/backup.ts` - Full backup API with create/restore/validate
  - `src/pages/BackupRestorePage.tsx` (903 lines) - Backup management UI
  - `src/pages/BackupRestorePage.test.tsx` - Tests
- All implementation steps complete

### Custom pipeline triggers ✅
- Implemented: Trigger creation, scheduling, condition configuration, execution history
- Files:
  - `src/api/triggers.ts` - Trigger CRUD + execution hooks
  - `src/pages/PipelineTriggersPage.tsx` (843 lines) - Full trigger management
  - `src/pages/PipelineTriggersPage.test.tsx` - Tests
- All implementation steps complete

### Export to VO services ✅
- Implemented: VOTable/CSV/FITS export with format selection, async jobs, progress tracking
- Files:
  - `src/api/vo-export.ts` - Export job management, TAP queries, progress polling
  - `src/pages/VOExportPage.tsx` - Export wizard with format/target selection
  - `src/pages/VOExportPage.test.tsx` - Tests
- All implementation steps complete

### Jupyter integration ✅
- Implemented: Notebook management, template launching, JupyterHub integration
- Files:
  - `src/api/jupyter.ts` - Notebook API hooks
  - `src/pages/JupyterPage.tsx` - Notebook browser and launcher
  - `src/pages/JupyterPage.test.tsx` - Tests
- All implementation steps complete

---

## ⚠️ PARTIALLY IMPLEMENTED

### QA rating consensus
- Implemented: Individual rating submission and display
- Files:
  - `src/api/ratings.ts` - Rating API with categories, flags, summaries
  - `src/components/rating/RatingCard.tsx` (301 lines) - Individual rating component
- Missing:
  - [ ] Multi-user consensus calculation and display (median/majority vote)
  - [ ] RatingsPanel showing all user votes with attributions
  - [ ] History view showing rating changes over time
  - [ ] Tests for consensus math and permission gating

---

## ❌ NOT IMPLEMENTED

### Comments/annotations
- Add threaded comments on sources/images/jobs; support mentions, markdown-lite, and attachments (if allowed).
- Real-time updates via SSE/WebSocket; moderation flag and edit/delete with permissions.
- Dependencies: comments CRUD + stream endpoints, attachment handling, role checks.
- Implementation steps:
  - [ ] Create `src/api/comments.ts` with hooks (list/create/update/delete/flag) plus stream subscription.
  - [ ] Build threaded comment UI with mention autocomplete and markdown-lite renderer; attachment uploader if permitted.
  - [ ] Add moderation actions with role gating and optimistic UI.
  - [ ] Tests: threading rendering, realtime updates, permission errors.

### Shared queries
- Allow saving filters with name/description/visibility (private/shared/global) and generate shareable links with serialized query state.
- UI: Save/Load panels integrated with existing filter components; show owner and last updated; apply restores filters.
- Dependencies: saved-query API with ACLs and stable serialization of filter config.
- Implementation steps:
  - [ ] Create `src/api/savedQueries.ts` - Define serialization format for filters; add hooks for save/list/delete/apply.
  - [ ] Build SaveQueryModal and SavedQueriesPanel; add apply action to restore filters.
  - [ ] Add visibility controls and owner badges; generate shareable links.
  - [ ] Tests: serialization round-trip, ACL enforcement feedback, apply flow.
