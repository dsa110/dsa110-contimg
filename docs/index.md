# DSA-110 Continuum Imaging Pipeline Documentation

Welcome to the documentation for the DSA-110 Continuum Imaging Pipeline.

## 🚀 Quick Start

**New here?** Start with the **[Quick Start Guide](QUICKSTART.md)** - get the pipeline running in 5 minutes.

| I want to...              | Go to...                                                   |
| ------------------------- | ---------------------------------------------------------- |
| Get running fast          | **[Quick Start](QUICKSTART.md)**                           |
| Understand the system     | [Architecture](ARCHITECTURE.md)                            |
| See how data flows        | [Ingestion Guide](guides/ingestion.md)                     |
| Understand storage        | [Storage & Files](guides/storage-and-file-organization.md) |
| Use the dashboard         | [Dashboard Guide](guides/dashboard.md)                     |
| Develop features          | [Developer Guide](DEVELOPER_GUIDE.md)                      |
| Use the API               | [API Reference](API_REFERENCE.md)                          |
| Operate the pipeline      | [Operations Runbook](operations/RUNBOOK.md)                |
| Fix problems              | [Troubleshooting](TROUBLESHOOTING.md)                      |

---

## 📚 Core Documentation

| Document                                  | Description                                    |
| ----------------------------------------- | ---------------------------------------------- |
| **[Quick Start](QUICKSTART.md)**          | Get running in 5 minutes                       |
| **[Developer Guide](DEVELOPER_GUIDE.md)** | Development environment, testing, contributing |
| **[Architecture](ARCHITECTURE.md)**       | System design, data flow, components           |
| **[API Reference](API_REFERENCE.md)**     | REST API, CLI, Python API documentation        |
| **[Troubleshooting](TROUBLESHOOTING.md)** | Problem diagnosis & resolution                 |

---

## 🔧 Workflow Guides

### Data Processing

| Guide                                                          | Description                               |
| -------------------------------------------------------------- | ----------------------------------------- |
| **[Ingestion](guides/ingestion.md)**                           | UVH5 subband discovery & MS conversion    |
| **[Calibration](guides/calibration.md)**                       | Bandpass and gain calibration             |
| **[Imaging](guides/imaging.md)**                               | Creating FITS images from MS              |
| **[Mosaicking](guides/mosaicking.md)**                         | Combining images into mosaics             |
| **[Visualization](guides/visualization.md)**                   | Plotting, diagnostics, and CARTA          |

### Catalogs & Data

| Guide                                                          | Description                               |
| -------------------------------------------------------------- | ----------------------------------------- |
| **[Catalog Overview](guides/catalog-overview.md)**             | Survey catalogs (NVSS, FIRST, VLASS)      |
| **[ATNF Catalog](guides/atnf-catalog.md)**                     | Pulsar catalog integration                |
| **[Storage & Files](guides/storage-and-file-organization.md)** | File organization, naming, database paths |

### Dashboard & Tools

| Guide                                                          | Description                               |
| -------------------------------------------------------------- | ----------------------------------------- |
| **[Dashboard](guides/dashboard.md)**                           | Web interface navigation                  |
| **[Validation Tools](guides/validation-tools.md)**             | Data quality and validation utilities     |

### Tutorials

| Guide                                                                                     | Description                                    |
| ----------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **[Finding Calibrator Transit](guides/Finding_and_Imaging_Peak_Transit_of_0834_555.md)** | Step-by-step: finding and imaging a calibrator |

---

## 🛠️ Operations

| Document                                             | Description                        |
| ---------------------------------------------------- | ---------------------------------- |
| **[Operations Runbook](operations/RUNBOOK.md)**      | Service management & alert response |
| **[Systemd Services](operations/systemd-services.md)** | Service configuration & management |
| **[CARTA Service](operations/carta-service.md)**     | CARTA visualization server setup   |
| **[Error Detection](operations/error-detection.md)** | Monitoring and alerting            |

---

## 📐 Design Documents

Technical designs and architecture decisions:

| Document                                                           | Description                          |
| ------------------------------------------------------------------ | ------------------------------------ |
| **[Complexity Reduction](design/COMPLEXITY_REDUCTION.md)**         | Major refactoring guide (active)     |
| **[Complexity Notes](design/COMPLEXITY_REDUCTION_NOTES.md)**       | Implementation notes for refactoring |
| **[Production Readiness](design/PRODUCTION_READINESS_ROADMAP.md)** | Production deployment checklist      |
| **[Pipeline Analysis](design/PIPELINE_ANALYSIS.md)**               | Pipeline architecture analysis       |
| **[GPU Implementation](design/GPU_implementation_plan.md)**        | GPU acceleration plans               |
| **[Execution Unification](design/EXECUTION_UNIFICATION_PLAN.md)**  | Task execution consolidation         |

---

## 📖 Additional Resources

| Document                                | Description                     |
| --------------------------------------- | ------------------------------- |
| **[System Context](SYSTEM_CONTEXT.md)** | Technical architecture overview |
| **[Code Map](CODE_MAP.md)**             | Navigate the codebase           |
| **[Roadmap](DEVELOPMENT_ROADMAP.md)**   | Current project status          |

---

## 📋 Changelog

Recent updates to the pipeline:

| Date       | Change                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------ |
| 2025-12-03 | [Visualization & Nightly Mosaics](changelog/2025-12-03-visualization-and-nightly-mosaics.md)     |
| 2025-12-01 | [ABSURD Deployment](changelog/2025-12-01-absurd-deployment.md)                                   |
| 2025-11-27 | [Frontend Routing](changelog/2025-11-27-frontend-routing.md)                                     |

---

## 👩‍💻 Developer Resources

| Document                                                     | Description                      |
| ------------------------------------------------------------ | -------------------------------- |
| **[Frontend Contributing](guides/frontend-contributing.md)** | React/Vite frontend development  |
| **[Scripts Guide](guides/scripts-developer-guide.md)**       | Pipeline scripts documentation   |
| **[Code Review Checklist](guides/code-review-checklist.md)** | PR review guidelines             |
| **[Commit Message Format](guides/commit-message-format.md)** | Git commit conventions           |
| **[Branch Protection](guides/branch-protection.md)**         | Branch policies                  |
| **[CASA Import Pattern](guides/casa-import-pattern.md)**     | CASA tools import best practices |
| **[Query Batching](guides/query-batching.md)**               | Database query optimization      |
| **[Ops Helpers](guides/ops-helpers.md)**                     | Operational helper utilities     |

---

## 📦 Archive

Historical and superseded documentation is preserved in `archive/`:

- `archive/consolidated/` - Previous detailed guides (now merged into core docs)
- `archive/2025-01/` - Historical status reports
- Browse for reference when deeper detail is needed
