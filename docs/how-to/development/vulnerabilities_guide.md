# Vulnerabilities for Non-Detail-Oriented Developers

**Date:** 2025-11-13  
**Purpose:** Identify what can still go wrong even with automation, and how to
prevent it

---

## Critical Vulnerabilities

### 1. 🚨 Ignoring Pre-commit Warnings

**Vulnerability:** Pre-commit hook shows warnings but doesn't block commits.

**What happens:**

```bash
git commit -m "Fix bug"
# Output:
# Warning: Using wrong Python environment: /usr/bin/python
# Warning: Found 5 console.log statements
# [Commit succeeds anyway]
```

**Why it's dangerous:**

- Developer sees warnings but commits anyway
- Code works locally (maybe) but fails in CI
- Python-dependent code fails silently
- Debug statements leak to production

**Prevention strategies:**

- ✅ **Make critical warnings fail commits** (convert warnings to errors)
- ✅ **Add CI checks that fail on warnings**
- ✅ **Require explicit confirmation for warnings**
- ✅ **Add post-commit hook that checks and warns**

---

### 2. 🚨 Not Running Setup Script

**Vulnerability:** Developer clones repo and starts coding without running
`./scripts/setup-dev.sh`.

**What happens:**

- Hooks not executable → commits bypass checks
- Prettier not installed → formatting fails
- Dependencies missing → code doesn't work
- Wrong Python → everything fails

**Why it's dangerous:**

- Code appears to work locally but fails in CI
- Other developers can't reproduce issues
- Production deployments fail

**Prevention strategies:**

- ✅ **Add README check** - Prominent setup instructions
- ✅ **Add git clone hook** - Auto-run setup after clone
- ✅ **Add CI validation** - Check that setup was run
- ✅ **Add startup check** - Scripts check environment on first run

---

### 3. 🚨 Copy-Pasting Code Without Understanding

**Vulnerability:** Developer copies code from Stack Overflow or other projects
without understanding.

**What happens:**

- Uses wrong Python path
- Uses wrong API patterns
- Breaks existing patterns
- Introduces security vulnerabilities

**Why it's dangerous:**

- Breaks consistency
- Introduces bugs
- Security issues
- Hard to maintain

**Prevention strategies:**

- ✅ **Code review requirements**
- ✅ **Pattern documentation** - Show correct examples
- ✅ **Linting rules** - Catch common mistakes
- ✅ **Architecture decision records** - Explain why patterns exist

---

### 4. 🚨 Not Reading Error Messages

**Vulnerability:** Developer sees error but doesn't read it, tries random fixes.

**What happens:**

```bash
Error: Using wrong Python: /usr/bin/python
Should be: /opt/miniforge/envs/casa6/bin/python
Fix: conda activate casa6

# Developer tries:
python --version  # Doesn't help
pip install something  # Wrong fix
```

**Why it's dangerous:**

- Wastes time
- Makes problems worse
- Doesn't fix root cause

**Prevention strategies:**

- ✅ **Make error messages extremely clear**
- ✅ **Add "What to do next" sections**
- ✅ **Add troubleshooting guide**
- ✅ **Add links to relevant docs**

---

### 5. 🚨 Not Checking Existing Code

**Vulnerability:** Developer creates new API endpoint without checking if one
exists.

**What happens:**

- Duplicates functionality
- Creates inconsistent APIs
- Breaks existing patterns
- Wastes time

**Why it's dangerous:**

- Code duplication
- Inconsistent behavior
- Maintenance burden

**Prevention strategies:**

- ✅ **API documentation** - List all endpoints
- ✅ **Code search tools** - Make it easy to find existing code
- ✅ **Code review** - Catch duplicates
- ✅ **Architecture docs** - Explain existing patterns

---

### 6. 🚨 Not Understanding the Domain

**Vulnerability:** Developer doesn't understand radio astronomy terms.

**What happens:**

- Uses wrong terminology
- Misunderstands requirements
- Implements wrong features
- Breaks scientific correctness

**Why it's dangerous:**

- Scientific errors
- Wrong calculations
- Data corruption
- Loss of trust

**Prevention strategies:**

