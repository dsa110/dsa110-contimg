# Documentation Consolidation Plan

> **⚠️ NOTE (December 2024):** This plan has been **superseded**. Instead of creating a monolithic `USER_GUIDE.md`, we adopted a **topic-based approach** with focused guides:
>
> - `guides/storage-and-file-organization.md` - File paths, naming, databases
> - `guides/dashboard.md` - Web interface
> - `guides/calibration.md` - Calibration workflows
> - `guides/imaging.md` - Image creation
> - `guides/mosaicking.md` - Mosaic building
> - `guides/visualization.md` - CARTA and plotting
>
> The original USER_GUIDE.md has been deleted and its content redistributed to these topic files.

**Date:** 2025-12-01  
**Status:** ~~Planning Phase~~ Superseded  
**Target:** Reduce ~127 active docs → 6 core files + specialized directories

---

## Current State Analysis

### File Count by Category

| Directory          | Files    | Lines       | Status                                             |
| ------------------ | -------- | ----------- | -------------------------------------------------- |
| `architecture/`    | 20       | ~8,000      | Merge to ARCHITECTURE.md                           |
| `guides/`          | 52       | ~15,000     | Split between USER_GUIDE.md and DEVELOPER_GUIDE.md |
| `reference/`       | 25       | ~5,000      | Merge to API_REFERENCE.md                          |
| `troubleshooting/` | 8        | ~1,200      | Merge to TROUBLESHOOTING.md                        |
| `testing/`         | 4        | ~800        | Merge to DEVELOPER_GUIDE.md                        |
| Root files         | 10       | ~6,000      | Keep essential, archive rest                       |
| `changelog/`       | 2        | ~200        | Keep as-is                                         |
| `archive/`         | 748      | -           | Keep as-is (historical)                            |
| `ragflow/`         | 207      | -           | Keep as-is (external tool)                         |
| **Total Active**   | **~127** | **~36,000** | **Target: 6 core files**                           |

---

## Target Structure

```
docs/
├── README.md                    # Navigation hub (keep, update)
├── QUICKSTART.md                # NEW: Get running in 5 minutes
├── USER_GUIDE.md                # NEW: Complete user documentation
├── DEVELOPER_GUIDE.md           # NEW: Complete developer documentation
├── API_REFERENCE.md             # NEW: Consolidated API reference
├── ARCHITECTURE.md              # NEW: System architecture overview
├── TROUBLESHOOTING.md           # NEW: All troubleshooting in one place
│
├── architecture-decisions/      # Keep: Historical ADRs
│   ├── 001-sqlite-over-postgres.md
│   ├── 002-absurd-framework.md
│   └── 003-orchestrator-conversion.md
│
├── changelog/                   # Keep: Release notes
│   ├── 2025-11-27-frontend-routing.md
│   └── 2025-12-01-absurd-deployment.md
│
├── assets/                      # Keep: Images, diagrams
│   └── images/
│
├── archive/                     # Keep: Historical documentation
│   └── [existing 748 files]
│
└── ragflow/                     # Keep: External tool docs
    └── [existing 207 files]
```

---

## Content Mapping: Source → Target

### 1. QUICKSTART.md (~200 lines)

**Purpose:** Get a new user running the pipeline in 5 minutes

**Source files to merge:**

- `guides/dashboard/dashboard-quickstart.md` (extract core)
- `guides/streaming/quickstart.md` (extract core)
- `guides/carta/quickstart.md` (extract core)
- `guides/ABSURD_QUICKSTART.md` (extract core)

**Outline:**

```markdown
# DSA-110 Continuum Imaging: Quick Start

## Prerequisites

- conda environment: casa6
- Access to /data/incoming and /stage

## 1. Activate Environment (30 seconds)

conda activate casa6

## 2. Start Services (1 minute)

# Start API server

systemctl start contimg-api

# Start streaming converter

systemctl start contimg-stream

## 3. Access Dashboard (30 seconds)

Open http://localhost:3210/ui/

## 4. Run First Conversion (3 minutes)

python -m dsa110_contimg.conversion.cli groups \
 /data/incoming /stage/dsa110-contimg/ms \
 "2025-12-01T00:00:00" "2025-12-01T01:00:00"

## Next Steps

- [User Guide](USER_GUIDE.md) - Complete operations guide
- [Developer Guide](DEVELOPER_GUIDE.md) - Development setup
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues
```

