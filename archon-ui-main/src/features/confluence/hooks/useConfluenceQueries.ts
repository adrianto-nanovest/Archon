/**
 * Confluence Query Hooks
 * Following TanStack Query best practices with query key factories
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSmartPolling, useToast } from "@/features/shared/hooks";
import { createOptimisticId } from "@/features/shared/utils/optimistic";
import { DISABLED_QUERY_KEY, STALE_TIMES } from "../../shared/config/queryPatterns";
import { confluenceService } from "../services";
import type {
  ConfluenceSource,
  ConfluenceSourceListResponse,
  ConfluenceSyncStatus,
  CreateSourceRequest,
} from "../types";

// Query keys factory for better organization and type safety
export const confluenceKeys = {
  all: ["confluence"] as const,
  lists: () => [...confluenceKeys.all, "list"] as const,
  detail: (id: string) => [...confluenceKeys.all, "detail", id] as const,
  status: (id: string) => [...confluenceKeys.all, "status", id] as const,
};

/**
 * Fetch all Confluence sources
 */
export function useConfluenceSources() {
  return useQuery<ConfluenceSourceListResponse>({
    queryKey: confluenceKeys.lists(),
    queryFn: () => confluenceService.listSources(),
    staleTime: STALE_TIMES.normal, // 30 seconds
  });
}

/**
 * Fetch a specific Confluence source detail
 */
export function useConfluenceDetail(sourceId: string | undefined) {
  return useQuery<ConfluenceSyncStatus>({
    queryKey: sourceId ? confluenceKeys.detail(sourceId) : DISABLED_QUERY_KEY,
    queryFn: () => (sourceId ? confluenceService.getStatus(sourceId) : Promise.reject("No source ID")),
    enabled: !!sourceId,
    staleTime: STALE_TIMES.normal,
  });
}

/**
 * Fetch sync status with optional smart polling
 * Use isPolling=true when actively monitoring sync progress
 */
export function useConfluenceSyncStatus(sourceId: string | undefined, isPolling: boolean = false) {
  const { refetchInterval } = useSmartPolling(STALE_TIMES.frequent);

  return useQuery<ConfluenceSyncStatus>({
    queryKey: sourceId ? confluenceKeys.status(sourceId) : DISABLED_QUERY_KEY,
    queryFn: () => (sourceId ? confluenceService.getStatus(sourceId) : Promise.reject("No source ID")),
    enabled: !!sourceId,
    staleTime: STALE_TIMES.frequent, // 5 seconds for sync status
    refetchInterval: isPolling ? refetchInterval : false,
  });
}

/**
 * Create a new Confluence source with optimistic updates
 */
export function useCreateSource() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (request: CreateSourceRequest) => confluenceService.createSource(request),
    onMutate: async (newSource) => {
      await queryClient.cancelQueries({ queryKey: confluenceKeys.lists() });
      const previous = queryClient.getQueryData<ConfluenceSourceListResponse>(confluenceKeys.lists());

      // Create optimistic source with temporary ID
      // ConfluenceSource uses source_id instead of id, so we create manually
      const localId = createOptimisticId();
      const optimisticSource: ConfluenceSource & { _optimistic: boolean; _localId: string } = {
        source_id: localId,
        source_type: "confluence",
        space_key: newSource.space_key,
        base_url: newSource.base_url,
        status: "ready",
        last_sync: null,
        total_pages: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        _optimistic: true,
        _localId: localId,
      };

      queryClient.setQueryData<ConfluenceSourceListResponse>(confluenceKeys.lists(), (old) => ({
        sources: [...(old?.sources || []), optimisticSource],
        count: (old?.count || 0) + 1,
      }));

      return { previous, localId };
    },
    onError: (err, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(confluenceKeys.lists(), context.previous);
      }
      showToast(err instanceof Error ? err.message : "Failed to create source", "error");
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: confluenceKeys.lists() });
      showToast(`Confluence source created: ${data.space_key}`, "success");
    },
  });
}

/**
 * Trigger a sync for a Confluence source
 */
export function useTriggerSync() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (sourceId: string) => confluenceService.triggerSync(sourceId),
    onSuccess: (data, sourceId) => {
      queryClient.invalidateQueries({ queryKey: confluenceKeys.status(sourceId) });
      queryClient.invalidateQueries({ queryKey: confluenceKeys.lists() });
      showToast(data.message, "success");
    },
    onError: (err) => {
      showToast(err instanceof Error ? err.message : "Failed to trigger sync", "error");
    },
  });
}

/**
 * Delete a Confluence source with optimistic updates
 */
export function useDeleteSource() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  return useMutation({
    mutationFn: (sourceId: string) => confluenceService.deleteSource(sourceId),
    onMutate: async (sourceId) => {
      await queryClient.cancelQueries({ queryKey: confluenceKeys.lists() });
      const previous = queryClient.getQueryData<ConfluenceSourceListResponse>(confluenceKeys.lists());

      queryClient.setQueryData<ConfluenceSourceListResponse>(confluenceKeys.lists(), (old) => ({
        sources: (old?.sources || []).filter((s) => s.source_id !== sourceId),
        count: Math.max(0, (old?.count || 0) - 1),
      }));

      return { previous };
    },
    onError: (err, _sourceId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(confluenceKeys.lists(), context.previous);
      }
      showToast(err instanceof Error ? err.message : "Failed to delete source", "error");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: confluenceKeys.all });
      showToast("Source deleted successfully", "success");
    },
  });
}
