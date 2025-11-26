# Post-Refactoring Analysis Tools

These tools help manage and understand a refactored codebase by identifying
issues, tracking changes, and maintaining context for AI assistants.

## 🛠️ Tools

### 1. `audit_documentation.py` - Documentation Audit

**Purpose:** Find outdated, incorrect, or broken documentation after
refactoring.

**What it detects:**

- Broken file references in markdown docs
- Stale date references (>6 months old)
- Outdated code examples with non-existent imports
- Documentation markers (TODO, FIXME, DEPRECATED)

**Usage:**

```bash
# Run from project root
./scripts/audit_documentation.py --root /data/dsa110-contimg/backend/src --output doc_audit.json

# Or with default settings
python scripts/audit_documentation.py
```

**Output:**

- Console summary showing high/medium/low priority issues
- JSON report with detailed findings and line numbers

**When to use:**

- After major refactoring
- Before releasing documentation updates
- Monthly as part of maintenance

---

### 2. `refactor_impact_analyzer.py` - Refactoring Impact Analysis

**Purpose:** Identify broken imports and test coverage gaps after restructuring
code.

**What it finds:**

- Orphaned imports (imports of moved/deleted modules)
- Files without corresponding tests
- Import dependency graph
- High-priority untested modules

**Usage:**

```bash
# Run for entire package
./scripts/refactor_impact_analyzer.py --root /data/dsa110-contimg/backend/src/dsa110_contimg --output refactor.json

# Or with defaults
python scripts/refactor_impact_analyzer.py
```

**Output:**

- List of broken imports with usage locations
- Untested modules ranked by priority
- JSON report with full dependency graph

**When to use:**

- Immediately after refactoring
- Before merging refactoring PRs
- To identify critical modules needing tests

---

### 3. `generate_ai_context.py` - AI Context Generator

**Purpose:** Create context files that help AI agents understand your codebase
structure and recent changes.

**What it generates:**

- Project structure overview
- Recent git commits (last 14 days)
- Most frequently imported modules
- Coding conventions detected in codebase
- Both JSON and Markdown formats

**Usage:**

```bash
# Generate context files
./scripts/generate_ai_context.py --root /data/dsa110-contimg/backend/src --output .ai-context.json

# Or with defaults
python scripts/generate_ai_context.py
```

**Output:**

- `.ai-context.json` - Machine-readable context for AI tools
- `.ai-context.md` - Human-readable summary

**When to use:**

- Weekly or after significant changes
- Before starting AI-assisted debugging sessions
- When onboarding new AI agents to your codebase

**How AI agents should use it:**

- Load `.ai-context.json` at conversation start
- Reference recent changes to understand current state
- Follow detected conventions when generating code

---

## 🔄 Recommended Workflow

### After Major Refactoring:

1. **Run Impact Analyzer** to find broken imports

   ```bash
   python scripts/refactor_impact_analyzer.py
   ```

2. **Fix Orphaned Imports** based on the report

3. **Run Documentation Audit** to update docs

   ```bash
   python scripts/audit_documentation.py
   ```

4. **Generate AI Context** for ongoing work

   ```bash
   python scripts/generate_ai_context.py
   ```

5. **Create GitHub Issues** for remaining items (see below)

### Weekly Maintenance:

```bash
# Quick health check
python scripts/refactor_impact_analyzer.py && \
python scripts/audit_documentation.py && \
python scripts/generate_ai_context.py
```

---

## 🎯 Integration with GitHub Issues

For best results, use these tools with **GitHub Issues** to track problems:

### Example Workflow:

```bash
# 1. Generate reports
python scripts/refactor_impact_analyzer.py --output refactor.json
python scripts/audit_documentation.py --output docs.json

# 2. Create issues from reports (manual or scripted)
#    - One issue per orphaned import cluster
#    - One issue per high-priority untested module
#    - One issue per broken documentation section

# 3. Use .ai-context.json when AI agents work on issues
#    - Paste content at start of conversation
#    - Or store in GitHub issue template
```

