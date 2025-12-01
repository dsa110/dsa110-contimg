import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import SesameResolver from "./SesameResolver";

/**
 * SesameResolver allows users to resolve astronomical object names to coordinates
 * using the CDS Sesame service (SIMBAD, NED, VizieR).
 *
 * Features:
 * - Multiple service options (All, SIMBAD, NED, VizieR)
 * - Caching of resolved objects
 * - Request cancellation support
 * - Error handling with retry logic
 */
const meta = {
  title: "Components/Query/SesameResolver",
  component: SesameResolver,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
  args: {
    onResolved: fn(),
  },
} satisfies Meta<typeof SesameResolver>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default resolver ready for input
 */
export const Default: Story = {};

/**
 * Resolver with custom styling
 */
export const CustomStyling: Story = {
  args: {
    className: "max-w-2xl mx-auto p-6 bg-blue-50 rounded-lg shadow-lg",
  },
};

/**
 * Multiple resolvers showing different use cases
 */
export const MultipleInstances: Story = {
  render: (args) => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold mb-2">Main Search</h3>
        <SesameResolver {...args} />
      </div>
      <div>
        <h3 className="text-lg font-bold mb-2">Quick Lookup</h3>
        <SesameResolver {...args} className="bg-gray-50 p-4 rounded" />
      </div>
    </div>
  ),
};

/**
 * Example usage with callback handling
 */
export const WithCallbackExample: Story = {
  render: () => {
    const handleResolved = (ra: number, dec: number, objectName: string) => {
      alert(`Resolved ${objectName}:\nRA: ${ra}°\nDec: ${dec}°`);
    };

    return (
      <div className="max-w-2xl">
        <div className="mb-4 p-4 bg-blue-50 rounded">
          <p className="text-sm text-gray-700">
            Try resolving: <strong>M31</strong>, <strong>NGC 1068</strong>, or{" "}
            <strong>Crab Nebula</strong>
          </p>
        </div>
        <SesameResolver onResolved={handleResolved} />
      </div>
    );
  },
};
