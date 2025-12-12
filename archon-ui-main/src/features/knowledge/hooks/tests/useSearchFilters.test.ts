/**
 * useSearchFilters Hook Tests
 * Story 5.4: Enhance Search UI with Confluence Filters
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { useAvailableSpaces, useSearchFilters } from "../useSearchFilters";

// Mock the Confluence service
vi.mock("../../../confluence/services", () => ({
  confluenceService: {
    listSources: vi.fn(),
  },
}));

// Mock query patterns
vi.mock("../../../shared/config/queryPatterns", () => ({
  STALE_TIMES: {
    instant: 0,
    realtime: 3_000,
    frequent: 5_000,
    normal: 30_000,
    rare: 300_000,
    static: Infinity,
  },
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

describe("useSearchFilters", () => {
  // Mock history.replaceState
  const mockReplaceState = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock history.replaceState
    vi.spyOn(window.history, "replaceState").mockImplementation(mockReplaceState);

    // Mock URLSearchParams to return empty search
    vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      pathname: "/knowledge",
      search: "",
    } as Location);
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it("should initialize with default filter values", () => {
    const { result } = renderHook(() => useSearchFilters());

    expect(result.current.filters).toEqual({
      sourceType: "all",
      spaceKeys: [],
      hasJiraLinks: false,
    });
    expect(result.current.hasActiveFilters).toBe(false);
  });

  it("should update filters via setFilters", () => {
    const { result } = renderHook(() => useSearchFilters());

    act(() => {
      result.current.setFilters({
        sourceType: "confluence",
        spaceKeys: ["DEVDOCS"],
        hasJiraLinks: true,
      });
    });

    expect(result.current.filters).toEqual({
      sourceType: "confluence",
      spaceKeys: ["DEVDOCS"],
      hasJiraLinks: true,
    });
    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("should update filters with functional update", () => {
    const { result } = renderHook(() => useSearchFilters());

    act(() => {
      result.current.setFilters((prev) => ({
        ...prev,
        sourceType: "web",
      }));
    });

    expect(result.current.filters.sourceType).toBe("web");
    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("should reset filters to defaults", () => {
    const { result } = renderHook(() => useSearchFilters());

    // First, set some filters
    act(() => {
      result.current.setFilters({
        sourceType: "confluence",
        spaceKeys: ["SPACE1", "SPACE2"],
        hasJiraLinks: true,
      });
    });

    expect(result.current.hasActiveFilters).toBe(true);

    // Reset filters
    act(() => {
      result.current.resetFilters();
    });

    expect(result.current.filters).toEqual({
      sourceType: "all",
      spaceKeys: [],
      hasJiraLinks: false,
    });
    expect(result.current.hasActiveFilters).toBe(false);
  });

  it("should update URL params when filters change", () => {
    const { result } = renderHook(() => useSearchFilters());

    act(() => {
      result.current.setFilters({
        sourceType: "confluence",
        spaceKeys: ["DEVDOCS"],
        hasJiraLinks: false,
      });
    });

    expect(window.history.replaceState).toHaveBeenCalled();
  });

  it("should initialize filters from URL params on page load", () => {
    // Mock URL with filter params
    vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      pathname: "/knowledge",
      search: "?source=confluence&spaces=DEVDOCS,TECHOPS&jira=true",
    } as Location);

    const { result } = renderHook(() => useSearchFilters());

    expect(result.current.filters).toEqual({
      sourceType: "confluence",
      spaceKeys: ["DEVDOCS", "TECHOPS"],
      hasJiraLinks: true,
    });
    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("should serialize multiple space keys as comma-separated in URL", () => {
    const { result } = renderHook(() => useSearchFilters());

    act(() => {
      result.current.setFilters({
        sourceType: "all",
        spaceKeys: ["SPACE1", "SPACE2", "SPACE3"],
        hasJiraLinks: false,
      });
    });

    // Verify replaceState was called with comma-separated spaces
    expect(window.history.replaceState).toHaveBeenCalledWith(
      {},
      "",
      expect.stringContaining("spaces=SPACE1%2CSPACE2%2CSPACE3"),
    );
  });

  it("should handle partial URL params gracefully", () => {
    // Only source type in URL
    vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      pathname: "/knowledge",
      search: "?source=web",
    } as Location);

    const { result } = renderHook(() => useSearchFilters());

    expect(result.current.filters).toEqual({
      sourceType: "web",
      spaceKeys: [],
      hasJiraLinks: false,
    });
  });

  it("should handle empty spaces param correctly", () => {
    vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      pathname: "/knowledge",
      search: "?spaces=",
    } as Location);

    const { result } = renderHook(() => useSearchFilters());

    expect(result.current.filters.spaceKeys).toEqual([]);
  });

  it("should detect active filters for source type", () => {
    const { result } = renderHook(() => useSearchFilters());

    act(() => {
      result.current.setFilters({
        sourceType: "web",
        spaceKeys: [],
        hasJiraLinks: false,
      });
    });

    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("should detect active filters for space keys", () => {
    const { result } = renderHook(() => useSearchFilters());

    act(() => {
      result.current.setFilters({
        sourceType: "all",
        spaceKeys: ["SPACE1"],
        hasJiraLinks: false,
      });
    });

    expect(result.current.hasActiveFilters).toBe(true);
  });

  it("should detect active filters for JIRA links", () => {
    const { result } = renderHook(() => useSearchFilters());

    act(() => {
      result.current.setFilters({
        sourceType: "all",
        spaceKeys: [],
        hasJiraLinks: true,
      });
    });

    expect(result.current.hasActiveFilters).toBe(true);
  });
});

describe("useAvailableSpaces", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should fetch available Confluence spaces", async () => {
    const mockResponse = {
      sources: [
        { source_id: "1", space_key: "DEVDOCS" },
        { source_id: "2", space_key: "TECHOPS" },
        { source_id: "3", space_key: "DEVDOCS" }, // Duplicate to test deduplication
      ],
      count: 3,
    };

    const { confluenceService } = await import("../../../confluence/services");
    vi.mocked(confluenceService.listSources).mockResolvedValue(mockResponse as any);

    const { result } = renderHook(() => useAvailableSpaces(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Should deduplicate and sort spaces
    expect(result.current.spaces).toEqual(["DEVDOCS", "TECHOPS"]);
  });

  it("should return empty array when no sources", async () => {
    const mockResponse = {
      sources: [],
      count: 0,
    };

    const { confluenceService } = await import("../../../confluence/services");
    vi.mocked(confluenceService.listSources).mockResolvedValue(mockResponse as any);

    const { result } = renderHook(() => useAvailableSpaces(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.spaces).toEqual([]);
  });

  it("should handle fetch error gracefully", async () => {
    const { confluenceService } = await import("../../../confluence/services");
    vi.mocked(confluenceService.listSources).mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useAvailableSpaces(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.spaces).toEqual([]);
    expect(result.current.error).toBeTruthy();
  });
});
