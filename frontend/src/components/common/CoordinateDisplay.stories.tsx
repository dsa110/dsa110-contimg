import type { Meta, StoryObj } from "@storybook/react-vite";
import CoordinateDisplay from "./CoordinateDisplay";

const meta: Meta<typeof CoordinateDisplay> = {
  title: "Common/CoordinateDisplay",
  component: CoordinateDisplay,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof CoordinateDisplay>;

export const Default: Story = {
  args: {
    raDeg: 83.633,
    decDeg: 22.0145,
  },
};

export const WithLabel: Story = {
  args: {
    raDeg: 83.633,
    decDeg: 22.0145,
    label: "Phase Center",
  },
};

export const Compact: Story = {
  args: {
    raDeg: 83.633,
    decDeg: 22.0145,
    compact: true,
  },
};

export const CompactWithLabel: Story = {
  args: {
    raDeg: 83.633,
    decDeg: 22.0145,
    compact: true,
    label: "Position",
  },
};

export const WithoutDecimal: Story = {
  args: {
    raDeg: 187.7059,
    decDeg: 12.3911,
    showDecimal: false,
  },
};

export const SouthernHemisphere: Story = {
  args: {
    raDeg: 201.365,
    decDeg: -43.0192,
  },
};

export const NearPole: Story = {
  args: {
    raDeg: 45.0,
    decDeg: 89.264,
    label: "Near Celestial Pole",
  },
};

export const GalacticCenter: Story = {
  args: {
    raDeg: 266.405,
    decDeg: -28.936,
    label: "Galactic Center",
  },
};

export const CrabNebula: Story = {
  args: {
    raDeg: 83.633,
    decDeg: 22.0145,
    label: "Crab Nebula (M1)",
  },
};

export const VirgoA: Story = {
  args: {
    raDeg: 187.7059,
    decDeg: 12.3911,
    label: "Virgo A (M87)",
  },
};
