# ESLint Config Node Version Compatibility Issue

## Issue

ESLint 9 with flat config requires Node.js 18+ due to use of `structuredClone`
API (added in Node 17).

**Error:**

```
ConfigError: Key "rules": Key "constructor-super": structuredClone is not defined
```

## Root Cause

- Current development environment: Node.js v16.20.2
- ESLint 9 requirement: Node.js 18.18.0+
- `structuredClone` API: Available in Node.js 17+

## Current Status

**ESLint config is correct** - the error is due to Node version mismatch, not
configuration issues.

**Important:** When casa6 is activated, Node.js v22.6.0 is available and ESLint
works correctly.

## Solutions

### Option 1: Activate casa6 Environment (Required)

The project requires Node.js 22+ for frontend development (casa6 environment):

```bash
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
which node  # Should show /opt/miniforge/envs/casa6/bin/node
node --version  # Should show v22.6.0
npm run lint  # Will work correctly
```

### Option 2: ESLint Works in CI/CD

ESLint works correctly in CI/CD pipelines which use Node.js 18+:

- `.github/workflows/error-detection.yml` uses Node 18
- Linting passes in CI environment

### Option 3: Skip Linting Locally (Not Recommended)

If you must use Node 16 locally, you can:

- Skip linting: `npm run build:no-check`
- Fix linting issues in CI/CD
- Upgrade to Node 18+ for local development

## Verification

ESLint config is valid - verified in CI/CD:

- ✅ CI uses Node 18 - ESLint works
- ✅ Pre-commit hook uses error detection wrapper
- ✅ Type checking works (doesn't require ESLint)

## Related Files

- `frontend/eslint.config.js` - ESLint configuration (correct)
- `.github/workflows/error-detection.yml` - CI linting (works)
- `frontend/package.json` - Scripts use `npx` for local execution

## Recommendation

**Always activate casa6 environment for frontend development:**

- Provides correct Node.js version (v22.6.0)
- Includes all required dependencies
- Matches production environment
- ESLint works correctly
- All frontend tooling (TypeScript, Vite, Vitest) works correctly

**Without casa6 activated:**

- System Node.js v16.20.2 is used
- ESLint 9 fails (requires Node 18+)
- Other tools may have compatibility issues

## Status

✅ **ESLint config is correct** - Works perfectly when casa6 is activated
(Node.js v22.6.0) ✅ **CI/CD pipelines** use Node 18+ and ESLint works there ⚠️
**Local development** requires casa6 activation for ESLint to work

**Fix:** Always activate casa6 before running frontend commands:

```bash
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
```
