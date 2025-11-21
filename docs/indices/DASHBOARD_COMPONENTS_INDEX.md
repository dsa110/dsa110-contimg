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
| [Dashboard Quickstart](../how-to/dashboard-quickstart.md) | [Full Dashboard Guide](../how-to/dashboard.md) | [Control Panel Quick Start](../how-to/control-panel-quickstart.md) | [Dashboard Development](../how-to/dashboard-development.md) |

### Developer Guide

| Development Setup                                                   | Component Design                                         | Testing                                                         | Styling                                                       |
| ------------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------- |
| [Frontend Initial Setup](../how-to/frontend-initial-setup.md)       | [Scientific UI Templates](../scientific_ui_templates.md) | [Playwright Python](../how-to/playwright-python-quick-start.md) | [Visual Improvements](../how-to/visual_improvements_task2.md) |
| [Development Workflow](../how-to/dashboard_development_workflow.md) | [UI Improvements](../how-to/task3_ux_improvements.md)    | [Frontend Testing](../how-to/run-all-frontend-tests.md)         | [Prettier Setup](../how-to/prettier_setup.md)                 |

### Deployment

| Docker                                              | Systemd                                               | Configuration                                              | Troubleshooting                                                        |
| --------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| [Docker Deployment](../operations/deploy-docker.md) | [Systemd Deployment](../operations/deploy-systemd.md) | [Safe Startup](../operations/starting_dashboard_safely.md) | [Blank Page Issues](../how-to/TROUBLESHOOTING_DASHBOARD_BLANK_PAGE.md) |
|                                                     |                                                       | [Vite Respawning](../operations/vite_respawning_fix.md)    | [Frontend Restart](../troubleshooting/frontend-restart-needed.md)      |

### Advanced Topics

- [UX Pattern Opportunities](../archive/task3_ux_pattern_opportunities.md)
- [Phase Implementations](../dev/phase1_implementation_status.md),
  [Phase 2](../dev/phase2_implementation_plan.md),
  [Phase 3](../dev/phase3_implementation_plan.md)
- [UI Testing Results](../dev/phase1_ui_testing_complete.md)

---

## Visualization

**Purpose:** Data display and analysis tools (JS9, CARTA)

**Documents:** 40 | **Recent Updates:** 2025-11-13

### JS9 Integration

| Getting Started                                     | Usage                                                      | Development                                  |
| --------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------- |
| [JS9 CASA Analysis](../how-to/js9_casa_analysis.md) | [CASA Analysis API](../reference/js9_casa_analysis_api.md) | [JS9 Setup](../archive/js9_casa_analysis.md) |

### CARTA Integration

| User Guide                                          | Quick Start                                         | Advanced                                                     | Deployment                                                |
| --------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------ | --------------------------------------------------------- |
| [CARTA Guide](../how-to/carta_integration_guide.md) | [CARTA Quick Start](../how-to/carta_quick_start.md) | [CARTA Websocket](../how-to/carta_websocket_enhancements.md) | [Enable Production](../how-to/enable-carta-production.md) |
| [Testing Guide](../how-to/carta_testing_guide.md)   |                                                     | [Port Allocation](../how-to/carta_port_allocation.md)        | [User Access](../how-to/carta_user_access.md)             |

### Visualization Features

| Image Filters                                                                | Data Display                                                    | Pointing Monitor                                              | QA Visualization                                     |
| ---------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------- |
| [Implementation Status](../reference/image_filters_implementation_status.md) | [Dashboard Pages](../reference/dashboard_pages_and_features.md) | [Pointing Visualization](../how-to/pointing-visualization.md) | [QA Framework](../QA_VISUALIZATION_DESIGN.md)        |
| [Test Results](../reference/image_filters_test_results.md)                   | [HTML Reports](../reference/html_reports_in_pipeline.md)        | [Deployment](../how-to/pointing-monitor-deployment.md)        | [QA Quick Start](../QA_VISUALIZATION_QUICK_START.md) |

