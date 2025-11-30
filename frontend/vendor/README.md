# Vendor Directory

This directory contains vendored (locally packaged) dependencies that cannot be installed via npm for various reasons.

## Contents

### aladin-lite-3.7.3-beta.tgz

**Why vendored:**
- The published npm package for Aladin Lite v3 is in beta and not yet stable on npm registry
- Direct dependency on the GitHub repository was causing installation issues
- The WASM binary needs to be properly bundled with the application

**Version:** 3.7.3-beta

**Source:** https://github.com/cds-astro/aladin-lite

**Last updated:** Check package.json for version reference

**How to update:**
1. Download the latest release from the Aladin Lite GitHub releases page
2. Test thoroughly in development environment
3. Replace the .tgz file in this directory
4. Update package.json to reference the new version
5. Run `npm install` to update the lock file
6. Test all sky viewer functionality (especially WASM initialization)

**Usage in code:**
```typescript
import A from "aladin-lite";
```

**Known issues:**
- WASM module requires special initialization (`await A.init`)
- Type definitions are incomplete (see AladinInstance interface extensions)

## Adding New Vendored Packages

Only vendor packages when absolutely necessary. Prefer npm packages whenever possible.

Valid reasons to vendor:
- Package not available on npm
- Specific version needed that's not published
- Custom build or patches required
- Binary/WASM dependencies with complex build processes

When adding a new vendored package:
1. Add it to this directory
2. Update package.json to reference it: `"package-name": "file:vendor/package.tgz"`
3. Document it in this README
4. Add update instructions
5. Consider contributing fixes upstream to avoid vendoring long-term

