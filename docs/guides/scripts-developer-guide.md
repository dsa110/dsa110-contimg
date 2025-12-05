# Developer Guide - Scripts Directory

This guide helps developers quickly find and use scripts in the organized
scripts directory.

## Quick Start

### For New Developers

```bash
# Complete setup (recommended)
./dev/quick-start.sh

# Or use the workflow shortcuts
source ./workflows.sh
dev-setup
```

### Finding Scripts

#### Using the Script Manager

```bash
# List all categories
./scripts list

# List scripts in a category
./scripts list tests

# Search for scripts
./scripts search calibration

# Get info about a script
./scripts info run-tests.sh

# Run a script
./scripts run dev/quick-start.sh
```

#### Manual Discovery

```bash
# Browse by category
ls dev/          # Development scripts
ls tests/         # Test scripts
ls quality/      # Quality assurance
ls utils/         # Utilities

# Search by name
find . -name "*test*" -type f
find . -name "*calibration*" -type f
```

## Workflow Shortcuts

Source the workflows file to get convenient aliases:

```bash
source ./workflows.sh
workflows-help  # Show all available shortcuts
```

### Common Shortcuts

- `dev-setup` - Quick developer setup
- `test-all` - Run all tests
- `quality-check` - Run quality checks
- `services-status` - Check service status
- `casa-cleanup` - Cleanup CASA logs

## Directory Organization

### :folder: [dev/](dev/)

Development environment setup and automation

- **Quick Start**: `dev/quick-start.sh`
- **See**: [dev/README.md](dev/README.md)

### :folder: [tests/](tests/)

Test scripts and utilities

- **Run Tests**: `utils/run-tests.sh`
- **See**: [tests/README.md](tests/README.md)

### :folder: [quality/](quality/)

Code quality, validation, and error detection

- **Quality Check**: `quality/check-code-quality.sh`
- **See**: [quality/README.md](quality/README.md)

### :folder: [utils/](utils/)

General utility scripts

- **Service Management**: `utils/manage-services.sh`
- **See**: [utils/README.md](utils/README.md)

### :folder: [casa/](casa/)

CASA log management and utilities

- **Cleanup**: `casa/cleanup_casa_logs.sh`
- **See**: [docs/README.md](docs/README.md) for detailed docs

### :folder: [calibration/](calibration/)

Calibration workflows and validation

- **Check Phasing**: `calibration/check_ms_phasing.py`

### :folder: [imaging/](imaging/)

Imaging and mosaic creation

- **Build Mosaic**: `imaging/build_60min_mosaic.py`

### :folder: [dashboard/](dashboard/)

Frontend and dashboard scripts

- **Build**: `dashboard/build-dashboard-production.sh`
- **Serve**: `dashboard/serve-dashboard-production.sh`

### :folder: [monitoring/](monitoring/)

Monitoring and health checks

- **Monitor Calibration**: `monitoring/monitor_calibration.py`

### :folder: [graphiti/](graphiti/)

Knowledge graph management

- **Ingest Docs**: `graphiti/graphiti_ingest_docs.py`

## Common Workflows

### Daily Development

```bash
# Start your day
source ./workflows.sh
services-status
test-all

# Before committing
quality-check
quality-fix
```

### Running Tests

```bash
# All tests
./utils/run-tests.sh

# Specific test
python tests/test_pipeline_endpoints.py

# Docker tests
./utils/run-tests-docker.sh

# Playwright tests
./utils/run-playwright-python-tests.sh
```

### Service Management

```bash
# Using the manager
./utils/manage-services.sh start all
./utils/manage-services.sh status
./utils/manage-services.sh stop api

# Or using shortcuts (after sourcing workflows.sh)
services-start all
services-status
services-stop api
```

### Quality Assurance

```bash
# Run all quality checks
./quality/check-code-quality.sh

# Auto-fix issues
./quality/auto-fix-common-issues.sh

# Error detection
./quality/auto-error-detection.sh
```

## Adding New Scripts

1. **Choose the right directory** based on function
2. **Follow naming conventions**:
   - Bash scripts: `kebab-case.sh`
   - Python scripts: `snake_case.py`
3. **Add documentation**:
   - Add a comment header describing purpose
   - Update the category README if significant
4. **Make executable**: `chmod +x script.sh`

## Getting Help

- **Script Manager**: `./scripts help`
- **Workflow Shortcuts**: `workflows-help` (after sourcing workflows.sh)
- **Category READMEs**: Check individual category README files
- **Main README**: [README.md](README.md)

## Tips

1. **Use the script manager** for discovery: `./scripts list`
2. **Source workflows.sh** for convenient aliases
3. **Check category READMEs** for detailed usage
4. **Use search** to find scripts: `./scripts search <keyword>`
