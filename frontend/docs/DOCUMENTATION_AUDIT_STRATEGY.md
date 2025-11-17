# Documentation Audit Strategy

**Date:** 2025-11-16  
**Purpose:** Determine which documentation files are up-to-date versus
out-of-date

## Strategy Overview

This strategy uses multiple verification methods to assess document freshness
and accuracy. Documents are evaluated across several dimensions to identify
those that need updates.

---

## Assessment Criteria

### 1. **Version/Technology Alignment Check**

**What to check:** Compare documented technology versions with actual
package.json versions

**Method:**

- Extract version claims from docs (e.g., "React 18", "Vite 7", "MUI v6")
- Compare against actual versions in `package.json`
- Flag mismatches as outdated

**Current Findings:**

- ✅ **Outdated:** `README.md` states "React 18" but actual is React 19.1.1
- ✅ **Outdated:** `README.md` states "Vite 7" but actual is Vite 6.4.1
- ⚠️ **Acknowledged:** `FRONTEND_CODEBASE_ANALYSIS.md` notes "MUI v7 (not v6 as
  docs suggest)"

**Command to verify:**

```bash
grep -E "React|Vite|MUI|TypeScript" package.json
grep -E "React [0-9]|Vite [0-9]|MUI v[0-9]" docs/*.md
```

---

### 2. **File Existence Verification**

**What to check:** Verify that files/pages/components mentioned in docs actually
exist

**Method:**

- Extract file paths, component names, and page names from documentation
- Check if files exist in the expected locations
- Flag "not implemented" claims if files actually exist

**Current Findings:**

- ✅ **Outdated:** `FRONTEND_CODEBASE_ANALYSIS.md` claims `HealthPage.tsx` is
  "not implemented" but file exists (modified Nov 15, 2025)
- ✅ **Outdated:** `FRONTEND_CODEBASE_ANALYSIS.md` claims `ObservingPage.tsx` is
  "not implemented" but file exists (modified Nov 15, 2025)
- ⚠️ **Action needed:** Update status from "not implemented" to "implemented"

**Command to verify:**

```bash
# Find claims of "not implemented" or "missing"
grep -i "not implemented\|missing\|does not exist\|empty.*directory" docs/*.md
# Then verify files actually exist
ls -la src/pages/HealthPage.tsx src/pages/ObservingPage.tsx
```

---

### 3. **File Modification Timestamp Comparison**

**What to check:** Compare document modification date with related source files

**Method:**

- Get document modification timestamp
- Get modification timestamps of files/features discussed in the document
- If source files are newer than the document, flag as potentially outdated

**Current Findings:**

- ✅ **Potentially outdated:** Most docs modified Nov 14, 2025 at 14:56
- ⚠️ **Recent changes:** Many source files modified Nov 15-16, 2025
- ✅ **Most recent doc:** `POINTING_VISUALIZATION_BACKGROUND.md` (Nov 15, 18:43)

**Command to verify:**

```bash
# Get doc timestamps
stat -c "%y %n" docs/*.md | sort
# Get source file timestamps mentioned in specific doc
stat -c "%y %n" src/pages/*.tsx src/components/*.tsx | sort
```

---

### 4. **Code-Documentation Consistency Check**

**What to check:** Verify that documented API calls, hooks, components match
actual implementation

**Method:**

- Extract API endpoint references, hook names, component props from docs
- Search codebase for these references
- Flag if documented features don't exist in code or have different signatures

**Example checks:**

- Documented hooks: `useHealthData()`, `useObservationData()` - do they exist?
- API endpoints: `/api/health`, `/api/observations` - are they correct?
- Component props: Does `<HealthPage />` accept the documented props?

**Command to verify:**

```bash
# Find hook references in docs
grep -E "use[A-Z][a-zA-Z]*\(\)" docs/*.md | sort -u
# Check if hooks exist
grep -r "export.*use[A-Z]" src/hooks/ src/components/
```

---

### 5. **Placeholder Date Detection**

**What to check:** Identify documents with incomplete or placeholder dates

**Method:**

