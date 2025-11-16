# Automated TypeScript Error Fixing Tools

## Available Automation Tools

### 1. **ESLint with Auto-fix** (Already Available)
- **What it can fix**: Formatting, some simple rule violations
- **What it CANNOT fix**: Unused imports/variables (TS6133) - detects but doesn't auto-remove for safety
- **Usage**: `npx eslint --fix src/`

### 2. **eslint-plugin-unused-imports** (Can Install)
- **What it can fix**: Automatically removes unused imports
- **Install**: `npm install -D eslint-plugin-unused-imports`
- **Usage**: Configure in eslint.config.js, then `npx eslint --fix`

### 3. **ts-prune** (Can Install)
- **What it can fix**: Finds unused exports (different from unused variables)
- **Install**: `npm install -D ts-prune`
- **Usage**: `npx ts-prune`

### 4. **TypeScript Compiler** (Already Available)
- **What it can fix**: Nothing automatically - only reports errors
- **Usage**: `npx tsc -b` (for checking)

### 5. **Custom Scripts** (Can Create)
- Pattern-based fixes for common error types
- Type assertion additions
- Null coalescing additions

## Current Error Breakdown

- **TS6133 (Unused variables)**: 92 errors - Can be partially automated
- **TS2322/TS2345 (Type mismatches)**: 53 errors - Requires context-aware fixes
- **Other errors**: ~92 errors - Various types requiring manual review

## Recommended Approach

### Phase 1: Install and Use eslint-plugin-unused-imports
```bash
npm install -D eslint-plugin-unused-imports
# Then configure in eslint.config.js
# Then run: npx eslint --fix src/
```

### Phase 2: Pattern-Based Script Fixes
For common patterns like:
- Adding `?? undefined` for null coalescing
- Adding type assertions for `unknown` types
- Fixing common prop type mismatches

### Phase 3: Manual Review
For complex type mismatches that require understanding context

