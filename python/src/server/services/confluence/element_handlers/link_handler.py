"""Link Handler for Confluence Storage Format HTML elements.

Processes internal page links and external links with bulk API optimization.
Implements three-phase processing to avoid N+1 query anti-pattern.
"""

import re
from typing import Any

# BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
# but it's available at runtime via bs4/__init__.py import from bs4.element.
# See: https://github.com/python/typeshed/issues/4968
from bs4 import BeautifulSoup, NavigableString  # type: ignore[attr-defined]

from .base import BaseElementHandler


class LinkHandler(BaseElementHandler):
    """
    Handler for Confluence links (page links and external links).

    Implements three-phase bulk processing:
    - Phase 1: Collect all unique page titles
    - Phase 2: Bulk API call for page resolution (single call)
    - Phase 3: Process internal page links
    - Phase 4: Process external links

    Features:
    - Bulk page title resolution (single API call for N pages)
    - JIRA link deduplication (Tier 2 extraction)
    - Google Drive icon detection (Docs, Sheets, Slides)
    - Graceful fallback to placeholders when API unavailable
    """

    def __init__(
        self,
        confluence_client: object | None = None,
        internal_links_tracker: list | None = None,
        external_links_tracker: list | None = None,
        jira_links_tracker: list | None = None,
    ) -> None:
        """
        Initialize Link Handler.

        Args:
            confluence_client: Optional ConfluenceClient for bulk page resolution
            internal_links_tracker: Shared list for internal page links
            external_links_tracker: Shared list for external links
            jira_links_tracker: Shared list for JIRA link deduplication (Tier 2)
        """
        super().__init__()
        self.confluence_client = confluence_client
        self.internal_links_tracker = (
            internal_links_tracker if internal_links_tracker is not None else []
        )
        self.external_links_tracker = (
            external_links_tracker if external_links_tracker is not None else []
        )
        self.jira_links_tracker = (
            jira_links_tracker if jira_links_tracker is not None else []
        )

    def _is_jira_duplicate(self, issue_key: str) -> bool:
        """Check if JIRA issue already in tracker (from Tier 1 macro handler)."""
        return any(link.get("issue_key") == issue_key for link in self.jira_links_tracker)

    async def process(self, soup: BeautifulSoup, space_id: str | None = None, **kwargs: Any) -> None:
        """
        Process all links in the document using bulk API optimization.

        Implements three-phase processing:
        1. Collect unique page titles
        2. Bulk resolve titles to page IDs/URLs (single API call)
        3. Replace link elements with markdown

        Args:
            soup: BeautifulSoup object (modified in-place)
            space_id: Confluence space ID (for page resolution)
            **kwargs: Additional arguments (confluence_client override)
        """
        # Allow confluence_client override from kwargs
        confluence_client = kwargs.get("confluence_client", self.confluence_client)

        # Phase 1: Collect all unique page titles from internal links
        page_links = soup.find_all("ac:link")
        page_titles = set()

        for link in page_links:
            ri_page = link.find("ri:page")
            if ri_page:
                title = ri_page.get("ri:content-title")
                if title:
                    page_titles.add(title)

        # Phase 2: Bulk API call for page resolution
        page_mapping = {}
        if confluence_client and space_id and page_titles:
            try:
                page_mapping = await confluence_client.find_pages_by_titles(
                    space_id, list(page_titles)
                )
                self.logger.debug(
                    f"Bulk resolved {len(page_titles)} page titles (found: {sum(1 for v in page_mapping.values() if v['page_id'])})"
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to resolve page titles in bulk: {e}. Using placeholders."
                )
                # Create placeholder mapping
                page_mapping = {
                    title: {"page_id": None, "url": None} for title in page_titles
                }
        else:
            # No client or space_id - create placeholder mapping
            page_mapping = {title: {"page_id": None, "url": None} for title in page_titles}

        # Phase 3: Process internal page links
        for link in page_links:
            ri_page = link.find("ri:page")
            if ri_page:
                title = ri_page.get("ri:content-title", "Unknown Page")
                link_text = link.get_text(strip=True) or title

                # Look up page info from bulk API result
                page_info = page_mapping.get(title, {"page_id": None, "url": None})
                page_id = page_info.get("page_id")
                actual_url = page_info.get("url")

                # Use placeholder in markdown if URL not found
                markdown_url = actual_url or f"PLACEHOLDER_{title.replace(' ', '_')}"

                # Add to internal links tracker (store actual URL, not placeholder)
                self.internal_links_tracker.append(
                    {"page_id": page_id, "title": title, "url": actual_url}
                )

                # Replace with markdown link
                markdown_link = f"[{link_text}]({markdown_url})"
                link.replace_with(NavigableString(markdown_link))

        # Phase 4: Process external links
        external_links = soup.find_all("a", href=True)

        for link in external_links:
            href = link.get("href", "")

            # Filter for http/https URLs only
            if not href.startswith(("http://", "https://")):
                continue

            link_text = link.get_text(strip=True) or href

            # Check for JIRA links (Tier 2 extraction with deduplication)
            jira_pattern = r"https?://[^/]+/browse/([A-Z]+-\d+)"
            jira_match = re.search(jira_pattern, href)
            if jira_match:
                issue_key = jira_match.group(1)
                # Only add if not already tracked by Tier 1 (macro handler)
                if not self._is_jira_duplicate(issue_key):
                    self.jira_links_tracker.append({"issue_key": issue_key, "url": href})
                    self.logger.debug(f"Tier 2 JIRA extraction: {issue_key} from URL")

            # Detect Google Drive links and add icons
            icon = ""
            if "docs.google.com/document" in href:
                icon = "📝 "  # Google Docs
            elif "docs.google.com/spreadsheets" in href:
                icon = "📊 "  # Google Sheets
            elif "docs.google.com/presentation" in href:
                icon = "📊 "  # Google Slides

            # Add to external links tracker
            self.external_links_tracker.append({"title": link_text, "url": href})

            # Replace with markdown link (with icon if applicable)
            markdown_link = f"[{icon}{link_text}]({href})"
            link.replace_with(NavigableString(markdown_link))

        self.logger.debug(
            f"Processed {len(page_links)} internal links and {len(external_links)} external links"
        )
