# Next Steps for Dashboard Testing

## Current Status

✅ **Phase 1: Cursor Browser Extension** - Complete

- Dashboard accessible and functional
- API endpoints working correctly
- Data loading successfully

✅ **Phase 2: Playwright Automated Tests** - Complete

- 7/7 tests passing
- Core functionality verified
- Test infrastructure operational

✅ **Phase 3: chrome-devtools MCP** - Ready

- Server running in Docker
- Available for deep debugging

## Immediate Next Steps

### 1. CI/CD Integration

**Goal:** Automate test execution in CI pipeline

**Tasks:**

- [ ] Add Playwright test step to CI workflow (GitHub Actions/GitLab CI)
- [ ] Configure Docker-based test execution
- [ ] Set up test artifacts (HTML reports, screenshots, videos)
- [ ] Add test failure notifications (Slack, email, etc.)
- [ ] Configure test retry logic for flaky tests

**Files to create/modify:**

- `.github/workflows/test.yml` or `.gitlab-ci.yml`
- `frontend/playwright.config.ts` (CI-specific settings)

### 2. Test Coverage Expansion

**Goal:** Increase test coverage across dashboard pages

**Tasks:**

- [ ] Add tests for Dashboard page (`/dashboard`)
- [ ] Add tests for Control page (`/control`)
- [ ] Add tests for Streaming page (`/streaming`)
- [ ] Add tests for Data Browser page (`/data`)
- [ ] Add tests for QA Visualization page (`/qa`)
- [ ] Add interaction tests (button clicks, form submissions)
- [ ] Add image selection and JS9 interaction tests
- [ ] Add error handling and edge case tests

**Test files to create:**

- `frontend/tests/e2e/dashboard-page.spec.ts`
- `frontend/tests/e2e/control-page.spec.ts`
- `frontend/tests/e2e/streaming-page.spec.ts`
- `frontend/tests/e2e/data-browser.spec.ts`
- `frontend/tests/e2e/interactions.spec.ts`

### 3. Performance Testing

**Goal:** Ensure dashboard meets performance requirements

**Tasks:**

- [ ] Use chrome-devtools MCP for performance profiling
- [ ] Measure page load times for each route
- [ ] Check Core Web Vitals (LCP, FID, CLS)
- [ ] Monitor API response times
- [ ] Test with large datasets
- [ ] Profile memory usage
- [ ] Identify performance bottlenecks

**Tools:**

- chrome-devtools MCP (`performance_start_trace`, `performance_stop_trace`)
- Playwright performance API
- Lighthouse CI

### 4. Documentation

**Goal:** Document testing strategy and workflows

**Tasks:**

- [ ] Document test strategy in `frontend/tests/e2e/README.md`
- [ ] Update main README with testing instructions
- [ ] Create test debugging guide
- [ ] Document test maintenance procedures
- [ ] Add examples for writing new tests
- [ ] Document CI/CD test execution

**Files to create:**

- `frontend/tests/e2e/README.md`
- `docs/testing-guide.md`

## Medium-Term Steps

### 5. Visual Regression Testing

**Goal:** Detect visual changes automatically

**Tasks:**

- [ ] Set up screenshot comparison tests
- [ ] Add visual diff detection
- [ ] Test responsive layouts across viewports
- [ ] Configure visual test baselines
- [ ] Set up visual test review process

**Tools:**

- Playwright screenshot comparison
- Percy or Chromatic (optional)

### 6. Accessibility Testing

**Goal:** Ensure dashboard is accessible

**Tasks:**

- [ ] Install `@axe-core/playwright`
- [ ] Add a11y tests to test suite
- [ ] Verify keyboard navigation
- [ ] Check ARIA labels and roles
- [ ] Test with screen readers
- [ ] Fix accessibility issues

**Example:**

```typescript
import { injectAxe, checkA11y } from "axe-playwright";

test("Dashboard is accessible", async ({ page }) => {
  await page.goto("/sky");
  await injectAxe(page);
  await checkA11y(page);
});
```

### 7. Cross-Browser Testing

**Goal:** Ensure compatibility across browsers

**Tasks:**

- [ ] Run tests on Firefox (already configured)
- [ ] Run tests on WebKit/Safari (already configured)
- [ ] Test on mobile viewports (already configured)
- [ ] Fix browser-specific issues
- [ ] Document browser support matrix

**Note:** Playwright config already includes Firefox, WebKit, and mobile
viewports.

### 8. API Testing Enhancement

**Goal:** Comprehensive API contract testing

**Tasks:**

- [ ] Add API contract tests
- [ ] Test error scenarios (404, 500, etc.)
- [ ] Verify WebSocket connections
- [ ] Test API rate limiting
- [ ] Test authentication/authorization
- [ ] Add API response validation

## Long-Term Steps

### 9. Monitoring & Observability

**Goal:** Track test health and performance

**Tasks:**

- [ ] Set up error tracking (Sentry, etc.)
- [ ] Monitor test flakiness rates
- [ ] Track test execution times
- [ ] Set up dashboards for test metrics
- [ ] Alert on test failures
- [ ] Track test coverage trends

### 10. Test Maintenance

**Goal:** Keep tests healthy and up-to-date

**Tasks:**

- [ ] Schedule regular test reviews
- [ ] Update tests for new features
- [ ] Refactor flaky tests
- [ ] Keep dependencies updated
- [ ] Remove obsolete tests
- [ ] Optimize slow tests

## Quick Wins (Can Do Now)

1. **Add npm script for tests:**

   ```json
   "test:e2e": "playwright test",
   "test:e2e:ui": "playwright test --ui"
   ```

2. **Create test helper utilities:**
   - `frontend/tests/e2e/helpers/page-helpers.ts`
   - `frontend/tests/e2e/helpers/api-helpers.ts`

3. **Add test data fixtures:**
   - `frontend/tests/e2e/fixtures/test-data.ts`

4. **Set up test tags:**
   - `@smoke` - Quick smoke tests
   - `@regression` - Full regression suite
   - `@slow` - Long-running tests

## Priority Order

1. **High Priority:**
   - CI/CD Integration (#1)
   - Test Coverage Expansion (#2)
   - Documentation (#4)

2. **Medium Priority:**
   - Performance Testing (#3)
   - Visual Regression (#5)
   - Accessibility Testing (#6)

3. **Lower Priority:**
   - Cross-Browser Testing (#7)
   - API Testing Enhancement (#8)
   - Monitoring (#9)
   - Test Maintenance (#10)

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Testing Library Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [chrome-devtools MCP Documentation](https://github.com/chrome-devtools-mcp)
