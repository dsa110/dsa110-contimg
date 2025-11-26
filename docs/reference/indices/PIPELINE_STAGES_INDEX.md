# Pipeline Stages Documentation Index

Complete documentation guide for each stage of the DSA-110 imaging pipeline.

**Quick Links:** [Streaming](#streaming) | [Calibration](#calibration) |
[Flagging](#flagging) | [Imaging](#imaging) | [Masking](#masking) |
[Mosaicing](#mosaicing) | [QA](#qa) | [Cross-Matching](#cross-matching) |
[Photometry](#photometry) | [ESE Detection](#ese-detection)

---

## Streaming

**Purpose:** Receive and convert raw UVH5 data to Measurement Sets

**Documents:** 13 | **Recent Updates:** 2025-11-13

| Learn                                                                 | Do                                               | Reference                                                 | Troubleshoot                                              |
| --------------------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------- | --------------------------------------------------------- |
| [Architecture](../../architecture/pipeline/streaming-architecture.md)                 | [Quick Start](../how-to/streaming.md)            | [Streaming API](../streaming-api.md)            | [Troubleshooting](../../guides/workflow/streaming-troubleshooting.md) |
| [Streaming vs Orchestrator](../../architecture/pipeline/streaming_vs_orchestrator.md) | [Control Guide](../../guides/workflow/streaming-control.md)  | [Converter Guide](../../guides/workflow/streaming_converter_guide.md) |                                                           |
| [Workflow](../../architecture/pipeline/STREAMING_MOSAIC_WORKFLOW.md)                  | [UVH5 to MS](../../guides/data-processing/uvh5_to_ms_conversion.md) | [CLI Reference](../cli.md)                      |                                                           |

**Test Coverage:** [Results](../../testing/reports/STREAMING_TESTS_COMPLETION.md)

---

## Calibration

**Purpose:** Determine and apply calibration solutions

**Documents:** 12 | **Recent Updates:** 2025-11-13

| Learn                                                         | Do                                                                 | Reference                                                        | Find Data                                                            |
| ------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------- | -------------------------------------------------------------------- |
| [Theory](../../architecture/pipeline/pipeline_overview.md#calibration)        | [Detailed Procedure](../../guides/data-processing/CALIBRATION_DETAILED_PROCEDURE.md)  | [Reference Antenna](../../operations/refant_quick_reference.md)     | [Calibrator Transit Data](../../guides/data-processing/FIND_CALIBRATOR_TRANSIT_DATA.md) |
| [Improvements](../../changelog/CALIBRATION_IMPROVEMENTS_2024.md) | [Current Procedure](../CURRENT_CALIBRATION_PROCEDURE.md) | [Calibrator Helper](../tutorials/notebooks/calibrator_helper.py) | [ESE Field Mapping](../../archive/analysis/FIELD_MAPPING_COMPLETE.md)   |
|                                                               | [Tutorial](../../guides/tutorials/calibrate-apply.md)                        |                                                                  |                                                                      |

**Test Coverage:** [Validation](../validation_api.md)

---

## Flagging

**Purpose:** Remove RFI and flagged data

**Documents:** 2 | **Recent Updates:** 2025-11-12

| Learn                                 | Do                                                        | Reference                                                      |
| ------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| [AOFlagger](../../architecture/science/aoflagger.md) | [Test Flag Subcommand](../../guides/development/TEST_FLAG_SUBCOMMAND.md) | [Pipeline Overview](../../architecture/pipeline/pipeline_overview.md#flagging) |

**Note:** Flagging is an optional stage; most observations use default AOFlagger
settings.

---

## Imaging

**Purpose:** Generate images from calibrated Measurement Sets

**Documents:** 22 | **Recent Updates:** 2025-11-13

| Learn                                                                | Do                                                             | Reference                                                              | Troubleshoot                                               |
| -------------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Pipeline Overview](../../architecture/pipeline/pipeline_overview.md#imaging)        | [CASA6 Guide](../CASA6_ENVIRONMENT_GUIDE.md)                   | [CASA Log Daemon](../operations/CASA_LOG_DAEMON_PROTECTION_SUMMARY.md) | [Log Daemon Fixes](../operations/CASA_LOG_DAEMON_FIXES.md) |
| [Stage Architecture](../../architecture/pipeline/pipeline_stage_architecture.md)     | [WSClean Usage](../../archive/analysis/WSCLEAN_USAGE_ANALYSIS.md) | [Log Monitoring](../operations/CASA_LOG_DAEMON_MONITORING.md)          |                                                            |
| [Image Filters](../image_filters_implementation_status.md) | [Image Testing](../image_filters_test_results.md)    | [Image Expectations](../../guides/data-processing/SKYMODEL_IMAGE_EXPECTATIONS.md)         |                                                            |

**Coverage:** [Test Execution](../../archive/status_reports/PHASE1_TESTING_RESULTS.md)

---

## Masking

**Purpose:** Generate and apply image masks

**Documents:** 5 | **Recent Updates:** 2025-11-13

| Learn                                                                           | Do                                                                                 | Reference                                                                 |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [Masking Guide](../../guides/data-processing/masking-guide.md)                                     | [Toggle Implementation](../../archive/analysis/MASKING_TOGGLE_IMPLEMENTATION_PLAN.md) | [Efficiency Analysis](../../archive/analysis/MASKING_EFFICIENCY_ANALYSIS.md) |
| [Implementation Status](../../archive/analysis/MASKING_IMPLEMENTATION_COMPLETE.md) |                                                                                    | [Masked Imaging](../../archive/analysis/MASKED_IMAGING_ANALYSIS.md)          |

---

## Mosaicing

**Purpose:** Combine multiple observations into unified mosaics

**Documents:** 17 | **Recent Updates:** 2025-11-12

| Learn                                                            | Do                                                         | Reference                                                          | Troubleshoot                                                                 |
| ---------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| [Mosaic Guide](../../guides/workflow/mosaic.md)                              | [Quick Start](../../guides/workflow/mosaic_quickstart.md)              | [LinearMosaic Parameters](../LINEARMOSAIC_PARAMETERS.md) | [Regridding Issues](../../archive/analysis/CRITICAL_MOSAIC_REGRIDDING_ISSUE.md) |
| [Workflow](../../architecture/pipeline/STREAMING_MOSAIC_WORKFLOW.md)             | [Build 60min Mosaic](../../guides/data-processing/BUILD_60MIN_MOSAIC_0834.md) | [Linear Setup](../../guides/data-processing/LINEAR_SETUP_QUICKSTART.md)               | [Status Explanation](../../archive/analysis/MOSAIC_STATUS_EXPLANATION.md)       |
| [DP3 Analysis](../../archive/analysis/dp3_multi_field_solutions.md) | [Linear Integration](../../guides/data-processing/LINEAR_INTEGRATION.md)      | [Batch Creation](../../guides/workflow/batch_mosaic_creation.md)               |                                                                              |

**Coverage:** [Build Tests](../../archive/analysis/MOSAIC_BUILD_TEST_RESULTS.md)

---

## QA (Quality Assurance)

**Purpose:** Verify data quality and generate reports

**Documents:** 25 | **Recent Updates:** 2025-11-13

| Learn                                                   | Do                                                     | Reference                                       | Dashboard                                                                                      |
| ------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [QA Framework Design](../QA_VISUALIZATION_DESIGN.md)    | [Quick Start](../QA_VISUALIZATION_QUICK_START.md)      | [Usage Guide](../QA_VISUALIZATION_USAGE.md)     | [Dashboard Integration](../../archive/qa_visualization/QA_VISUALIZATION_DASHBOARD_INTEGRATION.md) |
| [Image Quality](../../guides/dashboard/js9_casa_analysis.md)         | [CASA Analysis](../reference/js9_casa_analysis_api.md) | [User Guide](../../archive/user_guide_qa_visualization.md) | [Dashboard Testing](../../archive/qa_visualization/QA_VISUALIZATION_DASHBOARD_TESTING.md)         |
| [Quality Control](../../guides/automation/QUALITY_ASSURANCE_SETUP.md) |                                                        |                                                 | [Dashboard Summary](../../archive/qa_visualization/QA_VISUALIZATION_DASHBOARD_SUMMARY.md)         |

**Coverage:** [Code Quality](../../archive/reports/CODE_QUALITY_FINAL_SUMMARY.md)

---

## Cross-Matching

**Purpose:** Identify sources and match with catalogs

**Documents:** 29 | **Recent Updates:** 2025-11-13

| Learn                                                        | Do                                                                             | Reference                                                                    | Catalog Tools                                                    |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [Cross-Matching Guide](../../guides/data-processing/cross-matching-guide.md)    | [Testing Synthetic](../../guides/development/testing_crossmatch_stage_with_synthetic_data.md) | [Catalog Documentation](../CATALOG_DOCUMENTATION_INDEX.md)         | [VAST Comparison](../../archive/RADIOPADRE_VS_VAST_TOOLS_COMPARISON.md)     |
| [Catalog Index](../CATALOG_DOCUMENTATION_INDEX.md) | [RAX Catalogs](../../guides/data-processing/build-first-rax-catalogs.md)                          | [Catalog Usage](../CATALOG_USAGE_GUIDE.md)                         | [NVSS Coverage](../FIRST_DECLINATION_COVERAGE.md)      |
| [External Tools](../../archive/EXTERNAL_TOOLS_EVALUATION.md)            | [VP from H5](../../guides/data-processing/build-vp-from-h5.md)                                    | [VAST Integration](../VAST_PIPELINE_CROSS_MATCHING_INTEGRATION.md) | [Radio Surveys](../RADIO_SURVEY_CATALOG_COMPARISON.md) |

**Coverage:** [Query Optimization](../../archive/progress-logs/nvss_query_optimization.md)

---

## Photometry

**Purpose:** Extract flux measurements and forced photometry

**Documents:** 8 | **Recent Updates:** 2025-11-13

| Learn                                                                   | Do                                                                           | Reference                                                                           |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [Photometry Manager](../../architecture/science/photometry_manager.md)                 | [Automation Assessment](../dev/analysis/photometry_automation_assessment.md) | [Forced Photometry](../dev/analysis/photometry_automation_implementation_review.md) |
| [Normalization Theory](../../architecture/science/photometry_normalization.md) | [Automation Roadmap](../dev/analysis/photometry_automation_roadmap.md)       | [Enhancements](../../archive/analysis/FORCED_PHOTOMETRY_ENHANCEMENTS.md)               |
|                                                                         | [Test Results](../../archive/analysis/FORCED_PHOTOMETRY_TESTS.md)               | [VAST Analysis](../../archive/analysis/VAST_FORCED_PHOTOMETRY_ANALYSIS.md)             |

---

## ESE Detection

**Purpose:** Automated error detection and correction

**Documents:** 26 | **Recent Updates:** 2025-11-13

| Learn                                                                     | Do                                                                  | Reference                                                                        | Advanced                                                               |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [ESE Guide](../../guides/data-processing/ese_detection_guide.md)                             | [Advanced Features](../../guides/data-processing/ese_detection_advanced_features.md)   | [Architecture](../../architecture/science/ese_detection_architecture.md)                        | [Implementation Phases](../../archive/progress-logs/ese_detection_implementation_phases.md) |
| [Auto-Error Detection](../../guides/error-handling/auto-error-detection-non-interactive.md) | [Enable Auto-Detection](../../guides/error-handling/enable-auto-error-detection.md)   | [Automated Pipeline](../../archive/progress-logs/ese_automated_pipeline_summary.md)                   | [Research Findings](../../archive/progress-logs/ese_detection_research_findings.md)         |
| [Error Handling](../../guides/error-handling/error-handling-implementation-summary.md)      | [System-Wide Setup](../../guides/error-handling/system-wide-error-detection-setup.md) | [Comprehensive Improvements](../../archive/progress-logs/ese_detection_comprehensive_improvements.md) |                                                                        |

**Coverage:**
[Complete Documentation](../../archive/progress-logs/ese_detection_complete_documentation_summary.md)

---

## Pipeline Overview Diagram

```
Raw Data          Processing                         Products
   │                  │                                 │
   ├─→ [Streaming]   → Measurement Sets
                       │
                       ├─→ [Calibration]     → Cal Solutions
                            │
                            ├─→ [Flagging]        → Flagged MS
                                 │
                                 ├─→ [Imaging]         → FITS Images
                                      │
                                      ├─→ [Masking]     → Masked Images
                                           │
                                           ├─→ [Mosaicing] → Mosaic
                                                │
                                                ├─→ [QA]           → QA Reports
                                                     │
                                                     ├─→ [Cross-Matching] → Source Catalog
                                                          │
                                                          ├─→ [Photometry] → Flux Measurements
                                                               │
                                                               └─→ [ESE Detection] → Error Reports
```

---

## Quick Reference

| Stage          | Input             | Output           | Duration    | Typical Users |
| -------------- | ----------------- | ---------------- | ----------- | ------------- |
| Streaming      | UVH5 files        | Measurement Sets | ~seconds    | Operators     |
| Calibration    | Raw MS            | Cal solutions    | ~minutes    | Operators     |
| Flagging       | Raw MS            | Flagged MS       | ~seconds    | Automatic     |
| Imaging        | Calibrated MS     | FITS images      | ~minutes    | System        |
| Masking        | FITS images       | Masked images    | ~seconds    | System        |
| Mosaicing      | Multiple images   | Mosaic image     | ~minutes    | Operators     |
| QA             | Pipeline outputs  | QA reports       | ~minutes    | Scientists    |
| Cross-Matching | Detection lists   | Source catalog   | ~seconds    | System        |
| Photometry     | Images & catalogs | Flux table       | ~minutes    | System        |
| ESE Detection  | All products      | Error reports    | ~continuous | Automatic     |

---

## Navigation

- [Back to Main Index](../START_HERE_DOCUMENT_INVENTORY.md)
- [Dashboard Components Index](./DASHBOARD_COMPONENTS_INDEX.md)
- [General Themes Index](./GENERAL_THEMES_INDEX.md)
- [Documentation Framework](../documentation_standards/DOCUMENTATION_ORGANIZATIONAL_FRAMEWORK.md)

---

**Last Updated:** 2025-11-15  
**Total Documents:** 132  
**Status:** Complete