### Pointing Monitor

| Visualization                                            | Deployment                                                   | Testing                                                              |
| -------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------------------------- |
| [Usage Guide](../how-to/pointing-visualization-usage.md) | [Deployment Guide](../how-to/pointing-monitor-deployment.md) | [Testing Results](../archive/reports/POINTING_VISUALIZATION_TEST.md) |

---

## Architecture

**Purpose:** System design, data flow, and component relationships

**Documents:** 32 | **Recent Updates:** 2025-11-12

### System Design

| Overview                                                        | Data Models                                               | State Management                                              | Frontend Design                                                         |
| --------------------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [Dashboard Architecture](../concepts/dashboard_architecture.md) | [Data Models](../concepts/dashboard_data_models.md)       | [State Management](../concepts/dashboard_state_management.md) | [Frontend Architecture](../concepts/dashboard_frontend_architecture.md) |
| [Vision & Design](../concepts/dashboard_vision_and_design.md)   | [Error Handling](../concepts/dashboard_error_handling.md) |                                                               |                                                                         |

### Pipeline Integration

| Workflow                                                              | Stream/Mosaic                                                                     | Patterns                                              | Reference                                                                 |
| --------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------- |
| [Streaming Mosaic Workflow](../concepts/STREAMING_MOSAIC_WORKFLOW.md) | [Pipeline Workflow Visualization](../concepts/pipeline_workflow_visualization.md) | [Pipeline Patterns](../concepts/pipeline_patterns.md) | [Pipeline Stage Architecture](../concepts/pipeline_stage_architecture.md) |

### Advanced Architecture

- [Mockups & Design](../concepts/dashboard_mockups.md)
- [Future Roadmap](../concepts/dashboard_future_roadmap.md)
- [MCP Browser Architecture](../concepts/browser_mcp_chrome_remote_desktop_architecture.md)
- [Design Improvements](../analysis/DASHBOARD_DESIGN_IMPROVEMENTS.md)

---

## Backend

**Purpose:** API endpoints, database, and server logic

**Documents:** 22 | **Recent Updates:** 2025-11-13

### API Reference

| Full Reference                                                 | Endpoints                                          | Testing                                                    | Validation                                       |
| -------------------------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------ |
| [Dashboard Backend API](../reference/dashboard_backend_api.md) | [API Endpoints](../reference/api-endpoints.md)     | [API Testing Summary](../reference/API_TESTING_SUMMARY.md) | [Validation API](../reference/validation_api.md) |
| [Generated Reference](../reference/api_reference_generated.md) | [Test Commands](../reference/API_TEST_COMMANDS.md) | [Test Results](../reference/API_TESTING_COMPLETE.md)       |                                                  |

### Database

| Schema                                             | Implementation                                                           | Catalog Migration                                          | Configuration                                                       |
| -------------------------------------------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------------------- |
| [Database Schema](../reference/database_schema.md) | [Implementation Status](../reference/dashboard_implementation_status.md) | [Catalog Migration](../dev/catalog_migration_to_sqlite.md) | [Backend Integration](../reference/backend_integration_snippets.md) |

### Operations

| Restart & Recovery                                      | Documentation                                                                      | Verification                                                     | Issues                                                              |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| [API Restart Guide](../operations/API_RESTART_GUIDE.md) | [Documentation Verification](../reference/dashboard_documentation_verification.md) | [Frontend Verification](../dev/frontend_verification_summary.md) | [Potential Issues](../implementation/potential_issues_and_fixes.md) |

### Development

- [Catalog Query Implementation](../dev/catalog_query_implementation_complete.md)
- [Catalog Tests](../dev/catalog_tests_summary.md)
- [Phase 3 Completion](../dev/phase3_backend_complete.md)

---

## Monitoring

**Purpose:** System health, performance, and operational tracking

**Documents:** 8 | **Recent Updates:** 2025-11-12

