# Quality Principles - Error Detection Framework

## Core Principle: Zero Tolerance for Test Failures

### The Mantra

**"If an error arises, or a test fails, the core causal issue must be identified
and solved."**

### Rationale

Every test failure represents:

- A gap in understanding
- A potential bug
- Technical debt
- A deviation from expected behavior

**No test failure is acceptable without investigation and resolution.**

---

## Anti-Patterns to Avoid

### ❌ Dismissing Failures

**Wrong:**

- "This test failure doesn't affect core functionality"
- "It's just an edge case"
- "The test itself might be wrong"
- "We can fix it later"

**Right:**

- Investigate the root cause
- Fix the underlying issue
- Verify the fix with the test
- Document the resolution

---

### ❌ Rationalizing Failures

**Wrong:**

- "It works in practice"
- "The test is too strict"
- "This is expected behavior"
- "It's a known limitation"

**Right:**

- Understand why the test expects different behavior
- Determine if test or implementation is wrong
- Fix whichever is incorrect
- Update documentation

---

### ❌ Ignoring Edge Cases

**Wrong:**

- "Edge cases don't matter"
- "It's rare, so we can ignore it"
- "Users won't hit this"

**Right:**

- Edge cases reveal design flaws
- They often become production bugs
- Fix them proactively
- Add tests to prevent regression

---

## Investigation Protocol

### Step 1: Reproduce

```bash
# Run the failing test in isolation
bash scripts/lib/__tests__/error-detection.test.sh

# Or run specific test
# (modify test script to run single test)
```

### Step 2: Understand

- What is the test checking?
- What is the expected behavior?
- What is the actual behavior?
- Why is there a discrepancy?

### Step 3: Root Cause Analysis

- Is the test correct?
- Is the implementation correct?
- Is there a misunderstanding?
- Is there a missing piece?

### Step 4: Fix

- Fix the root cause
- Not the symptom
- Not the test (unless test is wrong)
- Verify fix resolves the issue

### Step 5: Verify

- Test passes
- No regressions
- Documentation updated
- Root cause documented

---

## Examples

### Example 1: Test Failure Dismissed

**What Happened:**

- Test failure dismissed as "doesn't affect core functionality"
- No investigation performed
- Bug left unfixed

**Why It's Wrong:**

- Test exists for a reason
- Failure indicates unexpected behavior
- May hide real bugs
- Creates technical debt

**Correct Approach:**

1. Investigate why test fails
2. Understand expected vs actual behavior
3. Fix the root cause
4. Verify test passes
5. Document the fix

---

### Example 2: Edge Case Ignored

**What Happened:**

- Edge case test fails
- Dismissed as "rare scenario"
- Not fixed

**Why It's Wrong:**

- Edge cases often become production bugs
- They reveal design flaws
- Users do hit edge cases
- Fixing prevents future issues

**Correct Approach:**

1. Understand the edge case
2. Determine if it's a real issue
3. Fix the underlying problem
4. Add tests to prevent regression
5. Document the edge case

---

## Implementation in Framework

### Test Execution

```bash
# All tests must pass
npm run test:error-detection

# If any test fails:
# 1. Investigate immediately
# 2. Fix root cause
# 3. Verify fix
# 4. Document resolution
```

### CI/CD Integration

```yaml
# Tests must pass for deployment
- name: Run tests
  run: npm run test:error-detection
  # Fail build if tests fail
  # No exceptions
```

### Pre-commit Hook

```bash
# Block commits if tests fail
if ! npm run test:error-detection; then
  echo "Tests must pass before commit"
  exit 1
fi
```

---

## Quality Metrics

### Test Coverage

- **Target:** 100% of critical paths
- **Current:** Track and improve
- **Gaps:** Document and address

### Test Pass Rate

- **Target:** 100%
- **Current:** Monitor continuously
- **Failures:** Investigate immediately

### Bug Detection

- **Target:** Catch bugs before production
- **Method:** Comprehensive testing
- **Failure:** Investigate why bug wasn't caught

---

## Enforcement

### Code Reviews

- Reject PRs with failing tests
- Require investigation of failures
- Verify fixes resolve issues

### CI/CD

- Fail builds on test failures
- No exceptions or workarounds
- Require fixes before merge

### Documentation

- Document all test failures
- Record root causes
- Track resolutions

---

## Summary

**Principle:** Every test failure must be investigated and fixed.

**Rationale:** Test failures indicate problems that need resolution.

**Approach:**

1. Investigate immediately
2. Find root cause
3. Fix properly
4. Verify resolution
5. Document learnings

**No exceptions.** No rationalizations. No dismissals.

---

## Related Documents

- `ERROR_DETECTION_FRAMEWORK.md` - Framework details
- `MISTAKE_LOG.md` - Recorded mistakes and learnings
- `REAL_WORLD_EDGE_CASES.md` - Edge cases that matter
