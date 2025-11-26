# Contributing to TODO.md

## Overview

`TODO.md` is a living document that tracks tasks, improvements, and next steps for the DSA-110 Continuum Imaging Pipeline. It's designed to be modified by multiple agents and maintainers over time.

**🔗 Linear Integration:** TODO items can be synced to Linear issues. See `docs/LINEAR_INTEGRATION.md` for details.

## ⚡ Automatic Date Updates

**IMPORTANT:** The date in `TODO.md` is automatically updated! You don't need to manually change it.

### How It Works

1. **Git Hook (Automatic):** When you commit changes to `TODO.md`, a pre-commit hook automatically updates the date to today
2. **Manual Update:** Run `make update-todo-date` or `python3 scripts/update_todo_date.py` to update the date manually
3. **No Manual Edits Needed:** The date line follows the pattern `**Last Updated:** YYYY-MM-DD` and will be automatically updated

### Requirements

- **Git Hook:** Automatically runs on commit (if git repo and hooks are enabled)
- **Makefile:** `make update-todo-date` (requires Python 3)
- **Script:** `scripts/update_todo_date.py` (can be run directly)

### If Date Doesn't Update Automatically

If the git hook doesn't run (e.g., in CI/CD or non-git environments):
- Run `make update-todo-date` before committing
- Or run `python3 scripts/update_todo_date.py` directly

---

## Quick Reference

### Adding a New Item

1. **Find the right section** (High/Medium/Low priority)
2. **Use this format:**
   ```markdown
   - [ ] **Item Title** (time estimate)
     - [ ] Subtask 1
     - [ ] Subtask 2
   ```
3. **Add context if needed:**
   - Time estimate: `(2-4 hours)` or `(30 minutes)`
   - Reference: `See: docs/file.md` or `(from source.md)`
   - Related files: `Related: path/to/file.py`
4. **Update the "Last Updated" date** at the top

### Marking an Item Complete

1. **Change the checkbox:**
   ```markdown
   - [x] **Item Title** (2025-01-27)
   ```

2. **Optionally move to "Recently Completed"** section:
   - Copy the completed item
   - Paste in appropriate subsection of "Recently Completed"
   - Remove from original location

3. **Update "Last Updated" date**

### Removing an Item

- **Don't delete** - move to "Recently Completed" if done
- **Only delete** if:
  - Item is duplicate
  - Item is no longer relevant (add note in changelog)
  - Item is superseded by another item

### Updating the Changelog

When making significant changes:
```markdown
- **YYYY-MM-DD:** Brief description of changes
  - Added/Modified/Removed items
  - Any important context
```

---

## Formatting Standards

### Priority Indicators
- 🔴 **High Priority** - Critical or blocking issues
- 🟡 **Medium Priority** - Important but not urgent
- 🟢 **Low Priority** - Nice to have, can wait

### Checkbox Format
- `- [ ]` - Unchecked (todo)
- `- [x]` - Checked (done)

### Time Estimates
- Use consistent format: `(X-Y hours)` or `(X minutes)`
- Include time estimates when known
- Helps prioritize work

### References
- **Documentation:** `See: docs/path/to/file.md`
- **Source:** `(from source.md)` or `(from docs/reports/file.md)`
- **Related files:** `Related: path/to/file.py`

### Completion Dates
- Format: `(YYYY-MM-DD)`
- Example: `(2025-01-27)`

---

## Best Practices

### For Agents

1. **Be specific** - Clear, actionable items are better than vague ones
2. **Group related items** - Keep similar tasks together
3. **Add context** - Include file paths, function names, or related docs
4. **Estimate time** - Helps with prioritization
5. **Update dates** - Always update "Last Updated" when modifying
6. **Check duplicates** - Search before adding new items

### For Maintainers

1. **Review regularly** - Keep the list current
2. **Archive completed items** - Move to "Recently Completed"
3. **Clean up** - Remove obsolete items periodically
4. **Prioritize** - Reorder items based on current needs
5. **Document changes** - Use changelog for significant updates

### Avoiding Conflicts

1. **One change per edit** - Focused edits reduce merge conflicts
2. **Use descriptive commit messages** - "Add TODO item for X" not "Update TODO"
3. **Check before adding** - Search for similar items first
4. **Group related changes** - Add multiple related items in one edit

---

## Example Workflows

### Adding a New Feature TODO

```markdown
## 🟡 Medium Priority

### New Feature (4-6 hours)
- [ ] **Implement Feature X**
  - [ ] Design API interface
  - [ ] Implement core logic in `src/module/file.py`
  - [ ] Add unit tests in `tests/test_file.py`
  - [ ] Update documentation
  - [ ] See: docs/design/feature_x.md
```

### Completing an Item

**Before:**
```markdown
- [ ] **Fix bug in calibration CLI**
```

**After (in original location):**
```markdown
- [x] **Fix bug in calibration CLI** (2025-01-27)
```

**Or move to Recently Completed:**
```markdown
### Bug Fixes (2025-01-27)
- [x] **Fix bug in calibration CLI**
```

### Updating Changelog

```markdown
## 📝 Changelog

- **2025-01-27:** Initial TODO list created with integration work next steps
- **2025-01-28:** Added feature X TODO items (4-6 hours)
  - Added API design tasks
  - Added implementation tasks
  - Added testing tasks
```

---

## Common Patterns

### Feature Development
```markdown
- [ ] **Feature Name** (time estimate)
  - [ ] Design/Planning
  - [ ] Implementation
  - [ ] Testing
  - [ ] Documentation
  - [ ] See: docs/design/feature.md
```

### Bug Fix
```markdown
- [ ] **Fix: Brief description** (time estimate)
  - [ ] Identify root cause
  - [ ] Implement fix in `path/to/file.py`
  - [ ] Add regression test
  - [ ] Verify fix works
```

### Optimization
```markdown
- [ ] **Optimize: Component/Operation** (time estimate)
  - [ ] Profile current implementation
  - [ ] Identify bottlenecks
  - [ ] Implement optimization
  - [ ] Benchmark improvement
  - [ ] Reference: `docs/optimizations/guide.md`
```

### Documentation
```markdown
- [ ] **Document: Topic** (time estimate)
  - [ ] Create/update `docs/path/to/file.md`
  - [ ] Add examples
  - [ ] Link from related docs
```

---

## Troubleshooting

### Merge Conflicts

If you encounter merge conflicts:
1. **Resolve by priority** - Keep the most recent/complete version
2. **Preserve both changes** - If both are valid, combine them
3. **Update changelog** - Note the conflict resolution

### Duplicate Items

If you find duplicates:
1. **Merge similar items** - Combine into one comprehensive item
2. **Keep the more detailed version** - Remove the simpler duplicate
3. **Update changelog** - Note the merge

### Outdated Items

If an item is no longer relevant:
1. **Move to changelog** - Add a note about why it's obsolete
2. **Remove from list** - Or mark as `[x]` with note "(obsolete)"
3. **Update date** - Keep "Last Updated" current

---

## Questions?

- **Formatting:** See examples in this guide
- **Priority:** Use best judgment, can be reorganized later
- **Time estimates:** Include when known, approximate is fine
- **Completing items:** Always move to "Recently Completed" section

---

## Summary

**Remember:**
- ✅ Use consistent formatting
- ✅ Update "Last Updated" date
- ✅ Add context and references
- ✅ Move completed items to "Recently Completed"
- ✅ Document significant changes in changelog
- ✅ Keep items specific and actionable

The goal is to make `TODO.md` easy to read, update, and maintain for everyone!