---

### 2. USER_GUIDE.md (~3,000 lines)

**Purpose:** Complete operations documentation for pipeline users

**Source files to merge:**
| Section | Source Files |
|---------|-------------|
| Installation | `guides/index.md`, root `README.md` |
| Configuration | `guides/configuration/pipeline_configuration.md`, `reference/env.md` |
| Running Pipeline | `guides/streaming/deployment.md`, `guides/streaming/api.md` |
| Dashboard | `guides/dashboard/dashboard-quickstart.md`, `guides/dashboard/persistent-dashboard.md` |
| Mosaicking | `guides/workflow/mosaic.md`, `guides/workflow/batch_mosaic_creation.md` |
| Calibration | `reference/calibration-overview.md`, `reference/CURRENT_CALIBRATION_PROCEDURE.md` |
| Monitoring | `reference/monitoring.md`, `guides/dashboard/pointing-monitor-deployment.md` |
| ABSURD | `guides/ABSURD_QUICKSTART.md`, `guides/absurd-deployment-plan.md` |
| CARTA | `guides/carta/index.md`, `guides/carta/deployment.md` |

**Outline:**

```markdown
# DSA-110 Continuum Imaging: User Guide

## Part 1: Getting Started

### 1.1 Prerequisites

### 1.2 Installation

### 1.3 Configuration

### 1.4 Verification

## Part 2: Pipeline Operations

### 2.1 Starting Services

### 2.2 Streaming Conversion

### 2.3 Batch Conversion

### 2.4 Monitoring Pipeline Health

## Part 3: Dashboard

### 3.1 Accessing the Dashboard

### 3.2 Observation Timeline

### 3.3 Image Gallery

### 3.4 Pointing Monitor

### 3.5 Control Panel

## Part 4: Workflows

### 4.1 Calibration

### 4.2 Imaging

### 4.3 Mosaicking

### 4.4 Source Extraction

## Part 5: Advanced Features

### 5.1 ABSURD Workflow Manager

### 5.2 CARTA Integration

### 5.3 Scheduling Pipelines

## Part 6: Reference

### 6.1 CLI Commands

### 6.2 Environment Variables

### 6.3 Port Assignments
```

---

### 3. DEVELOPER_GUIDE.md (~2,500 lines)

**Purpose:** Complete development documentation

**Source files to merge:**
| Section | Source Files |
|---------|-------------|
| Setup | `guides/development/README.md`, `guides/contributing/index.md` |
| Architecture | `architecture/BACKEND_STRUCTURE.md`, `architecture/architecture/modules.md` |
| Testing | `testing/README.md`, `testing/CONTRACT_TESTING.md` |
| Frontend | `architecture/dashboard/dashboard_frontend_architecture.md` |
| Database | `reference/database_schema.md`, `reference/DATABASE_REFERENCE_INDEX.md` |
| Code Style | `guides/contributing/archive/rules.md` |
| Deployment | `guides/dashboard/dashboard_deployment.md`, `deployment/CALIBRATORS_MIGRATION.md` |

**Outline:**

```markdown
# DSA-110 Continuum Imaging: Developer Guide

## Part 1: Development Setup

### 1.1 Environment Setup

### 1.2 Repository Structure

### 1.3 Running Tests

### 1.4 Code Style & Linting

## Part 2: Architecture

### 2.1 System Overview

### 2.2 Module Organization

### 2.3 Data Flow

### 2.4 Database Schema

## Part 3: Backend Development

### 3.1 Pipeline Stages

### 3.2 Conversion Module

### 3.3 Calibration Module

### 3.4 Imaging Module

### 3.5 Adding New Features

## Part 4: Frontend Development

### 4.1 React Architecture

### 4.2 Components

### 4.3 State Management

### 4.4 API Integration

## Part 5: Testing

### 5.1 Contract Tests

### 5.2 Unit Tests

### 5.3 Integration Tests

### 5.4 End-to-End Tests

## Part 6: Deployment

### 6.1 Production Setup

### 6.2 Systemd Services

### 6.3 Database Migrations

### 6.4 Monitoring Setup
```

