import type { Meta, StoryObj } from "@storybook/react-vite";
import QAMetrics from "./QAMetrics";

const meta: Meta<typeof QAMetrics> = {
  title: "Common/QAMetrics",
  component: QAMetrics,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
  argTypes: {
    grade: {
      control: "select",
      options: ["good", "warn", "fail", undefined],
    },
  },
};

export default meta;
type Story = StoryObj<typeof QAMetrics>;

export const Good: Story = {
  args: {
    grade: "good",
    summary: "All metrics within acceptable range",
    noiseJy: 0.000045,
    dynamicRange: 15000,
    beamMajorArcsec: 15.2,
    beamMinorArcsec: 12.8,
    beamPaDeg: 45,
  },
};

export const Warning: Story = {
  args: {
    grade: "warn",
    summary: "Elevated noise level detected",
    noiseJy: 0.00012,
    dynamicRange: 8000,
    beamMajorArcsec: 16.5,
    beamMinorArcsec: 11.2,
    beamPaDeg: -30,
  },
};

export const Failed: Story = {
  args: {
    grade: "fail",
    summary: "Severe imaging artifacts present",
    noiseJy: 0.0005,
    dynamicRange: 2000,
    beamMajorArcsec: 22.0,
    beamMinorArcsec: 8.5,
    beamPaDeg: 12,
  },
};

export const Compact: Story = {
  args: {
    grade: "good",
    noiseJy: 0.000045,
    dynamicRange: 15000,
    compact: true,
  },
};

export const MinimalInfo: Story = {
  args: {
    grade: "good",
    summary: "Image processed successfully",
  },
};

export const WithPeakFlux: Story = {
  args: {
    grade: "good",
    noiseJy: 0.00005,
    dynamicRange: 20000,
    peakFluxJy: 0.85,
    beamMajorArcsec: 14.0,
    beamMinorArcsec: 13.5,
    beamPaDeg: 0,
  },
};

export const MicroJyNoise: Story = {
  args: {
    grade: "good",
    summary: "Very low noise",
    noiseJy: 0.000008,
    dynamicRange: 50000,
  },
};

export const MilliJyNoise: Story = {
  args: {
    grade: "warn",
    summary: "Higher than expected noise",
    noiseJy: 0.002,
    dynamicRange: 500,
  },
};
