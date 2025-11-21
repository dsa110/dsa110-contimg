# DSA-110 Continuum Imaging Pipeline Documentation

Welcome to the central documentation hub for the DSA-110 Continuum Imaging
Pipeline.

## 📚 Documentation Structure

This documentation is organized into the following sections:

### 🏗️ [Architecture & Design](architecture/README.md)

**Start here to understand how the pipeline works.**

- [**Workflow Thought Experiment**](architecture/WORKFLOW_THOUGHT_EXPERIMENT.md):
  The "Iceberg" analysis of all potential failure modes.
- [**Execution Themes**](architecture/EXECUTION_THEMES.md): Streaming vs. Batch
  execution models.
- [**Pipeline Documentation Index**](architecture/README_PIPELINE_DOCUMENTATION.md):
  The original detailed index.
- [**Defaults & Minimal Input**](architecture/DEFAULTS_AND_MINIMAL_INPUT.md):
  How to run with zero config.

### 🚀 [Operations & Runbooks](operations/README.md)

**For operators running the pipeline in production.**

- [**Runbooks**](runbooks/): Step-by-step guides for common tasks.
- [**Deployment**](deployment/): How to deploy the pipeline.

### 🔄 [Absurd Integration](absurd/README.md)

**Documentation for the durable workflow manager.**

- [**Quick Start**](absurd/ABSURD_QUICK_START.md): Getting started with Absurd.
- [**Integration Analysis**](absurd/ABSURD_INTEGRATION_ANALYSIS.md): How Absurd
  fits into the pipeline.

### 💻 [Developer Zone](dev/README.md)

**For contributors and developers.**

- [**Reports**](reports/): Historical implementation reports and status updates.
- [**Concepts**](concepts/): Deep dives into specific technical concepts.

---

## ⚡ Quick Links

- **I want to run the pipeline:** See
  [Defaults & Minimal Input](architecture/DEFAULTS_AND_MINIMAL_INPUT.md).
- **I want to understand the code:** See
  [Architecture](architecture/README_PIPELINE_DOCUMENTATION.md).
- **I want to fix a bug:** Check [Reports](reports/) to see recent changes.

---

_Documentation generated on November 21, 2025._
