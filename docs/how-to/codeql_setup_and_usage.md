# CodeQL Setup and Usage Guide

## Overview

CodeQL is integrated into the dsa110-contimg repository for automated security
and code quality analysis.

## Quick Start

### Running Analysis Locally

```bash
cd /data/dsa110-contimg
export PATH="$HOME/codeql:$PATH"

# Create database (if needed)
codeql database create --language=python codeql-db-python --source-root=. \
  --command="echo 'No build needed'"

# Run analysis
codeql database analyze codeql-db-python \
  --format=sarif-latest \
  --output=codeql-results.sarif \
  codeql/python-queries:codeql-suites/python-security-and-quality.qls
```

### Viewing Results

1. **GitHub Code Scanning** (Recommended)
   - Upload `codeql-results.sarif` to GitHub
   - View in Security tab → Code scanning alerts

2. **VS Code SARIF Viewer**
   - Install "SARIF Viewer" extension
   - Open `codeql-results.sarif`

3. **Command Line Summary**
   ```bash
   # Parse results (requires Python)
   python3 -c "
   import json
   data = json.load(open('codeql-results.sarif'))
   results = data['runs'][0]['results']
   print(f'Total findings: {len(results)}')
   "
   ```

## CI/CD Integration

CodeQL analysis runs automatically on:

- Every push to `main` or `develop` branches
- Every pull request
- Weekly scheduled runs (Mondays at 2 AM UTC)
- Manual trigger via `workflow_dispatch`

### Workflow File

Location: `.github/workflows/codeql-analysis.yml`

### Viewing CI Results

1. Go to GitHub repository
2. Click "Actions" tab
3. Select "CodeQL Security Analysis" workflow
4. View results in "Security" tab → "Code scanning alerts"

## Custom Queries

Custom queries are located in `.codeql/queries/`:

- `casa-security.ql` - Detects unsafe CASA task calls
- `hardcoded-paths.ql` - Detects hardcoded data paths

### Running Custom Queries

```bash
codeql database analyze codeql-db-python \
  --format=sarif-latest \
  --output=custom-results.sarif \
  .codeql/queries/
```

### Creating New Queries

1. Create `.ql` file in `.codeql/queries/`
2. Follow CodeQL query syntax
3. Add metadata header (name, description, tags)
4. Test locally before committing

## Configuration

Configuration file: `.codeql/codeql-config.yml`

### Excluded Paths

The following paths are excluded from analysis:

- `archive/` - Legacy code
- `node_modules/` - Dependencies
- `.venv/` - Virtual environment
- Test outputs and caches

### Query Filters

- Excluded: `py/unused-import`, `py/unused-local-variable` (too many false
  positives, handled by linters)
- Included: Custom queries from `.codeql/queries/`

## Common Issues and Fixes

### High Priority Security Issues

1. **Path Injection** (186 findings)
   - Fix: Validate and sanitize all path inputs
   - Use `os.path.join()` and validate paths

2. **Shell Command from Input** (153 findings)
   - Fix: Use parameterized commands
   - Avoid `shell=True` with user input
   - Use `subprocess` with argument lists

3. **Clear Text Logging** (99 findings)
   - Fix: Sanitize logs before writing
   - Use secure logging practices
   - Remove sensitive data from logs

### Code Quality Issues

1. **Unused Imports** (3,387 findings)
   - Fix: Remove unused imports
   - Use automated tools: `autoflake`, `isort`

2. **Empty Except Blocks** (541 findings)
   - Fix: Add proper error handling
   - Log exceptions appropriately

3. **File Not Closed** (105 findings)
   - Fix: Use context managers (`with` statements)
   - Ensure files are closed

## Best Practices

1. **Review Findings Regularly**
   - Check GitHub Security tab weekly
   - Address high-priority issues immediately

2. **Fix Before Merge**
   - Review CodeQL results in PRs
   - Fix or document exceptions for security findings

3. **Custom Queries**
   - Add project-specific patterns
   - Share useful queries with team

4. **Database Updates**
   - Recreate database after major refactoring
   - Keep database up to date with codebase

## Troubleshooting

### Database Creation Fails

**Error**: "Python 3.7 or later is required"

**Fix**:

```bash
export PATH="/opt/miniforge/envs/casa6/bin:$HOME/codeql:$PATH"
```

### Analysis Takes Too Long

**Solution**:

- Use `--threads=N` to limit CPU usage
- Run specific query suites instead of full suite
- Exclude large directories in `.codeql/codeql-config.yml`

### False Positives

**Solution**:

- Add exclusions to `.codeql/codeql-config.yml`
- Document exceptions in code comments
- Create custom queries for project-specific patterns

## Resources

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [CodeQL Query Writing](https://codeql.github.com/docs/writing-codeql-queries/)
- [GitHub Code Scanning](https://docs.github.com/en/code-security/code-scanning)
- [CodeQL Query Examples](https://github.com/github/codeql/tree/main/python/ql/src)

## Related Documentation

- `internal/docs/dev/status/2025-11/codeql_setup.md` - Initial setup
  instructions
- `internal/docs/dev/status/2025-11/codeql_results_summary.md` - Analysis
  results summary
- `.codeql/codeql-config.yml` - Configuration file
