# Managing a Large Refactored Codebase

## :direct_hit: Your Situation

You have a **large scientific codebase** that was recently refactored, with:

- Outdated documentation scattered throughout
- AI agents losing context due to size
- Hard to track what broke during refactoring

## :white_heavy_check_mark: Recommended Approach

### 1. **Use GitHub Issues as Your Source of Truth** (BEST SOLUTION)

This is the most effective way to manage post-refactoring chaos:

**Why it works:**

- :white_heavy_check_mark: Each issue maintains **persistent context** that AI agents can reference
- :white_heavy_check_mark: **No size limits** - full conversation history preserved
- :white_heavy_check_mark: **Link related issues** - track dependencies between fixes
- :white_heavy_check_mark: **GitHub Copilot can work on entire issues** with full codebase access
- :white_heavy_check_mark: **Team visibility** - everyone sees what's broken and being fixed

**Setup:**

```bash
# 1. Initialize if not already a git repo
cd /data/dsa110-contimg
git init  # (skip if already done)

# 2. Create a GitHub repo (if you haven't)
# Use GitHub UI or CLI

# 3. Use labels to organize
# - post-refactor-bug
# - docs-outdated
# - needs-tests
# - orphaned-import
```

**Workflow:**

1. Create one issue per problem (not mega-issues)
2. Include specific file paths and line numbers
3. Tag with appropriate labels
4. When asking AI for help, reference the issue number
5. Link related issues together
6. Close when verified fixed

### 2. **Analysis Tools** (in `src/dsa110_contimg/scripts/ops/`)

I've created 3 tools to help identify problems:

#### `audit_documentation.py` - Find outdated docs

```bash
# Scope to specific directories to avoid scanning everything
python -m dsa110_contimg.scripts.ops.audit_documentation \
  --root /data/dsa110-contimg/backend/docs \
  --output doc_audit.json

# For just your main documentation
python scripts/audit_documentation.py \
  --root /data/dsa110-contimg/backend/src/dsa110_contimg \
  --output doc_audit.json
```

#### `refactor_impact_analyzer.py` - Find broken imports

```bash
# Run on your main package only (not entire parent dir)
python scripts/refactor_impact_analyzer.py \
  --root /data/dsa110-contimg/backend/src/dsa110_contimg \
  --output refactor.json
```

#### `generate_ai_context.py` - Help AI agents understand your code

```bash
# Generate context for just your package
python scripts/generate_ai_context.py \
  --root /data/dsa110-contimg/backend/src/dsa110_contimg \
  --output .ai-context.json
```

**:warning: Important:** Don't run these on the massive parent directory - scope to:

- `backend/src/dsa110_contimg/` for code analysis
- `backend/docs/` for doc audits

### 3. **Create a Refactoring Tracking Document**

Create a simple `REFACTORING_STATUS.md` at the project root:

```markdown
# Refactoring Status

## What Changed

- [ ] Module X moved from A to B
- [ ] Function Y renamed to Z
- [ ] Class W refactored into multiple classes

## Known Issues

See GitHub Issues with label `post-refactor-bug`

## Migration Guide

- Old import: `from dsa110_contimg.old.module import X`
- New import: `from dsa110_contimg.new.module import X`

## Status

- [ ] All orphaned imports fixed
- [ ] Documentation updated
- [ ] Tests passing
- [ ] AI context file updated
```

This gives AI agents a quick overview without analyzing everything.

### 4. **Efficient AI Agent Usage**

**Instead of:** "Fix all the problems in my codebase"

**Do this:**

1. Run targeted analysis:

   ```bash
   python scripts/refactor_impact_analyzer.py \
     --root /data/dsa110-contimg/backend/src/dsa110_contimg \
     --output /tmp/analysis.json
   ```

2. Create specific GitHub issues from results:
   - Issue #1: "Fix orphaned import in api/routes.py line 42"
   - Issue #2: "Add tests for calibration/apply_service.py"
   - Issue #3: "Update docs/api/README.md broken links"

3. Work on ONE issue at a time with AI:

   ```
   "Help me fix Issue #1: the import at api/routes.py:42
   references old_module which was moved to new_module"
   ```

4. Paste `.ai-context.json` into conversation for context:
   ```
   "Here's the project context: [paste .ai-context.json]
   Now help me with Issue #1..."
   ```

## :rocket: Quick Start (Next Steps)

1. **Right now:** Create a GitHub repo if you don't have one

2. **Run focused analysis:**

   ```bash
   cd /data/dsa110-contimg/backend/src

   # Find broken imports in your code
   python scripts/refactor_impact_analyzer.py \
     --root dsa110_contimg \
     --output /tmp/refactor.json

   # Check just the docs folder
   python scripts/audit_documentation.py \
     --root dsa110_contimg/docs \
     --output /tmp/docs.json
   ```

3. **Review the JSON output** (it's in `/tmp/`)
   - Look at high-priority issues first
   - Group similar issues together

4. **Create 5-10 GitHub issues** from the most critical problems

5. **Generate AI context** for future conversations:

   ```bash
   python scripts/generate_ai_context.py \
     --root dsa110_contimg \
     --output .ai-context.json
   ```

6. **Start fixing issues one by one** with AI help

## :electric_light_bulb: Pro Tips

### For Large Codebases:

1. **Divide and conquer** - Don't analyze everything at once
   - Focus on one module/package at a time
   - Use `--root` flag to scope analysis

2. **Prioritize** - Fix in this order:
   1. Broken imports that prevent code from running
   2. Missing tests for critical modules
   3. High-traffic documentation that's outdated
   4. Low-priority doc cleanup

3. **Use issue templates** for consistency:

   ```markdown
   ## Problem

   [One-line description]

   ## Location

   File: path/to/file.py Line: 42

   ## Context

   Introduced during [date] refactoring

   ## Fix

   [Specific change needed]
   ```

4. **Batch similar fixes** - Fix all similar imports in one PR

5. **Update context regularly**:
   ```bash
   # After fixing 5-10 issues, regenerate
   python scripts/generate_ai_context.py
   ```

### Working with AI Agents:

- :white_heavy_check_mark: **Do:** Provide specific file paths and line numbers
- :white_heavy_check_mark: **Do:** Share `.ai-context.json` at conversation start
- :white_heavy_check_mark: **Do:** Reference GitHub issue numbers for context
- :white_heavy_check_mark: **Do:** Work on one focused problem per conversation
- :cross_mark: **Don't:** Ask AI to "fix everything"
- :cross_mark: **Don't:** Give vague descriptions like "update the docs"
- :cross_mark: **Don't:** Try to fix 10 different things in one session

## :books: Tools Documentation

See `scripts/REFACTORING_TOOLS.md` for detailed tool documentation.

## 🆘 If You're Overwhelmed

Start with just these 3 things:

1. **Create 3 GitHub issues** for the 3 most critical problems
2. **Run:** `python scripts/refactor_impact_analyzer.py --root dsa110_contimg`
3. **Fix the top orphaned import** from the report

Then repeat. Progress over perfection!
