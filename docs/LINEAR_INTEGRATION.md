# Linear Integration for TODO.md

This document describes how to sync TODO.md items with Linear issues.

---

## Overview

The Linear integration allows you to:
- **Sync TODO items to Linear** - Automatically create Linear issues from TODO.md items
- **Track issues** - Link TODO items to Linear issues using issue IDs
- **Bi-directional sync** - Keep TODO.md and Linear in sync

---

## Setup

### 1. Get Linear API Key

1. Go to Linear Settings → API → Personal API keys
2. Create a new API key
3. Copy the API key (it starts with `lin_api_`)

### 2. Get Your Team Key

1. In Linear, go to your team/workspace
2. The team key is usually a short identifier like `ENG`, `PROD`, `DEV`, etc.
3. You can find it in the team URL or settings

### 3. Create Configuration File

```bash
# Copy the example config
cp .linear_config.json.example .linear_config.json

# Edit with your credentials
nano .linear_config.json
```

Your `.linear_config.json` should look like:
```json
{
  "api_key": "lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "team_key": "ENG"
}
```

**Important:** The `.linear_config.json` file is in `.gitignore` and will not be committed to the repository.

---

## Usage

### Sync TODO.md to Linear

**Dry run (see what would be created):**
```bash
make sync-linear-dry-run
# or
python3 scripts/linear_sync.py --dry-run
```

**Actual sync:**
```bash
make sync-linear
# or
python3 scripts/linear_sync.py
```

**Sync all items (including completed):**
```bash
python3 scripts/linear_sync.py --all
```

### How It Works

1. **Parses TODO.md** - Extracts all unchecked TODO items
2. **Creates Linear issues** - One issue per TODO item
3. **Links back to TODO.md** - Adds Linear issue ID to TODO item
4. **Priority mapping:**
   - 🔴 High Priority → Linear Priority 0 (Urgent)
   - 🟡 Medium Priority → Linear Priority 1 (High)
   - 🟢 Low Priority → Linear Priority 2 (Medium)
   - 📋 Separate Projects → Linear Priority 3 (Low)

### Example

**Before sync:**
```markdown
- [ ] **Fix bug in calibration CLI**
```

**After sync:**
```markdown
- [ ] **Fix bug in calibration CLI** (Linear: ENG-123)
```

The Linear issue will be created with:
- **Title:** "Fix bug in calibration CLI"
- **Description:** Section name, time estimate, and source reference
- **Priority:** Based on TODO section
- **Team:** Your configured team

---

## Features

### Automatic Issue Creation
- Unchecked TODO items are automatically created as Linear issues
- Each issue includes context from TODO.md (section, time estimate)

### Issue Linking
- Linear issue IDs are automatically added to TODO items
- Format: `(Linear: ENG-123)`
- Allows bi-directional tracking

### Priority Mapping
- TODO.md priority sections map to Linear priorities
- Ensures important items are flagged correctly

### Time Estimates
- Time estimates from TODO.md are included in Linear issue descriptions
- Helps with planning and prioritization

---

## Workflow

### Initial Sync
1. Set up `.linear_config.json` with your API key and team
2. Run `make sync-linear-dry-run` to preview changes
3. Run `make sync-linear` to create issues
4. TODO.md will be updated with Linear issue IDs

### Ongoing Sync
1. Add new items to TODO.md
2. Run `make sync-linear` periodically
3. New items will be created as Linear issues
4. Existing items (with Linear IDs) will be updated

### Manual Updates
- Update TODO items in Linear (title, description, status)
- Run sync to update TODO.md (if you add reverse sync later)
- Or manually update TODO.md and run sync

---

## Troubleshooting

### "Config file not found"
- Ensure `.linear_config.json` exists in project root
- Copy from `.linear_config.json.example` if needed

### "Team not found"
- Check your team key is correct
- Team key is case-sensitive
- Verify team exists in your Linear workspace

### "API authentication failed"
- Verify your API key is correct
- Ensure API key hasn't expired
- Check API key has necessary permissions

### "Failed to create issue"
- Check team permissions
- Verify Linear API is accessible
- Check rate limits (Linear has rate limiting)

### Issues not linking back
- Check file permissions on TODO.md
- Ensure script has write access
- Verify TODO.md format matches expected pattern

---

## API Requirements

### Dependencies
```bash
pip install requests
```

### Linear API Permissions
Your API key needs permissions to:
- Read teams
- Create issues
- Update issues
- Read issues

---

## Advanced Usage

### Custom Priority Mapping
Edit `scripts/linear_sync.py` to customize priority mapping:
```python
# In parse_items() method
if '## 🔴 High Priority' in line:
    current_priority = 0  # Linear priority 0 = Urgent
```

### Custom Issue States
Add state mapping to create issues in specific states:
```python
# In create_issue() method
if state_id:
    input_data["stateId"] = state_id
```

### Filter by Section
Modify the script to sync only specific sections:
```python
# Only sync high priority items
items = [item for item in items if item['priority'] == 0]
```

---

## Limitations

- **One-way sync (TODO → Linear):** Currently syncs TODO.md to Linear, not reverse
- **No automatic updates:** Changes in Linear don't automatically update TODO.md
- **Manual linking:** Completed items need to be marked manually
- **No conflict resolution:** If both TODO.md and Linear are edited, manual sync needed

---

## Future Enhancements

Potential improvements:
- [ ] Bi-directional sync (Linear → TODO.md)
- [ ] Automatic status updates (completed in Linear → checked in TODO.md)
- [ ] Conflict resolution
- [ ] Webhook integration for real-time updates
- [ ] Support for subtasks/checklists
- [ ] Label/project mapping

---

## Related Documentation

- [Linear API Documentation](https://linear.app/developers/graphql)
- [Linear GraphQL Schema](https://linear.app/developers/api-reference)
- `docs/CONTRIBUTING_TODO.md` - How to modify TODO.md
- `scripts/linear_sync.py` - Sync script source code

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review Linear API documentation
3. Check script logs for detailed error messages
4. Verify configuration file format

