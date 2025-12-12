/**
 * Search Filters Component
 * Provides Confluence-specific filters for search results
 * Story 5.4: Enhance Search UI with Confluence Filters
 */

import { Folder, Globe, Link2, Upload } from "lucide-react";
import { useCallback } from "react";
import { Checkbox } from "../../ui/primitives/checkbox";
import { Label } from "../../ui/primitives/label";
import { cn, glassmorphism } from "../../ui/primitives/styles";
import { Switch } from "../../ui/primitives/switch";
import { ToggleGroup, ToggleGroupItem } from "../../ui/primitives/toggle-group";
import type { SearchFiltersState, SourceTypeFilter } from "../types";

interface SearchFiltersProps {
  filters: SearchFiltersState;
  onFiltersChange: (filters: SearchFiltersState) => void;
  availableSpaces: string[];
  className?: string;
}

// Static color map for source type badges (no dynamic Tailwind)
const sourceTypeBadgeColors = {
  web: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  upload: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  confluence: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
} as const;

/**
 * SearchFilters - Filter sidebar for knowledge base search
 *
 * Features:
 * - Source type filter (Web/Upload/Confluence)
 * - Confluence space multi-select
 * - "Has JIRA Links" toggle
 * - URL query param persistence
 */
export const SearchFilters: React.FC<SearchFiltersProps> = ({
  filters,
  onFiltersChange,
  availableSpaces,
  className,
}) => {
  // Handle source type change
  const handleSourceTypeChange = useCallback(
    (value: string) => {
      if (value) {
        onFiltersChange({
          ...filters,
          sourceType: value as SourceTypeFilter,
        });
      }
    },
    [filters, onFiltersChange],
  );

  // Handle space selection toggle
  const handleSpaceToggle = useCallback(
    (spaceKey: string, checked: boolean) => {
      const newSpaceKeys = checked ? [...filters.spaceKeys, spaceKey] : filters.spaceKeys.filter((k) => k !== spaceKey);

      onFiltersChange({
        ...filters,
        spaceKeys: newSpaceKeys,
      });
    },
    [filters, onFiltersChange],
  );

  // Handle JIRA links toggle
  const handleJiraLinksChange = useCallback(
    (checked: boolean) => {
      onFiltersChange({
        ...filters,
        hasJiraLinks: checked,
      });
    },
    [filters, onFiltersChange],
  );

  // Clear all space selections
  const handleClearSpaces = useCallback(() => {
    onFiltersChange({
      ...filters,
      spaceKeys: [],
    });
  }, [filters, onFiltersChange]);

  // Select all spaces
  const handleSelectAllSpaces = useCallback(() => {
    onFiltersChange({
      ...filters,
      spaceKeys: [...availableSpaces],
    });
  }, [filters, availableSpaces, onFiltersChange]);

  // Only show Confluence filters when source type includes Confluence
  const showConfluenceFilters = filters.sourceType === "all" || filters.sourceType === "confluence";

  return (
    <div
      className={cn(
        "flex flex-col gap-5 p-4 rounded-lg",
        glassmorphism.background.subtle,
        glassmorphism.border.default,
        className,
      )}
    >
      {/* Filter Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200">Filters</h3>
      </div>

      {/* Source Type Filter */}
      <div className="flex flex-col gap-2">
        <Label className="text-xs text-gray-400">Source Type</Label>
        <ToggleGroup
          type="single"
          size="sm"
          value={filters.sourceType}
          onValueChange={handleSourceTypeChange}
          aria-label="Filter by source type"
          className="w-full justify-start"
        >
          <ToggleGroupItem
            value="all"
            aria-label="All sources"
            title="All sources"
            className="flex items-center gap-1.5 px-3"
          >
            <span className="text-xs">All</span>
          </ToggleGroupItem>
          <ToggleGroupItem
            value="web"
            aria-label="Web sources"
            title="Web sources"
            className="flex items-center gap-1.5 px-2"
          >
            <Globe className="w-3.5 h-3.5" aria-hidden="true" />
          </ToggleGroupItem>
          <ToggleGroupItem
            value="upload"
            aria-label="Uploaded documents"
            title="Uploaded documents"
            className="flex items-center gap-1.5 px-2"
          >
            <Upload className="w-3.5 h-3.5" aria-hidden="true" />
          </ToggleGroupItem>
          <ToggleGroupItem
            value="confluence"
            aria-label="Confluence"
            title="Confluence"
            className="flex items-center gap-1.5 px-2"
          >
            <Folder className="w-3.5 h-3.5" aria-hidden="true" />
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      {/* Confluence Space Multi-Select */}
      {showConfluenceFilters && availableSpaces.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-gray-400">Confluence Spaces</Label>
            <div className="flex items-center gap-2">
              {filters.spaceKeys.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearSpaces}
                  className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                  aria-label="Clear space selection"
                >
                  Clear
                </button>
              )}
              {filters.spaceKeys.length < availableSpaces.length && (
                <button
                  type="button"
                  onClick={handleSelectAllSpaces}
                  className="text-xs text-cyan-500 hover:text-cyan-400 transition-colors"
                  aria-label="Select all spaces"
                >
                  All
                </button>
              )}
            </div>
          </div>

          <div
            className={cn(
              "flex flex-col gap-1 max-h-40 overflow-y-auto p-2 rounded-md",
              "bg-black/20 dark:bg-black/20 border border-white/5",
            )}
            role="group"
            aria-label="Confluence space selection"
          >
            {availableSpaces.map((spaceKey) => (
              <label
                key={spaceKey}
                className={cn(
                  "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer",
                  "hover:bg-white/5 transition-colors",
                )}
              >
                <Checkbox
                  checked={filters.spaceKeys.includes(spaceKey)}
                  onCheckedChange={(checked) => handleSpaceToggle(spaceKey, checked === true)}
                  color="cyan"
                  aria-label={`Select space ${spaceKey}`}
                />
                <span className={cn("text-xs px-1.5 py-0.5 rounded border", sourceTypeBadgeColors.confluence)}>
                  {spaceKey}
                </span>
              </label>
            ))}
          </div>

          {filters.spaceKeys.length > 0 && (
            <p className="text-xs text-gray-500">
              {filters.spaceKeys.length} space{filters.spaceKeys.length !== 1 ? "s" : ""} selected
            </p>
          )}
        </div>
      )}

      {/* Has JIRA Links Toggle */}
      {showConfluenceFilters && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Link2 className="w-4 h-4 text-blue-400" aria-hidden="true" />
            <Label htmlFor="jira-links-toggle" className="text-xs text-gray-300 cursor-pointer">
              Has JIRA Links
            </Label>
          </div>
          <Switch
            id="jira-links-toggle"
            checked={filters.hasJiraLinks}
            onCheckedChange={handleJiraLinksChange}
            color="blue"
            size="sm"
            aria-label="Filter results with JIRA links"
          />
        </div>
      )}

      {/* Active Filters Summary */}
      {(filters.sourceType !== "all" || filters.spaceKeys.length > 0 || filters.hasJiraLinks) && (
        <div className="pt-3 border-t border-white/10">
          <p className="text-xs text-gray-500 mb-2">Active filters:</p>
          <div className="flex flex-wrap gap-1.5">
            {filters.sourceType !== "all" && (
              <span
                className={cn(
                  "text-xs px-2 py-0.5 rounded-full border",
                  filters.sourceType === "web" && sourceTypeBadgeColors.web,
                  filters.sourceType === "upload" && sourceTypeBadgeColors.upload,
                  filters.sourceType === "confluence" && sourceTypeBadgeColors.confluence,
                )}
              >
                {filters.sourceType}
              </span>
            )}
            {filters.spaceKeys.length > 0 && (
              <span className={cn("text-xs px-2 py-0.5 rounded-full border", sourceTypeBadgeColors.confluence)}>
                {filters.spaceKeys.length} space{filters.spaceKeys.length !== 1 ? "s" : ""}
              </span>
            )}
            {filters.hasJiraLinks && (
              <span className="text-xs px-2 py-0.5 rounded-full border bg-blue-500/20 text-blue-400 border-blue-500/30">
                JIRA
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
