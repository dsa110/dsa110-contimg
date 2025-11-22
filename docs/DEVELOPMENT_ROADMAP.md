# Development Roadmap & Status

**Last Updated:** November 21, 2025

This document tracks the high-level progress of the DSA-110 Continuum Imaging
Pipeline.

---

## 📅 2025 Timeline

### ✅ Completed Milestones

#### **November 2025: Browser Testing & Reliability**

- **Status:** ✅ Complete
- **Focus:** End-to-End Browser Testing, Health Checks, Timeout Handling.
- **Key Deliverables:**
  - Playwright Test Suite (`scripts/tests/test_operations_page_playwright.js`)
  - Pipeline Health Checks (`src/dsa110_contimg/pipeline/health.py`)
  - [Details: Phase 1 Browser Testing Complete](logs/phase1_browser_testing_complete.md)

#### **January 2025: Advanced Monitoring & Dashboard**

- **Status:** ✅ Complete
- **Focus:** Event Bus, Cache Statistics, Pipeline Stage Monitoring.
- **Key Deliverables:**
  - Event Bus Monitor (`/api/events`)
  - Cache Statistics (`/api/cache`)
  - Pipeline Stage Dashboard
  - [Details: Phase 3 Implementation Complete](logs/phase3_complete.md)
  - [Details: Phase 2 Implementation Summary](logs/phase2_implementation_summary.md)

---

## 🚧 Active Development (Q4 2025)

### **1. "Absurd" Workflow Integration**

- **Goal:** Fully migrate all cron-based tasks to the Absurd workflow manager.
- **Status:** In Progress (Integration Phase)
- **Docs:** [Absurd Documentation Index](concepts/absurd_documentation_index.md)

### **2. Catalog-Based Validation**

- **Goal:** Automated validation of astrometry and flux scale against
  NVSS/VLASS.
- **Status:** Implementation Started
  (`src/dsa110_contimg/qa/catalog_validation.py`)
- **Docs:**
  [High Priority Improvements](implementation/high_priority_improvements.md)

---

## 🔮 Future Roadmap

1.  **Full Production Deployment:** Move all components to
    `/data/dsa110-contimg/` (Done) and finalize `/stage/` directory structure.
2.  **Automated Self-Healing:** Expand the "Health Check" system to
    automatically recover from common failures (e.g., WSClean hangs).
