TODO: Outstanding Feature Work

- Configurable alerts
  - Implement alert policy CRUD UI (thresholds, durations, channels, severity, silence windows) backed by `/alert-policies` endpoints; validate with zod before submit.
  - Surface per-metric overrides and link current firing alerts to policies; show dry-run preview of which alerts would fire.
  - Frontend pieces: AlertPolicyList/Editor modal, silence creation inline, reuse NotificationBell/Panel for delivery channels.
  - Dependencies: backend storage/evaluation of policies, role checks for edit vs view, SSE/WebSocket stream of firing alerts.
  - Implementation steps:
    - [x] Confirm API contract for policy CRUD, dry-run, silences; generate types/openapi clients.
    - [x] Add hooks (`useAlertPolicies`, `useCreateAlertPolicy`, etc.) with optimistic updates and invalidation.
    - [x] Build policy list/table with filters, enable/disable toggle, and link to firing alerts.
    - [x] Build policy editor modal with zod validation and dry-run preview panel.
    - [x] Add inline silence creation from firing alerts; show active silences.
    - [x] Tests: basic editor validation; Storybook states (empty/error/loading) still pending.

- Log aggregation UI
  - Integrate with log store (Loki/Elastic) via a query API supporting text search, level filters, time ranges, and labels (service/job/run ID).
  - Build LogViewer with live tail toggle, pagination/virtualized list, highlight errors/warnings, and saved searches.
  - Add deep links from Jobs and Health panels (pre-filter by job id/service name).
  - Dependencies: log query/tail endpoints and auth redaction of sensitive fields.
  - Implementation steps:
    - [x] Define query params (q, level, labels, range, cursor) and response shape; add client + hooks (`useLogs`, `useLogTail`).
    - [x] Implement LogViewer with virtualized list, syntax highlighting, and sticky filters; add saved searches dropdown.
    - [x] Add live tail mode with backpressure (batch append) and auto-scroll toggle.
    - [x] Wire entry points from Jobs/Health pages with pre-populated filters.
    - [ ] Tests: hook pagination, tail reconnect, component filter interactions.

- Resource utilization (CPU/memory/disk)
  - Consume Prometheus (or similar) metrics for core services; predefine queries for 1h/6h/24h windows with downsampling.
  - Frontend: ResourceUtilizationPanel using ECharts (stacked area/line + sparkline cards), unit normalization (bytes -> GiB), and threshold indicators.
  - Add drill-down per service/pod and export as CSV/PNG.
  - Dependencies: metrics endpoint with service labels; consistent time bases (ISO timestamps).
  - Implementation steps:
    - [ ] Map metrics queries to API calls; add typed client + hooks (`useResourceMetrics`).
    - [ ] Build sparkline cards + main chart with range selector; include threshold bands.
    - [ ] Add drill-down modal per service/pod with legend toggles and export buttons.
    - [ ] Integrate panel into HealthDashboard; add loading/error/empty states.
    - [ ] Tests: hook transforms, unit formatting, chart renders with sample fixtures.

- Data cleanup UI (archival/deletion)
  - Provide wizard: select scope via filters (age, size, tags, status), run dry-run to estimate impact (bytes freed, counts), then submit archival/delete job.
  - Require multi-step confirmation with audit note; route execution through existing Jobs/Batch flows for status tracking.
  - Show policy hints from retention rules and block destructive actions without proper role.
  - Dependencies: cleanup/dry-run/execute APIs, RBAC, server-side guardrails.
  - Implementation steps:
    - [ ] Confirm cleanup/dry-run payloads; add client + hooks for dry-run and submit.
    - [ ] Build wizard steps: filters -> dry-run preview -> confirmation with audit note -> submit to Jobs.
    - [ ] Surface retention policy hints and RBAC errors inline; disable destructive actions when blocked.
    - [ ] Link to submitted job detail for status; add toast notifications.
    - [ ] Tests: dry-run flow, confirmation gating, RBAC error handling.

