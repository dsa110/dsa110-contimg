import type { Meta, StoryObj } from "@storybook/react";
import WeightMapViewer from "./WeightMapViewer";

const meta: Meta<typeof WeightMapViewer> = {
  title: "Components/FITS/WeightMapViewer",
  component: WeightMapViewer,
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Weight Map Viewer displays mosaic images alongside their inverse-variance weight maps. " +
          "Features include toggling between mosaic and weight map views, statistics panel showing " +
          "noise improvement, and validation of √N noise improvement.",
      },
    },
  },
  tags: ["autodocs"],
  argTypes: {
    mosaicUrl: {
      description: "URL to the mosaic FITS file",
      control: "text",
    },
    weightMapUrl: {
      description: "URL to the weight map FITS file",
      control: "text",
    },
    effectiveNoiseJy: {
      description: "Effective noise from inverse-variance weighting (Jy)",
      control: { type: "number", min: 0, step: 0.0001 },
    },
    nImages: {
      description: "Number of images combined in the mosaic",
      control: { type: "number", min: 1, step: 1 },
    },
    medianRmsJy: {
      description: "Median RMS noise of input images (Jy)",
      control: { type: "number", min: 0, step: 0.0001 },
    },
    width: {
      description: "Viewer width in pixels",
      control: { type: "number", min: 200, max: 1024, step: 50 },
    },
    height: {
      description: "Viewer height in pixels",
      control: { type: "number", min: 200, max: 1024, step: 50 },
    },
  },
};

export default meta;
type Story = StoryObj<typeof WeightMapViewer>;

/**
 * Default story showing a typical mosaic with weight map.
 *
 * Note: This requires a running backend server with actual FITS files.
 * In Storybook, this will show the UI but may not load actual images.
 */
export const Default: Story = {
  args: {
    mosaicUrl: "/api/fits/example_mosaic.fits",
    weightMapUrl: "/api/fits/example_mosaic.weights.fits",
    effectiveNoiseJy: 0.00035,
    nImages: 8,
    medianRmsJy: 0.001,
    width: 512,
    height: 512,
  },
};

/**
 * Deep mosaic with many images showing significant noise improvement.
 */
export const DeepMosaic: Story = {
  args: {
    mosaicUrl: "/api/fits/deep_mosaic.fits",
    weightMapUrl: "/api/fits/deep_mosaic.weights.fits",
    effectiveNoiseJy: 0.0001,
    nImages: 100,
    medianRmsJy: 0.001,
    width: 600,
    height: 600,
  },
};

/**
 * Quick-look mosaic with fewer images.
 */
export const QuicklookMosaic: Story = {
  args: {
    mosaicUrl: "/api/fits/quicklook_mosaic.fits",
    weightMapUrl: "/api/fits/quicklook_mosaic.weights.fits",
    effectiveNoiseJy: 0.0007,
    nImages: 2,
    medianRmsJy: 0.001,
    width: 400,
    height: 400,
  },
};

/**
 * Example where noise doesn't match √N expectation.
 * This can happen with non-uniform coverage or varying input quality.
 */
export const NonUniformCoverage: Story = {
  args: {
    mosaicUrl: "/api/fits/nonuniform_mosaic.fits",
    weightMapUrl: "/api/fits/nonuniform_mosaic.weights.fits",
    effectiveNoiseJy: 0.0006, // Higher than expected for 8 images
    nImages: 8,
    medianRmsJy: 0.001,
    width: 512,
    height: 512,
  },
};

/**
 * Minimal stats - only showing the viewer without statistics.
 */
export const MinimalView: Story = {
  args: {
    mosaicUrl: "/api/fits/minimal_mosaic.fits",
    weightMapUrl: "/api/fits/minimal_mosaic.weights.fits",
    // No stats provided
    width: 512,
    height: 512,
  },
};
