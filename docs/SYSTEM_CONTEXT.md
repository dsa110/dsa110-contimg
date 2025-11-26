# System Context & Architecture Framework

**Purpose:** This document provides a deep-dive technical overview of the
DSA-110 Continuum Imaging Pipeline. It serves as a "mental model" for developers
and AI agents to understand the system's implementation details without reading
every source file.

**Last Updated:** November 25, 2025

---

## 1. System Overview

The pipeline is a **hybrid streaming/batch system** designed to process radio
astronomy data from the DSA-110 telescope.

- **Input:** Raw visibility data (UVH5 format) in `/data/incoming/`.
- **Processing:** A stage-based Python pipeline (`dsa110_contimg`).
- **Orchestration:** "Absurd" (a custom asyncio/SQLite-based workflow manager).
- **Output:** Calibrated Measurement Sets (MS) and Images (FITS) in
  `/stage/dsa110-contimg/`.
- **Interface:** A React/Vite dashboard for monitoring and control.

---

## 2. Data Model (SQLite)

The system relies on direct SQLite interactions (no ORM) for performance and
simplicity. It uses multiple separated databases to manage state.

### **Products Database** (`state/products.sqlite3`)

- **Managed by:** `backend/src/dsa110_contimg/database/products.py`
- **Key Tables:**
  - `ms_index`: Tracks the lifecycle of a Measurement Set.
    - `path` (PK): Absolute path to the MS.
    - `status`: Current processing state (e.g., 'calibrated', 'imaged').
    - `stage`: The specific pipeline stage currently running.
  - `images`: Registry of generated image products.
    - `path`: Path to the FITS file.
    - `type`: 'continuum', 'dirty', 'residual', etc.
    - `noise_jy`: Quality metric.
  - `calibrator_transits`: Pre-calculated transit times for calibrators.
  - `transient_candidates`: Detected transient sources.
  - `jobs` & `batch_jobs`: Execution history.

### **Other Active Databases**

- **`ingest.sqlite3`**: Queue management for incoming data.
  - `ingest_queue`: Tracks file groups (16 subbands) and their state.
  - `performance_metrics`: Tracks writer performance.
- **`cal_registry.sqlite3`**: Calibration tables and validity windows.
  - `caltables`: Path, validity window, quality metrics.
- **`hdf5.sqlite3`**: Index of raw HDF5 files.
  - `hdf5_file_index`: Maps subbands to files.
- **`master_sources.sqlite3`**: Large catalog of sources (1.6M+).
- **`calibrator_registry.sqlite3`**: Registry of known calibrators (created on
  demand).

### **Concurrency Strategy**

- **WAL Mode:** Write-Ahead Logging is enabled (`PRAGMA journal_mode=WAL`) to
  allow non-blocking reads.
- **Timeouts:** Explicit 30s busy timeouts to handle lock contention.

---

## 3. Control Flow & Pipeline Logic

### **The Stage Pattern**

- **Base Class:** `PipelineStage` (in
  `backend/src/dsa110_contimg/pipeline/stages.py`).
- **Implementation:** Concrete stages (e.g., `CatalogSetupStage`) are in
  `backend/src/dsa110_contimg/pipeline/stages_impl.py`.
- **Context:** Data is passed between stages via a `PipelineContext` object
  (immutable Pydantic model).

### **The "Absurd" Workflow Engine**

- **Type:** Custom Asyncio Task Queue.
- **Worker:** `backend/src/dsa110_contimg/absurd/worker.py`.
- **Real-Time:** Uses WebSockets to broadcast `task_update` events to the
  frontend.
- **Persistence:** Tasks are persisted to SQLite to survive restarts.

### **Science Logic (Deep Dive)**

- **Self-Calibration (`calibration/selfcal.py`):**
  - Implements an iterative loop: `Initial Imaging` -> `Phase-only Self-cal` ->
    `Amplitude+Phase Self-cal`.
  - Uses `casatasks` (gaincal, applycal) if available.
  - Key heuristic: Solint (solution interval) decreases as the model improves.
- **Imaging Wrapper (`imaging/cli_imaging.py`):**
  - Wraps `wsclean` via `subprocess`.
  - Enforces a fixed image extent of **3.5° x 3.5°** (`FIXED_IMAGE_EXTENT_DEG`).
  - Includes performance tracking decorators (`@track_performance`).

### **Component Deep Dives**

- **Transit Precalculation:**
  - **Source:** `backend/src/dsa110_contimg/conversion/transit_precalc.py`
  - **Mechanism:** Calculates transit times for registered calibrators using
    `astropy`.
  - **Storage:** `calibrator_transits` table in `products.sqlite3`.
- **Parallel-Subband Writer:**
  - **Source:**
    `backend/src/dsa110_contimg/conversion/strategies/direct_subband.py`
  - **Implementation:** `DirectSubbandWriter` (aliased as `parallel-subband`).
  - **Usage:** Production default. Writes 16 subbands directly to MS.
- **CARTA Integration:**
  - **Deployment:** Docker container `carta-backend` on port 9002.
  - **Mounts:** Read-only access to `/stage` and `/data`.
  - **URL:** `http://localhost:9002` (proxied via Dashboard).

---

## 4. Frontend Architecture

- **Stack:** React 18 + TypeScript + Vite.
- **Location:** `/data/dsa110-contimg/frontend/`.
- **State Management:** React Query (implied by "Cache Statistics" features).
- **Testing:** Playwright for E2E testing
  (`scripts/tests/test_operations_page_playwright.js`).
- **Build:** Optimized for "scratch" environments (`npm run build:scratch`).

### **Frontend Component Structure**

- **Pages:** Located in `frontend/src/pages/`. Key pages include:
  - `OperationsPage.tsx`: Main control center.
  - `SkyViewPage.tsx`: Image visualization.
  - `AbsurdPage.tsx`: Workflow manager status.
- **API Layer:** `frontend/src/api/` contains typed clients (e.g., `absurd.ts`,
  `websocket.ts`).
- **Visualization:** Uses **JS9** for FITS viewing (`contexts/JS9Context.tsx`)
  and **CARTA** integration (`components/CARTA/`).

---

## 5. Developer Cheat Sheet

| Task                   | File/Directory to Check                                                     |
| :--------------------- | :-------------------------------------------------------------------------- |
| **Modify DB Schema**   | `backend/src/dsa110_contimg/database/products.py` (Look for `CREATE TABLE`) |
| **Add Pipeline Stage** | `backend/src/dsa110_contimg/pipeline/stages_impl.py`                        |
| **Debug WSClean**      | `backend/src/dsa110_contimg/imaging/cli_imaging.py`                         |
| **Check Health Logic** | `backend/src/dsa110_contimg/pipeline/health.py`                             |
| **Frontend Routes**    | `frontend/src/App.tsx` (implied)                                            |
| **Run Tests**          | `ops/scripts/tests/`                                                        |

---

## 6. Critical Constraints

1.  **File System:** The `/stage/` directory is fast SSD (scratch), while
    `/data/` is persistent storage. Code must respect this separation.
2.  **No ORM:** Do not introduce SQLAlchemy or Django ORM. Use raw SQL with the
    provided helper functions.
3.  **Asyncio:** The core orchestration is async; avoid blocking calls in the
    `Absurd` worker loop.
