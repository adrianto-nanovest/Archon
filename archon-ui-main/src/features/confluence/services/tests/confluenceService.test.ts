/**
 * Confluence Service Contract Tests
 * Story 6.2: Implement Frontend Component Tests
 *
 * These tests verify:
 * 1. Service methods have correct type signatures
 * 2. Mock return types match actual API response shapes
 * 3. Type safety is enforced at compile time
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  ConfluenceSource,
  ConfluenceSourceListResponse,
  ConfluenceSyncStatus,
  CreateSourceRequest,
  DeleteSourceResponse,
  SyncTriggerResponse,
} from "../../types";

// Mock the API client
vi.mock("@/features/shared/api/apiClient", () => ({
  callAPIWithETag: vi.fn(),
}));

// Import service after mocking
import { confluenceService } from "../confluenceService";

describe("confluenceService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("type contracts", () => {
    it("listSources returns ConfluenceSourceListResponse shape", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");

      const mockResponse: ConfluenceSourceListResponse = {
        sources: [
          {
            source_id: "src-123",
            source_type: "confluence",
            space_key: "DEVDOCS",
            base_url: "https://company.atlassian.net/wiki",
            status: "ready",
            last_sync: "2024-01-15T10:30:00Z",
            total_pages: 42,
            created_at: "2024-01-01T00:00:00Z",
            updated_at: "2024-01-15T10:30:00Z",
          },
        ],
        count: 1,
      };

      vi.mocked(callAPIWithETag).mockResolvedValue(mockResponse);

      const result = await confluenceService.listSources();

      // Type checks at compile time
      expect(result.sources).toBeDefined();
      expect(Array.isArray(result.sources)).toBe(true);
      expect(typeof result.count).toBe("number");

      // Validate source shape
      if (result.sources.length > 0) {
        const source: ConfluenceSource = result.sources[0];
        expect(typeof source.source_id).toBe("string");
        expect(source.source_type).toBe("confluence");
        expect(typeof source.space_key).toBe("string");
        expect(typeof source.base_url).toBe("string");
        expect(typeof source.total_pages).toBe("number");
        expect(typeof source.created_at).toBe("string");
        expect(typeof source.updated_at).toBe("string");
      }
    });

    it("createSource accepts CreateSourceRequest and returns ConfluenceSource", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");

      const request: CreateSourceRequest = {
        base_url: "https://company.atlassian.net/wiki",
        api_token: "secret-token",
        email: "user@company.com",
        space_key: "NEWSPACE",
        deletion_strategy: "weekly_reconciliation",
      };

      const mockResponse: ConfluenceSource = {
        source_id: "src-456",
        source_type: "confluence",
        space_key: "NEWSPACE",
        base_url: "https://company.atlassian.net/wiki",
        status: "ready",
        last_sync: null,
        total_pages: 0,
        created_at: "2024-01-20T00:00:00Z",
        updated_at: "2024-01-20T00:00:00Z",
      };

      vi.mocked(callAPIWithETag).mockResolvedValue(mockResponse);

      const result = await confluenceService.createSource(request);

      // Verify request was passed correctly
      expect(callAPIWithETag).toHaveBeenCalledWith("/api/confluence/sources", {
        method: "POST",
        body: JSON.stringify(request),
      });

      // Type checks at compile time
      expect(typeof result.source_id).toBe("string");
      expect(result.source_type).toBe("confluence");
      expect(result.space_key).toBe(request.space_key);
      expect(result.base_url).toBe(request.base_url);
    });

    it("triggerSync accepts sourceId and returns SyncTriggerResponse", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");

      const sourceId = "src-123";
      const mockResponse: SyncTriggerResponse = {
        operation_id: "op-789",
        message: "Sync started for space DEVDOCS",
        source_id: sourceId,
      };

      vi.mocked(callAPIWithETag).mockResolvedValue(mockResponse);

      const result = await confluenceService.triggerSync(sourceId);

      // Verify endpoint was called correctly
      expect(callAPIWithETag).toHaveBeenCalledWith(`/api/confluence/${sourceId}/sync`, {
        method: "POST",
      });

      // Type checks at compile time
      expect(typeof result.operation_id).toBe("string");
      expect(typeof result.message).toBe("string");
      expect(result.source_id).toBe(sourceId);
    });

    it("getStatus returns ConfluenceSyncStatus shape", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");

      const sourceId = "src-123";
      const mockResponse: ConfluenceSyncStatus = {
        status: "syncing",
        last_sync: "2024-01-15T10:30:00Z",
        sync_metrics: {
          pages_added: 10,
          pages_updated: 5,
          pages_deleted: 0,
          pages_processed: 15,
          total_pages: 100,
          start_time: "2024-01-20T00:00:00Z",
          errors: [],
        },
        total_pages: 100,
        active_operation: {
          operation_id: "op-789",
          status: "processing",
          progress: 50,
          log: "Processing page 50/100",
          logs: ["Started sync", "Processing page 50/100"],
          pages_processed: 50,
          total_pages: 100,
          current_step: "Processing pages",
        },
      };

      vi.mocked(callAPIWithETag).mockResolvedValue(mockResponse);

      const result = await confluenceService.getStatus(sourceId);

      // Verify endpoint was called correctly
      expect(callAPIWithETag).toHaveBeenCalledWith(`/api/confluence/${sourceId}/status`);

      // Type checks at compile time
      expect(typeof result.status).toBe("string");
      expect(typeof result.total_pages).toBe("number");
      expect(result.sync_metrics).toBeDefined();

      // Validate active_operation shape when present
      if (result.active_operation) {
        expect(typeof result.active_operation.operation_id).toBe("string");
        expect(typeof result.active_operation.status).toBe("string");
        expect(typeof result.active_operation.progress).toBe("number");
        expect(typeof result.active_operation.log).toBe("string");
      }
    });

    it("getStatus handles idle status with null active_operation", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");

      const sourceId = "src-123";
      const mockResponse: ConfluenceSyncStatus = {
        status: "idle",
        last_sync: "2024-01-15T10:30:00Z",
        sync_metrics: {},
        total_pages: 42,
        active_operation: null,
      };

      vi.mocked(callAPIWithETag).mockResolvedValue(mockResponse);

      const result = await confluenceService.getStatus(sourceId);

      expect(result.status).toBe("idle");
      expect(result.active_operation).toBeNull();
    });

    it("deleteSource returns DeleteSourceResponse shape", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");

      const sourceId = "src-123";
      const mockResponse: DeleteSourceResponse = {
        deleted: true,
        source_id: sourceId,
      };

      vi.mocked(callAPIWithETag).mockResolvedValue(mockResponse);

      const result = await confluenceService.deleteSource(sourceId);

      // Verify endpoint was called correctly
      expect(callAPIWithETag).toHaveBeenCalledWith(`/api/confluence/${sourceId}`, {
        method: "DELETE",
      });

      // Type checks at compile time
      expect(typeof result.deleted).toBe("boolean");
      expect(result.deleted).toBe(true);
      expect(result.source_id).toBe(sourceId);
    });
  });

  describe("API endpoints", () => {
    it("listSources calls correct endpoint", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockResolvedValue({ sources: [], count: 0 });

      await confluenceService.listSources();

      expect(callAPIWithETag).toHaveBeenCalledWith("/api/confluence/sources");
    });

    it("createSource calls POST /api/confluence/sources", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockResolvedValue({});

      const request: CreateSourceRequest = {
        base_url: "https://test.atlassian.net/wiki",
        api_token: "token",
        email: "test@test.com",
        space_key: "TEST",
      };

      await confluenceService.createSource(request);

      expect(callAPIWithETag).toHaveBeenCalledWith("/api/confluence/sources", {
        method: "POST",
        body: JSON.stringify(request),
      });
    });

    it("triggerSync calls POST /api/confluence/{id}/sync", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockResolvedValue({});

      await confluenceService.triggerSync("source-abc");

      expect(callAPIWithETag).toHaveBeenCalledWith("/api/confluence/source-abc/sync", {
        method: "POST",
      });
    });

    it("getStatus calls GET /api/confluence/{id}/status", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockResolvedValue({});

      await confluenceService.getStatus("source-xyz");

      expect(callAPIWithETag).toHaveBeenCalledWith("/api/confluence/source-xyz/status");
    });

    it("deleteSource calls DELETE /api/confluence/{id}", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockResolvedValue({});

      await confluenceService.deleteSource("source-123");

      expect(callAPIWithETag).toHaveBeenCalledWith("/api/confluence/source-123", {
        method: "DELETE",
      });
    });
  });

  describe("error handling", () => {
    it("propagates API errors from listSources", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockRejectedValue(new Error("Network error"));

      await expect(confluenceService.listSources()).rejects.toThrow("Network error");
    });

    it("propagates API errors from createSource", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockRejectedValue(new Error("Invalid credentials"));

      const request: CreateSourceRequest = {
        base_url: "https://test.atlassian.net/wiki",
        api_token: "bad-token",
        email: "test@test.com",
        space_key: "TEST",
      };

      await expect(confluenceService.createSource(request)).rejects.toThrow("Invalid credentials");
    });

    it("propagates API errors from triggerSync", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockRejectedValue(new Error("Sync already in progress"));

      await expect(confluenceService.triggerSync("source-123")).rejects.toThrow("Sync already in progress");
    });

    it("propagates API errors from getStatus", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockRejectedValue(new Error("Source not found"));

      await expect(confluenceService.getStatus("invalid-id")).rejects.toThrow("Source not found");
    });

    it("propagates API errors from deleteSource", async () => {
      const { callAPIWithETag } = await import("@/features/shared/api/apiClient");
      vi.mocked(callAPIWithETag).mockRejectedValue(new Error("Cannot delete source with active sync"));

      await expect(confluenceService.deleteSource("source-123")).rejects.toThrow(
        "Cannot delete source with active sync",
      );
    });
  });
});
