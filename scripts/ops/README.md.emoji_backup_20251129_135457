# Scripts Directory

This directory contains utility scripts organized by function for managing
various aspects of the dsa110-contimg project.

## Directory Structure

The scripts directory is organized into the following categories:

### 📁 [archive/](archive/)

Temporary storage for deprecated or redundant scripts pending removal.

### 📁 [calibration/](calibration/)

Scripts for calibration workflows, bandpass analysis, and calibration
validation:

- Bandpass checking and verification
- Phase center validation
- Reference antenna recommendations
- Calibration artifact management
- Measurement set phasing checks

### 📁 [casa/](casa/)

CASA (Common Astronomy Software Applications) related scripts:

- Log management daemons and cleanup
- CASA environment setup
- CASA command wrappers
- Log monitoring and health checks

**See [docs/README.md](docs/README.md) for detailed CASA log management
documentation.**

### 📁 [dashboard/](dashboard/)

Frontend and dashboard related scripts:

- Dashboard build and deployment
- Frontend development tools
- Health checks for dashboard and API
- CARTA integration scripts

### 📁 [dev/](dev/)

Development environment setup and automation:

- Developer setup scripts
- Pre-commit hooks
- Code quality automation
- Environment validation
- Test dependency verification

### 📁 [docs/](docs/)

Documentation files:

- `README.md` - Detailed CASA log management documentation
- `INVENTORY.md` - Script inventory and migration plan
- `INTEGRATION_GUIDE.md` - Integration testing guide
- `TEST_SCRIPT_VERIFICATION.md` - Test script verification documentation
- `CASA_LOG_DAEMON_INOTIFY.md` - CASA log daemon inotify documentation

### 📁 [graphiti/](graphiti/)

Knowledge graph management scripts:

- Document ingestion
- Component management
- Guardrails checking
- Re-embedding utilities

### 📁 [imaging/](imaging/)

Imaging and mosaic creation scripts:

- Mosaic building and visualization
- Transit mosaic generation
- Tile processing
- Image creation utilities

### 📁 [lib/](lib/)

Reusable library scripts and shared utilities:

- Error detection functions
- Environment dependency checks
- Anti-pattern detection
- Test utilities

### 📁 [monitoring/](monitoring/)

Monitoring and health check scripts:

- Calibration monitoring
- Publish status monitoring
- Milestone tracking
- Health check utilities

### 📁 [quality/](quality/)

Code quality, validation, and error detection scripts:

- Error detection automation
- Code quality checks
- Output suppression auditing
- Pre-commit validation
- Port validation
- Environment validation

### 📁 [services/](services/)

Systemd service and timer files:

- CASA log daemon services
- Log cleanup timers
- Service management configurations

### 📁 [templates/](templates/)

Template scripts for creating new scripts:

- Dependency check templates
- Other script templates

### 📁 [tests/](tests/)

Test scripts and test utilities:

- Integration tests
- End-to-end tests
- Unit tests
- Test organization utilities
- Test templates

### 📁 [utils/](utils/)

General utility scripts:

- Data analysis and benchmarking
- Data registration and organization
- Conversion utilities
- Documentation generation
- Database initialization
- Runner and wrapper scripts
- Miscellaneous utilities

## Quick Reference

### Finding Scripts

**By Function:**

- **CASA operations**: `casa/`
- **Calibration**: `calibration/`
- **Imaging/Mosaics**: `imaging/`
- **Testing**: `tests/`
- **Development**: `dev/`
- **Monitoring**: `monitoring/`
- **Quality checks**: `quality/`
- **Dashboard**: `dashboard/`

**By File Type:**

- **Systemd services**: `services/`
- **Python scripts**: Various directories (see above)
- **Bash scripts**: Various directories (see above)
- **Documentation**: `docs/`

## Common Tasks

### Running CASA Log Management

```bash
# Manual cleanup
./casa/cleanup_casa_logs.sh --keep-hours 24

# Check daemon status
sudo systemctl status casa-log-daemon
```

### Running Tests

```bash
# Run all tests
./tests/run-tests.sh

# Run specific test
python tests/test_pipeline_endpoints.py
```

### Development Setup

```bash
# Setup developer environment
./dev/developer-setup.sh

# Install developer automations
./dev/install-developer-automations.sh
```

### Quality Checks

```bash
# Run code quality checks
./quality/check-code-quality.sh

# Run error detection
./quality/auto-error-detection.sh
```

## Migration Notes

This directory was reorganized to improve maintainability. If you're looking for
a script that was previously in the root directory:

1. Check the appropriate category directory above
2. Use `find` to search: `find . -name "script_name*"`
3. Check `docs/INVENTORY.md` for migration information

## Script Discovery Tools

### Script Manager (`./scripts`)

A unified tool for discovering and running scripts:

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

### Workflow Shortcuts (`workflows.sh`)

Source this file for convenient aliases:

```bash
source ./workflows.sh
workflows-help  # Show all shortcuts

# Then use shortcuts like:
dev-setup
test-all
quality-check
services-status
```

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for a comprehensive developer
guide.

## Contributing

When adding new scripts:

1. Place them in the appropriate category directory
2. Follow existing naming conventions
3. Update this README if adding a new category
4. Add documentation in `docs/` if needed
5. Update the category README if it's a significant addition
