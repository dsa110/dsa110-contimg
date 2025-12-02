import type { TestRunnerConfig } from "@storybook/test-runner";
import { toMatchImageSnapshot } from "jest-image-snapshot";

const config: TestRunnerConfig = {
  setup() {
    expect.extend({ toMatchImageSnapshot });
  },
  async postVisit(page, context) {
    // Wait for any animations to complete
    await page.waitForTimeout(100);

    // Take a screenshot for visual regression testing
    const image = await page.screenshot();
    expect(image).toMatchImageSnapshot({
      customSnapshotsDir: `${process.cwd()}/__snapshots__`,
      customSnapshotIdentifier: `${context.id}`,
      failureThreshold: 0.03, // 3% threshold for acceptable differences
      failureThresholdType: "percent",
    });
  },
};

export default config;
