import type { Meta, StoryObj } from "@storybook/react-vite";
import { AntennaFlaggingSummary } from "./AntennaFlaggingSummary";

const meta: Meta<typeof AntennaFlaggingSummary> = {
  title: "Calibration/AntennaFlaggingSummary",
  component: AntennaFlaggingSummary,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof AntennaFlaggingSummary>;

// Generate antenna data for DSA-110 (110 antennas)
function generateAntennaData(
  pattern: "healthy" | "some-flagged" | "many-flagged"
): Record<string, number> {
  const data: Record<string, number> = {};
  for (let i = 1; i <= 110; i++) {
    const antName = `ant${i}`;
    let percent: number;
    switch (pattern) {
      case "healthy":
        percent = Math.random() * 5;
        break;
      case "some-flagged":
        percent = i % 10 === 0 ? 25 + Math.random() * 30 : Math.random() * 10;
        break;
      case "many-flagged":
        percent =
          Math.random() < 0.3 ? 40 + Math.random() * 50 : Math.random() * 20;
        break;
    }
    data[antName] = percent;
  }
  return data;
}

export const Healthy: Story = {
  args: {
    antennaFlagging: generateAntennaData("healthy"),
  },
};

export const SomeFlagged: Story = {
  args: {
    antennaFlagging: generateAntennaData("some-flagged"),
  },
};

export const ManyFlagged: Story = {
  args: {
    antennaFlagging: generateAntennaData("many-flagged"),
  },
};

export const CustomThresholds: Story = {
  args: {
    antennaFlagging: generateAntennaData("some-flagged"),
    warningThreshold: 10,
    maxThreshold: 30,
  },
};

export const SmallArray: Story = {
  args: {
    antennaFlagging: {
      ant1: 2.5,
      ant2: 5.1,
      ant3: 45.2,
      ant4: 8.3,
      ant5: 12.1,
      ant6: 3.2,
      ant7: 62.5,
      ant8: 1.8,
    },
  },
};
