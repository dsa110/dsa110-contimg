# GitHub Issues Quick Reference

## ✅ I Just Created 3 Example Issues

Check them out:

- **Issue #32**: Fix orphaned imports for pipeline.stages_impl (21 files)
- **Issue #33**: Fix orphaned imports for pipeline.config (11 files)
- **Issue #34**: Add tests for 184 untested modules

View at: https://github.com/dsa110/dsa110-contimg/issues

## 🏷️ Labels I Used

- `post-refactor` - Issues introduced during refactoring
- `bug` - Broken functionality (like orphaned imports)
- `high-priority` - Needs immediate attention
- `testing` - Related to test coverage
- `enhancement` - Improvements (like adding tests)

## 📝 Creating Issues Manually (GitHub Web UI)

### Method 1: GitHub Website

1. Go to: https://github.com/dsa110/dsa110-contimg/issues
2. Click **"New issue"** button
3. Fill in:
   - **Title**: Short, specific description
   - **Body**: Use the template below
4. Add **labels** from the sidebar
5. Click **"Submit new issue"**

### Method 2: Using GitHub CLI (if installed)

```bash
# Install GitHub CLI first (if needed)
# brew install gh  # or apt install gh

# Create an issue
gh issue create \
  --title "Fix import in api/routes.py" \
  --body "Line 42 references old_module which was moved" \
  --label "post-refactor,bug"

# List issues
gh issue list

# View an issue
gh issue view 32
```

## 📋 Issue Template (Copy & Paste)

```markdown
## Problem

[Brief description of what's broken or needed]

## Location

- File: `path/to/file.py`
- Line: 42

## Impact

[High/Medium/Low] - [Why it matters]

## Steps to Reproduce (for bugs)

1. Run command X
2. See error Y

## Investigation Needed (for unknowns)

1. Find where module was moved
2. Update imports
3. Test functionality

## Context

Introduced during [date] refactoring See [related issue #X] for more context

## Analysis Output (if applicable)
```

[Paste relevant output from audit tools]

```

## Definition of Done
- [ ] Code fixed
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Verified with audit tools
```

## 🎨 Recommended Labels for Your Project

### Priority

- `high-priority` - Fix ASAP
- `medium-priority` - Fix soon
- `low-priority` - Fix when you can

### Type

- `bug` - Something broken
- `enhancement` - New feature or improvement
- `documentation` - Docs update needed
- `testing` - Test-related

### Source

- `post-refactor` - Issues from refactoring
- `technical-debt` - Should fix but not urgent

### Status

- `needs-investigation` - Don't know the fix yet
- `ready-to-implement` - Know what to do
- `blocked` - Waiting on something else

### To Create Labels:

1. Go to: https://github.com/dsa110/dsa110-contimg/labels
2. Click **"New label"**
3. Enter name, description, and color
4. Click **"Create label"**

## 🔗 Using Issues with AI Agents

### Starting a conversation:

```
Help me with issue #32:
https://github.com/dsa110/dsa110-contimg/issues/32

Here's the AI context: [paste .ai-context.json]

I need to find where pipeline.stages_impl was moved to.
```

### Referencing issues in commits:

```bash
git commit -m "Fix orphaned import in api/routes.py

Fixes #32 - Updated import to use new module location"
```

### Linking issues together:

In issue body or comments:

```markdown
Related to #32 Blocks #34 Depends on #33
```

## 🤖 Creating Issues from Analysis Tools

### Option 1: Manual (Recommended for first batch)

1. Run analysis tool:

   ```bash
   python scripts/refactor_impact_analyzer.py \
     --root dsa110_contimg \
     --output /tmp/analysis.json
   ```

2. Review JSON output:

   ```bash
   python -m json.tool /tmp/analysis.json | less
   ```

3. Create one issue per problem group (e.g., one per orphaned module)

### Option 2: Automated (for bulk creation)

Create a script `scripts/create_issues_from_analysis.py`:

```python
#!/usr/bin/env python3
import json
import subprocess

# Load analysis
with open('/tmp/analysis.json') as f:
    data = json.load(f)

# Create issues for each orphaned import
for orphan in data['orphaned_imports'][:10]:  # First 10
    title = f"Fix orphaned import: {orphan['module']}"
    body = f"""## Problem
Module `{orphan['module']}` imported in {orphan['count']} files but doesn't exist.

## Files Affected
{chr(10).join(f'- {f}' for f in orphan['imported_by'])}

## Context
Post-refactoring cleanup
"""

    # Use gh CLI to create
    subprocess.run([
        'gh', 'issue', 'create',
        '--title', title,
        '--body', body,
        '--label', 'post-refactor,bug'
    ])
```

## 📊 Organizing Issues

### Use Projects (Kanban board)

1. Go to: https://github.com/dsa110/dsa110-contimg/projects
2. Click **"New project"**
3. Choose **"Board"** template
4. Create columns:
   - 📋 Backlog
   - 🔍 In Progress
   - ✅ Done
5. Drag issues between columns

### Use Milestones (for grouping)

1. Go to: https://github.com/dsa110/dsa110-contimg/milestones
2. Create milestone: "Post-Refactor Cleanup"
3. Add issues to milestone
4. Track progress

## 🚀 Workflow Example

### Daily workflow:

```bash
# 1. Check what needs work
gh issue list --label "high-priority"

# 2. Start working on issue #32
gh issue view 32

# 3. Create a branch
git checkout -b fix-issue-32

# 4. Make changes, commit
git commit -m "Fix orphaned imports (part of #32)"

# 5. Push and create PR
git push -u origin fix-issue-32
gh pr create --fill

# 6. In PR description, reference issue
# "Fixes #32"

# 7. When PR merged, issue auto-closes
```

## 💡 Pro Tips

1. **One issue = One problem** - Don't create mega-issues

2. **Use templates** - Copy the template above for consistency

3. **Link aggressively** - Connect related issues, PRs, commits

4. **Update regularly** - Add comments as you learn more

5. **Close when done** - Don't leave zombie issues open

6. **Search before creating** - Avoid duplicates:

   ```
   gh issue list --search "orphaned import"
   ```

7. **Batch similar work** - Fix all similar imports in one PR

8. **Use issue numbers everywhere**:
   - In commit messages: `"Fix #32"`
   - In PR descriptions: `"Closes #32, #33"`
   - In comments: `"Related to #32"`

## 📚 More Resources

- GitHub Issues Guide: https://docs.github.com/en/issues
- GitHub CLI Manual: https://cli.github.com/manual/
- Labels Best Practices:
  https://medium.com/@dave_lunny/sane-github-labels-c5d2e6004b63
