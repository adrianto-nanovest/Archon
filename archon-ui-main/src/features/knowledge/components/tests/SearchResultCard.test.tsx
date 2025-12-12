/**
 * SearchResultCard Component Tests
 * Story 5.4: Enhance Search UI with Confluence Filters
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "../../../testing/test-utils";
import type { ConfluenceSearchResult, JiraIssueLink } from "../../types";
import { SearchResultCard } from "../SearchResultCard";

// Base mock result
const mockWebResult: ConfluenceSearchResult = {
  id: "chunk-123",
  source_id: "source-123",
  source_type: "url",
  title: "Web Page Title",
  content: "This is the content of a web page search result that was crawled.",
  section: "Documentation",
  url: "https://example.com/docs",
  metadata: {
    title: "Web Page Title",
  },
};

const mockConfluenceResult: ConfluenceSearchResult = {
  id: "chunk-456",
  source_id: "source-456",
  source_type: "confluence",
  title: "Confluence Page Title",
  content: "This is content from a Confluence page with some technical documentation.",
  section: "Architecture",
  url: "https://company.atlassian.net/wiki/spaces/DEVDOCS/pages/123456",
  spaceKey: "DEVDOCS",
  path: "/parent/child/grandchild",
  jiraIssueLinks: [
    { issue_key: "PROJ-123", issue_url: "https://company.atlassian.net/browse/PROJ-123" },
    { issue_key: "PROJ-456", issue_url: "https://company.atlassian.net/browse/PROJ-456" },
  ],
  metadata: {
    title: "Confluence Page Title",
  },
};

const mockUploadResult: ConfluenceSearchResult = {
  id: "chunk-789",
  source_id: "source-789",
  source_type: "file",
  title: "Uploaded Document.pdf",
  content: "Content extracted from an uploaded PDF document.",
  metadata: {
    title: "Uploaded Document.pdf",
  },
};

describe("SearchResultCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Base functionality", () => {
    it("renders web result with title and content", () => {
      render(<SearchResultCard result={mockWebResult} />);

      expect(screen.getByText("Web Page Title")).toBeInTheDocument();
      expect(screen.getByText(/this is the content/i)).toBeInTheDocument();
    });

    it("renders correct source type badge for web", () => {
      render(<SearchResultCard result={mockWebResult} />);

      expect(screen.getByText("web")).toBeInTheDocument();
    });

    it("renders correct source type badge for upload", () => {
      render(<SearchResultCard result={mockUploadResult} />);

      expect(screen.getByText("upload")).toBeInTheDocument();
    });

    it("renders correct source type badge for confluence", () => {
      render(<SearchResultCard result={mockConfluenceResult} />);

      expect(screen.getByText("confluence")).toBeInTheDocument();
    });

    it("truncates long content to 200 characters", () => {
      const longContent = "A".repeat(300);
      const resultWithLongContent: ConfluenceSearchResult = {
        ...mockWebResult,
        content: longContent,
      };

      render(<SearchResultCard result={resultWithLongContent} />);

      // Content should be truncated with ellipsis
      const contentElement = screen.getByText(/A{100,}/);
      expect(contentElement.textContent?.length).toBeLessThan(210); // 200 + "..."
    });

    it("shows section when available", () => {
      render(<SearchResultCard result={mockWebResult} />);

      expect(screen.getByText("Section:")).toBeInTheDocument();
      expect(screen.getByText("Documentation")).toBeInTheDocument();
    });

    it("is clickable when onClick is provided", () => {
      const mockOnClick = vi.fn();
      render(<SearchResultCard result={mockWebResult} onClick={mockOnClick} />);

      const card = screen.getByRole("button");
      fireEvent.click(card);

      expect(mockOnClick).toHaveBeenCalled();
    });

    it("is keyboard accessible when onClick is provided", () => {
      const mockOnClick = vi.fn();
      render(<SearchResultCard result={mockWebResult} onClick={mockOnClick} />);

      const card = screen.getByRole("button");
      fireEvent.keyDown(card, { key: "Enter" });

      expect(mockOnClick).toHaveBeenCalled();
    });

    it("is not a button when onClick is not provided", () => {
      render(<SearchResultCard result={mockWebResult} />);

      expect(screen.queryByRole("button")).not.toBeInTheDocument();
    });
  });

  describe("Confluence-specific features", () => {
    it("shows Confluence space badge", () => {
      render(<SearchResultCard result={mockConfluenceResult} />);

      // Should show space key badge
      const badges = screen.getAllByText("DEVDOCS");
      expect(badges.length).toBeGreaterThan(0);
    });

    it("renders JIRA chips when present", () => {
      render(<SearchResultCard result={mockConfluenceResult} />);

      expect(screen.getByRole("button", { name: /open jira issue proj-123/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /open jira issue proj-456/i })).toBeInTheDocument();
    });

    it("JIRA chips open in new tab when clicked", () => {
      const mockOpen = vi.fn();
      vi.stubGlobal("open", mockOpen);

      render(<SearchResultCard result={mockConfluenceResult} />);

      const jiraChip = screen.getByRole("button", { name: /open jira issue proj-123/i });
      fireEvent.click(jiraChip);

      expect(mockOpen).toHaveBeenCalledWith(
        "https://company.atlassian.net/browse/PROJ-123",
        "_blank",
        "noopener,noreferrer",
      );

      vi.unstubAllGlobals();
    });

    it("shows breadcrumbs when path is present", () => {
      render(<SearchResultCard result={mockConfluenceResult} />);

      // Breadcrumbs should show path segments
      expect(screen.getByLabelText("Page hierarchy")).toBeInTheDocument();
      expect(screen.getByText("parent")).toBeInTheDocument();
      expect(screen.getByText("child")).toBeInTheDocument();
      expect(screen.getByText("grandchild")).toBeInTheDocument();
    });

    it("truncates breadcrumbs when path has more than 5 levels", () => {
      const deepPath: ConfluenceSearchResult = {
        ...mockConfluenceResult,
        path: "/level1/level2/level3/level4/level5/level6/level7",
      };

      render(<SearchResultCard result={deepPath} />);

      // Should show first 2, ellipsis, and last 2
      expect(screen.getByText("level1")).toBeInTheDocument();
      expect(screen.getByText("level2")).toBeInTheDocument();
      expect(screen.getByText("...")).toBeInTheDocument();
      expect(screen.getByText("level6")).toBeInTheDocument();
      expect(screen.getByText("level7")).toBeInTheDocument();
      // Middle levels should not be visible
      expect(screen.queryByText("level4")).not.toBeInTheDocument();
    });

    it("limits displayed JIRA chips to 5", () => {
      const manyJiraLinks: JiraIssueLink[] = Array.from({ length: 8 }, (_, i) => ({
        issue_key: `PROJ-${i + 1}`,
        issue_url: `https://jira.atlassian.com/browse/PROJ-${i + 1}`,
      }));

      const resultWithManyJira: ConfluenceSearchResult = {
        ...mockConfluenceResult,
        jiraIssueLinks: manyJiraLinks,
      };

      render(<SearchResultCard result={resultWithManyJira} />);

      // Should show 5 chips plus "+3 more"
      expect(screen.getByText("+3 more")).toBeInTheDocument();
      expect(screen.getByText("PROJ-1")).toBeInTheDocument();
      expect(screen.getByText("PROJ-5")).toBeInTheDocument();
      expect(screen.queryByText("PROJ-6")).not.toBeInTheDocument();
    });

    it("does not show JIRA section when no links present", () => {
      const noJiraResult: ConfluenceSearchResult = {
        ...mockConfluenceResult,
        jiraIssueLinks: [],
      };

      render(<SearchResultCard result={noJiraResult} />);

      expect(screen.queryByRole("button", { name: /open jira issue/i })).not.toBeInTheDocument();
    });

    it("does not show breadcrumbs when path is empty", () => {
      const noPathResult: ConfluenceSearchResult = {
        ...mockConfluenceResult,
        path: undefined,
      };

      render(<SearchResultCard result={noPathResult} />);

      expect(screen.queryByLabelText("Page hierarchy")).not.toBeInTheDocument();
    });
  });

  describe("Mixed results handling", () => {
    it("does not show Confluence metadata for web results", () => {
      render(<SearchResultCard result={mockWebResult} />);

      expect(screen.queryByLabelText("Page hierarchy")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /open jira issue/i })).not.toBeInTheDocument();
    });

    it("does not show Confluence metadata for upload results", () => {
      render(<SearchResultCard result={mockUploadResult} />);

      expect(screen.queryByLabelText("Page hierarchy")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /open jira issue/i })).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper aria-label for card", () => {
      render(<SearchResultCard result={mockWebResult} />);

      expect(screen.getByLabelText(/search result: web page title/i)).toBeInTheDocument();
    });

    it("JIRA chips have proper aria-labels", () => {
      render(<SearchResultCard result={mockConfluenceResult} />);

      expect(screen.getByRole("button", { name: /open jira issue proj-123 in new tab/i })).toBeInTheDocument();
    });

    it("breadcrumbs navigation has proper aria-label", () => {
      render(<SearchResultCard result={mockConfluenceResult} />);

      expect(screen.getByRole("navigation", { name: /page hierarchy/i })).toBeInTheDocument();
    });
  });
});
