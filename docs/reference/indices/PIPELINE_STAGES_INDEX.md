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
| [Architecture](../concepts/streaming-architecture.md)                 | [Quick Start](../how-to/streaming.md)            | [Streaming API](../reference/streaming-api.md)            | [Troubleshooting](../how-to/streaming-troubleshooting.md) |
| [Streaming vs Orchestrator](../concepts/streaming_vs_orchestrator.md) | [Control Guide](../how-to/streaming-control.md)  | [Converter Guide](../how-to/streaming_converter_guide.md) |                                                           |
| [Workflow](../concepts/STREAMING_MOSAIC_WORKFLOW.md)                  | [UVH5 to MS](../how-to/uvh5_to_ms_conversion.md) | [CLI Reference](../reference/cli.md)                      |                                                           |

**Test Coverage:** [Results](../testing/STREAMING_TESTS_COMPLETION.md)

---

## Calibration

**Purpose:** Determine and apply calibration solutions

**Documents:** 12 | **Recent Updates:** 2025-11-13

| Learn                                                         | Do                                                                 | Reference                                                        | Find Data                                                            |
| ------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------- | -------------------------------------------------------------------- |
| [Theory](../concepts/pipeline_overview.md#calibration)        | [Detailed Procedure](../how-to/CALIBRATION_DETAILED_PROCEDURE.md)  | [Reference Antenna](../operations/refant_quick_reference.md)     | [Calibrator Transit Data](../how-to/FIND_CALIBRATOR_TRANSIT_DATA.md) |
| [Improvements](../changelog/CALIBRATION_IMPROVEMENTS_2024.md) | [Current Procedure](../reference/CURRENT_CALIBRATION_PROCEDURE.md) | [Calibrator Helper](../tutorials/notebooks/calibrator_helper.py) | [ESE Field Mapping](../archive/analysis/FIELD_MAPPING_COMPLETE.md)   |
|                                                               | [Tutorial](../tutorials/calibrate-apply.md)                        |                                                                  |                                                                      |

**Test Coverage:** [Validation](../reference/validation_api.md)

---

## Flagging

**Purpose:** Remove RFI and flagged data

**Documents:** 2 | **Recent Updates:** 2025-11-12

| Learn                                 | Do                                                        | Reference                                                      |
| ------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| [AOFlagger](../concepts/aoflagger.md) | [Test Flag Subcommand](../how-to/TEST_FLAG_SUBCOMMAND.md) | [Pipeline Overview](../concepts/pipeline_overview.md#flagging) |

**Note:** Flagging is an optional stage; most observations use default AOFlagger
settings.

---

## Imaging

**Purpose:** Generate images from calibrated Measurement Sets

**Documents:** 22 | **Recent Updates:** 2025-11-13

| Learn                                                                | Do                                                             | Reference                                                              | Troubleshoot                                               |
| -------------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Pipeline Overview](../concepts/pipeline_overview.md#imaging)        | [CASA6 Guide](../CASA6_ENVIRONMENT_GUIDE.md)                   | [CASA Log Daemon](../operations/CASA_LOG_DAEMON_PROTECTION_SUMMARY.md) | [Log Daemon Fixes](../operations/CASA_LOG_DAEMON_FIXES.md) |
| [Stage Architecture](../concepts/pipeline_stage_architecture.md)     | [WSClean Usage](../archive/analysis/WSCLEAN_USAGE_ANALYSIS.md) | [Log Monitoring](../operations/CASA_LOG_DAEMON_MONITORING.md)          |                                                            |
| [Image Filters](../reference/image_filters_implementation_status.md) | [Image Testing](../reference/image_filters_test_results.md)    | [Image Expectations](../how-to/SKYMODEL_IMAGE_EXPECTATIONS.md)         |                                                            |

**Coverage:** [Test Execution](../testing/PHASE1_TESTING_RESULTS.md)

---

## Masking

**Purpose:** Generate and apply image masks

**Documents:** 5 | **Recent Updates:** 2025-11-13

| Learn                                                                           | Do                                                                                 | Reference                                                                 |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [Masking Guide](../how-to/masking-guide.md)                                     | [Toggle Implementation](../archive/analysis/MASKING_TOGGLE_IMPLEMENTATION_PLAN.md) | [Efficiency Analysis](../archive/analysis/MASKING_EFFICIENCY_ANALYSIS.md) |
| [Implementation Status](../archive/analysis/MASKING_IMPLEMENTATION_COMPLETE.md) |                                                                                    | [Masked Imaging](../archive/analysis/MASKED_IMAGING_ANALYSIS.md)          |

---

## Mosaicing

**Purpose:** Combine multiple observations into unified mosaics

**Documents:** 17 | **Recent Updates:** 2025-11-12

| Learn                                                            | Do                                                         | Reference                                                          | Troubleshoot                                                                 |
| ---------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| [Mosaic Guide](../how-to/mosaic.md)                              | [Quick Start](../how-to/mosaic_quickstart.md)              | [LinearMosaic Parameters](../reference/LINEARMOSAIC_PARAMETERS.md) | [Regridding Issues](../archive/analysis/CRITICAL_MOSAIC_REGRIDDING_ISSUE.md) |
| [Workflow](../concepts/STREAMING_MOSAIC_WORKFLOW.md)             | [Build 60min Mosaic](../how-to/BUILD_60MIN_MOSAIC_0834.md) | [Linear Setup](../how-to/LINEAR_SETUP_QUICKSTART.md)               | [Status Explanation](../archive/analysis/MOSAIC_STATUS_EXPLANATION.md)       |
| [DP3 Analysis](../archive/analysis/dp3_multi_field_solutions.md) | [Linear Integration](../how-to/LINEAR_INTEGRATION.md)      | [Batch Creation](../how-to/batch_mosaic_creation.md)               |                                                                              |

**Coverage:** [Build Tests](../archive/analysis/MOSAIC_BUILD_TEST_RESULTS.md)

---

## QA (Quality Assurance)

**Purpose:** Verify data quality and generate reports

**Documents:** 25 | **Recent Updates:** 2025-11-13

| Learn                                                   | Do                                                     | Reference                                       | Dashboard                                                                                      |
| ------------------------------------------------------- | ------------------------------------------------------ | ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [QA Framework Design](../QA_VISUALIZATION_DESIGN.md)    | [Quick Start](../QA_VISUALIZATION_QUICK_START.md)      | [Usage Guide](../QA_VISUALIZATION_USAGE.md)     | [Dashboard Integration](../archive/qa_visualization/QA_VISUALIZATION_DASHBOARD_INTEGRATION.md) |
| [Image Quality](../how-to/js9_casa_analysis.md)         | [CASA Analysis](../reference/js9_casa_analysis_api.md) | [User Guide](../user_guide_qa_visualization.md) | [Dashboard Testing](../archive/qa_visualization/QA_VISUALIZATION_DASHBOARD_TESTING.md)         |
| [Quality Control](../how-to/QUALITY_ASSURANCE_SETUP.md) |                                                        |                                                 | [Dashboard Summary](../archive/qa_visualization/QA_VISUALIZATION_DASHBOARD_SUMMARY.md)         |

**Coverage:** [Code Quality](../archive/reports/CODE_QUALITY_FINAL_SUMMARY.md)

---

## Cross-Matching

**Purpose:** Identify sources and match with catalogs

**Documents:** 29 | **Recent Updates:** 2025-11-13

| Learn                                                        | Do                                                                             | Reference                                                                    | Catalog Tools                                                    |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [Cross-Matching Guide](../how-to/cross-matching-guide.md)    | [Testing Synthetic](../how-to/testing_crossmatch_stage_with_synthetic_data.md) | [Catalog Documentation](../reference/CATALOG_DOCUMENTATION_INDEX.md)         | [VAST Comparison](../RADIOPADRE_VS_VAST_TOOLS_COMPARISON.md)     |
| [Catalog Index](../reference/CATALOG_DOCUMENTATION_INDEX.md) | [RAX Catalogs](../how-to/build-first-rax-catalogs.md)                          | [Catalog Usage](../reference/CATALOG_USAGE_GUIDE.md)                         | [NVSS Coverage](../reference/FIRST_DECLINATION_COVERAGE.md)      |
| [External Tools](../EXTERNAL_TOOLS_EVALUATION.md)            | [VP from H5](../how-to/build-vp-from-h5.md)                                    | [VAST Integration](../reference/VAST_PIPELINE_CROSS_MATCHING_INTEGRATION.md) | [Radio Surveys](../reference/RADIO_SURVEY_CATALOG_COMPARISON.md) |

**Coverage:** [Query Optimization](../dev/nvss_query_optimization.md)

---

## Photometry

**Purpose:** Extract flux measurements and forced photometry

**Documents:** 8 | **Recent Updates:** 2025-11-13

| Learn                                                                   | Do                                                                           | Reference                                                                           |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [Photometry Manager](../concepts/photometry_manager.md)                 | [Automation Assessment](../dev/analysis/photometry_automation_assessment.md) | [Forced Photometry](../dev/analysis/photometry_automation_implementation_review.md) |
| [Normalization Theory](../concepts/science/photometry_normalization.md) | [Automation Roadmap](../dev/analysis/photometry_automation_roadmap.md)       | [Enhancements](../archive/analysis/FORCED_PHOTOMETRY_ENHANCEMENTS.md)               |
|                                                                         | [Test Results](../archive/analysis/FORCED_PHOTOMETRY_TESTS.md)               | [VAST Analysis](../archive/analysis/VAST_FORCED_PHOTOMETRY_ANALYSIS.md)             |

---

## ESE Detection

**Purpose:** Automated error detection and correction

**Documents:** 26 | **Recent Updates:** 2025-11-13

| Learn                                                                     | Do                                                                  | Reference                                                                        | Advanced                                                               |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| [ESE Guide](../how-to/ese_detection_guide.md)                             | [Advanced Features](../how-to/ese_detection_advanced_features.md)   | [Architecture](../concepts/ese_detection_architecture.md)                        | [Implementation Phases](../dev/ese_detection_implementation_phases.md) |
| [Auto-Error Detection](../how-to/auto-error-detection-non-interactive.md) | [Enable Auto-Detection](../how-to/enable-auto-error-detection.md)   | [Automated Pipeline](../dev/ese_automated_pipeline_summary.md)                   | [Research Findings](../dev/ese_detection_research_findings.md)         |
| [Error Handling](../how-to/error-handling-implementation-summary.md)      | [System-Wide Setup](../how-to/system-wide-error-detection-setup.md) | [Comprehensive Improvements](../dev/ese_detection_comprehensive_improvements.md) |                                                                        |

**Coverage:**
[Complete Documentation](../dev/ese_detection_complete_documentation_summary.md)

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
- [Documentation Framework](../DOCUMENTATION_ORGANIZATIONAL_FRAMEWORK.md)

---

**Last Updated:** 2025-11-15  
**Total Documents:** 132  
**Status:** Complete
