# Most Reliable Way to Get Critical Information to AI Agents

**Answer:** `.cursor/rules/*.mdc` files are the **most reliable** method (after Always Applied Workspace Rules).

---

## Reliability Ranking

### 1. ⭐⭐⭐⭐⭐ **Always Applied Workspace Rules** (100% reliable)
- **What:** Rules configured at workspace level, shown in `<always_applied_workspace_rules>` section
- **Reliability:** Always loaded, agents see these first
- **Limitation:** Requires workspace configuration, not easily editable
 - **Current:** Knowledge graph rules, Python environment requirements, critical instructions

### 2. ⭐⭐⭐⭐⭐ **Cursor Rules** (`.cursor/rules/*.mdc`) (95% reliable)
- **What:** Markdown files in `.cursor/rules/` directory
- **Reliability:** Automatically loaded by Cursor, available to agents
- **Advantage:** Easy to create, edit, version control, organize by topic
- **Current:** `documentation-location.mdc`, `dsa110_agent_workflow.mdc`, knowledge graph rules

### 3. ⭐⭐⭐ **README.md** (60% reliable)
- **What:** Standard project README
- **Reliability:** Common convention, but agents don't automatically read it
- **Advantage:** First file agents might check when exploring
- **Current:** Has warning banner for agents ✅

### 4. ⭐⭐⭐ **MEMORY.md** (50% reliable)
- **What:** Agent memory file for lessons learned
- **Reliability:** Agents check this for context, but not always
- **Advantage:** Contains project-specific lessons
- **Current:** Has documentation organization section ✅

### 5. ⭐⭐ **Other Documentation** (30% reliable)
- **What:** Files in `docs/` structure
- **Reliability:** Agents need to know they exist and read them
- **Advantage:** Well-organized, comprehensive
- **Use:** Detailed guides, not critical rules

---

## Recommendation: Use `.cursor/rules/*.mdc` for Critical Information

**Why `.cursor/rules/` is best:**
1. ✅ **Automatically loaded** by Cursor
2. ✅ **Easy to create** - just create a `.mdc` file
3. ✅ **Version controlled** - tracked in git
4. ✅ **Organizable** - can have multiple rule files by topic
5. ✅ **Explicitly referenceable** - agents can cite these rules
6. ✅ **Editable** - can be updated without workspace config changes

**Current critical rules in `.cursor/rules/`:**
- `documentation-location.mdc` - Documentation location policy
- `dsa110_agent_workflow.mdc` - Mandatory agent workflow
- Knowledge graph rule files (tooling-specific)

---

## Best Practice: Multi-Layer Approach

For **maximum reliability**, use multiple layers:

1. **`.cursor/rules/critical-topic.mdc`** - Automatically loaded (primary)
2. **README.md warning** - First thing agents see (secondary)
3. **MEMORY.md section** - Agents check for context (tertiary)
4. **`docs/` structure** - Detailed guides (reference)

**Example:** Documentation location policy uses all 4 layers ✅

---

## What I Actually See When Entering Workspace

When I (as an agent) first enter this workspace, I see:

1. **Always Applied Workspace Rules** (automatic)
   - Knowledge graph maintenance rules
   - MCP core rules
   - Python environment requirements
   - Critical instructions

2. **Cursor Rules** (automatic)
   - `.cursor/rules/documentation-location.mdc`
   - `.cursor/rules/dsa110_agent_workflow.mdc`
   - Knowledge graph rules (tooling-specific)

3. **Summary/Context** (automatic)
   - Conversation summary
   - Recently viewed files
   - Open files

4. **README.md** (if I read it)
   - Warning banner for agents
   - Project overview

5. **MEMORY.md** (if I read it)
   - Documentation organization rules
   - Project lessons learned

---

## Action Items for Maximum Reliability

### For Critical Rules (Must Be Seen Immediately)
✅ **Create `.cursor/rules/critical-rule.mdc`** - Automatically loaded
✅ **Add to README.md** - Warning banner
✅ **Add to MEMORY.md** - Context section

### For Important Context (Should Be Discoverable)
✅ **Put in `docs/` structure** - Well-organized
✅ **Link from README.md** - Easy to find
✅ **Link from MEMORY.md** - Context reference

---

## Conclusion

**Most Reliable Method:** `.cursor/rules/*.mdc` files

**Why:** Automatically loaded by Cursor, easy to create/maintain, version controlled, explicitly referenceable.

**For Critical Information:** Use `.cursor/rules/` + README.md + MEMORY.md (multi-layer approach for maximum reliability).

---

**See Also:**
- [Documentation Quick Reference](docs/DOCUMENTATION_QUICK_REFERENCE.md)
- [Agent Safeguards Complete](docs/AGENT_SAFEGUARDS_COMPLETE.md)
- [Cursor Rules Directory](.cursor/rules/)
