/**
 * Main Knowledge Base View Component
 * Orchestrates the knowledge base UI using vertical slice architecture
 * Story 5.4: Enhanced with Confluence search filters
 */

import { useQuery } from "@tanstack/react-query";
import { Folder, Globe, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ConfluenceSourceList, NewConfluenceSourceModal } from "@/features/confluence";
import { STALE_TIMES } from "@/features/shared/config/queryPatterns";
import { useToast } from "@/features/shared/hooks/useToast";
import { CrawlingProgress } from "../../progress/components/CrawlingProgress";
import type { ActiveOperation } from "../../progress/types";
import { Button } from "../../ui/primitives/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../ui/primitives/tabs";
import { AddKnowledgeDialog } from "../components/AddKnowledgeDialog";
import { KnowledgeHeader } from "../components/KnowledgeHeader";
import { KnowledgeList } from "../components/KnowledgeList";
import { SearchFilters } from "../components/SearchFilters";
import { SearchResultCard } from "../components/SearchResultCard";
import { knowledgeKeys, useKnowledgeSummaries } from "../hooks/useKnowledgeQueries";
import { useAvailableSpaces, useSearchFilters } from "../hooks/useSearchFilters";
import { KnowledgeInspector } from "../inspector/components/KnowledgeInspector";
import { knowledgeService } from "../services";
import type { ConfluenceSearchResult, ExtendedSearchOptions, KnowledgeItem, KnowledgeItemsFilter } from "../types";

