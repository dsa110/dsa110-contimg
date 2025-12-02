# Storybook Snapshot Testing

This project uses Storybook test-runner with jest-image-snapshot for visual regression testing.

## Overview

Visual regression testing captures screenshots of each Storybook story and compares them against
baseline images to detect unintended visual changes.

## Setup

The test runner is configured in `.storybook/test-runner.ts` with:

- **3% failure threshold**: Small pixel differences (up to 3%) are tolerated
- **Automatic snapshots**: Each story gets a screenshot stored in `__snapshots__/`

## Running Tests

### Prerequisites

Storybook must be running before you can run snapshot tests.

### Commands

```bash
# Start Storybook in one terminal
npm run storybook

# Run snapshot tests (in another terminal)
npm run test:storybook

# Update snapshots when intentional visual changes are made
npm run test:storybook:update

# CI mode (builds and serves Storybook, then runs tests)
npm run test:storybook:ci
```

## Workflow

### During Development

1. Make UI changes to components
2. Run `npm run test:storybook` to check for visual regressions
3. If changes are intentional, run `npm run test:storybook:update` to update baselines

### In CI/CD

The `test:storybook:ci` script:

1. Builds the static Storybook
2. Serves it on port 6100
3. Runs all snapshot tests
4. Fails if any visual regressions are detected

## Snapshots Directory

```
__snapshots__/
├── common-card--default-snap.png
├── common-card--with-actions-snap.png
├── storage-diskusagepanel--healthy-snap.png
└── ...
```

## Best Practices

1. **Review snapshot diffs carefully** - Ensure changes are intentional
2. **Commit snapshots to version control** - Baselines should be tracked
3. **Update snapshots atomically** - Update all affected snapshots together
4. **Use meaningful story names** - Snapshot files are named after stories

## Configuration

### Failure Threshold

Adjust the `failureThreshold` in `.storybook/test-runner.ts`:

```typescript
expect(image).toMatchImageSnapshot({
  failureThreshold: 0.03, // 3% - adjust as needed
  failureThresholdType: "percent",
});
```

### Excluding Stories

Add `parameters.snapshot.skip = true` to stories you want to exclude:

```typescript
export const AnimatedStory: Story = {
  parameters: {
    snapshot: { skip: true },
  },
};
```

## Troubleshooting

### Flaky Tests

- Increase `waitForTimeout` in test-runner.ts for animation-heavy components
- Disable animations in Storybook for test stability

### Font Rendering Differences

- Use consistent fonts across CI and local environments
- Consider using Docker for consistent rendering

### CI Failures

- Ensure the Storybook build includes all required assets
- Verify the port (6100) is available in CI environment
