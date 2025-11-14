# Refactoring Checklist - Anti-Pattern Resolution

## When Anti-Pattern Detected

Use this checklist to systematically refactor away from anti-patterns.

---

## Step 1: Identify

- [ ] **What anti-pattern is present?**
  - Document the specific anti-pattern
  - Note where it occurs
  - Identify scope (file, function, module)

- [ ] **Why does it exist?**
  - Historical reasons?
  - Time pressure?
  - Lack of knowledge?
  - Copy-paste?

- [ ] **What problems does it cause?**
  - Maintenance issues?
  - Bugs?
  - Performance?
  - Readability?

---

## Step 2: Understand

- [ ] **What is the correct pattern/solution?**
  - Research best practices
  - Find documented patterns
  - Consult team/expertise

- [ ] **What are the constraints?**
  - Time available?
  - Dependencies?
  - Breaking changes?
  - Risk level?

- [ ] **What is the impact of fixing?**
  - Files affected?
  - Tests needed?
  - Documentation updates?
  - Team communication?

---

## Step 3: Plan

- [ ] **Create refactoring plan**
  - Break into small steps
  - Identify dependencies
  - Plan test strategy
  - Estimate effort

- [ ] **Identify risks**
  - What could go wrong?
  - How to mitigate?
  - Rollback plan?

- [ ] **Get approval if needed**
  - Code review?
  - Team discussion?
  - Stakeholder approval?

---

## Step 4: Execute

- [ ] **Write tests first** (if applicable)
  - Tests for current behavior
  - Tests for desired behavior
  - Ensure tests pass

- [ ] **Refactor incrementally**
  - Small, safe changes
  - Test after each change
  - Commit frequently

- [ ] **Maintain functionality**
  - Behavior should not change
  - All tests pass
  - No regressions

---

## Step 5: Verify

- [ ] **All tests pass**
  - Unit tests
  - Integration tests
  - Manual testing

- [ ] **No regressions**
  - Check related functionality
  - Verify edge cases
  - Confirm performance

- [ ] **Code quality improved**
  - Anti-pattern removed
  - Better pattern applied
  - Code is cleaner

---

## Step 6: Document

- [ ] **Update code comments**
  - Explain new approach
  - Document decisions
  - Add context

- [ ] **Update documentation**
  - README if needed
  - Architecture docs
  - Team knowledge base

- [ ] **Record in technical debt log**
  - Mark as resolved
  - Document learnings
  - Share with team

---

## Common Anti-Pattern Refactorings

### Magic Numbers → Named Constants

**Before:**

```javascript
if (timeout > 3600) {
  // ...
}
```

**After:**

```javascript
const ONE_HOUR_IN_SECONDS = 3600;
if (timeout > ONE_HOUR_IN_SECONDS) {
  // ...
}
```

**Checklist:**

- [ ] Identify all magic numbers
- [ ] Create named constants
- [ ] Replace all occurrences
- [ ] Add comments if needed
- [ ] Update tests

---

### Code Duplication → Extract Function

**Before:**

```javascript
// Repeated code in multiple places
const result = data.map((item) => item.value * 2).filter((v) => v > 10);
```

**After:**

```javascript
function processItems(items) {
  return items.map((item) => item.value * 2).filter((v) => v > 10);
}
```

**Checklist:**

- [ ] Identify duplicated code
- [ ] Extract to function
- [ ] Replace all occurrences
- [ ] Add tests for function
- [ ] Verify behavior unchanged

---

### Dismissive Language → Proper Documentation

**Before:**

```javascript
// Edge case, probably won't happen
if (value === null) return;
```

**After:**

```javascript
// Handle null values: API may return null for missing data
// Return early to prevent downstream errors
if (value === null) {
  logger.warn("Null value received, skipping processing");
  return;
}
```

**Checklist:**

- [ ] Remove dismissive comments
- [ ] Add proper explanation
- [ ] Document why it's needed
- [ ] Add error handling if missing
- [ ] Add tests for edge case

---

## Technical Debt Tracking

### When Anti-Pattern Detected

Add to `TECHNICAL_DEBT.md`:

```markdown
## [Date] Anti-Pattern: [Name]

**Location:** [file/function] **Type:** [Code/Process/Test] **Impact:**
[High/Medium/Low] **Effort:** [Estimate] **Status:** [New/In Progress/Resolved]

**Description:** [What anti-pattern exists]

**Problems:**

- [List problems it causes]

**Solution:** [How to fix it]

**Refactoring Steps:**

1. [Step 1]
2. [Step 2]
3. [Step 3]
```

---

## Review Process

### After Refactoring

1. **Code Review**
   - Verify anti-pattern removed
   - Confirm better pattern applied
   - Check tests adequate

2. **Team Discussion**
   - Share learnings
   - Update guidelines
   - Prevent recurrence

3. **Documentation**
   - Update patterns catalog
   - Add to knowledge base
   - Train team if needed

---

## Summary

**Process:**

1. Identify → 2. Understand → 3. Plan → 4. Execute → 5. Verify → 6. Document

**Key Principles:**

- Small, incremental changes
- Test thoroughly
- Maintain functionality
- Document learnings
- Share knowledge

**Goal:** Systematically eliminate anti-patterns and improve code quality.
