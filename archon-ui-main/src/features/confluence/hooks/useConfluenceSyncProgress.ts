/**
 * Confluence Sync Progress Hook
 * Wrapper around useOperationProgress for Confluence sync operations
 *
 * REUSES existing progress infrastructure - no new polling logic!
 * Uses STALE_TIMES.frequent (5s) for polling interval
 */

import { useOperationProgress } from "@/features/progress/hooks/useProgressQueries";
import type { ProgressResponse } from "@/features/progress/types";
import { STALE_TIMES } from "@/features/shared/config/queryPatterns";

interface UseConfluenceSyncProgressOptions {
  /** Callback when sync completes successfully */
  onComplete?: (data: ProgressResponse) => void;
  /** Callback when sync fails */
  onError?: (error: string) => void;
}

/**
 * Hook to track Confluence sync operation progress
 *
 * @param operationId - The operation ID from useTriggerSync response (null to disable)
 * @param options - Callbacks for completion and error
 * @returns Progress data and status flags
 *
 * @example
 * ```tsx
 * const { data, isLoading, isComplete, isFailed, isActive } = useConfluenceSyncProgress(
 *   operationId,
 *   {
 *     onComplete: (data) => {
 *       showToast("Sync complete!", "success");
 *       refetchSources();
 *     },
 *     onError: (error) => {
 *       showToast(`Sync failed: ${error}`, "error");
 *     },
 *   }
 * );
 * ```
 */
export function useConfluenceSyncProgress(operationId: string | null, options?: UseConfluenceSyncProgressOptions) {
  return useOperationProgress(operationId, {
    onComplete: options?.onComplete,
    onError: options?.onError,
    pollingInterval: STALE_TIMES.frequent, // 5 seconds
  });
}

export type { UseConfluenceSyncProgressOptions };
