# Code to Documentation Map

**Purpose:** This document links the active source code directories to their
corresponding documentation and status. Use this to navigate the codebase.

**Last Updated:** December 4, 2025

---

## :world_map::variation_selector-16: System Map

### 1. Core Pipeline Infrastructure

**Code Location:** `backend/src/dsa110_contimg/pipeline/` **Status:** :green_circle:
**Production**

| Component         | Code File        | Documentation                         |
| :---------------- | :--------------- | :------------------------------------ |
| **Health Checks** | `health.py`      | [Architecture](ARCHITECTURE.md)       |
| **Timeouts**      | `timeout.py`     | [Architecture](ARCHITECTURE.md)       |
| **Stage Logic**   | `stages_impl.py` | [Architecture](ARCHITECTURE.md)       |
| **Context**       | `context.py`     | [Developer Guide](DEVELOPER_GUIDE.md) |

### 2. Workflow Management ("ABSURD")

**Code Location:** `backend/src/dsa110_contimg/absurd/` & `scripts/ops/absurd/`
**Status:** :green_circle: **Active Integration**

| Component        | Code File                               | Documentation                                   |
| :--------------- | :-------------------------------------- | :---------------------------------------------- |
| **Overview**     | `README.md`                             | `backend/docs/ops/absurd-service-activation.md` |
| **Setup Script** | `scripts/ops/absurd/setup_absurd_db.sh` | `backend/docs/ops/absurd-service-activation.md` |

### 3. Quality Assurance (QA)

**Code Location:** `backend/src/dsa110_contimg/qa/` **Status:** :yellow_circle: **In
Development**

| Component              | Code File               | Documentation                                  |
| :--------------------- | :---------------------- | :--------------------------------------------- |
| **Catalog Validation** | `catalog_validation.py` | [API Reference](API_REFERENCE.md)              |
| **Visualization**      | `visualization/`        | [Visualization Guide](guides/visualization.md) |

### 4. Imaging & Calibration

**Code Location:** `backend/src/dsa110_contimg/imaging/` &
`backend/src/dsa110_contimg/calibration/` **Status:** :green_circle: **Production**

| Component           | Code File                | Documentation                              |
| :------------------ | :----------------------- | :----------------------------------------- |
| **WSClean Wrapper** | `imaging/cli_imaging.py` | [Troubleshooting](TROUBLESHOOTING.md)      |
| **Imaging CLI**     | `imaging/cli.py`         | [Imaging Guide](guides/imaging.md)         |
| **Calibration**     | `calibration/cli.py`     | [Calibration Guide](guides/calibration.md) |

### 5. Frontend Dashboard

**Code Location:** `frontend/src/` **Status:** :green_circle: **Production**

| Component           | Code File                  | Documentation                          |
| :------------------ | :------------------------- | :------------------------------------- |
| **Main App**        | `App.tsx`                  | [Dashboard Guide](guides/dashboard.md) |
| **Operations Page** | `pages/OperationsPage.tsx` | [Dashboard Guide](guides/dashboard.md) |
| **API Client**      | `api/client.ts`            | [API Reference](API_REFERENCE.md)      |

---

## :warning: Note

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).
For operational guides, see the [Guides](guides/index.md) section.
