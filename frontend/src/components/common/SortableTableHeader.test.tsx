import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SortableTableHeader, { useTableSort, SortDirection } from "./SortableTableHeader";
import { renderHook, act } from "@testing-library/react";

describe("SortableTableHeader", () => {
  const defaultProps = {
    columnKey: "name",
    sortColumn: null as string | null,
    sortDirection: null as SortDirection,
    onSort: vi.fn(),
  };

  describe("rendering", () => {
    it("renders children as header content", () => {
      render(
        <table>
          <thead>
            <tr>
              <SortableTableHeader {...defaultProps}>Name</SortableTableHeader>
            </tr>
          </thead>
        </table>
      );
      expect(screen.getByText("Name")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <table>
          <thead>
            <tr>
              <SortableTableHeader {...defaultProps} className="text-right">
                Name
              </SortableTableHeader>
            </tr>
          </thead>
        </table>
      );
      expect(screen.getByRole("columnheader")).toHaveClass("text-right");
    });

    it("has role columnheader", () => {
      render(
        <table>
          <thead>
            <tr>
              <SortableTableHeader {...defaultProps}>Name</SortableTableHeader>
            </tr>
          </thead>
        </table>
      );
      expect(screen.getByRole("columnheader")).toBeInTheDocument();
    });
  });

  describe("sort indicators", () => {
    it("shows inactive indicators when not sorted", () => {
      render(
        <table>
          <thead>
            <tr>
              <SortableTableHeader {...defaultProps}>Name</SortableTableHeader>
            </tr>
          </thead>
        </table>
      );
      const header = screen.getByRole("columnheader");
      expect(header).toHaveAttribute("aria-sort", "none");
    });

    it("shows ascending indicator when sorted ascending", () => {
      render(
        <table>
          <thead>
            <tr>
              <SortableTableHeader {...defaultProps} sortColumn="name" sortDirection="asc">
                Name
              </SortableTableHeader>
            </tr>
          </thead>
        </table>
      );
      const header = screen.getByRole("columnheader");
      expect(header).toHaveAttribute("aria-sort", "ascending");
    });

    it("shows descending indicator when sorted descending", () => {
      render(
        <table>
          <thead>
            <tr>
              <SortableTableHeader {...defaultProps} sortColumn="name" sortDirection="desc">
                Name
              </SortableTableHeader>
            </tr>
          </thead>
        </table>
      );
      const header = screen.getByRole("columnheader");
      expect(header).toHaveAttribute("aria-sort", "descending");
    });
  });

  describe("click handling", () => {
    it("calls onSort with columnKey when clicked", async () => {
      const onSort = vi.fn();
      render(
        <table>
          <thead>
            <tr>
              <SortableTableHeader {...defaultProps} onSort={onSort}>
                Name
              </SortableTableHeader>
            </tr>
          </thead>
        </table>
      );
      await userEvent.click(screen.getByRole("columnheader"));
      expect(onSort).toHaveBeenCalledWith("name");
    });
  });
});

describe("useTableSort hook", () => {
  const testData = [
    { name: "Charlie", age: 30 },
    { name: "Alice", age: 25 },
    { name: "Bob", age: 35 },
  ];

  it("returns initial sort state", () => {
    const { result } = renderHook(() => useTableSort(testData));
    expect(result.current.sortColumn).toBeNull();
    expect(result.current.sortDirection).toBeNull();
    expect(result.current.sortedData).toEqual(testData);
  });

  it("respects default column and direction", () => {
    const { result } = renderHook(() => useTableSort(testData, "name", "asc"));
    expect(result.current.sortColumn).toBe("name");
    expect(result.current.sortDirection).toBe("asc");
  });

  it("toggles to ascending when clicking unsorted column", () => {
    const { result } = renderHook(() => useTableSort(testData));
    act(() => {
      result.current.handleSort("name");
    });
    expect(result.current.sortColumn).toBe("name");
    expect(result.current.sortDirection).toBe("asc");
  });

  it("toggles to descending when clicking ascending column", () => {
    const { result } = renderHook(() => useTableSort(testData, "name", "asc"));
    act(() => {
      result.current.handleSort("name");
    });
    expect(result.current.sortDirection).toBe("desc");
  });

  it("toggles to null when clicking descending column", () => {
    const { result } = renderHook(() => useTableSort(testData, "name", "desc"));
    act(() => {
      result.current.handleSort("name");
    });
    expect(result.current.sortColumn).toBeNull();
    expect(result.current.sortDirection).toBeNull();
  });

  it("switches to ascending when clicking different column", () => {
    const { result } = renderHook(() => useTableSort(testData, "name", "desc"));
    act(() => {
      result.current.handleSort("age");
    });
    expect(result.current.sortColumn).toBe("age");
    expect(result.current.sortDirection).toBe("asc");
  });

  it("sorts string data ascending", () => {
    const { result } = renderHook(() => useTableSort(testData, "name", "asc"));
    expect(result.current.sortedData![0].name).toBe("Alice");
    expect(result.current.sortedData![1].name).toBe("Bob");
    expect(result.current.sortedData![2].name).toBe("Charlie");
  });

  it("sorts string data descending", () => {
    const { result } = renderHook(() => useTableSort(testData, "name", "desc"));
    expect(result.current.sortedData![0].name).toBe("Charlie");
    expect(result.current.sortedData![2].name).toBe("Alice");
  });

  it("sorts numeric data ascending", () => {
    const { result } = renderHook(() => useTableSort(testData, "age", "asc"));
    expect(result.current.sortedData![0].age).toBe(25);
    expect(result.current.sortedData![2].age).toBe(35);
  });

  it("sorts numeric data descending", () => {
    const { result } = renderHook(() => useTableSort(testData, "age", "desc"));
    expect(result.current.sortedData![0].age).toBe(35);
    expect(result.current.sortedData![2].age).toBe(25);
  });

  it("handles null values in data", () => {
    const dataWithNulls = [
      { name: "Alice", age: null },
      { name: "Bob", age: 25 },
      { name: null, age: 30 },
    ];
    const { result } = renderHook(() =>
      useTableSort(dataWithNulls as unknown as { name: string; age: number }[], "name", "asc")
    );
    // Nulls should sort to end in ascending order
    expect(result.current.sortedData![2].name).toBeNull();
  });

  it("handles undefined data", () => {
    const { result } = renderHook(() => useTableSort(undefined));
    expect(result.current.sortedData).toBeUndefined();
  });
});
