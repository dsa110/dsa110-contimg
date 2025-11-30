import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import AppLayout from "./AppLayout";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

/**
 * AppLayout provides the main application structure with navigation header and content area.
 *
 * Features:
 * - Top navigation bar with active route highlighting
 * - Connection status banner (shows when offline)
 * - Responsive main content area
 */
const meta = {
  title: "Layout/AppLayout",
  component: AppLayout,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
  },
  decorators: [
    (Story) => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: Infinity },
        },
      });

      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="*" element={<Story />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof AppLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default layout showing the home page route as active
 */
export const HomePage: Story = {
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Story />}>
            <Route
              index
              element={
                <div className="p-8">
                  <h1 className="text-3xl font-bold">Home Page Content</h1>
                </div>
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    ),
  ],
};

/**
 * Layout with Images page active
 */
export const ImagesPage: Story = {
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/images"]}>
        <Routes>
          <Route path="/images" element={<Story />}>
            <Route
              index
              element={
                <div className="p-8">
                  <h1 className="text-3xl font-bold">Images List</h1>
                </div>
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    ),
  ],
};

/**
 * Layout with Sources page active
 */
export const SourcesPage: Story = {
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/sources"]}>
        <Routes>
          <Route path="/sources" element={<Story />}>
            <Route
              index
              element={
                <div className="p-8">
                  <h1 className="text-3xl font-bold">Sources List</h1>
                </div>
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    ),
  ],
};

/**
 * Layout with Jobs page active
 */
export const JobsPage: Story = {
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/jobs"]}>
        <Routes>
          <Route path="/jobs" element={<Story />}>
            <Route
              index
              element={
                <div className="p-8">
                  <h1 className="text-3xl font-bold">Jobs List</h1>
                </div>
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    ),
  ],
};

/**
 * Layout with scrollable content to demonstrate the full page structure
 */
export const WithScrollableContent: Story = {
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Story />}>
            <Route
              index
              element={
                <div className="p-8 space-y-4">
                  <h1 className="text-3xl font-bold mb-4">Scrollable Content</h1>
                  {Array.from({ length: 50 }, (_, i) => (
                    <p key={i} className="text-gray-700">
                      Lorem ipsum dolor sit amet, consectetur adipiscing elit. Paragraph {i + 1}.
                    </p>
                  ))}
                </div>
              }
            />
          </Route>
        </Routes>
      </MemoryRouter>
    ),
  ],
};
