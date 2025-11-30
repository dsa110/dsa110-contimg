import type { Meta, StoryObj } from "@storybook/react";
import AladinLiteViewer from "./AladinLiteViewer";

/**
 * AladinLiteViewer embeds an interactive sky viewer using the Aladin Lite library.
 *
 * Features:
 * - Interactive sky navigation
 * - Multiple survey options
 * - Source markers
 * - Zoom controls
 * - Fullscreen mode
 * - Deferred loading (load on demand)
 */
const meta = {
  title: "Components/Widgets/AladinLiteViewer",
  component: AladinLiteViewer,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof AladinLiteViewer>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default viewer pointing at M31 (Andromeda Galaxy)
 */
export const Default: Story = {
  args: {
    raDeg: 10.68458,
    decDeg: 41.26917,
    fov: 1.0,
    height: 600,
  },
};

/**
 * Viewer showing Crab Nebula with source marker
 */
export const WithSourceMarker: Story = {
  args: {
    raDeg: 83.63308,
    decDeg: 22.0145,
    fov: 0.5,
    sourceName: "Crab Nebula (M1)",
    height: 600,
  },
};

/**
 * Wide field view of the galactic center
 */
export const WideField: Story = {
  args: {
    raDeg: 266.417,
    decDeg: -29.008,
    fov: 5.0,
    height: 600,
  },
};

/**
 * Narrow field view for detailed observation
 */
export const NarrowField: Story = {
  args: {
    raDeg: 180.0,
    decDeg: 0.0,
    fov: 0.1,
    height: 600,
  },
};

/**
 * Custom survey (2MASS color)
 */
export const CustomSurvey: Story = {
  args: {
    raDeg: 83.63308,
    decDeg: 22.0145,
    fov: 1.0,
    survey: "P/2MASS/color",
    height: 600,
  },
};

/**
 * Without fullscreen controls
 */
export const NoFullscreen: Story = {
  args: {
    raDeg: 150.0,
    decDeg: 30.0,
    fov: 1.0,
    showFullscreen: false,
    height: 600,
  },
};

/**
 * Compact viewer
 */
export const Compact: Story = {
  args: {
    raDeg: 200.0,
    decDeg: -10.0,
    fov: 0.5,
    height: 400,
  },
};

/**
 * Tall viewer
 */
export const TallViewer: Story = {
  args: {
    raDeg: 100.0,
    decDeg: 20.0,
    fov: 1.0,
    height: 800,
  },
};

/**
 * Viewer with custom styling
 */
export const CustomStyling: Story = {
  args: {
    raDeg: 45.0,
    decDeg: 15.0,
    fov: 1.0,
    height: 600,
    className: "border-4 border-purple-500 rounded-lg shadow-2xl",
  },
};

/**
 * Multiple viewers in a grid
 */
export const MultipleViewers: Story = {
  render: () => (
    <div className="grid grid-cols-2 gap-4 p-4">
      <AladinLiteViewer
        raDeg={10.68458}
        decDeg={41.26917}
        fov={1.0}
        height={400}
        sourceName="M31"
      />
      <AladinLiteViewer raDeg={83.63308} decDeg={22.0145} fov={0.5} height={400} sourceName="M1" />
      <AladinLiteViewer
        raDeg={201.365}
        decDeg={-43.019}
        fov={2.0}
        height={400}
        sourceName="Centaurus A"
      />
      <AladinLiteViewer raDeg={148.888} decDeg={69.065} fov={1.5} height={400} sourceName="M82" />
    </div>
  ),
};
