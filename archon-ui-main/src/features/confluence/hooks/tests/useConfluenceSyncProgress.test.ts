/**
 * useConfluenceSyncProgress Hook Tests
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProgressResponse } from "../../../progress/types";
import { renderHook, waitFor } from "../../../testing/test-utils";
import { useConfluenceSyncProgress } from "../useConfluenceSyncProgress";

// Mock the progress hook
const mockUseOperationProgress = vi.fn();

vi.mock("@/features/progress/hooks/useProgressQueries", () => ({
  useOperationProgress: (progressId: string | null, options?: object) => {
    return mockUseOperationProgress(progressId, options);
  },
}));

vi.mock("@/features/shared/config/queryPatterns", () => ({
  STALE_TIMES: {
    instant: 0,
    realtime: 3_000,
    frequent: 5_000,
    normal: 30_000,
    rare: 300_000,
    static: Infinity,
  },
  DISABLED_QUERY_KEY: ["disabled"] as const,
  createRetryLogic: (maxRetries = 2) => {
    return (failureCount: number, _error: unknown) => failureCount < maxRetries;
  },
}));

describe("useConfluenceSyncProgress", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseOperationProgress.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      isComplete: false,
      isFailed: false,
      isActive: false,
    });
  });

  it("returns inactive state when no operationId", () => {
    renderHook(() => useConfluenceSyncProgress(null));

    expect(mockUseOperationProgress).toHaveBeenCalledWith(null, expect.any(Object));
  });

  it("passes operationId to useOperationProgress", () => {
    renderHook(() => useConfluenceSyncProgress("op-123"));

    expect(mockUseOperationProgress).toHaveBeenCalledWith("op-123", expect.any(Object));
  });

  it("uses STALE_TIMES.frequent (5s) for polling interval", () => {
    renderHook(() => useConfluenceSyncProgress("op-123"));

    expect(mockUseOperationProgress).toHaveBeenCalledWith(
      "op-123",
      expect.objectContaining({
        pollingInterval: 5_000,
      }),
    );
  });

  it("calls onComplete callback when operation completes", async () => {
    const mockOnComplete = vi.fn();
    const completedData: ProgressResponse = {
      progressId: "op-123",
      status: "completed",
      progress: 100,
    };

    // First call returns active, update to return complete later
    mockUseOperationProgress.mockImplementation((_id, options) => {
      // Simulate completion callback
      if (options?.onComplete) {
        options.onComplete(completedData);
      }
      return {
        data: completedData,
        isLoading: false,
        error: null,
        isComplete: true,
        isFailed: false,
        isActive: false,
      };
    });

    renderHook(() =>
      useConfluenceSyncProgress("op-123", {
        onComplete: mockOnComplete,
      }),
    );

    await waitFor(() => {
      expect(mockOnComplete).toHaveBeenCalledWith(completedData);
    });
  });

  it("calls onError callback when operation fails", async () => {
    const mockOnError = vi.fn();

    mockUseOperationProgress.mockImplementation((_id, options) => {
      // Simulate error callback
      if (options?.onError) {
        options.onError("Sync failed: Connection timeout");
      }
      return {
        data: { status: "error", error: "Connection timeout" },
        isLoading: false,
        error: null,
        isComplete: false,
        isFailed: true,
        isActive: false,
      };
    });

    renderHook(() =>
      useConfluenceSyncProgress("op-123", {
        onError: mockOnError,
      }),
    );

    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith("Sync failed: Connection timeout");
    });
  });

  it("returns progress data from useOperationProgress", () => {
    const mockProgressData: ProgressResponse = {
      progressId: "op-123",
      status: "processing",
      progress: 50,
      message: "Processing pages",
    };

    mockUseOperationProgress.mockReturnValue({
      data: mockProgressData,
      isLoading: false,
      error: null,
      isComplete: false,
      isFailed: false,
      isActive: true,
    });

    const { result } = renderHook(() => useConfluenceSyncProgress("op-123"));

    expect(result.current.data).toEqual(mockProgressData);
    expect(result.current.isActive).toBe(true);
  });

  it("returns loading state correctly", () => {
    mockUseOperationProgress.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      isComplete: false,
      isFailed: false,
      isActive: false,
    });

    const { result } = renderHook(() => useConfluenceSyncProgress("op-123"));

    expect(result.current.isLoading).toBe(true);
  });

  describe("state transitions", () => {
    it("handles idle -> syncing -> completed flow", async () => {
      const mockOnComplete = vi.fn();

      // Start idle
      mockUseOperationProgress.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
        isComplete: false,
        isFailed: false,
        isActive: false,
      });

      const { result, rerender } = renderHook(() =>
        useConfluenceSyncProgress("op-123", { onComplete: mockOnComplete }),
      );

      expect(result.current.isActive).toBe(false);

      // Transition to syncing (active)
      const syncingData: ProgressResponse = {
        progressId: "op-123",
        status: "processing",
        progress: 50,
        message: "Processing page 50/100",
      };

      mockUseOperationProgress.mockReturnValue({
        data: syncingData,
        isLoading: false,
        error: null,
        isComplete: false,
        isFailed: false,
        isActive: true,
      });

      rerender();

      expect(result.current.data?.status).toBe("processing");
      expect(result.current.isActive).toBe(true);

      // Transition to completed
      const completedData: ProgressResponse = {
        progressId: "op-123",
        status: "completed",
        progress: 100,
      };

      mockUseOperationProgress.mockImplementation((_id, options) => {
        if (options?.onComplete) {
          options.onComplete(completedData);
        }
        return {
          data: completedData,
          isLoading: false,
          error: null,
          isComplete: true,
          isFailed: false,
          isActive: false,
        };
      });

      rerender();

      await waitFor(() => {
        expect(result.current.isComplete).toBe(true);
        expect(mockOnComplete).toHaveBeenCalledWith(completedData);
      });
    });

    it("handles idle -> syncing -> error flow", async () => {
      const mockOnError = vi.fn();

      // Start idle
      mockUseOperationProgress.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
        isComplete: false,
        isFailed: false,
        isActive: false,
      });

      const { result, rerender } = renderHook(() => useConfluenceSyncProgress("op-123", { onError: mockOnError }));

      expect(result.current.isActive).toBe(false);

      // Transition to syncing (active)
      mockUseOperationProgress.mockReturnValue({
        data: { progressId: "op-123", status: "processing", progress: 25 },
        isLoading: false,
        error: null,
        isComplete: false,
        isFailed: false,
        isActive: true,
      });

      rerender();

      expect(result.current.isActive).toBe(true);

      // Transition to error
      mockUseOperationProgress.mockImplementation((_id, options) => {
        if (options?.onError) {
          options.onError("API rate limit exceeded");
        }
        return {
          data: { status: "error", error: "API rate limit exceeded" },
          isLoading: false,
          error: null,
          isComplete: false,
          isFailed: true,
          isActive: false,
        };
      });

      rerender();

      await waitFor(() => {
        expect(result.current.isFailed).toBe(true);
        expect(mockOnError).toHaveBeenCalledWith("API rate limit exceeded");
      });
    });

    it("handles retry after failure", () => {
      const mockOnError = vi.fn();

      // Start in failed state
      mockUseOperationProgress.mockReturnValue({
        data: { status: "error", error: "Connection timeout" },
        isLoading: false,
        error: null,
        isComplete: false,
        isFailed: true,
        isActive: false,
      });

      const { result, rerender } = renderHook(() => useConfluenceSyncProgress("op-123", { onError: mockOnError }));

      expect(result.current.isFailed).toBe(true);

      // Retry - operation starts again (new operation ID would be used in real scenario)
      mockUseOperationProgress.mockReturnValue({
        data: { progressId: "op-124", status: "processing", progress: 0 },
        isLoading: false,
        error: null,
        isComplete: false,
        isFailed: false,
        isActive: true,
      });

      rerender();

      expect(result.current.isFailed).toBe(false);
      expect(result.current.isActive).toBe(true);
    });
  });
});
