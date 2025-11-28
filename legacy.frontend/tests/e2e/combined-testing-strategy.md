# Combined Testing Strategy: Playwright + Cursor Browser + chrome-devtools

## Overview

This document outlines how to use three complementary browser testing tools
together:

1. **Playwright MCP** - Automated E2E tests (CI/CD, regression testing)
2. **Cursor Browser Extension** - Interactive browser automation (quick checks,
   manual testing)
3. **chrome-devtools MCP** - Advanced debugging & inspection (performance,
   console, network)

## Tool Roles

### Playwright MCP

- **Purpose**: Automated, repeatable E2E tests
- **Best for**:
  - Regression testing
  - CI/CD pipelines
  - Comprehensive test coverage
  - Screenshot comparisons
- **Limitations**: Requires test files, runs in isolated browser context

### Cursor Browser Extension

- **Purpose**: Interactive browser automation
- **Best for**:
  - Quick visual verification
  - Ad-hoc testing
  - Real-time interaction
  - Immediate feedback
- **Limitations**: Single browser instance, manual trigger

### chrome-devtools MCP

- **Purpose**: Advanced debugging and inspection
- **Best for**:
  - Console log analysis
  - Network request inspection
  - Performance profiling
  - Element inspection
  - Debugging complex issues
- **Limitations**: Requires MCP server registration, Docker-based

## Testing Workflow

### Phase 1: Quick Visual Check (Cursor Browser Extension)

1. Navigate to dashboard page
2. Take snapshot to verify layout
3. Check for obvious visual issues
4. Verify key elements are present

### Phase 2: Automated Testing (Playwright)

1. Run comprehensive E2E test suite
2. Verify all critical paths
3. Check for regressions
4. Generate test reports

### Phase 3: Deep Debugging (chrome-devtools)

1. Inspect console messages for errors
2. Analyze network requests
3. Check performance metrics
4. Debug specific issues found in Phase 1 or 2

## Example: Testing Sky View Page

### Step 1: Cursor Browser Extension (Quick Check)

```typescript
// Navigate and verify
browser_navigate("http://localhost:5174/sky");
browser_snapshot(); // Check layout
browser_console_messages(); // Quick error check
```

### Step 2: Playwright (Automated Test)

```typescript
// Run comprehensive test
test("Sky View page loads correctly", async ({ page }) => {
  await page.goto("/sky");
  await expect(page.locator('[data-testid="sky-viewer"]')).toBeVisible();
  // ... more assertions
});
```

### Step 3: chrome-devtools (Deep Debug)

```typescript
// If issues found, debug with chrome-devtools
navigate_page({ url: "http://localhost:5174/sky" });
list_console_messages({ types: ["error"] });
list_network_requests({ resourceTypes: ["xhr", "fetch"] });
take_snapshot({ verbose: true });
```

## Best Practices

1. **Start with Cursor Browser** for quick visual verification
2. **Run Playwright tests** for comprehensive coverage
3. **Use chrome-devtools** when issues are found or for performance analysis
4. **Avoid conflicts**: Don't run multiple tools on the same browser instance
   simultaneously
5. **Clear browser locks** if tools conflict:
   `rm -rf ~/.cache/ms-playwright/mcp-*`

## Conflict Resolution

If browser locks occur:

```bash
# Check for locks
ls -la ~/.cache/ms-playwright/

# Kill conflicting processes
ps aux | grep playwright | grep -v grep
kill <PID>

# Remove locks
rm -rf ~/.cache/ms-playwright/mcp-*
```

## Dashboard URLs

- **Development**: http://localhost:5174
- **Sky View**: http://localhost:5174/sky
- **Dashboard**: http://localhost:5174/dashboard
- **Control**: http://localhost:5174/control

## Test Files

- **Playwright E2E**: `frontend/tests/e2e/*.spec.ts`
- **Playwright Unit**: `frontend/tests/playwright/*.spec.ts`
- **Config**: `frontend/playwright.config.ts`
