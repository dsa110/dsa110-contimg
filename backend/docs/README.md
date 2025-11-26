# DSA-110 Continuum Imaging Pipeline Documentation

Welcome to the central documentation hub for the DSA-110 Continuum Imaging
Pipeline.

## Documentation Structure

This documentation is organized into the following sections:

### [Architecture & Design](architecture/)

**Start here to understand how the pipeline works.**

- [Workflow Thought Experiment](architecture/WORKFLOW_THOUGHT_EXPERIMENT.md):
  The "Iceberg" analysis of all potential failure modes.
- [Execution Themes](architecture/EXECUTION_THEMES.md): Streaming vs. Batch
  execution models.
- [Pipeline Documentation Index](architecture/README_PIPELINE_DOCUMENTATION.md):
  The original detailed index.
- [Defaults & Minimal Input](architecture/DEFAULTS_AND_MINIMAL_INPUT.md):
  How to run with zero config.

### [Operations & Runbooks](operations/)

**For operators running the pipeline in production.**

- [Runbooks](runbooks/): Step-by-step guides for common tasks.
- [Deployment](deployment/): How to deploy the pipeline.

### [Absurd Integration](absurd/)

**Documentation for the durable workflow manager.**

### [Developer Zone](dev/)

**For contributors and developers.**

- [Reports](reports/): Historical implementation reports and status updates.
- [Concepts](concepts/): Deep dives into specific technical concepts.

### [Examples](examples/)

**Example scripts and notebooks demonstrating pipeline usage.**

- `absurd_integration_example.py`: Absurd workflow integration
- `create_10min_mosaic.py`: Creating mosaics programmatically
- `create_15min_mosaic.ipynb`: Jupyter notebook mosaic example

---

## Quick Links

- **I want to run the pipeline:** See
  [Defaults & Minimal Input](architecture/DEFAULTS_AND_MINIMAL_INPUT.md).
- **I want to understand the code:** See
  [Architecture](architecture/README_PIPELINE_DOCUMENTATION.md).
- **I want to fix a bug:** Check [Reports](reports/) to see recent changes.

---

_Documentation last updated: November 26, 2025._
