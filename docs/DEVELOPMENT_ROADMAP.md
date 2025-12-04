# Development Roadmap & Status

**Last Updated:** November 21, 2025

This document tracks the high-level progress of the DSA-110 Continuum Imaging
Pipeline.

---

## :calendar: 2025 Timeline

### :check: Completed Milestones

#### **November 2025: Browser Testing & Reliability**

- **Status:** :check: Complete
- **Focus:** End-to-End Browser Testing, Health Checks, Timeout Handling.
- **Key Deliverables:**
  - Playwright Test Suite (`scripts/tests/test_operations_page_playwright.js`)
  - Pipeline Health Checks (`backend/src/dsa110_contimg/pipeline/health.py`)
  - Details: Phase 1 Browser Testing Complete

#### **January 2025: Advanced Monitoring & Dashboard**

- **Status:** :check: Complete
- **Focus:** Event Bus, Cache Statistics, Pipeline Stage Monitoring.
- **Key Deliverables:**
  - Event Bus Monitor (`/api/events`)
  - Cache Statistics (`/api/cache`)
  - Pipeline Stage Dashboard
  - Details: Phase 3 Implementation Complete
  - Details: Phase 2 Implementation Summary

---

## :construction_sign: Active Development (Q4 2025)

### **1. "Absurd" Workflow Integration**

- **Goal:** Fully migrate all cron-based tasks to the Absurd workflow manager.
- **Status:** In Progress (Integration Phase)
- **Docs:** Absurd Documentation Index

### **2. Catalog-Based Validation**

- **Goal:** Automated validation of astrometry and flux scale against
  NVSS/VLASS.
- **Status:** Implementation Started
  (`backend/src/dsa110_contimg/qa/catalog_validation.py`)
- **Docs:**
  High Priority Improvements

---

## :crystal_ball: Future Roadmap

1.  **Full Production Deployment:** Move all components to
    `/data/dsa110-contimg/` (Done) and finalize `/stage/` directory structure.
2.  **Automated Self-Healing:** Expand the "Health Check" system to
    automatically recover from common failures. _(Note: WSClean Docker hangs
    have been fixed by removing NTFS-FUSE volume mounts.)_
