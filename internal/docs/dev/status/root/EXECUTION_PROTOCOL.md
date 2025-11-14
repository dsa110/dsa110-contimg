# Execution Protocol - Browser Testing & Deployment

## Environment Requirements

### Frontend Work (Current Task)

- **Environment**: Node.js / npm (system-level)
- **NOT Required**: casa6 conda environment
- **Commands**: `npm run dev`, `npm run build`, `npm test`,
  `npx playwright test`
- **Location**: `/data/dsa110-contimg/frontend/`

### Backend/Python Work (If Needed)

- **Environment**: casa6 conda environment
- **Python Path**: `/opt/miniforge/envs/casa6/bin/python`
- **Activation**: `conda activate casa6` or use full path

## Mistake Tracking Protocol

### Definition of a Mistake

Any action that slows down work, including:

- Running wrong command
- Forgetting to check environment
- Syntax errors in commands
- Wrong file paths
- Missing prerequisites
- Incorrect assumptions
- Not verifying before proceeding

### Mistake Log Format

```
[MISTAKE] Phase X.Y: Description
  - What happened: [details]
  - Impact: [time wasted, incorrect result, etc.]
  - Correction: [what was done to fix]
```

## Enforcement Mechanisms by Phase

### Phase 1: Pre-Deployment Validation

**Checkpoints:**

- [ ] Verify Node.js environment before running npm commands
- [ ] Check current directory before each command
- [ ] Verify file exists before reading/editing
- [ ] Confirm TypeScript errors are from our code, not unrelated files
- [ ] Validate each fix before moving to next step

**Mistake Prevention:**

- Always `cd` to correct directory first
- Use `pwd` to confirm location
- Check file existence with `ls` or `test -f`
- Read error messages fully before fixing
- Test fixes immediately after applying

### Phase 2: Browser Testing

**Checkpoints:**

- [ ] Verify dev server is running before tests
- [ ] Check test file paths are correct
- [ ] Confirm Playwright is installed
- [ ] Verify test URLs match actual server
- [ ] Check browser console after each test

**Mistake Prevention:**

- Start dev server first, wait for confirmation
- Use absolute paths for test files
- Verify test syntax before running
- Check test output for actual failures vs. environment issues
- Document any test flakiness

### Phase 3: Production Build

**Checkpoints:**

- [ ] Verify all dependencies installed
- [ ] Check build configuration
- [ ] Confirm output directory exists
- [ ] Validate build artifacts
- [ ] Compare bundle sizes

**Mistake Prevention:**

- Run `npm install` if package.json changed
- Review build config before building
- Check dist/ directory after build
- Verify no build warnings are critical
- Test production build locally before deployment

### Phase 4: Deployment

**Checkpoints:**

- [ ] Verify deployment configuration
- [ ] Check environment variables
- [ ] Confirm backup exists (if applicable)
- [ ] Validate deployment scripts
- [ ] Test deployment in staging first (if available)

**Mistake Prevention:**

- Review config files before deployment
- Test deployment scripts dry-run first
- Verify rollback procedure exists
- Check deployment logs immediately
- Validate deployment success before proceeding

### Phase 5: Post-Deployment

**Checkpoints:**

- [ ] Verify production URL accessible
- [ ] Check error logs
- [ ] Test critical functionality
- [ ] Monitor for issues
- [ ] Document deployment

**Mistake Prevention:**

- Test production immediately after deployment
- Check multiple browsers/devices
- Monitor logs for first 15 minutes
- Have rollback plan ready
- Document everything

## Execution Checklist Template

Before each command:

1. [ ] Am I in the right directory?
2. [ ] Is the right environment active?
3. [ ] Do I have the prerequisites?
4. [ ] Is this the right command?
5. [ ] What do I expect to happen?

After each command:

1. [ ] Did it work as expected?
2. [ ] Any errors or warnings?
3. [ ] Do I need to verify the result?
4. [ ] Should I log this step?

## Self-Correction Protocol

When a mistake is identified:

1. **Stop immediately** - Don't compound the mistake
2. **Log the mistake** - Record what happened
3. **Assess impact** - How much time/effort wasted?
4. **Fix immediately** - Correct the issue
5. **Verify fix** - Confirm it's actually fixed
6. **Learn** - Update protocol to prevent recurrence

## Progress Tracking

After each phase:

- [ ] Review mistake log
- [ ] Identify patterns
- [ ] Update enforcement mechanisms
- [ ] Document learnings
- [ ] Adjust next phase approach
