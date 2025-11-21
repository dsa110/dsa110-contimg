# Viewing CodeQL Results with SARIF Viewers

## Available SARIF Files

- `codeql-results.sarif` (11 MB) - Full security and quality analysis
- `custom-results.sarif` (if generated) - Custom query results

## Using SARIF Viewer (VS Code Extension)

### Opening Results

1. **Open SARIF file directly**:
   - In VS Code: `File → Open File → codeql-results.sarif`
   - Or use command palette: `Ctrl+Shift+P` → "SARIF: Open SARIF file"

2. **View Results**:
   - Results appear in the "SARIF" panel (bottom panel)
   - Browse by file, rule, or severity
   - Click on findings to jump to source code

### Features

- **Filter by severity**: Error, Warning, Note
- **Filter by rule**: e.g., `py/path-injection`,
  `py/shell-command-constructed-from-input`
- **Group by file**: See all issues in a specific file
- **Navigate to code**: Click finding to jump to line

### Keyboard Shortcuts

- `Ctrl+Shift+P` → "SARIF: Focus on SARIF View"
- Use arrow keys to navigate findings
- `Enter` to jump to code location

## Using SARIF Explorer

### Opening Results

1. **Command Line**:

   ```bash
   # If SARIF Explorer has CLI
   sarif-explorer codeql-results.sarif
   ```

2. **VS Code Integration**:
   - SARIF Explorer may integrate with VS Code
   - Check extension documentation for specific commands

### Features

- Interactive exploration of results
- Advanced filtering and search
- Export capabilities
- Comparison between runs

## Quick Analysis Commands

### Count Findings by Rule

```bash
cd /data/dsa110-contimg
python3 -c "
import json
data = json.load(open('codeql-results.sarif'))
results = data['runs'][0]['results']
rules = {}
for r in results:
    rule = r.get('ruleId', 'unknown')
    rules[rule] = rules.get(rule, 0) + 1

print('Top 10 rules by finding count:')
for rule, count in sorted(rules.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f'  {rule}: {count}')
"
```

### Find Issues in Specific File

```bash
cd /data/dsa110-contimg
python3 -c "
import json
data = json.load(open('codeql-results.sarif'))
results = data['runs'][0]['results']

# Find issues in routes.py
file_issues = [r for r in results if 'api/routes.py' in r.get('locations', [{}])[0].get('physicalLocation', {}).get('artifactLocation', {}).get('uri', '')]

print(f'Issues in routes.py: {len(file_issues)}')
for r in file_issues[:5]:
    rule = r.get('ruleId', 'unknown')
    region = r.get('locations', [{}])[0].get('physicalLocation', {}).get('region', {})
    line = region.get('startLine', '?')
    print(f'  Line {line}: {rule}')
"
```

### Export High Priority Issues

```bash
cd /data/dsa110-contimg
python3 -c "
import json
data = json.load(open('codeql-results.sarif'))
results = data['runs'][0]['results']

# Filter high priority security issues
high_priority = [r for r in results if r.get('ruleId') in [
    'py/path-injection',
    'py/shell-command-constructed-from-input',
    'py/clear-text-logging-sensitive-data'
]]

# Create filtered SARIF
filtered_sarif = {
    'version': data['version'],
    '$schema': data.get('$schema'),
    'runs': [{
        'tool': data['runs'][0]['tool'],
        'results': high_priority
    }]
}

with open('codeql-results-high-priority.sarif', 'w') as f:
    json.dump(filtered_sarif, f, indent=2)

print(f'Exported {len(high_priority)} high-priority issues to codeql-results-high-priority.sarif')
"
```

## Viewing in GitHub

### Upload to GitHub Code Scanning

1. **Via GitHub UI**:
   - Go to repository → Security tab → Code scanning
   - Click "Upload SARIF"
   - Select `codeql-results.sarif`
   - View results in Security tab

2. **Via GitHub CLI**:
   ```bash
   gh api repos/:owner/:repo/code-scanning/sarifs \
     -X POST \
     -f commit_sha=$(git rev-parse HEAD) \
     -f ref=$(git rev-parse --abbrev-ref HEAD) \
     -f sarif=@codeql-results.sarif
   ```

### Viewing Results

- **Security Tab**: Repository → Security → Code scanning alerts
- **Filter by severity**: Error, Warning
- **Filter by rule**: Click on rule name
- **View in context**: Click finding to see code

## Best Practices

1. **Start with High Priority**:
   - Filter to `py/path-injection`, `py/shell-command-constructed-from-input`
   - Focus on `src/` directory (exclude `archive/`)

2. **Group by File**:
   - Fix all issues in one file before moving to next
   - Start with files with most issues

3. **Verify Fixes**:
   - Re-run CodeQL after fixes
   - Compare before/after SARIF files
   - Verify issue count decreases

4. **Document Exceptions**:
   - If a finding is a false positive, document it
   - Add comments in code explaining why it's safe

## Troubleshooting

### SARIF Viewer Not Showing Results

1. Check file is valid JSON:

   ```bash
   python3 -m json.tool codeql-results.sarif > /dev/null && echo "Valid JSON"
   ```

2. Reload VS Code window:
   - `Ctrl+Shift+P` → "Developer: Reload Window"

3. Check extension is enabled:
   - Extensions → Search "SARIF" → Verify enabled

### Large Files

If SARIF file is too large:

- Use filtered export (see above)
- Focus on specific query suites
- Use command-line tools for analysis

## Related Documentation

- `internal/docs/dev/status/2025-11/codeql_results_summary.md` - Analysis
  summary
- `docs/how-to/fixing_codeql_security_issues.md` - How to fix issues
- `docs/how-to/codeql_setup_and_usage.md` - CodeQL usage guide