- ✅ **Domain glossary** - Define all terms
- ✅ **Code comments** - Explain domain concepts
- ✅ **Domain expert review** - For scientific code
- ✅ **Unit tests** - Verify scientific correctness

---

### 7. 🚨 Not Testing Locally

**Vulnerability:** Developer commits code without testing locally.

**What happens:**

- Breaks CI immediately
- Wastes CI resources
- Blocks other developers
- Creates merge conflicts

**Why it's dangerous:**

- CI failures
- Broken main branch
- Team productivity loss

**Prevention strategies:**

- ✅ **Pre-commit hooks** - Run tests before commit
- ✅ **Local test scripts** - Make testing easy
- ✅ **CI feedback** - Fast feedback on failures
- ✅ **Test requirements** - Document how to test

---

### 8. 🚨 Not Reading Documentation

**Vulnerability:** Developer doesn't read docs, makes assumptions.

**What happens:**

- Creates files in wrong locations
- Uses wrong patterns
- Breaks conventions
- Wastes time

**Why it's dangerous:**

- Inconsistent codebase
- Hard to maintain
- Breaks workflows

**Prevention strategies:**

- ✅ **Prominent documentation links**
- ✅ **Inline documentation** - In code comments
- ✅ **Code review** - Check documentation adherence
- ✅ **Documentation as code** - Enforce doc standards

---

### 9. 🚨 Using Wrong Commands

**Vulnerability:** Developer uses `python` instead of casa6, even with warnings.

**What happens:**

```bash
# Developer runs:
python script.py  # Wrong!

# Should be:
/opt/miniforge/envs/casa6/bin/python script.py
```

**Why it's dangerous:**

- Code fails silently
- Wrong dependencies
- Inconsistent behavior

**Prevention strategies:**

- ✅ **Wrapper scripts** - Hide complexity
- ✅ **Aliases** - Make correct commands easy
- ✅ **Makefile targets** - Standardize commands
- ✅ **Fail fast** - Scripts check Python on startup

---

### 10. 🚨 Not Checking Git Status

**Vulnerability:** Developer commits wrong files or forgets to add files.

**What happens:**

- Commits temporary files
- Forgets to commit important changes
- Commits secrets
- Breaks builds

**Why it's dangerous:**

- Security issues
- Broken builds
- Lost work

**Prevention strategies:**

- ✅ **Pre-commit hooks** - Check for secrets
- ✅ **Git hooks** - Warn about uncommitted changes
- ✅ **.gitignore** - Comprehensive ignore patterns
- ✅ **Code review** - Catch issues

---

### 11. 🚨 Not Understanding Workflow

**Vulnerability:** Developer doesn't understand the pipeline workflow.

**What happens:**

- Breaks workflow steps
- Uses wrong data paths
- Breaks dependencies
- Corrupts data

**Why it's dangerous:**

- Pipeline failures
- Data corruption
- Production issues

**Prevention strategies:**

- ✅ **Workflow documentation** - Clear diagrams
- ✅ **Workflow validation** - Check workflow integrity
- ✅ **Code review** - Verify workflow understanding
- ✅ **Integration tests** - Test full workflow

---

### 12. 🚨 Not Understanding API Contracts

**Vulnerability:** Developer changes API without updating frontend, or vice
versa.

**What happens:**

- Frontend breaks
- Backend breaks
- Inconsistent behavior
- Production failures

**Why it's dangerous:**

- Broken integrations
- User-facing bugs
- Production outages

**Prevention strategies:**

- ✅ **API contracts** - Document all contracts
- ✅ **Contract tests** - Verify contracts
- ✅ **Type safety** - TypeScript helps
- ✅ **Code review** - Check contract changes

---

### 13. 🚨 Not Understanding Database Schema

**Vulnerability:** Developer queries wrong tables or uses wrong column names.

**What happens:**

- Wrong data returned
- Queries fail
- Data corruption
- Performance issues

**Why it's dangerous:**

- Data integrity issues
- Application failures
- Security issues

**Prevention strategies:**

- ✅ **Schema documentation** - Document all tables
- ✅ **Type safety** - Use ORM or typed queries
- ✅ **Migration checks** - Validate schema changes
- ✅ **Code review** - Verify database usage

---

### 14. 🚨 Not Understanding Frontend Architecture

**Vulnerability:** Developer breaks existing patterns or architecture.