### GitHub Issue Template Example:

```markdown
## Context

- See [AI Context](.ai-context.md) for project structure
- Related to refactoring on [date]

## Issue

[From audit tool output]

## Files Affected

[From tool report]

## Definition of Done

- [ ] Code updated
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Re-run audit tools to verify fix
```

---

## 📊 Example Output

### Refactor Impact Analyzer:

```
🔴 Orphaned Imports: 12
   • dsa110_contimg.old_module.utils (used in 5 files)
     - dsa110_contimg/api/routes.py
     - dsa110_contimg/imaging/pipeline.py
     ...

🧪 Files Without Tests: 23
   High Priority: 8
   • dsa110_contimg/api/job_runner.py (12 funcs, 3 classes)
   • dsa110_contimg/calibration/apply_service.py (8 funcs, 2 classes)
```

### Documentation Auditor:

```
🔴 High Priority Issues: 8
   • docs/api/README.md:42 - Referenced file not found: "dsa110_contimg/old_api.py"
   • docs/setup.md:15 - Code example imports non-existent module: dsa110_contimg.legacy

🟡 Medium Priority Issues: 15
   • docs/architecture.md:5 - Documentation date is 412 days old: "2024-01-15"
```

---

## 🚀 Advanced Usage

### Custom Migration Mapping

If you have a specific old→new module mapping:

```python
# create_migration_map.py
from scripts.refactor_impact_analyzer import RefactorAnalyzer

analyzer = RefactorAnalyzer('/data/dsa110-contimg/backend/src/dsa110_contimg')
analyzer.scan()

migration_map = {
    'dsa110_contimg.old_module': 'dsa110_contimg.new_module',
    'dsa110_contimg.legacy.utils': 'dsa110_contimg.utils.helpers',
}

tasks = analyzer.generate_migration_map(migration_map)
print(f"Need to update {tasks['total_tasks']} locations")
```

### Integrate with CI/CD

```yaml
# .github/workflows/doc-audit.yml
name: Documentation Audit

on: [pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Documentation Audit
        run: |
          python scripts/audit_documentation.py
          # Fail if high-priority issues found
          python -c "import json; data=json.load(open('documentation_audit.json')); exit(len([i for i in data['issues'] if i.get('severity')=='high']))"
```

---

## 💡 Tips for Working with AI Agents

1. **Share `.ai-context.json` at conversation start**
   - Paste the JSON into your prompt
   - Or reference specific sections

2. **Create focused issues**
   - One issue = one problem
   - Include context and affected files
   - Link related issues

3. **Update context regularly**
   - Run `generate_ai_context.py` weekly
   - Always run after merging major changes

4. **Use issue labels**
   - `post-refactor`: Issues from refactoring
   - `docs-outdated`: Documentation needs update
   - `needs-tests`: Missing test coverage

5. **Maintain a refactoring log**
   - Create `REFACTORING_LOG.md` with what changed
   - Reference it in `.ai-context.md`

---

## 📚 Additional Resources

### Related Scripts in `scripts/ops/`:

- `migrate_to_new_structure.py` - Migration automation
- `verify_migration.py` - Verify migration completeness
- `python_environment_audit.py` - Check Python environment

### Documentation:

- [Main docs](../../../../docs/README.md)
- [Operations guide](../../../../docs/operations/)
- [Reports](../../../../docs/reports/)

---

## 🐛 Troubleshooting

**Import errors after running analyzer:**

- The analyzer only reports issues, doesn't fix them
- Use the JSON output to create a fixing script

**Too many low-priority issues:**

- Focus on `high` and `medium` severity first
- Use `--severity high` flag (if implemented)

**Git history not available:**

- Ensure you're in a git repository
- Context generator will skip git info if unavailable

---

## 🤝 Contributing

To add new analysis features:

1. Follow existing tool structure
2. Output JSON reports for automation
3. Provide both summary and detailed output
4. Document in this README