| System Health                                                          | Pointing Tracking                                       | Log Management                                                | Performance                                                       |
| ---------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------- |
| [CASA Log Daemon](../operations/CASA_LOG_DAEMON_PROTECTION_SUMMARY.md) | [Pointing Monitor](../how-to/pointing-visualization.md) | [Log Monitoring](../operations/CASA_LOG_DAEMON_MONITORING.md) | [Performance Guide](../how-to/performance_and_scalability.md)     |
|                                                                        | [Deployment](../how-to/pointing-monitor-deployment.md)  | [Log Fixes](../operations/CASA_LOG_DAEMON_FIXES.md)           | [Implementation](../how-to/performance_implementation_summary.md) |

---

## Control Panel

**Purpose:** Operations interface for system control

**Documents:** 4 | **Recent Updates:** 2025-11-13

| Quick Start                                                       | Full Reference                                          | Advanced                                            | Usage                                                  |
| ----------------------------------------------------------------- | ------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------ |
| [Control Panel Quickstart](../how-to/control-panel-quickstart.md) | [Control Panel Reference](../concepts/control-panel.md) | [Streaming Control](../how-to/streaming-control.md) | [Cheatsheet](../reference/control-panel-cheatsheet.md) |

---

## Dashboard Feature Matrix

### Core Features

| Feature               | Status   | Documentation                                                 | Notes                   |
| --------------------- | -------- | ------------------------------------------------------------- | ----------------------- |
| Image Viewing (JS9)   | Complete | [Reference](../reference/js9_casa_analysis_api.md)            | FITS file inspection    |
| Image Viewing (CARTA) | Complete | [Guide](../how-to/carta_quick_start.md)                       | Advanced visualization  |
| Pointing Monitor      | Complete | [Guide](../how-to/pointing-visualization.md)                  | Real-time tracking      |
| Source Display        | Complete | [Reference](../reference/dashboard_pages_and_features.md)     | Catalog visualization   |
| Image Filters         | Complete | [Status](../reference/image_filters_implementation_status.md) | Filtering and selection |
| Control Panel         | Complete | [Quick Start](../how-to/control-panel-quickstart.md)          | Operations interface    |

### Architecture & Infrastructure

| Component          | Status   | Documentation                                                |
| ------------------ | -------- | ------------------------------------------------------------ |
| React Frontend     | Complete | [Frontend Setup](../how-to/frontend-initial-setup.md)        |
| Backend API        | Complete | [API Reference](../reference/dashboard_backend_api.md)       |
| Database           | Complete | [Schema](../reference/database_schema.md)                    |
| WebSocket Support  | Complete | [CARTA WebSocket](../how-to/carta_websocket_enhancements.md) |
| Docker Deployment  | Complete | [Guide](../operations/deploy-docker.md)                      |
| Systemd Deployment | Complete | [Guide](../operations/deploy-systemd.md)                     |

---

## Development Phases

### Phase 1: Core Features

- Status: Complete
- Documentation: [Phase 1 Status](../dev/phase1_implementation_status.md)
- Testing: [Results](../dev/phase1_test_results.md)

### Phase 2: Advanced Features

- Status: Complete
- Documentation: [Phase 2 Status](../dev/phase2_implementation_plan.md)
- Testing: [Results](../dev/phase2_testing_summary.md)

### Phase 3: Polish & Integration

- Status: Complete
- Documentation: [Phase 3 Status](../dev/phase3_complete.md)
- Testing: [Results](../dev/phase3_testing_summary.md)

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

- [Back to Main Index](../START_HERE_DOCUMENT_INVENTORY.md)
- [Pipeline Stages Index](./PIPELINE_STAGES_INDEX.md)
- [General Themes Index](./GENERAL_THEMES_INDEX.md)
- [Documentation Framework](../DOCUMENTATION_ORGANIZATIONAL_FRAMEWORK.md)

---

**Last Updated:** 2025-11-15  
**Total Documents:** 195  
**Status:** Complete
