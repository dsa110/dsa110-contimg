/**
 * Tests for SaveQueryModal component
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SaveQueryModal } from "./SaveQueryModal";
import type { UrlFilterState } from "../../hooks/useUrlFilterState";

// Mock the API hooks
const mockCreateMutate = vi.fn();
const mockUpdateMutate = vi.fn();

vi.mock("../../api/savedQueries", async () => {
  const actual = await vi.importActual("../../api/savedQueries");
  return {
    ...actual,
    useCreateSavedQuery: () => ({
      mutateAsync: mockCreateMutate,
      isPending: false,
    }),
    useUpdateSavedQuery: () => ({
      mutateAsync: mockUpdateMutate,
      isPending: false,
    }),
  };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("SaveQueryModal", () => {
  const defaultFilters: UrlFilterState = {
    ra: 180,
    dec: 45,
    radius: 5,
    minFlux: 0.1,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateMutate.mockResolvedValue({
      id: "new-query-id",
      name: "Test Query",
      visibility: "private",
      context: "sources",
      filters: defaultFilters,
      owner_id: "user-1",
      owner_username: "testuser",
      use_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      can_edit: true,
    });
  });

  it("renders nothing when closed", () => {
    render(
      <SaveQueryModal
        isOpen={false}
        onClose={() => {}}
        filters={defaultFilters}
        context="sources"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByText("Save Query")).not.toBeInTheDocument();
  });

  it("renders modal when open", () => {
    render(
      <SaveQueryModal
        isOpen={true}
        onClose={() => {}}
        filters={defaultFilters}
        context="sources"
      />,
      { wrapper: createWrapper() }
    );

    expect(
      screen.getByRole("heading", { name: "Save Query" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByText(/visibility/i)).toBeInTheDocument();
  });

  it("displays filter summary", () => {
    render(
      <SaveQueryModal
        isOpen={true}
        onClose={() => {}}
        filters={defaultFilters}
        context="sources"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Filters to Save/i)).toBeInTheDocument();
    expect(screen.getByText(/Cone:/)).toBeInTheDocument();
    expect(screen.getByText(/Flux:/)).toBeInTheDocument();
  });

  it("shows warning when no filters are active", () => {
    render(
      <SaveQueryModal
        isOpen={true}
        onClose={() => {}}
        filters={{}}
        context="sources"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/No filters active/)).toBeInTheDocument();
  });

  it("shows error when name is empty", async () => {
    const user = userEvent.setup();
    render(
      <SaveQueryModal
        isOpen={true}
        onClose={() => {}}
        filters={defaultFilters}
        context="sources"
      />,
      { wrapper: createWrapper() }
    );

    // Submit without entering name
    await user.click(screen.getByRole("button", { name: /save query/i }));

    expect(screen.getByText(/Name is required/i)).toBeInTheDocument();
    expect(mockCreateMutate).not.toHaveBeenCalled();
  });

  it("calls onClose when cancel is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(
      <SaveQueryModal
        isOpen={true}
        onClose={onClose}
        filters={defaultFilters}
        context="sources"
      />,
      { wrapper: createWrapper() }
    );

    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("creates query and calls callbacks on success", async () => {
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    const user = userEvent.setup();

    render(
      <SaveQueryModal
        isOpen={true}
        onClose={onClose}
        filters={defaultFilters}
        context="sources"
        onSuccess={onSuccess}
      />,
      { wrapper: createWrapper() }
    );

    // Enter name
    await user.type(screen.getByLabelText(/name/i), "My Test Query");

    // Submit
    await user.click(screen.getByRole("button", { name: /save query/i }));

    await waitFor(() => {
      expect(mockCreateMutate).toHaveBeenCalledWith({
        name: "My Test Query",
        description: undefined,
        visibility: "private",
        context: "sources",
        filters: defaultFilters,
      });
    });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("allows selecting different visibility", async () => {
    const user = userEvent.setup();

    render(
      <SaveQueryModal
        isOpen={true}
        onClose={() => {}}
        filters={defaultFilters}
        context="sources"
      />,
      { wrapper: createWrapper() }
    );

    // Click shared option (using the label that contains both text)
    const sharedOption = screen.getByText("👥 Shared");
    await user.click(sharedOption);

    // Enter name and submit
    await user.type(screen.getByLabelText(/name/i), "Shared Query");
    await user.click(screen.getByRole("button", { name: /save query/i }));

    await waitFor(() => {
      expect(mockCreateMutate).toHaveBeenCalledWith(
        expect.objectContaining({ visibility: "shared" })
      );
    });
  });

  it("populates form when editing existing query", () => {
    const existingQuery = {
      id: "existing-id",
      name: "Existing Query",
      description: "Some description",
      visibility: "shared" as const,
      context: "sources" as const,
      filters: defaultFilters,
      owner_id: "user-1",
      owner_username: "testuser",
      use_count: 5,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      can_edit: true,
    };

    render(
      <SaveQueryModal
        isOpen={true}
        onClose={() => {}}
        filters={defaultFilters}
        context="sources"
        existingQuery={existingQuery}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText("Edit Saved Query")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Existing Query")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Some description")).toBeInTheDocument();
  });

  it("calls update mutation when editing", async () => {
    mockUpdateMutate.mockResolvedValue({
      id: "existing-id",
      name: "Updated Query",
      visibility: "private",
      context: "sources",
      filters: defaultFilters,
      owner_id: "user-1",
      owner_username: "testuser",
      use_count: 5,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      can_edit: true,
    });

    const existingQuery = {
      id: "existing-id",
      name: "Existing Query",
      description: undefined,
      visibility: "private" as const,
      context: "sources" as const,
      filters: defaultFilters,
      owner_id: "user-1",
      owner_username: "testuser",
      use_count: 5,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      can_edit: true,
    };

    const user = userEvent.setup();

    render(
      <SaveQueryModal
        isOpen={true}
        onClose={() => {}}
        filters={defaultFilters}
        context="sources"
        existingQuery={existingQuery}
      />,
      { wrapper: createWrapper() }
    );

    // Clear and type new name
    const nameInput = screen.getByLabelText(/name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Updated Query");

    // Submit
    await user.click(screen.getByRole("button", { name: /update query/i }));

    await waitFor(() => {
      expect(mockUpdateMutate).toHaveBeenCalledWith({
        id: "existing-id",
        data: expect.objectContaining({ name: "Updated Query" }),
      });
    });
  });
});
