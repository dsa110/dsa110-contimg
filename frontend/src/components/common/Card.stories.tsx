import type { Meta, StoryObj } from "@storybook/react-vite";
import { Card } from "./Card";

const meta: Meta<typeof Card> = {
  title: "Common/Card",
  component: Card,
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
  argTypes: {
    padding: {
      control: "select",
      options: ["none", "sm", "md", "lg"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof Card>;

export const Default: Story = {
  args: {
    title: "Card Title",
    children: <p className="text-gray-600">This is the card content.</p>,
  },
};

export const WithSubtitle: Story = {
  args: {
    title: "Card Title",
    subtitle: "A helpful description of the card content",
    children: <p className="text-gray-600">This is the card content with a subtitle above.</p>,
  },
};

export const WithActions: Story = {
  args: {
    title: "Card with Actions",
    actions: (
      <>
        <button className="btn btn-secondary text-sm">Edit</button>
        <button className="btn btn-primary text-sm">Save</button>
      </>
    ),
    children: <p className="text-gray-600">This card has action buttons in the header.</p>,
  },
};

export const Hoverable: Story = {
  args: {
    title: "Hoverable Card",
    hoverable: true,
    children: <p className="text-gray-600">Hover over me to see the shadow effect!</p>,
  },
};

export const NoPadding: Story = {
  args: {
    title: "No Padding",
    padding: "none",
    children: (
      <div className="bg-blue-50 p-4">
        <p className="text-blue-800">Content goes edge-to-edge.</p>
      </div>
    ),
  },
};

export const ComplexContent: Story = {
  args: {
    title: "Pipeline Status",
    subtitle: "Last updated 5 minutes ago",
    actions: <span className="badge badge-success">Running</span>,
    children: (
      <dl className="grid grid-cols-2 gap-4">
        <div>
          <dt className="text-xs text-gray-500 uppercase">Jobs Completed</dt>
          <dd className="text-2xl font-bold text-gray-900">42</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500 uppercase">Queue Depth</dt>
          <dd className="text-2xl font-bold text-gray-900">7</dd>
        </div>
      </dl>
    ),
  },
};