export const KnowledgeView = () => {
  // View state
  const [activeTab, setActiveTab] = useState<"sources" | "confluence">("sources");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "technical" | "business">("all");
  const [isSearchMode, setIsSearchMode] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Dialog state
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isConfluenceModalOpen, setIsConfluenceModalOpen] = useState(false);
  const [inspectorItem, setInspectorItem] = useState<KnowledgeItem | null>(null);
  const [inspectorInitialTab, setInspectorInitialTab] = useState<"documents" | "code">("documents");

  // Search filters state (Story 5.4)
  const { filters, setFilters, hasActiveFilters } = useSearchFilters();
  const { spaces: availableSpaces } = useAvailableSpaces();

  // RAG Search query (Story 5.4)
  const ragSearchOptions = useMemo<ExtendedSearchOptions | null>(() => {
    if (!searchQuery || searchQuery.length < 2) return null;
    return {
      query: searchQuery,
      knowledge_type: typeFilter !== "all" ? typeFilter : undefined,
      sourceType: filters.sourceType,
      spaceKeys: filters.spaceKeys.length > 0 ? filters.spaceKeys : undefined,
      hasJiraLinks: filters.hasJiraLinks || undefined,
    };
  }, [searchQuery, typeFilter, filters]);

  // RAG Search results query
  const {
    data: searchResults,
    isLoading: isSearching,
    error: searchError,
  } = useQuery({
    queryKey: ragSearchOptions ? [...knowledgeKeys.all, "rag-search", ragSearchOptions] : ["disabled"],
    queryFn: () => (ragSearchOptions ? knowledgeService.searchKnowledgeBase(ragSearchOptions) : Promise.reject()),
    enabled: !!ragSearchOptions && isSearchMode,
    staleTime: STALE_TIMES.normal,
  });

  // Filter search results based on active filters (client-side for multi-space support)
  const filteredSearchResults = useMemo(() => {
    if (!searchResults?.results) return [];

    let results = searchResults.results as ConfluenceSearchResult[];

    // Filter by source type if not "all"
    if (filters.sourceType !== "all") {
      results = results.filter((r) => {
        if (filters.sourceType === "confluence") return !!r.spaceKey;
        if (filters.sourceType === "web") return r.source_type === "url" && !r.spaceKey;
        if (filters.sourceType === "upload") return r.source_type === "file";
        return true;
      });
    }

    // Filter by space keys if specified
    if (filters.spaceKeys.length > 0) {
      results = results.filter((r) => r.spaceKey && filters.spaceKeys.includes(r.spaceKey));
    }

    // Filter by JIRA links if enabled
    if (filters.hasJiraLinks) {
      results = results.filter((r) => r.jiraIssueLinks && r.jiraIssueLinks.length > 0);
    }

    return results;
  }, [searchResults, filters]);

  // Build filter object for API - memoize to prevent recreating on every render
  const filter = useMemo<KnowledgeItemsFilter>(() => {
    const f: KnowledgeItemsFilter = {
      page: 1,
      per_page: 100,
    };

    if (searchQuery) {
      f.search = searchQuery;
    }

    if (typeFilter !== "all") {
      f.knowledge_type = typeFilter;
    }

    return f;
  }, [searchQuery, typeFilter]);

  // Fetch knowledge summaries (no automatic polling!)
  const { data, isLoading, error, refetch, setActiveCrawlIds, activeOperations } = useKnowledgeSummaries(filter);

  const knowledgeItems = data?.items || [];
  const totalItems = data?.total || 0;
  const hasActiveOperations = activeOperations.length > 0;

  // Toast notifications
  const { showToast } = useToast();
  const previousOperations = useRef<ActiveOperation[]>([]);

  // Track crawl completions and errors for toast notifications
  useEffect(() => {
    // Find operations that just completed or failed
    const finishedOps = previousOperations.current.filter((prevOp) => {
      const currentOp = activeOperations.find((op) => op.operation_id === prevOp.operation_id);
      // Operation disappeared from active list - check its final status
      return (
        !currentOp &&
        ["crawling", "processing", "storing", "document_storage", "completed", "error", "failed"].includes(
          prevOp.status,
        )
      );
    });

    // Show toast for each finished operation
    finishedOps.forEach((op) => {
      // Check if it was an error or success
      if (op.status === "error" || op.status === "failed") {
        // Show error message with details
        const errorMessage = op.message || "Operation failed";
        showToast(`❌ ${errorMessage}`, "error", 7000);
      } else if (op.status === "completed") {
        // Show success message
        const message = op.message || "Operation completed";
        showToast(`✅ ${message}`, "success", 5000);
      }

      // Remove from active crawl IDs
      setActiveCrawlIds((prev) => prev.filter((id) => id !== op.operation_id));

      // Refetch summaries after any completion
      refetch();
    });

    // Update previous operations
    previousOperations.current = [...activeOperations];
  }, [activeOperations, showToast, refetch, setActiveCrawlIds]);

  const handleAddKnowledge = () => {
    setIsAddDialogOpen(true);
  };

  const handleViewDocument = (sourceId: string) => {
    // Find the item and open inspector to documents tab
    const item = knowledgeItems.find((k) => k.source_id === sourceId);
    if (item) {
      setInspectorInitialTab("documents");
      setInspectorItem(item);
    }
  };

  const handleViewCodeExamples = (sourceId: string) => {
    // Open the inspector to code examples tab
    const item = knowledgeItems.find((k) => k.source_id === sourceId);
    if (item) {
      setInspectorInitialTab("code");
      setInspectorItem(item);
    }
  };

  const handleDeleteSuccess = () => {
    // TanStack Query will automatically refetch
  };

  // Toggle search mode with Enter key
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && searchQuery.length >= 2) {
      setIsSearchMode(true);
      setShowFilters(true);
    }
  };

  // Exit search mode
  const handleExitSearchMode = () => {
    setIsSearchMode(false);
    setShowFilters(false);
  };

  // Update search query and optionally enter search mode
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    // Exit search mode if query is cleared
    if (!query) {
      setIsSearchMode(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div onKeyDown={handleSearchKeyDown}>
        <KnowledgeHeader
          totalItems={totalItems}
          isLoading={isLoading}
          searchQuery={searchQuery}
          onSearchChange={handleSearchChange}
          typeFilter={typeFilter}
          onTypeFilterChange={setTypeFilter}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          onAddKnowledge={handleAddKnowledge}
        />
      </div>

      {/* Search Mode Header */}
      {isSearchMode && (
        <div className="flex items-center justify-between px-6 py-3 border-b border-white/10 bg-cyan-500/5">
          <div className="flex items-center gap-3">
            <Search className="w-5 h-5 text-cyan-400" />
            <span className="text-sm text-gray-300">
              Search Results for &quot;{searchQuery}&quot;
              {filteredSearchResults.length > 0 && (
                <span className="ml-2 text-gray-500">({filteredSearchResults.length} results)</span>
              )}
            </span>
            {hasActiveFilters && (
              <span className="px-2 py-0.5 text-xs bg-cyan-500/20 text-cyan-400 rounded-full border border-cyan-500/30">
                Filters Active
              </span>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={handleExitSearchMode} className="text-gray-400 hover:text-white">
            <X className="w-4 h-4 mr-1" />
            Exit Search
          </Button>
        </div>
      )}

      {/* Search Results View (Story 5.4) */}
      {isSearchMode ? (
        <div className="flex-1 flex overflow-hidden">
          {/* Filters Sidebar */}
          {showFilters && (
            <aside className="w-64 shrink-0 p-4 border-r border-white/10 overflow-y-auto">
              <SearchFilters filters={filters} onFiltersChange={setFilters} availableSpaces={availableSpaces} />
            </aside>
          )}

          {/* Search Results */}
          <main className="flex-1 overflow-y-auto p-6">
            {isSearching ? (
              <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm text-gray-400">Searching knowledge base...</p>
                </div>
              </div>
            ) : searchError ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-red-400 mb-2">Search failed</p>
                  <p className="text-sm text-gray-500">
                    {searchError instanceof Error ? searchError.message : "Unknown error"}
                  </p>
                </div>
              </div>
            ) : filteredSearchResults.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Search className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400 mb-1">No results found</p>
                  <p className="text-sm text-gray-500">
                    {hasActiveFilters ? "Try adjusting your filters or search query" : "Try a different search query"}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {filteredSearchResults.map((result, index) => (
                  <SearchResultCard
                    key={result.id || `result-${index}`}
                    result={result}
                    onClick={() => {
                      // Could open inspector or link to source
                    }}
                  />
                ))}
              </div>
            )}
          </main>
        </div>
      ) : (
        <>
          {/* Tab Navigation */}
          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as "sources" | "confluence")}
            className="flex-1 flex flex-col"
          >
            <div className="flex justify-center px-6 py-4">
              <TabsList>
                <TabsTrigger value="sources" color="blue">
                  <Globe className="w-4 h-4 mr-2" />
                  Web & Documents
                </TabsTrigger>
                <TabsTrigger value="confluence" color="cyan">
                  <Folder className="w-4 h-4 mr-2" />
                  Confluence
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Web & Documents Tab */}
            <TabsContent value="sources" className="flex-1 overflow-auto px-6 pb-6">
              {/* Active Operations - Show at top when present */}
              {hasActiveOperations && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white/90">
                      Active Operations ({activeOperations.length})
                    </h3>
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                      <div className="w-2 h-2 bg-cyan-400 dark:bg-cyan-400 rounded-full animate-pulse" />
                      Live Updates
                    </div>
                  </div>
                  <CrawlingProgress onSwitchToBrowse={() => {}} />
                </div>
              )}

              {/* Knowledge Items List */}
              <KnowledgeList
                items={knowledgeItems}
                viewMode={viewMode}
                isLoading={isLoading}
                error={error}
                onRetry={refetch}
                onViewDocument={handleViewDocument}
                onViewCodeExamples={handleViewCodeExamples}
                onDeleteSuccess={handleDeleteSuccess}
                activeOperations={activeOperations}
                onRefreshStarted={(progressId) => {
                  setActiveCrawlIds((prev) => [...prev, progressId]);
                }}
              />
            </TabsContent>

            {/* Confluence Tab */}
            <TabsContent value="confluence" className="flex-1 overflow-auto px-6 pb-6">
              <ConfluenceSourceList
                onAddSource={() => setIsConfluenceModalOpen(true)}
                onSyncStarted={(operationId) => {
                  setActiveCrawlIds((prev) => [...prev, operationId]);
                }}
              />
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Dialogs */}
      <AddKnowledgeDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        onSuccess={() => {
          setIsAddDialogOpen(false);
          refetch();
        }}
        onCrawlStarted={(progressId) => {
          setActiveCrawlIds((prev) => [...prev, progressId]);
        }}
      />

      <NewConfluenceSourceModal
        open={isConfluenceModalOpen}
        onOpenChange={setIsConfluenceModalOpen}
        onSuccess={() => {
          setIsConfluenceModalOpen(false);
        }}
      />

      {/* Knowledge Inspector Modal */}
      {inspectorItem && (
        <KnowledgeInspector
          item={inspectorItem}
          open={!!inspectorItem}
          onOpenChange={(open) => {
            if (!open) setInspectorItem(null);
          }}
          initialTab={inspectorInitialTab}
        />
      )}
    </div>
  );
};