---

### 4. API_REFERENCE.md (~1,500 lines)

**Purpose:** Complete API documentation

**Source files to merge:**

- `reference/api_reference.md`
- `reference/api-endpoints.md`
- `reference/api.md`
- `reference/pipeline-api.md`
- `reference/validation_api.md`
- `reference/dashboard_backend_api.md`
- `guides/streaming/api.md`

**Outline:**

```markdown
# DSA-110 Continuum Imaging: API Reference

## Overview

### Base URL

### Authentication

### Response Format

## Conversion API

### POST /api/conversion/convert

### GET /api/conversion/status/{job_id}

### GET /api/conversion/groups

## Calibration API

### POST /api/calibration/run

### GET /api/calibration/tables

### GET /api/calibrator-imaging/pointing/status

## Imaging API

### POST /api/imaging/image

### GET /api/imaging/status/{job_id}

## Mosaic API

### POST /api/mosaic/create

### GET /api/mosaic/status/{name}

### GET /api/mosaic/list

## Data Access API

### GET /api/data/observations

### GET /api/data/images

### GET /api/data/products

## Pipeline API

### GET /api/pipeline/status

### POST /api/pipeline/execute

### GET /api/pipeline/runs

## Streaming API

### GET /api/streaming/status

### POST /api/streaming/control
```

---

### 5. ARCHITECTURE.md (~2,000 lines)

**Purpose:** System architecture overview

**Source files to merge:**

- `architecture/architecture/architecture.md`
- `architecture/architecture/DIRECTORY_ARCHITECTURE.md`
- `architecture/architecture/performance_considerations.md`
- `architecture/pipeline/pipeline_stage_architecture.md`
- `architecture/pipeline/streaming-architecture.md`
- `architecture/pipeline/pipeline_overview.md`
- `SYSTEM_CONTEXT.md`
- `CODE_MAP.md`

**Outline:**

```markdown
# DSA-110 Continuum Imaging: Architecture

## Part 1: System Overview

### 1.1 High-Level Architecture

### 1.2 Data Flow

### 1.3 Component Interactions

## Part 2: Pipeline Architecture

### 2.1 Stage-Based Design

### 2.2 Streaming Converter

### 2.3 Batch Processing

### 2.4 ABSURD Integration

## Part 3: Data Architecture

### 3.1 Directory Structure

### 3.2 Database Schema

### 3.3 File Formats

## Part 4: Frontend Architecture

### 4.1 Dashboard Components

### 4.2 State Management

### 4.3 Real-time Updates

## Part 5: Performance

### 5.1 I/O Optimization

### 5.2 Memory Management

### 5.3 Parallelization

## Part 6: Code Map

### 6.1 Module Dependencies

### 6.2 Key Classes

### 6.3 Extension Points
```

---

### 6. TROUBLESHOOTING.md (~1,000 lines)

**Purpose:** All troubleshooting in one searchable document

**Source files to merge:**

- `troubleshooting/runbooks/troubleshooting_common_scenarios.md`
- `troubleshooting/known-issues/image-metadata-population.md`
- `troubleshooting/resolved/casa-shutdown-error.md`
- `troubleshooting/resolved/frontend-restart-needed.md`
- `troubleshooting/resolved/ms-permission-errors.md`
- `troubleshooting/docker-wsclean.md`
- `guides/error-handling.md`
- `guides/streaming/troubleshooting.md`
- `guides/dashboard/TROUBLESHOOTING_DASHBOARD_BLANK_PAGE.md`

**Outline:**

