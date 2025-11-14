# Technical Debt - Anti-Pattern Catalog

## Overview

This document tracks technical debt related to anti-patterns that need
refactoring.

**Purpose:**

- Catalog anti-patterns found in codebase
- Track refactoring progress
- Prioritize improvements
- Share knowledge

---

## Format

```markdown
## [Date] Anti-Pattern: [Name]

**Location:** [file/function/module] **Type:** Code | Process | Test |
Architecture **Impact:** High | Medium | Low **Effort:** [Estimate in
hours/days] **Status:** New | In Progress | Resolved | Deferred

**Description:** [What anti-pattern exists and where]

**Problems:**

- [Problem 1]
- [Problem 2]

**Solution:** [How to fix it]

**Refactoring Steps:**

1. [Step 1]
2. [Step 2]

**Related:**

- [Links to issues, PRs, docs]
```

---

## Active Technical Debt

### [2025-01-12] Anti-Pattern: Dismissive Language in Commit Messages

**Location:** Commit messages **Type:** Process **Impact:** Medium **Effort:**
Low (prevention added) **Status:** Resolved

**Description:** Commit messages contained dismissive language like "doesn't
matter", "edge case", "probably fine"

**Problems:**

- Hides real issues
- Creates technical debt
- Poor documentation

**Solution:**

- Pre-commit hook added to detect dismissive language
- Code review guidelines updated
- CI/CD checks added

**Refactoring Steps:**

1. ✅ Added pre-commit hook
2. ✅ Created detection script
3. ✅ Updated PR template
4. ✅ Added CI/CD checks

**Related:**

- `.husky/pre-commit`
- `scripts/lib/anti-pattern-detection.sh`
- `.github/workflows/anti-pattern-check.yml`

---

## Resolved Technical Debt

_(Move resolved items here with resolution date)_

---

## Deferred Technical Debt

_(Items deferred for future consideration)_

---

## How to Add New Debt

1. **Identify anti-pattern**
   - Use detection scripts
   - Code review findings
   - Manual discovery

2. **Document following format**
   - Use template above
   - Be specific
   - Include context

3. **Prioritize**
   - Assess impact
   - Estimate effort
   - Assign priority

4. **Track progress**
   - Update status
   - Document steps
   - Record resolution

---

## Review Process

### Monthly Review

**When:** First Monday of each month

**Process:**

1. Review all active debt
2. Prioritize based on impact
3. Assign to sprints
4. Update status
5. Extract patterns

**Output:**

- Updated priorities
- Sprint assignments
- Pattern learnings
- Process improvements

---

## Metrics

### Current State

- **Total Debt Items:** [Count]
- **High Impact:** [Count]
- **Medium Impact:** [Count]
- **Low Impact:** [Count]
- **In Progress:** [Count]
- **Resolved This Month:** [Count]

### Goals

- **Reduce high-impact debt** by [X]% per quarter
- **Resolve** [X] items per sprint
- **Prevent** new debt through detection

---

## Related Documents

- `QUALITY_PRINCIPLES.md` - Quality standards
- `ANTI_PATTERN_HANDLING.md` - Handling approach
- `REFACTORING_CHECKLIST.md` - Refactoring process
- `MISTAKE_LOG.md` - Mistake tracking

---

## Notes

- Keep entries specific and actionable
- Update regularly
- Use for sprint planning
- Share learnings with team
