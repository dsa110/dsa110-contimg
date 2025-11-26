# Prettier Setup and Usage

**Date:** 2025-11-13  
**Status:** Configured and Active

---

## Overview

Prettier is now configured for automatic code formatting across the entire
codebase. It runs automatically on commit (pre-commit hook) and in CI (GitHub
Actions).

---

## Supported File Types

Prettier is configured to format the following file types:

- **JavaScript** (`.js`)
- **TypeScript** (`.ts`)
- **JSX / TSX** (`.jsx`, `.tsx`)
- **JSON** (`.json`)
- **YAML** (`.yaml`, `.yml`)
- **HTML** (`.html`)
- **CSS / SCSS / Less** (`.css`, `.scss`, `.less`)
- **Markdown** (`.md`)
- **GraphQL** (`.graphql`)
- **Vue** (`.vue`)

---

## Configuration

### Root Configuration

- **File:** `.prettierrc` (root directory)
- **Ignore File:** `.prettierignore` (root directory)

### Key Settings

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": false,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

### File-Specific Overrides

- **Markdown:** `printWidth: 80`, `proseWrap: "always"`
- **JSON:** `printWidth: 80`
- **YAML:** Standard formatting

---

## Usage

### Manual Formatting

#### Format All Frontend Files

```bash
cd frontend
npm run format
```

#### Check Formatting (No Changes)

```bash
cd frontend
npm run format:check
```

#### Format Specific Files

```bash
cd frontend
npx prettier --write "src/**/*.ts" "src/**/*.tsx"
```

#### Format Root-Level Files

```bash
npx prettier --write "*.{js,json,yaml,yml,md}"
```

### Automatic Formatting

#### Pre-Commit Hook

Prettier runs automatically on commit via the `.husky/pre-commit` hook:

1. **Staged files are automatically formatted** before commit
2. **Formatting check fails the commit** if files need formatting
3. **Only checks files that are staged** (efficient)

**What happens:**

- Prettier formats staged files automatically
- If formatting fails, commit is blocked with helpful error message
- You can re-stage and commit after formatting

#### CI/CD Integration

Prettier runs in GitHub Actions on:

- **Pull Requests** (when relevant files change)
- **Push to main/develop** (when relevant files change)

**Workflow:** `.github/workflows/prettier-check.yml`

**What happens:**

- Prettier checks formatting in CI
- PRs fail if formatting is incorrect
- Clear error messages indicate which files need formatting

---

## Ignored Files

The following are excluded from Prettier formatting (see `.prettierignore`):

- `node_modules/`
- Build outputs (`dist/`, `build/`, etc.)
- Log files
- Environment files (`.env*`)
- IDE files
- Large data files (`.fits`, `.uvh5`, etc.)
- Package manager lock files

---

## Troubleshooting

### Pre-Commit Hook Fails

**Error:** "Prettier formatting check failed"

**Solution:**

```bash
# Format the files manually
cd frontend
npm run format

# Or format specific files
npx prettier --write "path/to/file.ts"

# Re-stage and commit
git add .
git commit
```

### CI Fails

**Error:** Prettier check fails in GitHub Actions

**Solution:**

1. Run Prettier locally:
   ```bash
   cd frontend
   npm run format
   ```
2. Commit the formatted files
3. Push to trigger CI again

### Prettier Not Found

**Error:** "npx not found" or "prettier not found"

**Solution:**

```bash
# Install dependencies
cd frontend
npm install

# Verify Prettier is available
npx prettier --version
```

---

## Best Practices

1. **Let Prettier format automatically** - Don't manually format code
2. **Run format before committing** - Use `npm run format` if pre-commit hook is
   disabled
3. **Check CI before merging** - Ensure Prettier passes in CI
4. **Use consistent settings** - Don't override Prettier config locally

---

## Integration Points

### Pre-Commit Hook

- **Location:** `.husky/pre-commit`
- **Runs:** Before every commit
- **Action:** Formats staged files, blocks commit if formatting fails

### CI/CD

- **Location:** `.github/workflows/prettier-check.yml`
- **Runs:** On PRs and pushes to main/develop
- **Action:** Checks formatting, fails PR if incorrect

### Package Scripts

- **Location:** `frontend/package.json`
- **Scripts:**
  - `npm run format` - Format all files
  - `npm run format:check` - Check formatting without changes

---

## Summary

✅ **Prettier is fully configured** for all supported file types  
✅ **Pre-commit hook** automatically formats staged files  
✅ **CI integration** ensures consistent formatting  
✅ **Easy manual commands** available via npm scripts

All code is now automatically formatted according to consistent standards!
