/**
 * Search Filters Hook
 * Manages search filter state with URL query param persistence
 * Story 5.4: Enhance Search UI with Confluence Filters
 */

import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { confluenceService } from "../../confluence/services";
import { STALE_TIMES } from "../../shared/config/queryPatterns";
import type { SearchFiltersState, SourceTypeFilter } from "../types";

// Default filter values
const DEFAULT_FILTERS: SearchFiltersState = {
  sourceType: "all",
  spaceKeys: [],
  hasJiraLinks: false,
};

/**
 * Parse filters from URL query params
 */
const parseFiltersFromUrl = (): SearchFiltersState => {
  if (typeof window === "undefined") return DEFAULT_FILTERS;

  const params = new URLSearchParams(window.location.search);

  return {
    sourceType: (params.get("source") as SourceTypeFilter) || "all",
    spaceKeys: params.get("spaces")?.split(",").filter(Boolean) || [],
    hasJiraLinks: params.get("jira") === "true",
  };
};

/**
 * Update URL query params with filter state
 */
const updateUrlParams = (filters: SearchFiltersState): void => {
  if (typeof window === "undefined") return;

  const params = new URLSearchParams();

  if (filters.sourceType !== "all") {
    params.set("source", filters.sourceType);
  }

  if (filters.spaceKeys.length > 0) {
    params.set("spaces", filters.spaceKeys.join(","));
  }

  if (filters.hasJiraLinks) {
    params.set("jira", "true");
  }

  // Update URL without page reload
  const newUrl = params.toString() ? `${window.location.pathname}?${params.toString()}` : window.location.pathname;

  window.history.replaceState({}, "", newUrl);
};

/**
 * Hook to manage search filters with URL persistence
 */
export function useSearchFilters() {
  // Initialize from URL params
  const [filters, setFiltersInternal] = useState<SearchFiltersState>(() => parseFiltersFromUrl());

  // Sync to URL on filter change
  useEffect(() => {
    updateUrlParams(filters);
  }, [filters]);

  // Setter that updates both state and URL
  const setFilters = useCallback(
    (newFilters: SearchFiltersState | ((prev: SearchFiltersState) => SearchFiltersState)) => {
      setFiltersInternal((prev) => {
        const next = typeof newFilters === "function" ? newFilters(prev) : newFilters;
        return next;
      });
    },
    [],
  );

  // Reset filters to defaults
  const resetFilters = useCallback(() => {
    setFiltersInternal(DEFAULT_FILTERS);
  }, []);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return filters.sourceType !== "all" || filters.spaceKeys.length > 0 || filters.hasJiraLinks;
  }, [filters]);

  return {
    filters,
    setFilters,
    resetFilters,
    hasActiveFilters,
  };
}

/**
 * Hook to fetch available Confluence spaces for filter dropdown
 */
export function useAvailableSpaces() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["confluence", "spaces-for-filter"],
    queryFn: async () => {
      const response = await confluenceService.listSources();
      // Extract unique space keys from sources
      const spaceKeys = response.sources.map((source) => source.space_key);
      return [...new Set(spaceKeys)].sort();
    },
    staleTime: STALE_TIMES.rare, // Spaces don't change often
  });

  return {
    spaces: data || [],
    isLoading,
    error,
  };
}
