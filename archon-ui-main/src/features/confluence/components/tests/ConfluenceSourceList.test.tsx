/**
 * ConfluenceSourceList Component Tests
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "../../../testing/test-utils";
import type { ConfluenceSourceListResponse } from "../../types";
import { ConfluenceSourceList } from "../ConfluenceSourceList";

// Mock dependencies
const mockUseConfluenceSources = vi.fn();

vi.mock("../../hooks/useConfluenceQueries", () => ({
  useConfluenceSources: () => mockUseConfluenceSources(),
  useTriggerSync: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteSource: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

const mockSources: ConfluenceSourceListResponse = {
  sources: [
    {
      source_id: "src-1",
      source_type: "confluence",
      space_key: "DEVDOCS",
      base_url: "https://company.atlassian.net/wiki",
      status: "ready",
      last_sync: "2024-01-15T10:30:00Z",
      total_pages: 42,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-15T10:30:00Z",
    },
    {
      source_id: "src-2",
      source_type: "confluence",
      space_key: "ENGINEERING",
      base_url: "https://company.atlassian.net/wiki",
      status: "syncing",
      last_sync: null,
      total_pages: 0,
      created_at: "2024-01-10T00:00:00Z",
      updated_at: "2024-01-10T00:00:00Z",
    },
  ],
  count: 2,
};

describe("ConfluenceSourceList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state with skeleton cards", () => {
    mockUseConfluenceSources.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<ConfluenceSourceList onAddSource={() => {}} />);

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(3);
  });

  it("renders empty state with CTA button", () => {
    mockUseConfluenceSources.mockReturnValue({
      data: { sources: [], count: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    const onAddSource = vi.fn();
    render(<ConfluenceSourceList onAddSource={onAddSource} />);

    expect(screen.getByText("No Confluence sources yet")).toBeInTheDocument();
    expect(screen.getByText("Add Confluence Source")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Add Confluence Source"));
    expect(onAddSource).toHaveBeenCalled();
  });

  it("renders list of source cards", () => {
    mockUseConfluenceSources.mockReturnValue({
      data: mockSources,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<ConfluenceSourceList onAddSource={() => {}} />);

    expect(screen.getByText("DEVDOCS")).toBeInTheDocument();
    expect(screen.getByText("ENGINEERING")).toBeInTheDocument();
  });

  it("renders error state with retry button", () => {
    const refetch = vi.fn();
    mockUseConfluenceSources.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("API error"),
      refetch,
    });

    render(<ConfluenceSourceList onAddSource={() => {}} />);

    expect(screen.getByText("Failed to load Confluence sources")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Try Again"));
    expect(refetch).toHaveBeenCalled();
  });

  it("shows Add Source button when sources exist", () => {
    mockUseConfluenceSources.mockReturnValue({
      data: mockSources,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    const onAddSource = vi.fn();
    render(<ConfluenceSourceList onAddSource={onAddSource} />);

    const addButton = screen.getByText("Add Source");
    fireEvent.click(addButton);
    expect(onAddSource).toHaveBeenCalled();
  });

  it("uses responsive grid layout", () => {
    mockUseConfluenceSources.mockReturnValue({
      data: mockSources,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<ConfluenceSourceList onAddSource={() => {}} />);

    const grid = screen.getByText("DEVDOCS").closest(".grid");
    expect(grid).toHaveClass("grid-cols-1", "md:grid-cols-2", "lg:grid-cols-3");
  });
});
