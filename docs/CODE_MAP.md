# Code to Documentation Map

**Purpose:** This document links the active source code directories to their
corresponding documentation and status. Use this to navigate the codebase.

**Last Updated:** November 25, 2025

---

## 🗺️ System Map

### 1. Core Pipeline Infrastructure

**Code Location:** `backend/src/dsa110_contimg/pipeline/` **Status:** 🟢
**Production**

| Component         | Code File        | Documentation                                                                             |
| :---------------- | :--------------- | :---------------------------------------------------------------------------------------- |
| **Health Checks** | `health.py`      | `concepts/pipeline_production_features.md` |
| **Timeouts**      | `timeout.py`     | `concepts/pipeline_production_features.md` |
| **Stage Logic**   | `stages_impl.py` | `concepts/pipeline_stage_architecture.md`   |
| **Context**       | `context.py`     | `concepts/pipeline_stage_architecture.md`   |

### 2. Workflow Management ("Absurd")

**Code Location:** `backend/src/dsa110_contimg/absurd/` & `ops/scripts/absurd/`
**Status:** 🟢 **Active Integration**

| Component        | Code File                               | Documentation                                                                         |
| :--------------- | :-------------------------------------- | :------------------------------------------------------------------------------------ |
| **Overview**     | `README.md`                             | `concepts/absurd_documentation_index.md` |
| **Setup Script** | `ops/scripts/absurd/setup_absurd_db.sh` | [`how-to/workflow/`](../how-to/workflow/)                                             |

### 3. Quality Assurance (QA)

**Code Location:** `backend/src/dsa110_contimg/qa/` **Status:** 🟡 **In
Development**

| Component              | Code File               | Documentation                                                                                     |
| :--------------------- | :---------------------- | :------------------------------------------------------------------------------------------------ |
| **Catalog Validation** | `catalog_validation.py` | `implementation/high_priority_improvements.md` |
| **Visualization**      | `visualization/`        | `concepts/qa_visualization_design.md`                   |

### 4. Imaging & Calibration

**Code Location:** `backend/src/dsa110_contimg/imaging/` &
`backend/src/dsa110_contimg/calibration/` **Status:** 🟢 **Production**

| Component           | Code File                | Documentation                                                                                 |
| :------------------ | :----------------------- | :-------------------------------------------------------------------------------------------- |
| **WSClean Wrapper** | `imaging/cli_imaging.py` | `troubleshooting/wsclean_docker_hang_fix.md` |
| **Self-Cal**        | `calibration/selfcal.py` | `concepts/architecture.md`                                     |

### 5. Frontend Dashboard

**Code Location:** `frontend/src/` **Status:** 🟢 **Production (Phase 3)**

| Component           | Code File                  | Documentation                                                                 |
| :------------------ | :------------------------- | :---------------------------------------------------------------------------- |
| **Main App**        | `App.tsx`                  | `logs/phase3_complete.md`                       |
| **Operations Page** | `pages/OperationsPage.tsx` | [`how-to/dashboard/`](../how-to/dashboard/)                                   |
| **API Client**      | `api/client.ts`            | `concepts/dashboard_architecture.md` |

---

## ⚠️ Deprecation Warnings

The following documentation areas are currently **out of sync** with the
codebase:

1.  **`docs/testing/CURRENT_STATUS.md`**: Claims automated testing is broken.
    **Incorrect.** See `docs/logs/phase1_browser_testing_complete.md` for the
    true status.
2.  **`docs/concepts/DIRECTORY_ARCHITECTURE.md`**: The "Proposed Structure"
    section is now the **Actual Structure**.
