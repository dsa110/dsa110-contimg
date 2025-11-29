import type { Meta, StoryObj } from "@storybook/react-vite";
import ImageThumbnail from "./ImageThumbnail";

const meta: Meta<typeof ImageThumbnail> = {
  title: "Common/ImageThumbnail",
  component: ImageThumbnail,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof ImageThumbnail>;

// Note: These will show the error/placeholder state since there's no real API
// In a real scenario, you'd mock the API or use a decorator

export const Small: Story = {
  args: {
    imageId: "test-image-1",
    size: "sm",
    alt: "Small thumbnail",
  },
};

export const Medium: Story = {
  args: {
    imageId: "test-image-2",
    size: "md",
    alt: "Medium thumbnail",
  },
};

export const Large: Story = {
  args: {
    imageId: "test-image-3",
    size: "lg",
    alt: "Large thumbnail",
  },
};

export const NotExpandable: Story = {
  args: {
    imageId: "test-image-4",
    size: "md",
    expandable: false,
  },
};

export const WithClickHandler: Story = {
  args: {
    imageId: "test-image-5",
    size: "md",
    onClick: () => alert("Thumbnail clicked!"),
  },
};

// You can add a decorator to mock successful image loading
// For now, these demonstrate the placeholder/error state
