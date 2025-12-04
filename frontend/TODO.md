# TODO: Outstanding Feature Work

---

## ✅ COMPLETED FEATURES

These features have been fully implemented.

### Configurable alerts ✅
- Implemented: AlertPolicyList/Editor modal, silence creation, NotificationBell integration
- Files: `src/api/alertPolicies.ts`, alert components in `src/components/`

### Log aggregation UI ✅
- Implemented: LogViewer with virtualized list, live tail, syntax highlighting
- Files: `src/api/logs.ts`, log viewer components

### Resource utilization (CPU/memory/disk) ✅
- Implemented: Full Prometheus metrics integration with ECharts visualization
- Files:
  - `src/api/metrics.ts` - `useMetricsDashboard` hook
  - `src/components/metrics/MetricsDashboardPanel.tsx` - Tabbed panel (Overview/Resources/Pipeline/Custom)
  - `src/components/metrics/ResourceMetricsPanel.tsx` - CPU/memory/disk/network gauges
  - `src/components/metrics/ServiceDrilldownModal.tsx` - Per-service drill-down with time range selector (1h/6h/24h) and CSV/PNG export
  - `src/pages/HealthDashboardPage.tsx` - Integrated into dashboard

### Data cleanup UI (archival/deletion) ✅
- Implemented: Multi-step wizard with dry-run preview and audit notes
- Files:
  - `src/api/cleanup.ts` - API hooks for dry-run and execution
  - `src/pages/DataCleanupWizardPage.tsx` - Full wizard implementation
  - `src/pages/DataCleanupWizardPage.test.tsx` - Comprehensive tests

### Backup status ✅
- Implemented: Full backup/restore management with history and validation
- Files:
  - `src/api/backup.ts` - Full backup API with create/restore/validate
  - `src/pages/BackupRestorePage.tsx` - Backup management UI
  - `src/pages/BackupRestorePage.test.tsx` - Tests

### Custom pipeline triggers ✅
- Implemented: Trigger creation, scheduling, condition configuration, execution history
- Files:
  - `src/api/triggers.ts` - Trigger CRUD + execution hooks
  - `src/pages/PipelineTriggersPage.tsx` - Full trigger management
  - `src/pages/PipelineTriggersPage.test.tsx` - Tests

### Export to VO services ✅
- Implemented: VOTable/CSV/FITS export with format selection, async jobs, progress tracking
- Files:
  - `src/api/vo-export.ts` - Export job management, TAP queries, progress polling
  - `src/pages/VOExportPage.tsx` - Export wizard with format/target selection
  - `src/pages/VOExportPage.test.tsx` - Tests

### Jupyter integration ✅
- Implemented: Notebook management, template launching, JupyterHub integration
- Files:
  - `src/api/jupyter.ts` - Notebook API hooks
  - `src/pages/JupyterPage.tsx` - Notebook browser and launcher
  - `src/pages/JupyterPage.test.tsx` - Tests

### Shared queries ✅
- Implemented: Save/load filter configurations with visibility controls and shareable links
- Files:
  - `src/api/savedQueries.ts` - Full API with hooks, serialization utilities, shareable URL generation
  - `src/components/queries/SaveQueryModal.tsx` - Modal for saving/editing queries
  - `src/components/queries/SavedQueriesPanel.tsx` - Panel for listing, applying, and managing saved queries
  - `src/api/savedQueries.test.ts` - 25 utility tests
  - `src/components/queries/SaveQueryModal.test.tsx` - 10 component tests
  - `src/components/queries/SavedQueriesPanel.test.tsx` - 16 component tests

---

## 🔮 FUTURE DEVELOPMENT

These features are planned for future implementation when priorities allow.

### QA rating consensus
- **Current state**: Individual rating submission and display implemented
- **Existing files**:
  - `src/api/ratings.ts` - Rating API with categories, flags, summaries
  - `src/components/rating/RatingCard.tsx` - Individual rating component
- **Future work**:
  - Multi-user consensus calculation and display (median/majority vote)
  - RatingsPanel showing all user votes with attributions
  - History view showing rating changes over time
  - Tests for consensus math and permission gating

### Comments/annotations
- **Current state**: Not implemented
- **Future work**:
  - Add threaded comments on sources/images/jobs with mentions and markdown-lite
  - Real-time updates via SSE/WebSocket
  - Moderation flag and edit/delete with permissions
  - `src/api/comments.ts` with CRUD hooks and stream subscription
  - Threaded comment UI with mention autocomplete
