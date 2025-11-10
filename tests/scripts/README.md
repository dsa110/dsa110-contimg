# Test Scripts

This directory contains test scripts for the DSA-110 continuum imaging pipeline.

## Contents

- **`test_pipeline_end_to_end.sh`** - Comprehensive end-to-end pipeline test
- **`test_suite_comprehensive.py`** - Comprehensive Python test suite for all modules
- **`test_qa_*.py`** - QA module tests
- **`test_data_accessibility.py`** - Data accessibility tests
- **`test_integration_points.py`** - Integration point tests
- **`test_photometry_without_db.py`** - Photometry tests
- **`test_alerting.py`** - Alerting system tests
- **`test_monitor_daemon.py`** - Monitor daemon tests
- **`test_ingest_vla_catalog.py`** - VLA catalog ingestion tests
- **`test_catalog_builder.py`** - Catalog builder tests
- **`test_graphiti_mcp.py`** - Knowledge graph MCP tests

## Running Tests

Most test scripts use relative path imports that automatically adjust for this directory location:

```bash
# Example: Run end-to-end test
cd /data/dsa110-contimg
bash tests/integration/test_pipeline_end_to_end.sh

# Example: Run comprehensive test suite
cd /data/dsa110-contimg
python tests/scripts/test_suite_comprehensive.py
```

The scripts use `sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))` to ensure they can import from the main codebase. Since scripts are in `tests/scripts/`, this correctly resolves to the repo root's `src/` directory.

**Note**: These scripts are standalone and run directly. For pytest-style tests, see `tests/unit/` and `tests/integration/`.
