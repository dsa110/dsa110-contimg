# Developer Handoff - Critical Warnings and Gotchas

**Date:** 2025-11-13  
**Purpose:** Essential information for developers taking over this project

---

## 🚨 CRITICAL: Python Environment

### **MANDATORY: Always Use casa6**

**This is the #1 mistake new developers make.**

**DO NOT use:**

- ❌ `python` or `python3` (system Python 3.6.9 - too old)
- ❌ Any other conda environment
- ❌ Virtual environments created with `venv` or `virtualenv`

**MUST use:**

- ✅ `/opt/miniforge/envs/casa6/bin/python` (Python 3.11.13)
- ✅ Or activate: `conda activate casa6`

**Why:**

- CASA dependencies (casatools, casatasks) are ONLY in casa6
- System Python lacks required features (e.g.,
  `from __future__ import annotations`)
- All pipeline scripts expect casa6
- Tests will fail without casa6

**How to verify:**

```bash
which python
# Should show: /opt/miniforge/envs/casa6/bin/python

python --version
# Should show: Python 3.11.13
```

**In Makefiles/scripts:**

```bash
# Always use this variable
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Or in shell scripts
PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
```

**Reference:** `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md`

---

## 📁 Directory Structure and Data Paths

### **Critical: Don't Create Files Without Checking Structure**

**Before creating ANY file:**

1. Read `docs/concepts/DIRECTORY_ARCHITECTURE.md`
2. Check `docs/DOCUMENTATION_QUICK_REFERENCE.md` for documentation location
   rules

### **Key Paths (Hardcoded in Code)**

**Data Storage:**

- **Incoming UVH5 files:** `/data/incoming/` (watched by streaming converter)
- **Processed MS files:** `/stage/dsa110-contimg/ms/`
- **Images:** `/stage/dsa110-contimg/images/`
- **State databases:** `/data/dsa110-contimg/state/` (NOT `/stage/.../state/`)
- **Scratch/temp:** `/stage/dsa110-contimg/` or `/dev/shm/` (tmpfs)

**Code:**

- **Source code:** `/data/dsa110-contimg/src/`
- **Frontend:** `/data/dsa110-contimg/frontend/`
- **Documentation:** `/data/dsa110-contimg/docs/` (structured, NOT root)

### **Documentation Organization**

**NEVER create markdown files in root directory!**

**Documentation goes in:**

- `docs/how-to/` - Step-by-step procedures
- `docs/concepts/` - Concept explanations
- `docs/reference/` - API/CLI reference
- `docs/archive/analysis/` - Analysis and investigations (archived)
- `internal/docs/dev/` - Internal dev notes

**Reference:** `docs/DOCUMENTATION_QUICK_REFERENCE.md`

---

## 🔧 Frontend Development

### **Environment Variables**

**Vite Environment Variables:**

- Must be prefixed with `VITE_` to be accessible in frontend
- Example: `VITE_API_URL` (not `API_URL`)
- Default API proxy: `http://127.0.0.1:8000` (see `frontend/vite.config.ts`)

**Backend API:**

- Dev mode: `http://127.0.0.1:8000` (Vite proxy)
- Production: `/api` (served from FastAPI at `/ui`)

### **TypeScript Configuration**

- Uses strict mode
- References: `tsconfig.app.json`, `tsconfig.node.json`
- No ESLint config file (uses package.json config)

### **Material-UI v6**

**DO NOT:**