- Backup status
  - Display last backup time per dataset/bucket, success/failure history, coverage percentage, and “last restore test” timestamp/result.
  - UI: BackupStatusCards + timeline chart; warning states for stale backups and restore gaps; link to logs for failures.
  - Dependencies: backup status/restore-check APIs and timestamp normalization.
  - Implementation steps:
    - [ ] Add client/hooks for backup status and restore check history.
    - [ ] Build cards with state badges and tooltip details; add timeline chart of recent runs.
    - [ ] Add “stale backup” threshold highlighting and link to failure logs.
    - [ ] Tests: data mapping, warning thresholds, empty/error states.

- Custom pipeline triggers
  - UI to compose templated workflows (stages + parameters) and launch; versioned templates with schema validation.
  - Provide presets and diff vs default pipeline params; surface recent runs/history.
  - Dependencies: workflow engine API, template schema discovery, permissions by role.
  - Implementation steps:
    - [ ] Fetch template list + schema; generate forms dynamically (zod from schema).
    - [ ] Build PipelineBuilder with stage blocks, param validation, and diff vs defaults.
    - [ ] Submit runs into Jobs; show recent runs/history with status chips.
    - [ ] Tests: form validation, submission payloads, history rendering.

- Export to VO services
  - Add export actions on sources/images: choose format (VOTable/CSV/FITS list) and target (download, SAMP hub).
  - Use async export job for large selections; show progress and retry/download links on completion.
  - Dependencies: VO export endpoints and SAMP bridge service.
  - Implementation steps:
    - [ ] Add export client/hooks with progress polling; handle both sync (small) and async (large) flows.
    - [ ] Build ExportModal with format/target selection and progress UI; add SAMP send action.
    - [ ] Integrate into source/image list/toolbars and Batch flows.
    - [ ] Tests: payload shaping, progress polling, error recovery.

- Jupyter integration
  - Enable “Open in notebook” actions that pre-seed context (IDs/URLs) via signed links to JupyterHub; optionally inline read-only viewer for notebooks.
  - Handle token handoff securely; add fallback to launch new notebook with template.
  - Dependencies: JupyterHub/Spawner URL + token exchange API, CORS/frame policy.
  - Implementation steps:
    - [ ] Define signed URL/token exchange flow; add client to request notebook link.
    - [ ] Add “Open in notebook” buttons on detail pages; pass context params.
    - [ ] Optional: read-only iframe viewer when allowed; handle frame denial gracefully.
    - [ ] Tests: URL construction, missing-permission handling, iframe fallback.

- QA rating consensus
  - Store per-user ratings; compute consensus (median/majority) and display user attributions and history.
  - UI: Ratings panel showing individual votes, aggregate badge, and change log; restrict edits to authenticated users.
  - Dependencies: auth identities, ratings API supporting multiple entries + audit trail.
  - Implementation steps:
    - [ ] Confirm ratings schema supports multi-user entries + timestamps; add client/hooks.
    - [ ] Build RatingsPanel with per-user entries, consensus calculation, and edit controls.
    - [ ] Add history view and permission-guarded edit/delete.
    - [ ] Tests: consensus math, permission gating, optimistic updates.

- Comments/annotations
  - Add threaded comments on sources/images/jobs; support mentions, markdown-lite, and attachments (if allowed).
  - Real-time updates via SSE/WebSocket; moderation flag and edit/delete with permissions.
  - Dependencies: comments CRUD + stream endpoints, attachment handling, role checks.
  - Implementation steps:
    - [ ] Implement comments client/hooks (list/create/update/delete/flag) plus stream subscription.
    - [ ] Build threaded comment UI with mention autocomplete and markdown-lite renderer; attachment uploader if permitted.
    - [ ] Add moderation actions with role gating and optimistic UI.
    - [ ] Tests: threading rendering, realtime updates, permission errors.

- Shared queries
  - Allow saving filters with name/description/visibility (private/shared/global) and generate shareable links with serialized query state.
  - UI: Save/Load panels integrated with existing filter components; show owner and last updated; apply restores filters.
  - Dependencies: saved-query API with ACLs and stable serialization of filter config.
  - Implementation steps:
    - [ ] Define serialization format for filters; add client/hooks for save/list/delete/apply.
    - [ ] Build SaveQueryModal and SavedQueriesPanel; add apply action to restore filters.
    - [ ] Add visibility controls and owner badges; generate shareable links.
    - [ ] Tests: serialization round-trip, ACL enforcement feedback, apply flow.
