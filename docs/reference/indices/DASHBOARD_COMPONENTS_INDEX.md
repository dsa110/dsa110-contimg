# Dashboard Components Documentation Index

Complete documentation guide for each component of the DSA-110 monitoring
dashboard.

**Quick Links:** [Frontend](#frontend) | [Visualization](#visualization) |
[Architecture](#architecture) | [Backend](#backend) | [Monitoring](#monitoring)
| [Control Panel](#control-panel)

---

## Frontend

**Purpose:** React user interface for dashboard and monitoring

**Documents:** 89 | **Recent Updates:** 2025-11-14

### User Guide

| Quick Start                                               | Full Guide                                     | Control Panel                                                      | Settings                                                    |
| --------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------- |
| [Dashboard Quickstart](../../guides/dashboard/dashboard-quickstart.md) | [Full Dashboard Guide](../../guides/dashboard/dashboard.md) | [Control Panel Quick Start](../../guides/dashboard/control-panel-quickstart.md) | [Dashboard Development](../../guides/dashboard/dashboard-development.md) |

### Developer Guide

| Development Setup                                                   | Component Design                                         | Testing                                                         | Styling                                                       |
| ------------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------- |
| [Frontend Initial Setup](../../guides/dashboard/frontend-initial-setup.md)       | [Scientific UI Templates](../../architecture/dashboard/scientific_ui_templates.md) | [Playwright Python](../../guides/development/playwright-python-quick-start.md) | [Visual Improvements](../../guides/dashboard/visual_improvements_task2.md) |
| [Development Workflow](../../guides/dashboard/dashboard_development_workflow.md) | [UI Improvements](../../guides/dashboard/task3_ux_improvements.md)    | [Frontend Testing](../../guides/dashboard/run-all-frontend-tests.md)         | [Prettier Setup](../../guides/development/prettier_setup.md)                 |

### Deployment

| Docker                                              | Systemd                                               | Configuration                                              | Troubleshooting                                                        |
| --------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| [Docker Deployment](../../operations/deploy-docker.md) | [Systemd Deployment](../../operations/deploy-systemd.md) | [Safe Startup](../../operations/starting_dashboard_safely.md) | [Blank Page Issues](../../guides/dashboard/TROUBLESHOOTING_DASHBOARD_BLANK_PAGE.md) |
|                                                     |                                                       | [Vite Respawning](../../operations/vite_respawning_fix.md)    | [Frontend Restart](../../troubleshooting/frontend-restart-needed.md)      |

### Advanced Topics

- UX Pattern Opportunities
- Phase Implementations,
  [Phase 2](../../architecture/implementation/phase2_implementation_plan.md),
  [Phase 3](../../architecture/implementation/phase3_implementation_plan.md)
- UI Testing Results

---

## Visualization

**Purpose:** Data display and analysis tools (JS9, CARTA)

**Documents:** 40 | **Recent Updates:** 2025-11-13

### JS9 Integration

| Getting Started                                     | Usage                                                      | Development                                  |
| --------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------- |
| [JS9 CASA Analysis](../../guides/dashboard/js9_casa_analysis.md) | CASA Analysis API | [JS9 Setup](../../guides/dashboard/js9_casa_analysis.md) |

### CARTA Integration

| User Guide                                          | Quick Start                                         | Advanced                                                     | Deployment                                                |
| --------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------- |
| CARTA Guide | CARTA Quick Start | [CARTA Websocket](../../guides/dashboard/carta_websocket_enhancements.md) | [Enable Production](../../guides/dashboard/enable-carta-production.md) |
| [Testing Guide](../../guides/dashboard/carta_testing_guide.md)   |                                                     | [Port Allocation](../../guides/dashboard/carta_port_allocation.md)        | User Access             |

### Visualization Features

| Image Filters                                                                | Data Display                                                    | Pointing Monitor                                              | QA Visualization                                     |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------- |
| [Implementation Status](../image_filters_implementation_status.md) | [Dashboard Pages](../dashboard_pages_and_features.md) | [Pointing Visualization](../../guides/dashboard/pointing-visualization.md) | QA Framework        |
| [Test Results](../image_filters_test_results.md)                   | [HTML Reports](../html_reports_in_pipeline.md)        | [Deployment](../../guides/dashboard/pointing-monitor-deployment.md)        | QA Quick Start |

### Pointing Monitor

| Visualization                                            | Deployment                                                   | Testing                                                              |
| -------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------- |
| [Usage Guide](../../guides/dashboard/pointing-visualization-usage.md) | [Deployment Guide](../../guides/dashboard/pointing-monitor-deployment.md) | [Testing Results](../../archive/reports/POINTING_VISUALIZATION_TEST.md) |

---

## Architecture

**Purpose:** System design, data flow, and component relationships

**Documents:** 32 | **Recent Updates:** 2025-11-12

### System Design

| Overview                                                        | Data Models                                               | State Management                                              | Frontend Design                                                         |
| --------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [Dashboard Architecture](../../architecture/dashboard/dashboard_architecture.md) | [Data Models](../../architecture/dashboard/dashboard_data_models.md)       | [State Management](../../architecture/dashboard/dashboard_state_management.md) | [Frontend Architecture](../../architecture/dashboard/dashboard_frontend_architecture.md) |
| [Vision & Design](../../architecture/dashboard/dashboard_vision_and_design.md)   | [Error Handling](../../architecture/dashboard/dashboard_error_handling.md) |                                                               |                                                                         |

### Pipeline Integration

| Workflow                                                              | Stream/Mosaic                                                                     | Patterns                                              | Reference                                                                 |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------- |
| [Streaming Mosaic Workflow](../../architecture/pipeline/STREAMING_MOSAIC_WORKFLOW.md) | [Pipeline Workflow Visualization](../../architecture/pipeline/pipeline_workflow_visualization.md) | [Pipeline Patterns](../../architecture/pipeline/pipeline_patterns.md) | [Pipeline Stage Architecture](../../architecture/pipeline/pipeline_stage_architecture.md) |

### Advanced Architecture

- [Mockups & Design](../../architecture/dashboard/dashboard_mockups.md)
- [Future Roadmap](../../architecture/dashboard/dashboard_future_roadmap.md)
- [MCP Browser Architecture](../../architecture/tools/browser_mcp_chrome_remote_desktop_architecture.md)
- Design Improvements

---

## Backend

**Purpose:** API endpoints, database, and server logic

**Documents:** 22 | **Recent Updates:** 2025-11-13

### API Reference

| Full Reference                                                 | Endpoints                                          | Testing                                                    | Validation                                       |
| -------------------------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------ |
| [Dashboard Backend API](../dashboard_backend_api.md) | [API Endpoints](../api-endpoints.md)     | [API Testing Summary](../../archive/status_reports/API_TESTING_SUMMARY.md) | [Validation API](../validation_api.md) |
| [Generated Reference](../api_reference_generated.md) | [Test Commands](../API_TEST_COMMANDS.md) | [Test Results](../../archive/status_reports/API_TESTING_COMPLETE.md)       |                                                  |

### Database

| Schema                                             | Implementation                                                           | Catalog Migration                                          | Configuration                                                       |
| -------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------------------- |
| [Database Schema](../database_schema.md) | [Implementation Status](../dashboard_implementation_status.md) | [Catalog Migration](../../archive/progress-logs/catalog_migration_to_sqlite.md) | [Backend Integration](../backend_integration_snippets.md) |

### Operations

| Restart & Recovery                                      | Documentation                                                                      | Verification                                                     | Issues                                                              |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| [API Restart Guide](../../operations/API_RESTART_GUIDE.md) | [Documentation Verification](../dashboard_documentation_verification.md) | [Frontend Verification](../../archive/progress-logs/frontend_verification_summary.md) | [Potential Issues](../../architecture/implementation/potential_issues_and_fixes.md) |

### Development

- [Catalog Query Implementation](../../archive/progress-logs/catalog_query_implementation_complete.md)
- [Catalog Tests](../../archive/progress-logs/catalog_tests_summary.md)
- [Phase 3 Completion](../../archive/progress-logs/phase3_backend_complete.md)

---

## Monitoring

**Purpose:** System health, performance, and operational tracking

**Documents:** 8 | **Recent Updates:** 2025-11-12

| System Health                                                          | Pointing Tracking                                       | Log Management                                                | Performance                                                       |
| ---------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| CASA Log Daemon | [Pointing Monitor](../../guides/dashboard/pointing-visualization.md) | Log Monitoring | Performance Guide     |
|                                                                        | [Deployment](../../guides/dashboard/pointing-monitor-deployment.md)  | Log Fixes           | Implementation |

---

## Control Panel

**Purpose:** Operations interface for system control

**Documents:** 4 | **Recent Updates:** 2025-11-13

| Quick Start                                                       | Full Reference                                          | Advanced                                            | Usage                                                  |
| ----------------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------ |
| [Control Panel Quickstart](../../guides/dashboard/control-panel-quickstart.md) | [Control Panel Reference](../../architecture/dashboard/control-panel.md) | [Streaming Control](../../guides/workflow/streaming-control.md) | [Cheatsheet](../control-panel-cheatsheet.md) |

---

## Dashboard Feature Matrix

### Core Features

| Feature               | Status   | Documentation                                                 | Notes                   |
| --------------------- | -------- | ------------------------------------------------------------- | ----------------------- |
| Image Viewing (JS9)   | Complete | Reference            | FITS file inspection    |
| Image Viewing (CARTA) | Complete | Guide                       | Advanced visualization  |
| Pointing Monitor      | Complete | [Guide](../../guides/dashboard/pointing-visualization.md)                  | Real-time tracking      |
| Source Display        | Complete | [Reference](../dashboard_pages_and_features.md)     | Catalog visualization   |
| Image Filters         | Complete | [Status](../image_filters_implementation_status.md) | Filtering and selection |
| Control Panel         | Complete | [Quick Start](../../guides/dashboard/control-panel-quickstart.md)          | Operations interface    |

### Architecture & Infrastructure

| Component          | Status   | Documentation                                                |
| ------------------ | -------- | ------------------------------------------------------------ |
| React Frontend     | Complete | [Frontend Setup](../../guides/dashboard/frontend-initial-setup.md)        |
| Backend API        | Complete | [API Reference](../dashboard_backend_api.md)       |
| Database           | Complete | [Schema](../database_schema.md)                    |
| WebSocket Support  | Complete | [CARTA WebSocket](../../guides/dashboard/carta_websocket_enhancements.md) |
| Docker Deployment  | Complete | [Guide](../../operations/deploy-docker.md)                      |
| Systemd Deployment | Complete | [Guide](../../operations/deploy-systemd.md)                     |

---

## Development Phases

### Phase 1: Core Features

- Status: Complete
- Documentation: Phase 1 Status
- Testing: [Results](../../archive/progress-logs/phase1_test_results.md)

### Phase 2: Advanced Features

- Status: Complete
- Documentation: [Phase 2 Status](../../architecture/implementation/phase2_implementation_plan.md)
- Testing: [Results](../../archive/progress-logs/phase2_testing_summary.md)

### Phase 3: Polish & Integration

- Status: Complete
- Documentation: [Phase 3 Status](../../archive/progress-logs/phase3_complete.md)
- Testing: [Results](../../archive/progress-logs/phase3_testing_summary.md)

---

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────┐
│         Frontend (React)                        │
│  ├─ Dashboard Pages                            │
│  ├─ Control Panel                              │
│  └─ Visualization Components                   │
└────────┬────────────────────────┬──────────────┘
         │ HTTP/WebSocket         │
         │                        │
    ┌────▼────────────────┐  ┌───▼──────────────┐
    │ Backend API         │  │ JS9/CARTA        │
    │ ├─ Endpoints        │  │ ├─ FITS Display  │
    │ ├─ Business Logic   │  │ └─ Analysis      │
    │ └─ Error Handling   │  └──────────────────┘
    └────┬────────────────┘
         │
    ┌────▼────────────────┐
    │ Database            │
    │ ├─ Sources          │
    │ ├─ Images           │
    │ └─ Metadata         │
    └─────────────────────┘
```

---

## Deployment Topologies

### Development

```
Local Machine
├─ React Dev Server (Port 5173)
├─ Backend API (Port 8000)
└─ SQLite Database
```

### Production

```
Docker Containers
├─ Frontend Container (Port 3000)
├─ Backend Container (Port 8000)
├─ Database Container (PostgreSQL)
└─ JS9/CARTA Servers (Ports 7777+)
```

---

## Navigation

- Back to Main Index
- [Pipeline Stages Index](./PIPELINE_STAGES_INDEX.md)
- [General Themes Index](./GENERAL_THEMES_INDEX.md)
- [Documentation Framework](../documentation_standards/DOCUMENTATION_ORGANIZATIONAL_FRAMEWORK.md)

---

**Last Updated:** 2025-11-15  
**Total Documents:** 195  
**Status:** Complete