```markdown
# DSA-110 Continuum Imaging: Troubleshooting

## Quick Diagnostics

### Health Check Commands

### Log Locations

### Common Error Patterns

## Conversion Issues

### HDF5 File Errors

### MS Writing Failures

### Subband Grouping Problems

## Calibration Issues

### Bandpass Table Errors

### Phase Calibration Failures

### Flux Scale Issues

## Imaging Issues

### WSClean Errors

### CASA tclean Problems

### Memory Exhaustion

## Dashboard Issues

### Blank Page

### API Connection Errors

### Real-time Updates Not Working

## Service Issues

### Systemd Service Failures

### Database Lock Errors

### Port Conflicts

## Resolved Issues Archive

### [Historical issues with solutions]
```

---

## Migration Strategy

### Phase 1: Create New Files (Week 1)

1. Create QUICKSTART.md with core content
2. Create USER_GUIDE.md skeleton with section headings
3. Create DEVELOPER_GUIDE.md skeleton
4. Create API_REFERENCE.md skeleton
5. Create ARCHITECTURE.md skeleton
6. Create TROUBLESHOOTING.md skeleton

### Phase 2: Migrate Content (Weeks 2-3)

1. Copy content from source files into appropriate sections
2. Deduplicate and harmonize conflicting information
3. Update internal links
4. Add cross-references between documents

### Phase 3: Redirect & Archive (Week 4)

1. Update mkdocs.yml to point to new structure
2. Move deprecated files to docs/archive/consolidated/
3. Create redirect stubs for common paths
4. Update .github/copilot-instructions.md

### Phase 4: Validation (Week 5)

1. Build mkdocs and verify all links work
2. Review with stakeholders
3. Update DocSearch index
4. Announce changes

---

## Files to Archive (move to docs/archive/consolidated/)

### From architecture/

- `architecture/architecture/` → merged to ARCHITECTURE.md
- `architecture/dashboard/` → merged to DEVELOPER_GUIDE.md + USER_GUIDE.md
- `architecture/pipeline/` → merged to ARCHITECTURE.md

### From guides/

- `guides/streaming/` → merged to USER_GUIDE.md
- `guides/dashboard/` → merged to USER_GUIDE.md
- `guides/workflow/` → merged to USER_GUIDE.md
- `guides/development/` → merged to DEVELOPER_GUIDE.md
- `guides/carta/` → merged to USER_GUIDE.md
- `guides/configuration/` → merged to USER_GUIDE.md

### From reference/

- Most files → merged to API_REFERENCE.md
- `mcp-tools.md`, `agent_guidelines.md` → keep separate (AI tooling)

### From troubleshooting/

- All files → merged to TROUBLESHOOTING.md

### From testing/

- All files → merged to DEVELOPER_GUIDE.md

---

## Files to Keep Separate

| File                            | Reason                    |
| ------------------------------- | ------------------------- |
| `docs/README.md`                | Navigation hub            |
| `docs/changelog/*`              | Release notes history     |
| `docs/archive/*`                | Historical reference      |
| `docs/ragflow/*`                | External tool integration |
| `reference/mcp-tools.md`        | AI tooling reference      |
| `reference/agent_guidelines.md` | AI coding guidelines      |
| `DEVELOPMENT_ROADMAP.md`        | Project planning          |

---

## Success Metrics

| Metric                         | Before  | After                  | Improvement    |
| ------------------------------ | ------- | ---------------------- | -------------- |
| Active doc files               | 127     | 6 core + 10 supporting | 95% reduction  |
| Navigation clicks to find info | 3-5     | 1-2                    | 60% reduction  |
| Duplicate content instances    | ~50     | 0                      | 100% reduction |
| Time to onboard new developer  | ~1 week | ~2 days                | 70% reduction  |

---

## Next Steps

1. [ ] Review this plan with stakeholders
2. [ ] Create QUICKSTART.md first (smallest, highest impact)
3. [ ] Progressively consolidate remaining docs
4. [ ] Update mkdocs.yml navigation
5. [ ] Archive deprecated files
6. [ ] Update copilot-instructions.md with new paths
