# Pre-commit Hooks Setup Guide

This guide explains how to set up and use pre-commit hooks for code quality
checks.

## Overview

Pre-commit hooks automatically run code quality checks before each commit. The
configuration is in `.pre-commit-config.yaml` and uses the casa6 Python
environment.

## Configuration

### Location

- Configuration file: `.pre-commit-config.yaml` (project root)
- All hooks use: `/opt/miniforge/envs/casa6/bin/python`

### Configured Hooks

#### Python Hooks (casa6)

- **black**: Code formatting
- **isort**: Import sorting
- **pylint**: Code quality (errors only)
- **pyflakes**: Undefined variable detection
- **flake8**: Style guide enforcement
- **mypy**: Static type checking
- **bandit**: Security linting

#### Frontend Hooks (husky)

- **prettier**: Code formatting
- **eslint**: Linting

#### Custom Hooks

- **output-handling-validation**: Validates output handling rules
- **validate-port-config**: Validates port configuration

## Setup Instructions

### Option 1: Using Husky (Recommended)

The project uses Husky for git hooks, which includes frontend formatting:

```bash
# Hooks are already configured in .husky/pre-commit
# No additional setup needed

# Verify hooks are executable
chmod +x .husky/pre-commit
```

### Option 2: Using Pre-commit (Alternative)

If you want to use the pre-commit framework directly:

```bash
# Install pre-commit (in casa6 or system Python)
conda activate casa6
pip install pre-commit

# Install git hooks
pre-commit install

# Install hooks for commit messages
pre-commit install --hook-type commit-msg
```

**Note**: The documentation recommends using Husky instead of
`pre-commit install` to avoid conflicts.

## Usage

### Automatic Execution

Hooks run automatically on `git commit`:

```bash
# Hooks will run automatically
git add .
git commit -m "Your message"
```

### Manual Execution

Run hooks manually on all files:

```bash
# Using husky (if configured)
.husky/pre-commit

# Or using pre-commit directly
conda activate casa6
pre-commit run --all-files
```

### Run Specific Hook

```bash
conda activate casa6

# Run black only
/opt/miniforge/envs/casa6/bin/black --check .

# Run flake8 only
/opt/miniforge/envs/casa6/bin/flake8 src/

# Run mypy only
/opt/miniforge/envs/casa6/bin/mypy src/
```

## Hook Behavior

### Auto-formatting Hooks

These hooks modify files automatically:

- **black**: Formats Python code
- **isort**: Sorts imports
- **prettier**: Formats frontend code

### Checking Hooks

These hooks only report issues (don't modify files):

- **pylint**: Reports code quality issues
- **flake8**: Reports style violations
- **mypy**: Reports type errors
- **bandit**: Reports security issues
- **pyflakes**: Reports undefined variables

## Troubleshooting

### Hook Fails: "Command not found"

If a hook fails with "command not found":

1. **Verify casa6 environment exists**:

   ```bash
   conda env list
   ```

2. **Verify tool is installed**:

   ```bash
   conda activate casa6
   which black
   which flake8
   ```

3. **Reinstall missing tools**:
   ```bash
   conda activate casa6
   conda install -c conda-forge black flake8 mypy pylint bandit
   ```

### Hook Fails: "Permission denied"

Make hooks executable:

```bash
chmod +x .husky/pre-commit
chmod +x .husky/post-commit
```

### Skip Hooks (Not Recommended)

To skip hooks for a single commit:

```bash
git commit --no-verify -m "Emergency fix"
```

**Warning**: Only skip hooks in emergencies. CI will still check your code.

### Pre-commit Conflicts with Husky

If you have both pre-commit and husky installed:

1. **Remove pre-commit hooks**: `pre-commit uninstall`
2. **Use husky only**: Hooks in `.husky/` will run automatically

## CI Integration

Pre-commit hooks are also run in CI:

- **Workflow**: `.github/workflows/pre-commit.yml`
- **Triggers**: On pull requests and pushes to main/develop
- **Runs**: All configured hooks on changed files

## Best Practices

1. **Let hooks format automatically**: Don't manually format code
2. **Fix issues before committing**: Address linting errors locally
3. **Check CI before merging**: Ensure hooks pass in CI
4. **Use consistent settings**: Don't override hook config locally

## Related Documentation

- [Prettier Setup](prettier_setup.md)
- [Black/Pylint Handover](BLACK_PYLINT_PRE_COMMIT_HANDOVER.md)
- [Environment Setup](ENVIRONMENT_SETUP.md)
