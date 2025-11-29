# Code to Documentation Map

**Purpose:** This document links the active source code directories to their
corresponding documentation and status. Use this to navigate the codebase.

**Last Updated:** November 26, 2025

---

## :world_map::variation_selector-16: System Map

### 1. Core Pipeline Infrastructure

**Code Location:** `backend/src/dsa110_contimg/pipeline/` **Status:** :green_circle:
**Production**

| Component         | Code File        | Documentation                                                              |
| :---------------- | :--------------- | :------------------------------------------------------------------------- |
| **Health Checks** | `health.py`      | [Pipeline Features](architecture/pipeline/pipeline_production_features.md) |
| **Timeouts**      | `timeout.py`     | [Pipeline Features](architecture/pipeline/pipeline_production_features.md) |
| **Stage Logic**   | `stages_impl.py` | [Stage Architecture](architecture/pipeline/pipeline_stage_architecture.md) |
| **Context**       | `context.py`     | [Stage Architecture](architecture/pipeline/pipeline_stage_architecture.md) |

### 2. Workflow Management ("Absurd")

**Code Location:** `backend/src/dsa110_contimg/absurd/` & `ops/scripts/absurd/`
**Status:** :green_circle: **Active Integration**

| Component        | Code File                               | Documentation                                    |
| :--------------- | :-------------------------------------- | :----------------------------------------------- |
| **Overview**     | `README.md`                             | [ABSURD Quickstart](guides/ABSURD_QUICKSTART.md) |
| **Setup Script** | `ops/scripts/absurd/setup_absurd_db.sh` | [Workflow Guides](guides/workflow/)              |

### 3. Quality Assurance (QA)

**Code Location:** `backend/src/dsa110_contimg/qa/` **Status:** :yellow_circle: **In
Development**

| Component              | Code File               | Documentation                               |
| :--------------------- | :---------------------- | :------------------------------------------ |
| **Catalog Validation** | `catalog_validation.py` | [API Reference](reference/api_reference.md) |
| **Visualization**      | `visualization/`        | [Dashboard](guides/dashboard/)              |

### 4. Imaging & Calibration

**Code Location:** `backend/src/dsa110_contimg/imaging/` &
`backend/src/dsa110_contimg/calibration/` **Status:** :green_circle: **Production**

| Component           | Code File                | Documentation                                                  |
| :------------------ | :----------------------- | :------------------------------------------------------------- |
| **WSClean Wrapper** | `imaging/cli_imaging.py` | [Docker Issues](troubleshooting/docker_wsclean_known_issue.md) |
| **Self-Cal**        | `calibration/selfcal.py` | [Architecture](architecture/architecture/architecture.md)      |

### 5. Frontend Dashboard

**Code Location:** `frontend/src/` **Status:** :green_circle: **Production (Phase 3)**

| Component           | Code File                  | Documentation                                                              |
| :------------------ | :------------------------- | :------------------------------------------------------------------------- |
| **Main App**        | `App.tsx`                  | [Dashboard Guide](guides/dashboard/dashboard-quickstart.md)                |
| **Operations Page** | `pages/OperationsPage.tsx` | [Dashboard Guide](guides/dashboard/)                                       |
| **API Client**      | `api/client.ts`            | [Dashboard Architecture](architecture/dashboard/dashboard_architecture.md) |

---

## :warning: Deprecation Warnings

The following documentation may be out of sync with the codebase:

1. **`docs/testing/CURRENT_STATUS.md`**: May contain outdated testing status.
   Check `docs/testing/` for current test documentation.

2. **`docs/architecture/architecture/DIRECTORY_ARCHITECTURE.md`**: The "Proposed
   Structure" section is now the **Actual Structure**.