- Flag dates containing "XX" as placeholders (e.g., "2025-01-XX")
- Compare with actual file modification dates
- Documents with placeholder dates that are older than related code may be
  outdated

**Current Findings:**

- ⚠️ **6 documents** use placeholder format: `2025-01-XX`
- ⚠️ **1 document** uses shell command: `$(date +"%Y-%m-%d %H:%M:%S")`
- ✅ **2 documents** have specific dates: `2025-11-11`

**Command to verify:**

```bash
grep -E "Date:.*XX|date.*XX|202[0-9]-[0-9]{2}-XX" docs/*.md
```

---

### 6. **TODO/FIXME/DEPRECATED Marker Detection**

**What to check:** Identify documents containing markers indicating incomplete
or outdated content

**Method:**

- Search for common markers: TODO, FIXME, XXX, HACK, DEPRECATED, OUTDATED
- Review context to determine if these indicate stale documentation

**Current Findings:**

- ⚠️ **13 documents** contain TODO/FIXME markers (62 total occurrences)
- Documents with most markers:
  - `FRONTEND_CODEBASE_ANALYSIS.md`: 18 occurrences
  - `FRONTEND_ANALYSIS_SUMMARY.md`: 9 occurrences
  - `SKYVIEW_ANALYSIS.md`: 11 occurrences

**Command to verify:**

```bash
grep -iE "TODO|FIXME|XXX|HACK|DEPRECATED|OUTDATED|out of date" docs/*.md | wc -l
```

---

### 7. **Cross-Document Consistency Check**

**What to check:** Compare statements across multiple documents for conflicts

**Method:**

- Extract key facts about the same feature from different documents
- Compare for contradictions
- Flag conflicting information

**Example checks:**

- Does README.md match FRONTEND_ANALYSIS_SUMMARY.md on tech stack?
- Do implementation docs match analysis docs on feature status?
- Are testing instructions consistent across TESTING.md and testing-strategy.md?

---

### 8. **Reference Link Verification**

**What to check:** Verify that URLs, file paths, and cross-references are valid

**Method:**

- Extract URLs, file paths, and cross-document references
- Verify links point to valid files/locations
- Flag broken references

**Example checks:**

- Relative links: `[README](README.md)` - does the file exist?
- Code references: `src/components/Example.tsx` - does it exist?
- API endpoints: `/api/example` - is this documented in backend?

---

### 9. **Git History Analysis** (If available)

**What to check:** Compare document last commit with related code commits

**Method:**

- Use git log to find when documents were last modified
- Compare with git log of related source files
- Documents with older commits than related code may be outdated

**Command to verify:**

```bash
git log --format="%ai %s" -- docs/FRONTEND_CODEBASE_ANALYSIS.md
git log --format="%ai %s" -- src/pages/HealthPage.tsx
```

---

### 10. **Implementation Status Claims**

**What to check:** Verify claims about "implemented", "not implemented",
"planned", "partial"

**Method:**

- Extract status claims from documentation
- Cross-reference with actual codebase
- Flag if status doesn't match reality

**Current Findings:**

- ✅ **Discrepancy found:** `FRONTEND_CODEBASE_ANALYSIS.md` says HealthPage "not
  implemented" but file exists
- ✅ **Discrepancy found:** `FRONTEND_CODEBASE_ANALYSIS.md` says ObservingPage
  "not implemented" but file exists

---

## Scoring System

Each document receives a **freshness score** based on:

| Criteria              | Weight | Points                    |
| --------------------- | ------ | ------------------------- |
| Version accuracy      | High   | -3 if outdated            |
| File existence claims | High   | -3 if wrong               |
| Recent modifications  | Medium | -2 if doc older than code |
| Code-doc consistency  | High   | -2 if mismatch            |
| Placeholder dates     | Low    | -1 if placeholder         |
| TODO/FIXME markers    | Medium | -1 per 5 markers          |
| Cross-doc consistency | Medium | -1 if conflict            |
| Broken references     | Medium | -1 per broken link        |
| Git history           | Low    | -1 if significantly older |
| Status claims         | High   | -2 if incorrect           |

