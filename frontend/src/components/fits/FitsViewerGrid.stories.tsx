import type { Meta, StoryObj } from "@storybook/react";
import FitsViewerGrid from "./FitsViewerGrid";
import { fn } from "@storybook/test";

/**
 * FitsViewerGrid displays multiple FITS images in a synchronized grid layout.
 * 
 * Features:
 * - Multiple column layouts (1-4 columns)
 * - Synchronized pan and zoom across viewers
 * - Individual panel labels
 * - Coordinate click handling
 * - Adjustable viewer size
 * 
 * Note: This component requires actual FITS files. The stories use placeholder URLs.
 */
const meta = {
  title: "Components/Widgets/FitsViewerGrid",
  component: FitsViewerGrid,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
  args: {
    onCoordinateClick: fn(),
  },
} satisfies Meta<typeof FitsViewerGrid>;

export default meta;
type Story = StoryObj<typeof meta>;

// Placeholder FITS URLs (would be actual file URLs in production)
const sampleFitsUrls = [
  "/api/fits/example1.fits",
  "/api/fits/example2.fits",
  "/api/fits/example3.fits",
  "/api/fits/example4.fits",
];

/**
 * Default 2-column grid
 */
export const TwoColumn: Story = {
  args: {
    fitsUrls: sampleFitsUrls.slice(0, 2),
    columns: 2,
    labels: ["Band 1", "Band 2"],
    viewerSize: 400,
  },
};

/**
 * 3-column grid for multi-band comparison
 */
export const ThreeColumn: Story = {
  args: {
    fitsUrls: sampleFitsUrls.slice(0, 3),
    columns: 3,
    labels: ["Low Freq", "Mid Freq", "High Freq"],
    viewerSize: 350,
  },
};

/**
 * 4-column grid for detailed comparison
 */
export const FourColumn: Story = {
  args: {
    fitsUrls: sampleFitsUrls,
    columns: 4,
    labels: ["Band 1", "Band 2", "Band 3", "Band 4"],
    viewerSize: 300,
  },
};

/**
 * Single column layout
 */
export const SingleColumn: Story = {
  args: {
    fitsUrls: sampleFitsUrls.slice(0, 2),
    columns: 1,
    labels: ["Primary", "Secondary"],
    viewerSize: 500,
  },
};

/**
 * Without synchronized views
 */
export const UnsynchronizedViews: Story = {
  args: {
    fitsUrls: sampleFitsUrls.slice(0, 2),
    columns: 2,
    syncViews: false,
    labels: ["Independent View 1", "Independent View 2"],
    viewerSize: 400,
  },
};

/**
 * Compact viewers
 */
export const Compact: Story = {
  args: {
    fitsUrls: sampleFitsUrls,
    columns: 4,
    viewerSize: 200,
    labels: ["A", "B", "C", "D"],
  },
};

/**
 * Large viewers
 */
export const Large: Story = {
  args: {
    fitsUrls: sampleFitsUrls.slice(0, 2),
    columns: 2,
    viewerSize: 600,
    labels: ["Full Detail 1", "Full Detail 2"],
  },
};

/**
 * Grid without labels
 */
export const NoLabels: Story = {
  args: {
    fitsUrls: sampleFitsUrls.slice(0, 2),
    columns: 2,
    viewerSize: 400,
  },
};

/**
 * Empty grid (no FITS files)
 */
export const Empty: Story = {
  args: {
    fitsUrls: [],
    columns: 2,
    viewerSize: 400,
  },
};

/**
 * Grid with custom styling
 */
export const CustomStyling: Story = {
  args: {
    fitsUrls: sampleFitsUrls.slice(0, 2),
    columns: 2,
    labels: ["Styled 1", "Styled 2"],
    viewerSize: 400,
    className: "border-4 border-green-500 rounded-lg p-4 bg-gray-50",
  },
};
