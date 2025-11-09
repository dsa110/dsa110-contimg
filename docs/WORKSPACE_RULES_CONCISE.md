# Workspace Rules: Concise Version for Always-Applied Rules

**Purpose:** Ultra-concise version for "Always Applied Workspace Rules" section  
**Full details:** `.cursor/rules/critical-requirements.mdc` and `docs/concepts/DIRECTORY_ARCHITECTURE.md`

---

## Recommended Text for Always-Applied Workspace Rules

Add this concise version to the workspace configuration's "Always Applied Workspace Rules":

```markdown
## ⚠️ CRITICAL: Python Environment - casa6 ONLY

**NEVER use `python`, `python3`, or system Python. ALWAYS use:**
`/opt/miniforge/envs/casa6/bin/python`

**Why:** System Python (3.6.9) lacks CASA dependencies. Pipeline WILL FAIL without casa6.

**Before ANY Python execution:**
1. Check: `test -x /opt/miniforge/envs/casa6/bin/python || exit 1`
2. Use: `/opt/miniforge/envs/casa6/bin/python` (not `python3`)
3. In scripts: `PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"`

**Details:** `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md`

---

## 📁 Codebase Organization

**Before creating files, check:** `docs/concepts/DIRECTORY_ARCHITECTURE.md`

**Key paths:**
- Code: `/data/dsa110-contimg/`
- Data: `/stage/dsa110-contimg/`
- Docs: `docs/` structure (see `.cursor/rules/documentation-location.mdc`)
- State DBs: `/data/dsa110-contimg/state/`

**Details:** `docs/concepts/DIRECTORY_ARCHITECTURE.md`
```

---

## My Recommendation

**Option: Put concise version directly in Always-Applied Rules**

**Why:**
1. ✅ **Maximum visibility** - Agents see it immediately, can't miss it
2. ✅ **No file lookup needed** - Critical info is right there
3. ✅ **Harder to ignore** - Prominent placement forces attention
4. ✅ **Works even if agents skip reading files** - It's in their context automatically

**Trade-offs:**
- ⚠️ Requires workspace config edit (one-time setup)
- ⚠️ Less flexible than referencing a file (but you can update the file and re-add to config)

**Alternative (if workspace config is hard to edit):**
- Put concise version in `.cursor/rules/critical-requirements-short.mdc`
- Reference it in workspace config
- Still very visible, but requires one file lookup

---

## Why Agents Keep Missing casa6 Requirement

**Problem:** Current rule might be:
- Too verbose (buried in long text)
- Not prominent enough (not at the top)
- Not explicit enough about NEVER using python/python3

**Solution:** Make it:
- **Ultra-concise** (3-4 lines max)
- **At the very top** of always-applied rules
- **Explicit prohibition** ("NEVER use python/python3")
- **Action-oriented** ("Before ANY Python execution...")

---

## Implementation Steps

1. **Copy the concise version above** into workspace "Always Applied Workspace Rules"
2. **Place casa6 requirement FIRST** (before other rules, before everything)
3. **Test:** Have an agent run a Python script - they should use casa6 automatically
4. **Monitor:** If agents still use wrong Python, make the rule even more explicit

---

**Files created:**
- `.cursor/rules/critical-requirements-short.mdc` - Concise version for always-applied rules
- `.cursor/rules/critical-requirements.mdc` - Full detailed version (reference)
- `docs/concepts/DIRECTORY_ARCHITECTURE.md` - Full organizational layout details