**What happens:**

- Inconsistent UI
- Broken components
- Performance issues
- Maintenance burden

**Why it's dangerous:**

- User experience issues
- Technical debt
- Hard to maintain

**Prevention strategies:**

- ✅ **Architecture docs** - Explain patterns
- ✅ **Component library** - Reusable components
- ✅ **Code review** - Check architecture adherence
- ✅ **Linting rules** - Enforce patterns

---

### 15. 🚨 Not Understanding CASA

**Vulnerability:** Developer uses wrong CASA commands or doesn't understand
CASA.

**What happens:**

- Wrong calibration
- Wrong imaging
- Data corruption
- Scientific errors

**Why it's dangerous:**

- Scientific correctness
- Data integrity
- Production failures

**Prevention strategies:**

- ✅ **CASA documentation** - Link to CASA docs
- ✅ **Code comments** - Explain CASA usage
- ✅ **Domain expert review** - For CASA code
- ✅ **Unit tests** - Verify CASA correctness

---

## Prevention Strategies Summary

### Automated (Already Done)

- ✅ Pre-commit hooks
- ✅ Environment checks
- ✅ Code quality checks
- ✅ Setup scripts

### Need to Add

#### 1. Make Critical Warnings Fail

**Action:** Convert critical warnings to errors in pre-commit hook

- Python environment → Error (not warning)
- Missing dependencies → Error
- Test organization → Already error

#### 2. Add README Prominence

**Action:** Make setup instructions impossible to miss

- Large "START HERE" section
- Setup script as first step
- Visual indicators

#### 3. Add Wrapper Scripts

**Action:** Create easy-to-use wrapper scripts

- `./run-python` → Uses casa6 automatically
- `./run-tests` → Uses casa6 automatically
- `./setup` → Runs setup-dev.sh

#### 4. Add Post-Commit Hook

**Action:** Check after commit and warn

- Verify setup was run
- Check for common mistakes
- Suggest fixes

#### 5. Add CI Validation

**Action:** CI checks that would catch issues

- Verify Python environment
- Check for console.log
- Verify setup was run
- Check documentation location

#### 6. Add Troubleshooting Guide

**Action:** Quick reference for common issues

- "I see this error, what do I do?"
- Step-by-step fixes
- Links to relevant docs

#### 7. Add Code Examples

**Action:** Show correct patterns

- API usage examples
- Component examples
- Test examples
- Workflow examples

#### 8. Add Architecture Decision Records

**Action:** Explain why patterns exist

- Why casa6?
- Why this structure?
- Why these conventions?

---

## Most Critical Additions

### Priority 1: Make Python Check Fail

**Why:** Python environment is critical, warnings are ignored.

**Change:**

```bash
# In .husky/pre-commit
# Change from warning to error for Python-dependent operations
if [ needs_python ] && [ "$CURRENT_PYTHON" != "$CASA6_PYTHON" ]; then
  echo "ERROR: Wrong Python environment" >&2
  exit 1
fi
```

### Priority 2: Add Wrapper Scripts

**Why:** Makes correct commands easy, wrong commands hard.

**Create:**

- `scripts/run-python.sh` - Wrapper that uses casa6
- `scripts/run-tests.sh` - Wrapper that uses casa6
- Add to PATH or create aliases

### Priority 3: Enhance README

**Why:** First thing developers see.

**Add:**

- Large "QUICK START" section at top
- Step-by-step setup
- Visual indicators
- Common mistakes section

### Priority 4: Add Post-Commit Hook

**Why:** Catches issues after commit, before push.

**Create:**

- `.husky/post-commit` - Checks and warns
- Non-blocking but visible
- Suggests fixes

---

## Summary

**Vulnerabilities identified:** 15 major areas

**Automation coverage:** Good, but warnings can be ignored

**Critical gaps:**

1. Warnings don't block commits
2. Setup script can be skipped
3. Wrong commands still work
4. Documentation can be ignored

**Recommended additions:**

1. Make critical checks fail (not just warn)
2. Add wrapper scripts
3. Enhance README
4. Add post-commit checks
5. Add troubleshooting guide

**Result:** Even non-detail-oriented developers will be caught by automated
checks, and clear guidance will help them fix issues.
