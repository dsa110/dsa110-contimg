# General Themes Documentation Index

Cross-cutting concerns and topics that span pipeline and dashboard
documentation.

**Quick Links:** [Testing](#testing) | [Development](#development) |
[Documentation](#documentation) | [Troubleshooting](#troubleshooting) |
[Operations](#operations) | [Tools](#tools) | [Environment](#environment) |
[Deployment](#deployment) | [Performance](#performance) | [Security](#security)

---

## Testing

**Purpose:** Test strategies, validation approaches, and quality assurance

**Documents:** 104 | **Recent Updates:** 2025-11-13

### Test Planning & Strategy

| Framework                                                      | Strategy                                                     | Planning                                                   | Approach                                               |
| -------------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------ |
| [Comprehensive Plan](../../testing/plans/COMPREHENSIVE_TESTING_PLAN.md) | [Automated Testing](../../archive/AUTOMATED_TESTING_STRATEGY.md) | [Unit Test Summary](../../testing/reports/unit_test_suite_summary.md) | [Practical Approach](../../testing/plans/PRACTICAL_APPROACH.md) |
| [Quick Start](../../testing/guides/QUICK_START.md)                       | [Implementation](../testing/IMPLEMENTATION_SUMMARY.md)       | [Current Status](../../testing/CURRENT_STATUS.md)             | [Test Organization](../../testing/plans/TEST_ORGANIZATION.md)  |

### Test Execution

| Execution                                         | Results                                                 | Analysis                                                     | Docker                                             |
| ------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------------------- |
| [Execution Log](../../testing/reports/TEST_EXECUTION_LOG.md) | [Results Summary](../../archive/status_reports/TEST_EXECUTION_SUMMARY.md) | [Remaining Analysis](../../testing/reports/REMAINING_TESTS_ANALYSIS.md) | [Docker Guide](../../testing/guides/DOCKER_TESTING_GUIDE.md) |
|                                                   | [Final Report](../../archive/status_reports/FINAL_TEST_REPORT.md)         | [Verification](../../archive/status_reports/VERIFICATION_RESULTS.md)           |                                                    |

### Specialized Testing

| Phase 1                                                                | Phase 2                                         | Frontend                                                      | Streaming                                              |
| ---------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------ |
| [Results](../../archive/status_reports/PHASE1_TESTING_RESULTS.md)                        | [Results](../testing/PHASE2_TESTING_SUMMARY.md) | [Browser Testing](../../guides/development/playwright-python-quick-start.md) | [Completion](../../testing/reports/STREAMING_TESTS_COMPLETION.md) |
| [Multiple Sources](../../archive/status_reports/PHASE1_MULTIPLE_SOURCES_TEST_RESULTS.md) |                                                 | [Automation Guide](../../archive/progress-logs/browser_testing_guide.md)           |                                                        |

### Validation & Coverage

| Coverage Analysis                                          | Validation Strategy                                               | API Testing                                         | QA                                                        |
| ---------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------- |
| [Coverage Plan](../coverage_improvement_plan.md) | [Validation Approach](../../archive/analysis/VALIDATION_APPROACH.md) | [API Testing](../../archive/status_reports/API_TESTING_COMPLETE.md) | [Quality Assurance](../../guides/automation/QUALITY_ASSURANCE_SETUP.md) |
| [Test Coverage](../test_coverage_analysis.md)    | [Focus Summary](../../archive/analysis/VALIDATION_FOCUS_SUMMARY.md)  | [Commands](../API_TEST_COMMANDS.md)       |                                                           |

---

## Development

**Purpose:** Implementation roadmaps, status tracking, and progress reports

**Documents:** 103 | **Recent Updates:** 2025-11-13

### Project Planning

| Roadmap                                          | Checklist                                                  | Phases                                                   | Status                                         |
| ------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| [Development Roadmap](../../DEVELOPMENT_ROADMAP.md) | [Implementation Checklist](../IMPLEMENTATION_CHECKLIST.md) | [Phase Summary](../../archive/progress-logs/implementation_summary.md)        | [Current Status](../../testing/CURRENT_STATUS.md) |
|                                                  |                                                            | [Phase 1 Status](../dev/phase1_implementation_status.md) |                                                |
|                                                  |                                                            | [Phase 2 Status](../../architecture/implementation/phase2_implementation_plan.md)   |                                                |
|                                                  |                                                            | [Phase 3 Status](../../archive/progress-logs/phase3_complete.md)              |                                                |

### Progress Tracking

| Completion                                              | Next Steps                                                     | Analysis                                                                       | Reports                                                         |
| ------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------- |
| [Phase 1 Complete](../../archive/progress-logs/phase1_completion_summary.md) | [Phase 1 Next](../../archive/progress-logs/phase1_next_steps_detailed.md)           | [Readiness Assessment](../dev/analysis/implementation_readiness_assessment.md) | [Monthly Updates](../../archive/analysis/IMPLEMENTATION_STATUS.md) |
| [Phase 2 Complete](../../architecture/implementation/implementation_plan.md)       | [Task Assessment](../dev/analysis/unaddressed_tasks_review.md) | [Cost Analysis](../dev/analysis/cost_free_improvements.md)                     |                                                                 |

### Feature Implementation

| Photometry                                                             | ESE Detection                                                            | Catalog Work                                                            | Image Filters                                                         |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [Automation Roadmap](../dev/analysis/photometry_automation_roadmap.md) | [Architecture](../../architecture/science/ese_detection_architecture.md)                | [Migration Plan](../../archive/progress-logs/catalog_migration_to_sqlite.md)                 | [Implementation](../image_filters_implementation_status.md) |
| [Assessment](../dev/analysis/photometry_automation_assessment.md)      | [Implementation Summary](../../archive/progress-logs/ese_detection_implementation_summary.md) | [Query Implementation](../../archive/progress-logs/catalog_query_implementation_complete.md) | [Testing](../image_filters_manual_testing_guide.md)         |

### Code Improvements

| Quality                                                                | Refactoring                                                        | Performance                                                        | Security                                            |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ | --------------------------------------------------- |
| [Quality Completion](../../archive/reports/CODE_QUALITY_FINAL_SUMMARY.md) | [Task 3 Architecture](../../guides/dashboard/task3_architecture_refactoring.md) | [Optimization API](../optimizations/OPTIMIZATION_API.md) | [CodeQL Setup](../../guides/development/codeql_setup_and_usage.md) |
| [Quality Work](../../archive/reports/CODE_QUALITY_WORK_COMPLETED.md)      | [Phase 2 Complete](../../guides/dashboard/task3_phase2_complete.md)             | [Profiling Guide](../optimizations/PROFILING_GUIDE.md)   | [Fixes](../../guides/development/fixing_codeql_security_issues.md) |

---

## Documentation

**Purpose:** Guides, references, and documentation practices

**Documents:** 67 | **Recent Updates:** 2025-11-13

### Getting Started

| Quick Reference                                                          | Quick Start                                                | Guides                                       | Indices                                                    |
| ------------------------------------------------------------------------ | ---------------------------------------------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| [Quick Reference Card](../../guides/operations/QUICK_REFERENCE_CARD.md)                | [QA Visualization](../QA_VISUALIZATION_QUICK_START.md)     | [Setup Guide](../CASA6_ENVIRONMENT_GUIDE.md) | [Documentation Index](../START_HERE_DOCUMENT_INVENTORY.md) |
| [Organizational Framework](../documentation_standards/DOCUMENTATION_ORGANIZATIONAL_FRAMEWORK.md) | [Dashboard Quick Start](../../guides/dashboard/dashboard-quickstart.md) | [Contributing](../contributing/index.md)     | [Inventory Report](../DOCUMENTATION_INVENTORY_REPORT.md)   |

### Reference & API

| General Reference                                      | API Docs                                                 | CLI Reference                       | Config                               |
| ------------------------------------------------------ | -------------------------------------------------------- | ----------------------------------- | ------------------------------------ |
| [Quick Reference](../documentation_standards/DOCUMENTATION_QUICK_REFERENCE.md) | [API Reference](../api_reference.md)           | [CLI Commands](../cli.md) | [Configuration](../configuration.md) |
| [README](../reference/README.md)                       | [Generated API](../api_reference_generated.md) |                                     |                                      |

### Documentation Authoring

| Improvements                                                               | Audit                                              | Organization                                                         | Best Practices                      |
| -------------------------------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------- |
| [Improvements Summary](../documentation_improvements_summary.md) | [Audit Summary](../DOCUMENTATION_AUDIT_SUMMARY.md) | [Consolidation Strategy](../documentation_standards/DOCUMENTATION_CONSOLIDATION_STRATEGY.md) | [Glossary](../../architecture/GLOSSARY.md) |

---

## Troubleshooting

**Purpose:** Bug fixes, error resolution, and debugging

**Documents:** 56 | **Recent Updates:** 2025-11-13

### Quick Fixes

| Common Issues                                                   | Quick Reference                                           | Frontend                                                              | Streaming                                                           |
| --------------------------------------------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------- |
| [Quick Reference](../../guides/operations/TROUBLESHOOTING_QUICK_REFERENCE.md) | [Dashboard Troubleshooting](../../guides/operations/troubleshooting.md) | [Blank Page Issue](../../guides/dashboard/TROUBLESHOOTING_DASHBOARD_BLANK_PAGE.md) | [Streaming Troubleshooting](../../guides/workflow/streaming-troubleshooting.md) |

### Error Handling

| Implementation                                                               | Detection                                                           | Resilience                                                   | Issues                                                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------- |
| [Error Handling Summary](../../guides/error-handling/error-handling-implementation-summary.md) | [Error Detection Setup](../../guides/error-handling/enable-auto-error-detection.md)   | [Resilience Guide](../../guides/error-handling/error-handling-resilience.md)   | [Potential Issues](../../architecture/implementation/potential_issues_and_fixes.md) |
|                                                                              | [System-Wide Setup](../../guides/error-handling/system-wide-error-detection-setup.md) | [Validation Output](../../guides/error-handling/output-handling-validation.md) | [Deep Dive Report](../../archive/reports/DEEP_DIVE_ISSUES_REPORT.md)   |

### Bug Analysis

| Analysis                                         | Fixes                                                        | Investigations                                                | Learnings                                                           |
| ------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------- | ------------------------------------------------------------------- |
| [Bug Fixes Task 2](../../guides/dashboard/bug_fixes_task2.md) | [Applied Fixes](../../archive/reports/FIXES_APPLIED_SUMMARY.md) | [Investigations](../../archive/analysis/UNANTICIPATED_ISSUES.md) | [Validation Learnings](../../archive/analysis/VALIDATION_LEARNINGS.md) |

---

## Operations

**Purpose:** Deployment, maintenance, and system operations

**Documents:** 32 | **Recent Updates:** 2025-11-13

### System Operations

| Port Management                                                           | Service Restart                                             | Log Daemon                                                                | Safeguards                                                            |
| ------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| [Port System Guide](../operations/PORT_SYSTEM_IMPLEMENTATION_GUIDE.md)    | [API Restart](../../operations/API_RESTART_GUIDE.md)           | [Protection Summary](../operations/CASA_LOG_DAEMON_PROTECTION_SUMMARY.md) | [Proactive Prevention](../../archive/status_reports/PROACTIVE_PREVENTION_SUMMARY.md) |
| [Port Quick Reference](../../operations/PORT_ASSIGNMENTS_QUICK_REFERENCE.md) | [Service Restart Fix](../../operations/service_restart_fix.md) | [Monitoring](../operations/CASA_LOG_DAEMON_MONITORING.md)                 | [Safeguards Complete](../../archive/AGENT_SAFEGUARDS_COMPLETE.md)                |

### Deployment & Infrastructure

| Docker                                          | Systemd                                           | Production                                                                    | Checklist                                                                |
| ----------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [Docker Deploy](../../operations/deploy-docker.md) | [Systemd Deploy](../../operations/deploy-systemd.md) | [Production Readiness](../../archive/reports/production_readiness_plan_2025-11-11.md) | [Deployment Checklist](../../operations/production_deployment_checklist.md) |

### Maintenance

| Monitoring                                                    | Scheduling                                                | Dashboard Ops                                              | Reference                                   |
| ------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------- |
| [Log Monitoring](../operations/CASA_LOG_DAEMON_MONITORING.md) | [Maintenance Schedule](../how-to/MAINTENANCE_SCHEDULE.md) | [Safe Startup](../../operations/starting_dashboard_safely.md) | [Operations Guide](../operations/README.md) |

---

## Tools

**Purpose:** External tool evaluation and integration

**Documents:** 26 | **Recent Updates:** 2025-11-13

### Tool Evaluation

| Comparison                                                      | Analysis                                                                                 | Evaluation                                           | Assessment                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------- |
| [External Tools](../../archive/EXTERNAL_TOOLS_EVALUATION.md)               | [Vast Tools Analysis](../../archive/analysis/VAST_TOOLS_REFERENCE_ANALYSIS.md)              | [RadioPadre Evaluation](../../archive/RADIOPADRE_EVALUATION.md) | [CASA MPI Evaluation](../../archive/reports/CASA_MPI_EVALUATION.md) |
| [RadioPadre vs VAST](../../archive/RADIOPADRE_VS_VAST_TOOLS_COMPARISON.md) | [VAST Detailed Comparison](../../archive/analysis/VAST_TOOLS_DSA110_DETAILED_COMPARISON.md) |                                                      |                                                                  |

### VAST Tools Integration

| Integration                                                                            | Analysis                                                               | Adoption                                                              | Workflow                                                                  |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [Cross-Matching Integration](../VAST_PIPELINE_CROSS_MATCHING_INTEGRATION.md) | [Adoption Summary](../../archive/analysis/VAST_TOOLS_ADOPTION_SUMMARY.md) | [Reference Analysis](../../archive/analysis/VAST_TO_DSA110_SYNTHESIS.md) | [Pipeline Imaging](../../archive/analysis/VAST_PIPELINE_IMAGING_WORKFLOW.md) |

### Special Tools

| WABIFAT                                                                       | CARTA                                                            | Worksheet Tools                                                    |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------ |
| [Implementation Status](../../archive/analysis/WABIFAT_IMPLEMENTATION_STATUS.md) | [Integration Complete](../archive/carta_integration_complete.md) | [Workspace Tools](../../archive/analysis/ANALYSIS_WORKSPACE_TOOLS.md) |
| [Verification Results](../../archive/analysis/WABIFAT_VERIFICATION_RESULTS.md)   | [Quick Start](../archive/carta_quick_start.md)                   |                                                                    |

---

## Environment

**Purpose:** Development environment setup and configuration

**Documents:** 20 | **Recent Updates:** 2025-11-14

### CASA6 Configuration

| Guide                                                    | Setup                                                    | Enforcement                                                      | Reference                                                           |
| -------------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------- |
| [CASA6 Environment Guide](../CASA6_ENVIRONMENT_GUIDE.md) | [Development Setup](../../development/DEVELOPMENT_SETUP.md) | [Enforcement](../../architecture/architecture/environment_dependency_enforcement.md) | [Critical Environment](../CRITICAL_PYTHON_ENVIRONMENT.md) |
|                                                          |                                                          | [Casa6 Enforcement](../../guides/development/casa6-enforcement.md)              | [Analysis Report](../../archive/status_reports/ENVIRONMENT_ANALYSIS_REPORT.md)    |

### Conda & Dependencies

| Dependency                                                               | Setup                                                     | Analysis                                         | Best Practices |
| ------------------------------------------------------------------------ | --------------------------------------------------------- | ------------------------------------------------ | -------------- |
| [Dependency Enforcement](../../architecture/architecture/APPLYING_DEPENDENCY_ENFORCEMENT.md) | [Package Installation](../../guides/development/package_installation.md) | [Test Agent Python](../../archive/TEST_AGENT_PYTHON_ENV.md) |                |

### Tools & Frameworks

| Tools                                                                 | Python                                                            | Playwright                                                                | Git/GitHub                                          |
| --------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------- |
| [Playwright Installation](../../guides/development/playwright-conda-installation.md) | [Python Environment](../CRITICAL_PYTHON_ENVIRONMENT.md) | [Testing Setup](../../guides/development/playwright-python-quick-start.md)               | [GitHub Copilot](../../guides/development/github_copilot_setup.md) |
|                                                                       |                                                                   | [Documentation Audit](../../guides/development/playwright-python-documentation-audit.md) |                                                     |

---

## Deployment

**Purpose:** Deployment strategies and production deployment

**Documents:** 18 | **Recent Updates:** 2025-11-13

### Deployment Methods

| Docker                                               | Systemd                                                 | Production Considerations                                                       |
| ---------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------- |
| [Docker Deployment](../../operations/deploy-docker.md)  | [Systemd Deployment](../../operations/deploy-systemd.md)   | [Production Deployment Summary](../../operations/production_deployment_summary.md) |
| [Docker Testing](../../testing/guides/DOCKER_TESTING_GUIDE.md) | [Systemd Migration](../../operations/systemd-migration.md) | [Production Readiness](../../archive/reports/production_readiness_plan_2025-11-11.md)   |

### Configuration & Ports

| Port Management                                                  | Configuration                                                         | Safe Startup                                               |
| ---------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Port System](../../operations/port_system_implementation_guide.md) | [Config Analysis](../../operations/port_organization_recommendations.md) | [Safe Startup](../../operations/starting_dashboard_safely.md) |
| [Port Enforcement](../../archive/status_reports/PORT_ENFORCEMENT_SUMMARY.md)    |                                                                       |                                                            |

---

## Performance

**Purpose:** Optimization, profiling, and scalability

**Documents:** 11 | **Recent Updates:** 2025-11-13

### Optimization

| Guide                                                               | Profiling                                                          | Implementation                                                            | Analysis                                                         |
| ------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [Parameter Optimization](../how-to/PARAMETER_OPTIMIZATION_GUIDE.md) | [Profiling Guide](../optimizations/PROFILING_GUIDE.md)   | [Implementation Summary](../how-to/performance_implementation_summary.md) | [Scalability Analysis](../how-to/performance_and_scalability.md) |
|                                                                     | [Optimization API](../optimizations/OPTIMIZATION_API.md) |                                                                           |                                                                  |

### Model Optimization

| Improvements                                                              | Latest Optimization                                                       |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [Implementation Summary](../how-to/performance_implementation_summary.md) | [model.py Optimization](../../changelog/2025-11-06-model-py-optimization.md) |

---

## Security

**Purpose:** Security safeguards and vulnerability management

**Documents:** 9 | **Recent Updates:** 2025-11-13

### Safeguards & Protections

| Safeguards                                             | Protections                                                    | Enhancements                                                                          | Verification                                                     |
| ------------------------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [Safeguards Complete](../../archive/AGENT_SAFEGUARDS_COMPLETE.md) | [Final Protections](../how-to/FINAL_PROTECTIONS_ADDED.md)      | [Enhancements Implemented](../../archive/reports/enhancements_implemented_2025-11-11.md) | [Status Verification](../../operations/port_safeguards_analysis.md) |
|                                                        | [Missing Safeguards](../../operations/MISSING_PORT_SAFEGUARDS.md) |                                                                                       |                                                                  |

### CodeQL & Vulnerability Management

| Security Analysis                                   | Setup                                                  | Issues                                                             | Fixes                                                        |
| --------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------ |
| [CodeQL Setup](../../guides/development/codeql_setup_and_usage.md) | [Viewing Results](../../guides/development/viewing_codeql_results.md) | [Critical Issues](../../archive/prettier/PRETTIER_CRITICAL_ISSUES.md) | [Security Fixes](../../guides/development/fixing_codeql_security_issues.md) |

---

## Quick Navigation by Need

### I Need to Understand Something

1. **Pipeline stage?** → [Pipeline Stages Index](./PIPELINE_STAGES_INDEX.md)
2. **Dashboard feature?** →
   [Dashboard Components Index](./DASHBOARD_COMPONENTS_INDEX.md)
3. **General topic?** → [This Index](./GENERAL_THEMES_INDEX.md)

### I Need to Do Something

1. **Deploy?** → [Deployment Section](#deployment)
2. **Fix a problem?** → [Troubleshooting Section](#troubleshooting)
3. **Test?** → [Testing Section](#testing)
4. **Optimize?** → [Performance Section](#performance)
5. **Add a feature?** → [Development Section](#development)

### I Need to Set Up Something

1. **Environment?** → [Environment Section](#environment)
2. **Dashboard?** → [Deployment Section](#deployment)
3. **Tests?** → [Testing Section](#testing)

---

## Statistics

| Category        | Documents | Status     |
| --------------- | --------- | ---------- |
| Testing         | 104       | Complete   |
| Development     | 103       | Active     |
| Documentation   | 67        | Maintained |
| Troubleshooting | 56        | Updated    |
| Operations      | 32        | Complete   |
| Tools           | 26        | Reference  |
| Environment     | 20        | Maintained |
| Deployment      | 18        | Complete   |
| Performance     | 11        | Reference  |
| Security        | 9         | Maintained |

**Total:** 446 documents (cross-cutting themes)

---

## Navigation

- [Back to Main Index](../START_HERE_DOCUMENT_INVENTORY.md)
- [Pipeline Stages Index](./PIPELINE_STAGES_INDEX.md)
- [Dashboard Components Index](./DASHBOARD_COMPONENTS_INDEX.md)
- [Documentation Framework](../documentation_standards/DOCUMENTATION_ORGANIZATIONAL_FRAMEWORK.md)

---

**Last Updated:** 2025-11-15  
**Total Unique Documents:** (Note: many docs appear in multiple themes)  
**Status:** Complete
