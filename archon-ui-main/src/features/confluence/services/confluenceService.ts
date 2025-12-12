/**
 * Confluence Service
 * Handles all Confluence API operations using shared API client
 */

import { callAPIWithETag } from "../../shared/api/apiClient";
import type {
  ConfluenceSource,
  ConfluenceSourceListResponse,
  ConfluenceSyncStatus,
  CreateSourceRequest,
  DeleteSourceResponse,
  SyncTriggerResponse,
} from "../types";

export const confluenceService = {
  /**
   * List all Confluence sources
   */
  async listSources(): Promise<ConfluenceSourceListResponse> {
    return callAPIWithETag<ConfluenceSourceListResponse>("/api/confluence/sources");
  },

  /**
   * Create a new Confluence source
   */
  async createSource(request: CreateSourceRequest): Promise<ConfluenceSource> {
    return callAPIWithETag<ConfluenceSource>("/api/confluence/sources", {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  /**
   * Trigger a sync for a Confluence source
   */
  async triggerSync(sourceId: string): Promise<SyncTriggerResponse> {
    return callAPIWithETag<SyncTriggerResponse>(`/api/confluence/${sourceId}/sync`, {
      method: "POST",
    });
  },

  /**
   * Get sync status for a Confluence source
   */
  async getStatus(sourceId: string): Promise<ConfluenceSyncStatus> {
    return callAPIWithETag<ConfluenceSyncStatus>(`/api/confluence/${sourceId}/status`);
  },

  /**
   * Delete a Confluence source
   */
  async deleteSource(sourceId: string): Promise<DeleteSourceResponse> {
    return callAPIWithETag<DeleteSourceResponse>(`/api/confluence/${sourceId}`, {
      method: "DELETE",
    });
  },
};
