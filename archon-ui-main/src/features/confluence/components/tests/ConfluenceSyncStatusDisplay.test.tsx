/**
 * ConfluenceSyncStatusDisplay Component Tests
 */

import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ProgressResponse } from "../../../progress/types";
import { render, screen } from "../../../testing/test-utils";
import { ConfluenceSyncStatusDisplay } from "../ConfluenceSyncStatusDisplay";

describe("ConfluenceSyncStatusDisplay", () => {
  const mockProgressData: ProgressResponse = {
    progressId: "op-123",
    status: "processing",
    progress: 50,
    message: "Processing pages",
    processedPages: 25,
    totalPages: 50,
    startedAt: new Date(Date.now() - 60000).toISOString(), // 1 minute ago
  };

  it("renders nothing when idle (no progress data)", () => {
    render(<ConfluenceSyncStatusDisplay progressData={null} />);

    // Component returns null when no progress data
    expect(screen.queryByText("Syncing")).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("renders progress bar with correct percentage", () => {
    render(
      <ConfluenceSyncStatusDisplay
        progressData={mockProgressData}
        isLoading={false}
        isComplete={false}
        isFailed={false}
      />,
    );

    // Check progress display
    expect(screen.getByText(/Processing 25 of 50 pages/)).toBeInTheDocument();
    expect(screen.getByText("Syncing")).toBeInTheDocument();
  });

  it("displays sync state correctly", () => {
    render(
      <ConfluenceSyncStatusDisplay
        progressData={mockProgressData}
        isLoading={false}
        isComplete={false}
        isFailed={false}
      />,
    );

    expect(screen.getByText("Syncing")).toBeInTheDocument();
  });

  it("shows/hides based on sync activity", () => {
    const { rerender } = render(<ConfluenceSyncStatusDisplay progressData={null} />);

    // No progress = hidden
    expect(screen.queryByText("Syncing")).not.toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();

    // With progress = visible
    rerender(
      <ConfluenceSyncStatusDisplay
        progressData={mockProgressData}
        isLoading={false}
        isComplete={false}
        isFailed={false}
      />,
    );

    expect(screen.getByText("Syncing")).toBeInTheDocument();
  });

  it("has correct accessibility attributes on Progress", () => {
    render(
      <ConfluenceSyncStatusDisplay
        progressData={mockProgressData}
        isLoading={false}
        isComplete={false}
        isFailed={false}
      />,
    );

    const progressBar = screen.getByRole("progressbar");
    expect(progressBar).toHaveAttribute("aria-valuenow", "50");
    expect(progressBar).toHaveAttribute("aria-valuemin", "0");
    expect(progressBar).toHaveAttribute("aria-valuemax", "100");
  });

  it("renders completed state with stats", () => {
    const completedData: ProgressResponse = {
      ...mockProgressData,
      status: "completed",
      progress: 100,
      stats: {
        pages_crawled: 50,
        documents_created: 150,
        errors: 0,
      },
    };

    render(
      <ConfluenceSyncStatusDisplay progressData={completedData} isLoading={false} isComplete={true} isFailed={false} />,
    );

    expect(screen.getByText("Sync Complete")).toBeInTheDocument();
    expect(screen.getByText(/50 pages synced/)).toBeInTheDocument();
  });

  it("renders error state with retry button", () => {
    const errorData: ProgressResponse = {
      ...mockProgressData,
      status: "error",
      error: "API rate limit exceeded",
    };

    const mockRetry = vi.fn();

    render(
      <ConfluenceSyncStatusDisplay
        progressData={errorData}
        isLoading={false}
        isComplete={false}
        isFailed={true}
        onRetry={mockRetry}
      />,
    );

    expect(screen.getByText("Sync Failed")).toBeInTheDocument();
    expect(screen.getByText("API rate limit exceeded")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("calls onRetry when retry button is clicked", async () => {
    const errorData: ProgressResponse = {
      ...mockProgressData,
      status: "error",
      error: "Connection failed",
    };

    const mockRetry = vi.fn();
    const user = userEvent.setup();

    render(
      <ConfluenceSyncStatusDisplay
        progressData={errorData}
        isLoading={false}
        isComplete={false}
        isFailed={true}
        onRetry={mockRetry}
      />,
    );

    const retryButton = screen.getByRole("button", { name: /retry/i });
    await user.click(retryButton);

    expect(mockRetry).toHaveBeenCalledTimes(1);
  });

  it("shows estimated time remaining during sync", () => {
    const progressWithTime: ProgressResponse = {
      ...mockProgressData,
      processedPages: 25,
      totalPages: 50,
      startedAt: new Date(Date.now() - 30000).toISOString(), // 30 seconds ago
    };

    render(
      <ConfluenceSyncStatusDisplay
        progressData={progressWithTime}
        isLoading={false}
        isComplete={false}
        isFailed={false}
      />,
    );

    // Should show some time estimate (exact value depends on calculation)
    expect(screen.getByText(/remaining/i)).toBeInTheDocument();
  });
});
