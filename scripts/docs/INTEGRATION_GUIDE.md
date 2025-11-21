# Error Detection Framework - Integration Guide

## Overview

This guide explains how to integrate the error detection framework into your
workflows.

---

## Quick Start

### Basic Usage

```bash
# Run any command with comprehensive error detection
./scripts/run-safe.sh "npm run build"
./scripts/run-safe.sh "npm test"
./scripts/run-safe.sh "npm run lint"
```

---

## Integration Options

### Option 1: Use Safe Scripts (Recommended)

The framework adds "safe" versions of common npm scripts:

```bash
cd frontend
npm run build:safe    # Build with error detection
npm run lint:safe     # Lint with error detection
npm run test:safe     # Test with error detection
```

### Option 2: Direct Library Usage

Source the library and use functions directly:

```bash
source scripts/lib/error-detection.sh

# Pre-flight checks only
preflight_checks

# Execute with monitoring
execute_with_monitoring "npm run build"

# Comprehensive detection
run_with_comprehensive_detection "npm run build"
```

### Option 3: CI/CD Integration

The framework includes GitHub Actions workflow:

```yaml
# .github/workflows/error-detection.yml
# Automatically runs error detection on push/PR
```

### Option 4: Pre-commit Hook

Husky pre-commit hook runs checks before commits:

```bash
# Install Husky (if not already installed)
cd frontend
npm install --save-dev husky
npx husky install

# Hook is already configured at .husky/pre-commit
```

---

## Function Reference

### Pre-Flight Functions

- `check_node_version [version]` - Check Node.js version
- `check_npm_version [version]` - Check npm version
- `verify_required_files` - Verify required files exist
- `check_dependencies` - Check dependencies installed
- `check_permissions` - Check write permissions
- `check_memory [min_mb]` - Check available memory
- `check_process_conflicts` - Check for conflicting processes
- `validate_config_files` - Validate config files
- `preflight_checks` - Run all pre-flight checks

### Execution Functions

- `execute_with_monitoring <command>` - Execute with error monitoring
- `detect_errors <output>` - Detect errors in output
- `detect_critical_warnings <output>` - Detect critical warnings

### Post-Execution Functions

- `validate_build_output` - Validate build artifacts
- `validate_test_results <output>` - Validate test results
- `post_execution_validation <command>` - Run post-execution checks

### Comprehensive Functions

- `run_with_comprehensive_detection <command>` - Full workflow

---

## Examples

### Example 1: Build with Error Detection

```bash
cd frontend
./scripts/run-safe.sh "npm run build"
```

**What happens:**

1. Pre-flight checks (Node version, deps, permissions)
2. Execute build with monitoring
3. Post-execution validation (check dist files)
4. Edge case detection

---

### Example 2: Custom Script with Error Detection

```bash
#!/bin/bash
source scripts/lib/error-detection.sh

# Pre-flight
preflight_checks || exit 1

# Execute
execute_with_monitoring "npm run build" || exit 1

# Validate
validate_build_output || exit 1

echo "Build successful!"
```

---

### Example 3: CI/CD Integration

```yaml
- name: Build with error detection
  run: |
    cd frontend
    source ../scripts/lib/error-detection.sh
    run_with_comprehensive_detection "npm run build"
```

---

## Configuration

### Customizing Checks

Edit `scripts/lib/error-detection.sh` to customize:

- Required Node.js version: `check_node_version "20.0.0"`
- Minimum memory: `check_memory 4096`
- Critical dependencies: Add to `critical_deps` array
- Error patterns: Modify `error_patterns` array

---

## Troubleshooting

### Script Not Found

```bash
# Make sure scripts are executable
chmod +x scripts/run-safe.sh scripts/lib/error-detection.sh
```

### Permission Denied

```bash
# Check write permissions
ls -la .
# Fix if needed
chmod u+w .
```

### Dependencies Missing

```bash
cd frontend
npm install
```

---

## Best Practices

1. **Use safe scripts for critical commands**

   ```bash
   npm run build:safe  # Instead of npm run build
   ```

2. **Run pre-flight checks before long operations**

   ```bash
   source scripts/lib/error-detection.sh
   preflight_checks || exit 1
   ```

3. **Integrate into CI/CD**
   - Use GitHub Actions workflow
   - Add to other CI systems similarly

4. **Use pre-commit hooks**
   - Catches errors before commit
   - Saves time in CI/CD

5. **Customize for your needs**
   - Adjust checks based on your environment
   - Add project-specific validations

---

## Next Steps

1. Test the implementation:

   ```bash
   cd frontend
   npm run build:safe
   ```

2. Integrate into your workflow:
   - Use safe scripts for critical commands
   - Add to CI/CD pipelines
   - Enable pre-commit hooks

3. Customize as needed:
   - Adjust checks for your environment
   - Add project-specific validations

---

## Support

For issues or questions:

- Check `ERROR_DETECTION_FRAMEWORK.md` for framework details
- Review `EDGE_CASE_ERROR_DETECTION.md` for edge cases
- See `REAL_WORLD_EDGE_CASES.md` for real-world examples
