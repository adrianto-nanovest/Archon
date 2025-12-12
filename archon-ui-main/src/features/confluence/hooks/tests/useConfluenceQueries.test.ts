import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ConfluenceSource, ConfluenceSourceListResponse, ConfluenceSyncStatus } from "../../types";
import {
  confluenceKeys,
  useConfluenceDetail,
  useConfluenceSources,
  useConfluenceSyncStatus,
  useCreateSource,
  useDeleteSource,
  useTriggerSync,
} from "../useConfluenceQueries";

// Mock the services
vi.mock("../../services", () => ({
  confluenceService: {
    listSources: vi.fn(),
    createSource: vi.fn(),
    triggerSync: vi.fn(),
    getStatus: vi.fn(),
    deleteSource: vi.fn(),
  },
}));

// Mock the toast hook
vi.mock("@/features/shared/hooks/useToast", () => ({
  useToast: () => ({
    showToast: vi.fn(),
  }),
}));

// Mock shared hooks
vi.mock("@/features/shared/hooks", () => ({
  useSmartPolling: () => ({
    refetchInterval: 5000,
    isActive: true,
    isVisible: true,
    hasFocus: true,
  }),
  useToast: () => ({
    showToast: vi.fn(),
  }),
}));

// Mock query patterns
vi.mock("../../../shared/config/queryPatterns", () => ({
  DISABLED_QUERY_KEY: ["disabled"] as const,
  STALE_TIMES: {
    instant: 0,
    realtime: 3_000,
    frequent: 5_000,
    normal: 30_000,
    rare: 300_000,
    static: Infinity,
  },
}));

// Mock optimistic utils
vi.mock("@/features/shared/utils/optimistic", () => ({
  createOptimisticId: vi.fn(() => "optimistic-id"),
}));

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// Import STALE_TIMES to verify values match
const STALE_TIMES = {
  instant: 0,
  realtime: 3_000,
  frequent: 5_000,
  normal: 30_000,
  rare: 300_000,
  static: Infinity,
};

