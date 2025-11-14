# Utility Scripts

General utility scripts for various tasks.

## Common Utilities

### Test Runners

- **`run-tests.sh`** - Main test runner
- **`run-tests-docker.sh`** - Docker-based test runner
- **`run-playwright-python-tests.sh`** - Playwright test runner
- **`run-safe.sh`** - Safe script runner with error detection

### Service Management

- **`manage-services.sh`** - Manage system services (API, dashboard, docs)
- **`check-ports.sh`** - Check port availability
- **`check-duplicate-services.sh`** - Check for duplicate services
- **`cleanup-duplicate-services.sh`** - Clean up duplicate services
- **`prevent-duplicate-services.sh`** - Prevent duplicate service instances
- **`service-lock.sh`** - Service locking mechanism
- **`enforce-port-safeguards.sh`** - Enforce port usage safeguards

### Data Processing

- **`analyze_baseline_flagging.py`** - Analyze baseline flagging
- **`analyze_coverage.py`** - Analyze test coverage
- **`benchmark_nvss_query.py`** - Benchmark NVSS queries
- **`backfill_eta_metric.py`** - Backfill ETA metrics
- **`find_earliest_data.py`** - Find earliest data files
- **`register_existing_data.py`** - Register existing data
- **`reorganize_ms_directory.py`** - Reorganize measurement set directories
- **`validate_ms_timing.py`** - Validate MS timing

### Conversion & Processing

- **`run_conversion.sh`** - Run data conversion
- **`run_batch_conversion_example.sh`** - Batch conversion example
- **`run_casa_cmd.sh`** - Run CASA commands
- **`run_bandpass_check.sh`** - Run bandpass checks

### Image Generation

- **`create_synthetic_images.py`** - Create synthetic images
- **`create_test_catalog.py`** - Create test catalog
- **`generate_skymodel_image.py`** - Generate skymodel images

### Documentation

- **`doc_audit.py`** - Audit documentation
- **`generate_api_reference.py`** - Generate API reference
- **`generate_mkdocs_config.py`** - Generate MkDocs configuration
- **`migrate_docs.sh`** - Migrate documentation

### Database

- **`init_databases.py`** - Initialize databases

### Wrappers

- **`command-wrapper.sh`** - Command wrapper utility
- **`python-wrapper.sh`** - Python wrapper utility
- **`run-python.sh`** - Run Python scripts
- **`copilot.sh`** - Copilot integration

### System Utilities

- **`scratch_sync.sh`** - Sync scratch directory
- **`linear_sync.py`** - Linear synchronization
- **`update_todo_date.py`** - Update TODO dates
- **`kill-vite-thoroughly.sh`** - Kill Vite processes
- **`check_browser_mcp.sh`** - Check browser MCP
- **`add-port-health-check.py`** - Add port health check

## Usage Examples

### Run Tests

```bash
./utils/run-tests.sh
```

### Manage Services

```bash
./utils/manage-services.sh start all
./utils/manage-services.sh status
```

### Run Safe Script

```bash
./utils/run-safe.sh "npm run build"
```