**Freshness Rating:**

- **Up-to-date:** Score ≥ 0
- **Needs review:** Score -1 to -3
- **Outdated:** Score ≤ -4

---

## Execution Plan

### Phase 1: Automated Checks (Quick Wins)

1. ✅ Version alignment check (COMPLETED - found issues)
2. ✅ File existence verification (COMPLETED - found issues)
3. ✅ Placeholder date detection (COMPLETED)
4. ✅ TODO marker detection (COMPLETED)

### Phase 2: Manual Verification

5. Code-documentation consistency check
6. Cross-document consistency review
7. Reference link verification

### Phase 3: Deep Analysis (If needed)

8. Git history analysis
9. Implementation status deep dive
10. Feature-by-feature comparison

---

## Priority Documents for Review

Based on initial findings:

### 🔴 High Priority (Outdated - Action Required)

1. **README.md**
   - ❌ States React 18 (actual: React 19)
   - ❌ States Vite 7 (actual: Vite 6)
   - 📅 Last modified: Nov 14, 2025

2. **FRONTEND_CODEBASE_ANALYSIS.md**
   - ❌ Claims HealthPage not implemented (file exists, modified Nov 15)
   - ❌ Claims ObservingPage not implemented (file exists, modified Nov 15)
   - ⚠️ 18 TODO/FIXME markers
   - 📅 Last modified: Nov 14, 2025 | Document date: 2025-01-XX

### 🟡 Medium Priority (Needs Review)

3. **FRONTEND_ANALYSIS_SUMMARY.md**
   - ⚠️ 9 TODO/FIXME markers
   - 📅 Document date: 2025-01-XX

4. **SKYVIEW_ANALYSIS.md**
   - ⚠️ 11 TODO/FIXME markers
   - 📅 Document date: 2025-01-XX

5. **testing-execution-report.md**
   - ⚠️ Uses shell command for date: `$(date +"%Y-%m-%d %H:%M:%S")`
   - 📅 Should have actual timestamp

### 🟢 Low Priority (Likely Up-to-Date)

6. **health-check-fix.md** - Specific date (2025-11-11)
7. **hot-reload-verification.md** - Specific date (2025-11-11)
8. **POINTING_VISUALIZATION_BACKGROUND.md** - Most recently modified (Nov 15,
   18:43)

---

## Recommended Actions

1. **Immediate fixes:**
   - Update README.md with correct React 19 and Vite 6 versions
   - Update FRONTEND_CODEBASE_ANALYSIS.md to reflect HealthPage and
     ObservingPage as implemented
   - Replace placeholder dates (2025-01-XX) with actual dates or file
     modification dates
   - Fix testing-execution-report.md date format

2. **Review cycle:**
   - Establish process: Update docs when modifying related code
   - Add pre-commit hook to flag outdated version references
   - Regular quarterly review of high-traffic documentation

3. **Documentation maintenance:**
   - Create template with date format standards
   - Add "Last Reviewed" field to all docs
   - Link documentation to related source files

---

## Tools & Commands Summary

```bash
# Check version mismatches
grep -E "React [0-9]|Vite [0-9]|MUI v[0-9]" docs/*.md
cat package.json | grep -E "react|vite|@mui/material"

# Check file existence claims
grep -i "not implemented\|missing\|empty.*directory" docs/*.md

# Check modification dates
stat -c "%y %n" docs/*.md | sort
stat -c "%y %n" src/pages/*.tsx | sort

# Find TODO markers
grep -iE "TODO|FIXME|XXX|DEPRECATED" docs/*.md | wc -l

# Find placeholder dates
grep -E "Date:.*XX|202[0-9]-[0-9]{2}-XX" docs/*.md

# Verify hooks/components exist
grep -E "use[A-Z][a-zA-Z]*\(\)" docs/*.md | sort -u
grep -r "export.*use[A-Z]" src/hooks/ src/components/
```

---

**Next Steps:** Proceed with Phase 2 manual verification for high-priority
documents.