- ❌ Suggest Blueprint UI, Ant Design, or other UI libraries
- ❌ Redesign architecture (it's already built)
- ❌ Change from Material-UI v6

**DO:**

- ✅ Use existing Material-UI components
- ✅ Follow existing patterns
- ✅ Check `package.json` before suggesting new dependencies

### **Known TODOs in Frontend**

**Incomplete features:**

- `ImageDetailPage.tsx`: Comments component, runs table
- `SourceDetailPage.tsx`: Comments, Plotly light curve, related sources

**These are intentional placeholders - don't remove them.**

---

## 🧪 Testing

### **Test Organization is Enforced**

**ALL test files MUST follow taxonomy:**

- Location: `tests/<type>/<module>/test_*.py`
- Types: `unit`, `integration`, `smoke`, `science`, `e2e`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

**Pre-commit hook validates test organization!**

**Quick reference:**

```bash
# Use template
python scripts/test-template.py <type> <module> <feature>

# Validate
./scripts/validate-test-organization.py
```

**Reference:** `docs/concepts/TEST_ORGANIZATION.md`

### **Test Execution Rules**

**Default (fast):**

```bash
# Unit tests only, exclude slow/integration
make test-unit
```

**Integration tests (requires synthetic data):**

```bash
TEST_WITH_SYNTHETIC_DATA=1 /opt/miniforge/envs/casa6/bin/python -m pytest tests/integration
```

**Always use casa6 Python for tests!**

---

## 🔄 Git Hooks and Prettier

### **Pre-commit Hook**

**What it does:**

1. Checks commit message for anti-patterns
2. Formats code with Prettier
3. Runs type-check and lint
4. Validates test organization

**Setup (automatic):**

```bash
# After clone, run:
./scripts/setup-dev.sh

# Or just:
cd frontend && npm install  # postinstall script fixes hook permissions
```

### **Prettier Configuration**

**Files formatted:**

- JavaScript, TypeScript, JSX, TSX
- JSON, YAML, HTML, CSS, SCSS, Less
- Markdown, GraphQL, Vue

**Pre-commit hook:**

- Automatically formats staged files
- Fails if files still need formatting after auto-format

**Manual formatting:**

```bash
cd frontend
npm run format        # Format all files
npm run format:check  # Check formatting
```

**Reference:** `docs/how-to/PRETTIER_WARNINGS.md`

---

## 🐛 Error Detection and Anti-Pattern Detection

### **Agent Setup Script**

**For AI agents or automated scripts:**

```bash
source /data/dsa110-contimg/scripts/agent-setup.sh
```

**This enables:**

- Auto error detection (wraps commands)
- Anti-pattern detection
- Error acknowledgment enforcement

**Reference:** `docs/how-to/agentic-session-setup.md`

### **Error Acknowledgment Rule**

**CRITICAL:** Never ignore, dismiss, or skip over errors.

**When tests fail:**

- ✅ Report exact failure count
- ✅ List all failing tests
- ✅ Investigate root causes
- ❌ Never claim "mostly works" with failures present

**Reference:** `.cursor/rules/error-acknowledgment.mdc`

---

## 🗄️ Database Locations

### **SQLite Databases**

**State databases (persistent):**

- Location: `/data/dsa110-contimg/state/`
- Files: `products.sqlite3`, `ingest.sqlite3`, `cal_registry.sqlite3`,
  `master_sources.sqlite3`

**NOT in `/stage/`** - these are state, not temporary data.

### **Database Schemas**

**DO NOT create new schemas without checking existing ones:**

- `products.sqlite3`: `ms_index`, `images`, `photometry`, `variability_stats`,
  `ese_candidates`
- `ingest.sqlite3`: `ingest_queue`, `subband_files`
- `cal_registry.sqlite3`: `caltables`
- `master_sources.sqlite3`: `sources` catalog

**Backend is read-only context** - don't modify database schemas when working on
frontend.

---

## 🔌 Backend API

### **FastAPI Backend**

**100+ endpoints already exist** - check before creating new ones.

**Key endpoints:**

- `GET /api/status` - Pipeline status
- `GET /api/metrics/system` - System metrics
- `GET /api/ese/candidates` - ESE candidates
- `POST /api/sources/search` - Source search

**Backend is read-only for frontend work** - reference only, don't modify.

---

## 📊 Radio Astronomy Domain Knowledge

### **Key Terms (Don't Hallucinate)**

- **MJD** = Modified Julian Date (days since 1858-11-17)
- **ESE** = Extreme Scattering Event (>5σ flux variability)
- **MS** = Measurement Set (CASA data format)
- **Calibration types:** K, BA, BP, GA, GP, 2G (CASA conventions)
- **NVSS** = NRAO VLA Sky Survey (catalog reference)

**Reference:** `.cursor/rules/radio-conventions.mdc`

---

## 🚫 Common Mistakes

### **1. Using System Python**

```bash
# WRONG
python scripts/test.py

# CORRECT
/opt/miniforge/envs/casa6/bin/python scripts/test.py
```

### **2. Creating Files in Wrong Location**

```bash
# WRONG
echo "# Status" > STATUS.md

# CORRECT
echo "# Status" > docs/dev/status/2025-11/status.md
```

### **3. Ignoring Test Failures**

```bash
# WRONG
"32 tests passed, core functionality works" (when 7 failed)

# CORRECT
"32 passed, 7 failed. Status: FAILURE. Investigating..."
```

### **4. Not Running Setup Script**

```bash
# After clone, always run:
./scripts/setup-dev.sh
```

### **5. Modifying Backend When Working on Frontend**

- Backend is read-only context for frontend work
- Check existing endpoints before creating new ones
- Don't modify database schemas

---

## 🔍 Debugging Tips

### **Frontend Issues**

**Check:**

1. Is dev server running? `cd frontend && npm run dev`
2. Is backend API running? `curl http://127.0.0.1:8000/api/status`
3. Check browser console for errors
4. Check Vite proxy configuration in `vite.config.ts`

### **Backend Issues**

**Check:**

1. Using casa6 Python? `which python`
2. Are databases accessible? `ls -la /data/dsa110-contimg/state/`
3. Check logs: `journalctl -u contimg-api` (if systemd)
4. Check environment variables in `ops/systemd/contimg.env`

### **Test Failures**

**Check:**

1. Using casa6 Python? `which python`
2. Test organization correct? `./scripts/validate-test-organization.py`
3. Dependencies installed? `cd frontend && npm install`
4. Synthetic data available? (for integration tests)

---

## 📚 Essential Documentation

**Read these first:**

1. `docs/concepts/DIRECTORY_ARCHITECTURE.md` - File organization
2. `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md` - Python environment
3. `docs/DOCUMENTATION_QUICK_REFERENCE.md` - Where to put docs
4. `docs/concepts/TEST_ORGANIZATION.md` - Test structure
5. `docs/how-to/PRETTIER_WARNINGS.md` - Prettier setup

**Project overview:**

- `README.md` - Project overview
- `docs/concepts/dashboard_architecture.md` - Dashboard architecture
- `docs/archive/analysis/DASHBOARD_OVERVIEW_DETAILED.md` - Dashboard details

---

## ⚙️ Environment Setup Checklist

**For new developers:**

```bash
# 1. Verify Python environment
which python
# Should be: /opt/miniforge/envs/casa6/bin/python

# 2. Setup git hooks and dependencies
./scripts/setup-dev.sh

# 3. Verify Prettier
cd frontend && npm run format:check

# 4. Verify tests
make test-unit

# 5. Start dev servers
# Terminal 1: Backend API
# Terminal 2: Frontend dev server
cd frontend && npm run dev
```

---

## 🎯 Workflow-Specific Gotchas

### **Frontend Development**

- **Don't suggest new UI libraries** - use Material-UI v6
- **Check existing API endpoints** before creating new ones
- **Follow existing component patterns** - don't redesign architecture
- **Use TypeScript strictly** - no `any` types without justification

### **Backend Development**

- **Always use casa6 Python** - no exceptions
- **Check directory structure** before creating files
- **Follow test organization** - pre-commit hook enforces it
- **Don't ignore errors** - acknowledge and investigate

### **Documentation**

- **Never create markdown in root** - use `docs/` structure
- **Check documentation location rules** before creating files
- **Follow naming conventions** - lowercase with underscores

---

## 🚨 Known Issues and Limitations

### **Incomplete Features**

- Image detail page: Comments, runs table (TODOs in code)
- Source detail page: Comments, Plotly light curve, related sources (TODOs)

**These are intentional placeholders - don't remove them.**

### **Environment-Specific**

- **Git file mode disabled** (`core.filemode=false`) - hooks need `chmod +x`
  after clone (auto-fixed by postinstall)
- **Prettier downloads on first run** if not in package.json (now fixed - in
  devDependencies)

### **Data Provenance**

**Always verify data source:**

- Files in `tests/`, `test_*`, `notebooks/` are TEST DATA
- Real observations: `/stage/dsa110-contimg/images/` or
  `/data/dsa110-contimg/products/images/`
- Check FITS headers for `DATE-OBS`, `TELESCOP` fields

**Reference:** `.cursor/rules/data-provenance-verification.mdc`

---

## 📞 Getting Help

**If stuck:**

1. Check this document first
2. Read relevant documentation in `docs/`
3. Check `.cursor/rules/` for project-specific rules
4. Review existing code patterns
5. Check test files for usage examples

**Common questions:**

- Python environment: `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md`
- File organization: `docs/concepts/DIRECTORY_ARCHITECTURE.md`
- Documentation: `docs/DOCUMENTATION_QUICK_REFERENCE.md`
- Testing: `docs/concepts/TEST_ORGANIZATION.md`
- Prettier: `docs/how-to/PRETTIER_WARNINGS.md`

---

## ✅ Quick Verification

**Run these to verify your setup:**

```bash
# 1. Python environment
which python
python --version

# 2. Git hooks
test -x .husky/pre-commit && echo "OK" || echo "NOT EXECUTABLE"

# 3. Prettier
cd frontend && npx prettier --version

# 4. Dependencies
cd frontend && npm list prettier

# 5. Test organization
./scripts/validate-test-organization.py
```

**All should pass!**

---

**Remember:** When in doubt, check the documentation first. Most issues are
covered in `docs/` or `.cursor/rules/`.
