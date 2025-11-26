# Development Scripts

Scripts for setting up and managing the development environment.

## Quick Start

```bash
# Complete developer setup (recommended for new developers)
./dev/quick-start.sh

# Or step by step:
./dev/developer-setup.sh
./dev/install-developer-automations.sh
```

## Available Scripts

### Setup Scripts

- **`quick-start.sh`** - Complete automated setup for new developers
- **`developer-setup.sh`** - Main developer environment setup
- **`setup-dev.sh`** - Alternative setup script
- **`setup-developer-env.sh`** - Environment configuration
- **`install-developer-automations.sh`** - Install development automation tools

### Validation Scripts

- **`verify-test-deps.sh`** - Verify test dependencies are installed
- **`check_codeql_status.sh`** - Check CodeQL analysis status

### Pre-commit Hooks

- **`pre-commit-doc-location.sh`** - Validate documentation location
- **`pre-commit-python-env.sh`** - Validate Python environment

### Configuration

- **`setup_python_warnings.sh`** - Configure Python warning filters

## Common Workflows

### First Time Setup

```bash
cd /data/dsa110-contimg/scripts
./dev/quick-start.sh
```

### Verify Environment

```bash
./dev/verify-test-deps.sh
```

### Update Pre-commit Hooks

```bash
# Hooks are automatically installed by developer-setup.sh
# To reinstall:
./dev/install-developer-automations.sh
```