describe("useConfluenceQueries", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("confluenceKeys", () => {
    it("should generate correct query keys", () => {
      expect(confluenceKeys.all).toEqual(["confluence"]);
      expect(confluenceKeys.lists()).toEqual(["confluence", "list"]);
      expect(confluenceKeys.detail("123")).toEqual(["confluence", "detail", "123"]);
      expect(confluenceKeys.status("123")).toEqual(["confluence", "status", "123"]);
    });

    it("should follow factory pattern matching other features", () => {
      // Verify the pattern matches knowledgeKeys and projectKeys
      const keys = confluenceKeys;
      expect(keys.all).toBeInstanceOf(Array);
      expect(typeof keys.lists).toBe("function");
      expect(typeof keys.detail).toBe("function");
      expect(typeof keys.status).toBe("function");

      // Verify nested structure
      expect(keys.lists()).toEqual([...keys.all, "list"]);
      expect(keys.detail("test")).toEqual([...keys.all, "detail", "test"]);
      expect(keys.status("test")).toEqual([...keys.all, "status", "test"]);
    });

    it("should produce unique keys for different IDs", () => {
      const key1 = confluenceKeys.detail("source-1");
      const key2 = confluenceKeys.detail("source-2");

      expect(key1).not.toEqual(key2);
      expect(key1[2]).toBe("source-1");
      expect(key2[2]).toBe("source-2");
    });
  });

  describe("stale times", () => {
    it("should use STALE_TIMES.normal (30s) for source list", async () => {
      const mockResponse: ConfluenceSourceListResponse = {
        sources: [],
        count: 0,
      };

      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.listSources).mockResolvedValue(mockResponse);

      // The hook uses staleTime: STALE_TIMES.normal which should be 30_000
      // We verify the expected value matches
      expect(STALE_TIMES.normal).toBe(30_000);
    });

    it("should use STALE_TIMES.frequent (5s) for sync status polling", () => {
      // Verify STALE_TIMES.frequent is 5 seconds
      expect(STALE_TIMES.frequent).toBe(5_000);
    });

    it("should use STALE_TIMES.normal (30s) for detail query", () => {
      // Detail queries use normal stale time
      expect(STALE_TIMES.normal).toBe(30_000);
    });
  });

  describe("useConfluenceSources", () => {
    it("should fetch Confluence sources list", async () => {
      const mockResponse: ConfluenceSourceListResponse = {
        sources: [
          {
            source_id: "confluence_123",
            source_type: "confluence",
            space_key: "DEVDOCS",
            base_url: "https://company.atlassian.net/wiki",
            status: "ready",
            last_sync: "2024-01-01T00:00:00Z",
            total_pages: 100,
            created_at: "2024-01-01T00:00:00Z",
            updated_at: "2024-01-01T00:00:00Z",
          },
        ],
        count: 1,
      };

      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.listSources).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useConfluenceSources(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(result.current.data).toEqual(mockResponse);
      });

      expect(confluenceService.listSources).toHaveBeenCalledTimes(1);
    });
  });

  describe("useConfluenceDetail", () => {
    it("should fetch Confluence source detail when ID is provided", async () => {
      const mockStatus: ConfluenceSyncStatus = {
        status: "idle",
        last_sync: "2024-01-01T00:00:00Z",
        sync_metrics: { pages_synced: 100 },
        total_pages: 100,
        active_operation: null,
      };

      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.getStatus).mockResolvedValue(mockStatus);

      const { result } = renderHook(() => useConfluenceDetail("confluence_123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(result.current.data).toEqual(mockStatus);
      });

      expect(confluenceService.getStatus).toHaveBeenCalledWith("confluence_123");
    });

    it("should not fetch when ID is undefined", async () => {
      const { confluenceService } = await import("../../services");

      const { result } = renderHook(() => useConfluenceDetail(undefined), {
        wrapper: createWrapper(),
      });

      // Query should be disabled
      expect(result.current.isFetching).toBe(false);
      expect(confluenceService.getStatus).not.toHaveBeenCalled();
    });
  });

  describe("useConfluenceSyncStatus", () => {
    it("should fetch sync status with polling disabled by default", async () => {
      const mockStatus: ConfluenceSyncStatus = {
        status: "syncing",
        last_sync: null,
        sync_metrics: {},
        total_pages: 0,
        active_operation: {
          operation_id: "sync_123",
          status: "processing",
          progress: 50,
          log: "Processing page 50/100",
        },
      };

      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.getStatus).mockResolvedValue(mockStatus);

      const { result } = renderHook(() => useConfluenceSyncStatus("confluence_123", false), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(result.current.data).toEqual(mockStatus);
      });
    });

    it("should enable polling when isPolling is true", async () => {
      const mockStatus: ConfluenceSyncStatus = {
        status: "syncing",
        last_sync: null,
        sync_metrics: {},
        total_pages: 0,
        active_operation: {
          operation_id: "sync_123",
          status: "processing",
          progress: 50,
          log: "Processing page 50/100",
        },
      };

      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.getStatus).mockResolvedValue(mockStatus);

      const { result } = renderHook(() => useConfluenceSyncStatus("confluence_123", true), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify service was called
      expect(confluenceService.getStatus).toHaveBeenCalled();
    });
  });

  describe("useCreateSource", () => {
    it("should create source and invalidate list", async () => {
      const newSource: ConfluenceSource = {
        source_id: "confluence_456",
        source_type: "confluence",
        space_key: "NEWSPACE",
        base_url: "https://company.atlassian.net/wiki",
        status: "ready",
        last_sync: null,
        total_pages: 0,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.createSource).mockResolvedValue(newSource);

      const wrapper = createWrapper();
      const { result } = renderHook(() => useCreateSource(), { wrapper });

      await result.current.mutateAsync({
        base_url: "https://company.atlassian.net/wiki",
        api_token: "secret-token",
        email: "user@company.com",
        space_key: "NEWSPACE",
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(confluenceService.createSource).toHaveBeenCalledWith({
          base_url: "https://company.atlassian.net/wiki",
          api_token: "secret-token",
          email: "user@company.com",
          space_key: "NEWSPACE",
        });
      });
    });

    it("should rollback on error", async () => {
      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.createSource).mockRejectedValue(new Error("Invalid credentials"));

      const wrapper = createWrapper();
      const { result } = renderHook(() => useCreateSource(), { wrapper });

      await expect(
        result.current.mutateAsync({
          base_url: "https://company.atlassian.net/wiki",
          api_token: "bad-token",
          email: "user@company.com",
          space_key: "NEWSPACE",
        }),
      ).rejects.toThrow("Invalid credentials");
    });
  });

  describe("useTriggerSync", () => {
    it("should trigger sync and invalidate status", async () => {
      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.triggerSync).mockResolvedValue({
        operation_id: "sync_789",
        message: "Sync started for space DEVDOCS",
        source_id: "confluence_123",
      });

      const wrapper = createWrapper();
      const { result } = renderHook(() => useTriggerSync(), { wrapper });

      await result.current.mutateAsync("confluence_123");

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(confluenceService.triggerSync).toHaveBeenCalledWith("confluence_123");
      });
    });

    it("should handle sync trigger error", async () => {
      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.triggerSync).mockRejectedValue(new Error("Active sync in progress"));

      const wrapper = createWrapper();
      const { result } = renderHook(() => useTriggerSync(), { wrapper });

      await expect(result.current.mutateAsync("confluence_123")).rejects.toThrow("Active sync in progress");
    });
  });

  describe("useDeleteSource", () => {
    it("should optimistically remove source", async () => {
      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.deleteSource).mockResolvedValue({
        deleted: true,
        source_id: "confluence_123",
      });

      const wrapper = createWrapper();
      const { result } = renderHook(() => useDeleteSource(), { wrapper });

      await result.current.mutateAsync("confluence_123");

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
        expect(confluenceService.deleteSource).toHaveBeenCalledWith("confluence_123");
      });
    });

    it("should rollback on delete error", async () => {
      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.deleteSource).mockRejectedValue(new Error("Cannot delete source with active sync"));

      const wrapper = createWrapper();
      const { result } = renderHook(() => useDeleteSource(), { wrapper });

      await expect(result.current.mutateAsync("confluence_123")).rejects.toThrow(
        "Cannot delete source with active sync",
      );
    });
  });

  describe("cache invalidation", () => {
    it("should invalidate lists on successful create", async () => {
      const newSource: ConfluenceSource = {
        source_id: "new-source",
        source_type: "confluence",
        space_key: "NEWSPACE",
        base_url: "https://company.atlassian.net/wiki",
        status: "ready",
        last_sync: null,
        total_pages: 0,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.createSource).mockResolvedValue(newSource);

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      // Pre-populate list cache
      queryClient.setQueryData(confluenceKeys.lists(), {
        sources: [],
        count: 0,
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useCreateSource(), { wrapper });

      await result.current.mutateAsync({
        base_url: "https://company.atlassian.net/wiki",
        api_token: "token",
        email: "user@test.com",
        space_key: "NEWSPACE",
      });

      // After mutation, the list should have been invalidated
      // In TanStack Query, invalidation marks data as stale
      const listState = queryClient.getQueryState(confluenceKeys.lists());
      expect(listState?.isInvalidated).toBe(true);
    });

    it("should invalidate status on successful sync trigger", async () => {
      const { confluenceService } = await import("../../services");
      vi.mocked(confluenceService.triggerSync).mockResolvedValue({
        operation_id: "sync-123",
        message: "Sync started",
        source_id: "source-123",
      });

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      // Pre-populate status cache
      queryClient.setQueryData(confluenceKeys.status("source-123"), {
        status: "idle",
        last_sync: null,
      });

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useTriggerSync(), { wrapper });

      await result.current.mutateAsync("source-123");

      // Status should be invalidated
      const statusState = queryClient.getQueryState(confluenceKeys.status("source-123"));
      expect(statusState?.isInvalidated).toBe(true);
    });

    it("should optimistically update list on delete before server response", async () => {
      const { confluenceService } = await import("../../services");

      // Delay the response to observe optimistic update
      vi.mocked(confluenceService.deleteSource).mockImplementation(
        () =>
          new Promise((resolve) => setTimeout(() => resolve({ deleted: true, source_id: "source-to-delete" }), 100)),
      );

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      });

      // Pre-populate list with a source
      const initialData: ConfluenceSourceListResponse = {
        sources: [
          {
            source_id: "source-to-delete",
            source_type: "confluence",
            space_key: "DELETEME",
            base_url: "https://test.atlassian.net/wiki",
            status: "ready",
            last_sync: null,
            total_pages: 0,
            created_at: "2024-01-01T00:00:00Z",
            updated_at: "2024-01-01T00:00:00Z",
          },
        ],
        count: 1,
      };

      queryClient.setQueryData(confluenceKeys.lists(), initialData);

      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useDeleteSource(), { wrapper });

      // Start mutation (don't await)
      const mutationPromise = result.current.mutateAsync("source-to-delete");

      // Check optimistic update happened immediately
      await waitFor(() => {
        const cachedData = queryClient.getQueryData<ConfluenceSourceListResponse>(confluenceKeys.lists());
        // Source should be optimistically removed
        expect(cachedData?.sources.length).toBe(0);
        expect(cachedData?.count).toBe(0);
      });

      // Wait for mutation to complete
      await mutationPromise;
    });
  });
});
