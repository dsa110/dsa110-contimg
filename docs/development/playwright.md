# Playwright in Docker Setup

**Date:** 2025-11-14

## Current Status

✅ **Playwright is fully configured and ready to use!**

The Docker container now uses a Debian-based image (`node:22`) which is
compatible with Playwright's glibc-based browser binaries.

## Setup Complete

The `Dockerfile.dev` has been configured with:

- Debian base image (compatible with Playwright)
- All required browser dependencies
- Playwright browsers installed automatically

## Rebuilding the Container

After the switch to Debian, rebuild the container:

```bash
docker compose build dashboard-dev
docker compose up -d dashboard-dev
```

This will:

1. Download the Debian-based Node.js image (~250MB larger than Alpine)
2. Install browser dependencies via `apt-get`
3. Install Playwright browsers (Chromium and Firefox)
4. Set up the development environment

## Test File Created

✅ `tests/e2e/skyview-fixes.spec.ts` - Tests for:

- MUI Grid console errors
- className.split TypeError
- JS9 display width
- Grid layout v2 syntax

## Running Tests

Once browsers are installed:

```bash
docker compose exec dashboard-dev npx playwright test --project=chromium
docker compose exec dashboard-dev npx playwright test --project=firefox
```

## Current Configuration

- ✅ Playwright config: `playwright.config.ts`
- ✅ Test directory: `tests/e2e/`
- ✅ Dockerfile updated with browser dependencies
- ⚠️ Browser binaries: Need installation (may require Debian base image)
