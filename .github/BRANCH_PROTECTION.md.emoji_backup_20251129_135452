# Branch Protection Recommendations

**Note:** These settings must be configured in GitHub repository settings. This
document serves as a reference.

## Recommended Branch Protection Rules

### Main Branch (`main`)

**Required Settings:**

- ✅ Require a pull request before merging
  - Required approvals: 1
  - Dismiss stale pull request approvals when new commits are pushed
  - Require review from Code Owners (if CODEOWNERS file exists)
- ✅ Require status checks to pass before merging
  - Required checks:
    - `environment-validation` (environment validation workflow)
    - `prettier-check` (Prettier formatting check)
    - `error-detection` (error detection workflow)
    - Any other required CI checks
- ✅ Require conversation resolution before merging
- ✅ Require linear history (no merge commits)
- ✅ Include administrators (enforce rules for admins too)

**Optional but Recommended:**

- ✅ Restrict pushes that create files larger than 10MB
- ✅ Require signed commits (if GPG signing is used)

### Develop Branch (`develop`)

**Required Settings:**

- ✅ Require a pull request before merging
  - Required approvals: 1
- ✅ Require status checks to pass before merging
  - Required checks:
    - `environment-validation`
    - `prettier-check`
    - `error-detection`
- ✅ Require conversation resolution before merging

**Optional:**

- ⚠️ Allow force pushes (for rebasing, but risky)
- ⚠️ Allow deletions (for cleanup, but risky)

## Status Checks Configuration

### Required Checks

These checks must pass before merging:

1. **environment-validation**
   - Validates setup was run
   - Checks git hooks
   - Verifies Prettier installation
   - Checks documentation location

2. **prettier-check**
   - Validates code formatting
   - Ensures consistent style

3. **error-detection**
   - Runs error detection checks
   - Validates code quality

### Optional Checks

These checks provide information but don't block merges:

- Code quality checks
- Test coverage reports
- Documentation builds

## Code Owners

If using CODEOWNERS file, configure:

- Require review from Code Owners
- Automatically request review from Code Owners

## How to Configure

1. Go to repository Settings
2. Navigate to Branches
3. Add rule for `main` branch
4. Configure settings as above
5. Repeat for `develop` branch

## Enforcement

**Current Status:** These are recommendations. Actual enforcement requires
GitHub repository admin access.

**To Implement:**

- Repository admin must configure in GitHub Settings
- Cannot be enforced via files in repository
- This document serves as documentation and checklist

## Related Documentation

- `.github/CODE_REVIEW_CHECKLIST.md` - Code review guidelines
- `.github/pull_request_template.md` - PR template with requirements
- `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md` - Developer warnings
