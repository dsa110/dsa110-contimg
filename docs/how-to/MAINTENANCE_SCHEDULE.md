# Maintenance Schedule: Output Suppression Prevention

This document outlines the regular maintenance tasks for the output suppression
prevention system.

---

## Weekly Tasks

### 1. Run Audit

**When:** Every Monday (or start of week)

**Command:**

```bash
./scripts/maintenance-audit-output-suppression.sh
```

**What it does:**

- Audits all suppression patterns in codebase
- Saves results to `docs/dev/audits/output-suppression-audit-YYYYMMDD.txt`
- Checks for non-whitelisted suppressions
- Provides statistics

**Time:** ~2 minutes

**Output:**

- Audit file with all suppressions
- Summary of whitelist statistics
- List of non-whitelisted suppressions (if any)

---

## Monthly Tasks

### 1. Whitelist Review

**When:** First Monday of each month

**Tasks:**

1. Review all whitelist entries in `.output-suppression-whitelist`
2. Check if files still exist
3. Verify line numbers are still correct
4. Remove obsolete entries
5. Update categories if needed

**Command:**

```bash
# Check for missing files
while IFS=: read -r file line rest; do
    if [[ ! "$file" =~ ^# ]] && [[ -n "$file" ]] && [[ ! -f "$file" ]]; then
        echo "Missing: $file"
    fi
done < .output-suppression-whitelist
```

**Time:** ~15 minutes

---

### 2. Pattern Analysis

**When:** First Monday of each month

**Tasks:**

1. Review audit results from past month
2. Identify new patterns
3. Document common legitimate uses
4. Update exception guidelines if needed

**Command:**

```bash
# Compare audits
ls -t docs/dev/audits/output-suppression-audit-*.txt | head -2 | xargs diff
```

**Time:** ~10 minutes

---

## Quarterly Tasks

### 1. Comprehensive Review

**When:** First Monday of each quarter

**Tasks:**

1. Full audit of all suppressions
2. Review all whitelist entries
3. Check for patterns that should be fixed
4. Update documentation
5. Team review meeting

**Time:** ~1 hour

---

### 2. Documentation Update

**When:** First Monday of each quarter

**Tasks:**

1. Update `internal/docs/dev/imported/OUTPUT_SUPPRESSION_EXCEPTIONS.md` with new
   patterns
2. Update team training materials
3. Review and update guidelines

**Time:** ~30 minutes

---

## When Code Changes

### If You Modify a File with Whitelisted Suppression

**Tasks:**

1. Check if suppression is still needed
2. Update line number if code moved
3. Remove entry if suppression removed
4. Add entry if new suppression added (with justification)

**Time:** ~2 minutes per file

---

### If You Add New Suppression

**Tasks:**

1. Determine if suppression is legitimate
2. Choose appropriate category
3. Add to whitelist with clear reason
4. Commit with whitelist entry

**Time:** ~3 minutes

---

## Automated Checks

### Pre-Commit Hook

**Runs:** Automatically on every commit

**What it checks:**

- All staged shell scripts for suppression patterns
- Whitelist for each suppression
- Blocks commit if not whitelisted

**No action needed** - runs automatically

---

### CI/CD Integration (Future)

**Planned:** Add to CI/CD pipeline

**What it would do:**

- Run audit on every PR
- Check for non-whitelisted suppressions
- Report statistics
- Block merge if issues found

---

## Maintenance Checklist

### Weekly

- [ ] Run maintenance audit script
- [ ] Review audit results
- [ ] Check for non-whitelisted suppressions

### Monthly

- [ ] Review whitelist entries
- [ ] Check for missing files
- [ ] Analyze patterns
- [ ] Update statistics

### Quarterly

- [ ] Comprehensive review
- [ ] Update documentation
- [ ] Team review meeting
- [ ] Pattern analysis

### As Needed

- [ ] Update whitelist when code changes
- [ ] Remove obsolete entries
- [ ] Add new legitimate exceptions
- [ ] Fix non-legitimate suppressions

---

## Tools Reference

### Audit Script

```bash
./scripts/maintenance-audit-output-suppression.sh
```

- Runs full audit
- Saves results to dated file
- Provides summary statistics

### Fix Script

```bash
./scripts/fix-non-legitimate-suppressions.sh
```

- Identifies problematic suppressions
- Suggests fixes
- Helps prioritize cleanup

### Manual Audit

```bash
./scripts/audit-output-suppression.sh
```

- Quick audit without saving
- Useful for ad-hoc checks

---

## Reporting

### Monthly Report Template

```markdown
# Output Suppression Audit Report - [Month Year]

## Summary

- Total suppressions: [count]
- Whitelist entries: [count]
- Non-whitelisted: [count]

## Changes

- Added: [count] entries
- Removed: [count] entries
- Updated: [count] entries

## Issues Found

- [List any issues]

## Recommendations

- [Any recommendations]
```

---

## Escalation

### If Non-Whitelisted Suppressions Found

**Action:**

1. Review each suppression
2. Determine if legitimate
3. Add to whitelist if needed
4. Fix code if not legitimate
5. Document decision

**Timeframe:** Within 1 week

---

### If Whitelist Becomes Too Large

**Action:**

1. Review all entries
2. Identify patterns
3. Consider code fixes instead
4. Remove obsolete entries
5. Update guidelines

**Threshold:** >200 entries

---

## Success Metrics

**Track:**

- Number of whitelist entries (should be stable or decreasing)
- Number of non-whitelisted suppressions (should be zero)
- Number of suppressions in codebase (should be stable)
- Time to resolve issues (should be <1 week)

---

## Resources

- **Whitelist:** `.output-suppression-whitelist`
- **Audit script:** `scripts/maintenance-audit-output-suppression.sh`
- **Fix script:** `scripts/fix-non-legitimate-suppressions.sh`
- **Documentation:**
  `internal/docs/dev/imported/OUTPUT_SUPPRESSION_EXCEPTIONS.md`
- **Team training:** `docs/how-to/TEAM_TRAINING_OUTPUT_SUPPRESSION.md`

---

**Remember:** Regular maintenance ensures the system continues to work
effectively and prevents technical debt from accumulating.
