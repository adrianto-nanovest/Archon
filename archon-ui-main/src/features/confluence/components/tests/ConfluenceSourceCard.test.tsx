/**
 * ConfluenceSourceCard Component Tests
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "../../../testing/test-utils";
import type { ConfluenceSource } from "../../types";
import { ConfluenceSourceCard } from "../ConfluenceSourceCard";

// Mock dependencies
vi.mock("../../hooks/useConfluenceQueries", () => ({
  useTriggerSync: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteSource: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("../../hooks/useConfluenceSyncProgress", () => ({
  useConfluenceSyncProgress: () => ({
    data: null,
    isLoading: false,
    isComplete: false,
    isFailed: false,
    isActive: false,
  }),
}));

vi.mock("@/features/shared/hooks", () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}));

const mockSource: ConfluenceSource = {
  source_id: "src-123",
  source_type: "confluence",
  space_key: "DEVDOCS",
  base_url: "https://company.atlassian.net/wiki",
  status: "ready",
  last_sync: "2024-01-15T10:30:00Z",
  total_pages: 42,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-15T10:30:00Z",
};

describe("ConfluenceSourceCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders source data correctly", () => {
    render(<ConfluenceSourceCard source={mockSource} onDeleteSuccess={() => {}} />);

    expect(screen.getByText("DEVDOCS")).toBeInTheDocument();
    expect(screen.getByText("DEVDOCS Space")).toBeInTheDocument();
    expect(screen.getByText("company.atlassian.net")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("shows ready status badge", () => {
    render(<ConfluenceSourceCard source={mockSource} onDeleteSuccess={() => {}} />);

    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("shows syncing status with animation", () => {
    const syncingSource = { ...mockSource, status: "syncing" };
    render(<ConfluenceSourceCard source={syncingSource} onDeleteSuccess={() => {}} />);

    expect(screen.getByText("Syncing...")).toBeInTheDocument();
  });

  it("shows error status", () => {
    const errorSource = { ...mockSource, status: "error" };
    render(<ConfluenceSourceCard source={errorSource} onDeleteSuccess={() => {}} />);

    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("displays last sync timestamp when available", () => {
    render(<ConfluenceSourceCard source={mockSource} onDeleteSuccess={() => {}} />);

    expect(screen.getByText(/Last sync:/)).toBeInTheDocument();
    expect(screen.getByText(/Jan 15, 2024/)).toBeInTheDocument();
  });

  it("displays created date in footer", () => {
    render(<ConfluenceSourceCard source={mockSource} onDeleteSuccess={() => {}} />);

    expect(screen.getByText(/Created:/)).toBeInTheDocument();
    expect(screen.getByText(/1\/1\/2024/)).toBeInTheDocument();
  });

  it("shows external link to Confluence space", () => {
    render(<ConfluenceSourceCard source={mockSource} onDeleteSuccess={() => {}} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://company.atlassian.net/wiki");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("applies optimistic styling when source is optimistic", () => {
    const optimisticSource = {
      ...mockSource,
      _optimistic: true,
      _localId: "local-123",
    };
    render(<ConfluenceSourceCard source={optimisticSource as ConfluenceSource} onDeleteSuccess={() => {}} />);

    // The motion.div wrapper with opacity-80 contains the .group class
    const container = screen.getByText("DEVDOCS Space").closest(".group");
    expect(container).toHaveClass("opacity-80");
  });

  it("shows OptimisticIndicator when source is optimistic", () => {
    const optimisticSource = {
      ...mockSource,
      _optimistic: true,
      _localId: "local-123",
    };
    render(<ConfluenceSourceCard source={optimisticSource as ConfluenceSource} onDeleteSuccess={() => {}} />);

    // OptimisticIndicator renders "Saving..." text
    expect(screen.getByText("Saving...")).toBeInTheDocument();
  });

  it("does not show OptimisticIndicator for non-optimistic sources", () => {
    render(<ConfluenceSourceCard source={mockSource} onDeleteSuccess={() => {}} />);

    // OptimisticIndicator should not be visible
    expect(screen.queryByText("Saving...")).not.toBeInTheDocument();
  });

  it("applies ring styling when source is optimistic", () => {
    const optimisticSource = {
      ...mockSource,
      _optimistic: true,
      _localId: "local-123",
    };
    const { container } = render(
      <ConfluenceSourceCard source={optimisticSource as ConfluenceSource} onDeleteSuccess={() => {}} />,
    );

    // DataCard should have the ring-1 ring-cyan-400/30 classes
    const dataCard = container.querySelector('[class*="ring-1"]');
    expect(dataCard).toBeInTheDocument();
  });
});
