/**
 * Confluence Types
 * Matches backend Pydantic models from confluence_api.py
 */

/**
 * Match: confluence_api.py -> ConfluenceSourceResponse
 * Confluence source with sync metadata
 */
export interface ConfluenceSource {
  source_id: string;
  source_type: "confluence";
  space_key: string;
  base_url: string;
  status: string | null;
  last_sync: string | null;
  total_pages: number;
  created_at: string;
  updated_at: string;
}

/**
 * Sync metrics for completed operations
 */
export interface ConfluenceSyncMetrics {
  pages_added: number;
  pages_updated: number;
  pages_deleted: number;
  pages_processed: number;
  total_pages: number;
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
  errors: string[];
}

/**
 * Active operation details during sync
 */
export interface ConfluenceActiveOperation {
  operation_id: string;
  status: string;
  progress: number;
  log: string;
  /** Array of log entries for expandable display */
  logs?: string[];
  /** Estimated completion timestamp (ISO string) */
  estimated_completion?: string;
  /** Number of pages processed so far */
  pages_processed?: number;
  /** Total number of pages to sync */
  total_pages?: number;
  /** Current step description */
  current_step?: string;
  /** When the operation started (ISO string) */
  started_at?: string;
}

/**
 * Match: confluence_api.py -> ConfluenceStatusResponse
 * Sync status with active operation details
 */
export interface ConfluenceSyncStatus {
  status: string; // "syncing" | "idle" | "completed" | "error"
  last_sync: string | null;
  sync_metrics: ConfluenceSyncMetrics | Record<string, unknown>;
  total_pages: number;
  active_operation: ConfluenceActiveOperation | null;
}

/**
 * Match: confluence_api.py -> CreateConfluenceSourceRequest
 * Request body for creating a Confluence source
 */
export interface CreateSourceRequest {
  base_url: string;
  api_token: string;
  email: string;
  space_key: string;
  deletion_strategy?: string; // default: "weekly_reconciliation"
}

/**
 * Match: confluence_api.py -> ConfluenceSourceListResponse
 * Response for listing Confluence sources
 */
export interface ConfluenceSourceListResponse {
  sources: ConfluenceSource[];
  count: number;
}

/**
 * Match: confluence_api.py -> SyncTriggerResponse
 * Response when triggering a sync operation
 */
export interface SyncTriggerResponse {
  operation_id: string;
  message: string;
  source_id: string;
}

/**
 * Match: confluence_api.py -> DeleteSourceResponse
 * Response for source deletion
 */
export interface DeleteSourceResponse {
  deleted: boolean;
  source_id: string;
}

/**
 * Match: confluence_api.py -> ConfluencePageSummary
 * Summary of a Confluence page for listing
 */
export interface ConfluencePageSummary {
  page_id: string;
  title: string;
  space_key: string;
  version: number;
  last_modified: string;
  is_deleted: boolean;
  path: string | null;
}

/**
 * Match: confluence_api.py -> ConfluencePagesListResponse
 * Paginated list of pages
 */
export interface ConfluencePagesListResponse {
  pages: ConfluencePageSummary[];
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
}
