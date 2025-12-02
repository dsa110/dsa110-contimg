import type { Meta, StoryObj } from "@storybook/react";
import { PageSkeleton } from "./PageSkeleton";

/**
 * PageSkeleton provides consistent loading states for different page types.
 *
 * Used in Suspense fallbacks to show content placeholders while data loads.
 */
const meta = {
  title: "Components/Common/PageSkeleton",
  component: PageSkeleton,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
  },
  argTypes: {
    variant: {
      control: "select",
      options: ["list", "detail", "dashboard"],
      description: "Type of page skeleton to display",
    },
  },
} satisfies Meta<typeof PageSkeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * List skeleton with multiple rows.
 * Used for pages like ImagesListPage, SourcesListPage, JobsListPage.
 */
export const List: Story = {
  args: {
    variant: "list",
  },
};

/**
 * Detail skeleton with header and content sections.
 * Used for pages like ImageDetailPage, SourceDetailPage, JobDetailPage.
 */
export const Detail: Story = {
  args: {
    variant: "detail",
  },
};

/**
 * Dashboard skeleton with multiple card placeholders.
 * Used for the HomePage dashboard.
 */
export const Dashboard: Story = {
  args: {
    variant: "cards",
  },
};
