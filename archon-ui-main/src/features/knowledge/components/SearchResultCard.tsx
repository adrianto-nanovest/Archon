/**
 * Search Result Card Component
 * Displays search results with Confluence metadata support
 * Story 5.4: Enhance Search UI with Confluence Filters
 */

import { ChevronRight, ExternalLink, FileText, Globe, Link2, Upload } from "lucide-react";
import type React from "react";
import { useMemo } from "react";
import { cn, glassmorphism } from "../../ui/primitives/styles";
import type { ConfluenceSearchResult, JiraIssueLink } from "../types";

interface SearchResultCardProps {
  result: ConfluenceSearchResult;
  jiraBaseUrl?: string;
  onClick?: () => void;
  className?: string;
}

// Static color map for source type badges (no dynamic Tailwind)
const sourceTypeBadgeColors = {
  web: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  upload: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  confluence: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  file: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  url: "bg-blue-500/20 text-blue-400 border-blue-500/30",
} as const;

// Source type icon mapping
const sourceTypeIcons = {
  web: Globe,
  upload: Upload,
  confluence: FileText,
  file: Upload,
  url: Globe,
} as const;

/**
 * JIRA Chip Component
 * Clickable chip that opens JIRA issue in new tab
 */
interface JiraChipProps {
  issueKey: string;
  issueUrl?: string;
  jiraBaseUrl: string;
}

const JiraChip: React.FC<JiraChipProps> = ({ issueKey, issueUrl, jiraBaseUrl }) => {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const url = issueUrl || `${jiraBaseUrl}/browse/${issueKey}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick(e as unknown as React.MouseEvent);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded",
        "bg-blue-500/20 text-blue-400 border border-blue-500/30",
        "hover:bg-blue-500/30 hover:border-blue-500/50 transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-blue-500/50",
      )}
      aria-label={`Open JIRA issue ${issueKey} in new tab`}
    >
      <Link2 className="w-3 h-3" aria-hidden="true" />
      {issueKey}
      <ExternalLink className="w-2.5 h-2.5 opacity-60" aria-hidden="true" />
    </button>
  );
};

/**
 * Breadcrumbs Component
 * Displays page hierarchy with truncation at 5 levels
 */
interface BreadcrumbsProps {
  path: string;
  className?: string;
}

const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ path, className }) => {
  const displaySegments = useMemo(() => {
    if (!path) return [];

    // path format: "/parent_id/child_id/grandchild_id"
    const segments = path.split("/").filter(Boolean);

    if (segments.length === 0) return [];

    // Truncate if more than 5 levels
    if (segments.length > 5) {
      return [...segments.slice(0, 2), "...", ...segments.slice(-2)];
    }

    return segments;
  }, [path]);

  if (displaySegments.length === 0) return null;

  return (
    <nav aria-label="Page hierarchy" className={cn("flex items-center gap-0.5 text-xs text-gray-500", className)}>
      {displaySegments.map((segment, index) => (
        <span key={`${segment}-${index}`} className="flex items-center">
          {index > 0 && <ChevronRight className="w-3 h-3 mx-0.5 opacity-50" aria-hidden="true" />}
          <span className={segment === "..." ? "text-gray-600" : "truncate max-w-[80px]"} title={segment}>
            {segment}
          </span>
        </span>
      ))}
    </nav>
  );
};

/**
 * SearchResultCard - Display a single search result
 *
 * Features:
 * - Base result info (title, content snippet)
 * - Confluence metadata when present:
 *   - Space badge (cyan)
 *   - JIRA chips (clickable, external link)
 *   - Hierarchy breadcrumbs (truncated at 5 levels)
 */
export const SearchResultCard: React.FC<SearchResultCardProps> = ({
  result,
  jiraBaseUrl = "https://jira.atlassian.com",
  onClick,
  className,
}) => {
  // Determine source type for badge display
  const sourceType = useMemo(() => {
    if (result.spaceKey) return "confluence";
    if (result.source_type === "file") return "upload";
    if (result.source_type === "url") return "web";
    return result.source_type || "web";
  }, [result.spaceKey, result.source_type]);

  const SourceIcon = sourceTypeIcons[sourceType as keyof typeof sourceTypeIcons] || Globe;
  const badgeColor =
    sourceTypeBadgeColors[sourceType as keyof typeof sourceTypeBadgeColors] || sourceTypeBadgeColors.web;

  // Get display title
  const displayTitle = result.title || result.metadata?.title || "Untitled";

  // Get content preview
  const contentPreview = useMemo(() => {
    const content = result.content || "";
    if (content.length > 200) {
      return `${content.substring(0, 200)}...`;
    }
    return content;
  }, [result.content]);

  // Confluence-specific metadata
  const isConfluence = Boolean(result.spaceKey);
  const hasJiraLinks = Boolean(result.jiraIssueLinks?.length);
  const hasPath = Boolean(result.path);

  const handleClick = () => {
    onClick?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <article
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick ? handleClick : undefined}
      onKeyDown={onClick ? handleKeyDown : undefined}
      className={cn(
        "flex flex-col gap-3 p-4 rounded-lg",
        glassmorphism.background.subtle,
        glassmorphism.border.default,
        glassmorphism.interactive.base,
        onClick && "cursor-pointer hover:bg-white/5",
        className,
      )}
      aria-label={`Search result: ${displayTitle}`}
    >
      {/* Header: Source type badge + Title */}
      <div className="flex items-start gap-3">
        {/* Source Type Badge */}
        <span
          className={cn("flex items-center gap-1.5 px-2 py-1 text-xs rounded-md border shrink-0", badgeColor)}
          title={`Source: ${sourceType}`}
        >
          <SourceIcon className="w-3.5 h-3.5" aria-hidden="true" />
          {sourceType}
        </span>

        {/* Title and Confluence Space Badge */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-medium text-gray-100 truncate">{displayTitle}</h3>

            {/* Confluence Space Badge */}
            {isConfluence && result.spaceKey && (
              <span
                className={cn("text-xs px-1.5 py-0.5 rounded border shrink-0", sourceTypeBadgeColors.confluence)}
                title={`Confluence space: ${result.spaceKey}`}
              >
                {result.spaceKey}
              </span>
            )}
          </div>

          {/* Breadcrumbs */}
          {hasPath && result.path && <Breadcrumbs path={result.path} className="mt-1" />}
        </div>
      </div>

      {/* Content Preview */}
      <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed">{contentPreview}</p>

      {/* JIRA Links */}
      {hasJiraLinks && result.jiraIssueLinks && (
        <div className="flex flex-wrap gap-1.5">
          {result.jiraIssueLinks.slice(0, 5).map((link: JiraIssueLink) => (
            <JiraChip
              key={link.issue_key}
              issueKey={link.issue_key}
              issueUrl={link.issue_url}
              jiraBaseUrl={jiraBaseUrl}
            />
          ))}
          {result.jiraIssueLinks.length > 5 && (
            <span className="text-xs text-gray-500 px-2 py-0.5">+{result.jiraIssueLinks.length - 5} more</span>
          )}
        </div>
      )}

      {/* Section indicator if available */}
      {result.section && (
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <span className="opacity-60">Section:</span>
          <span className="truncate">{result.section}</span>
        </div>
      )}
    </article>
  );
};
