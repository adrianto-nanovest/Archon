"""
JIRA Macro Handler for Confluence Storage Format.

Implements 3-tier JIRA issue extraction strategy for maximum coverage (~100%).
"""

# BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
# but it's available at runtime via bs4/__init__.py import from bs4.element.
# See: https://github.com/python/typeshed/issues/4968
from bs4 import NavigableString  # type: ignore[attr-defined]

from .base import BaseMacroHandler


class JiraMacroHandler(BaseMacroHandler):
    """
    Handler for Confluence JIRA macros.

    Implements Tier 1 extraction (macro parameters) only. Tier 2 (URL patterns)
    and Tier 3 (plain text regex) are implemented in Story 2.3 and 2.4.
    """

    def __init__(self, jira_client: object | None = None, jira_links_tracker: list | None = None) -> None:
        """
        Initialize JIRA macro handler.

        Args:
            jira_client: Optional JIRA client for JQL query execution
            jira_links_tracker: Shared list for deduplication across tiers
        """
        super().__init__()
        self.jira_client = jira_client
        self.jira_links_tracker = jira_links_tracker if jira_links_tracker is not None else []

    def _is_duplicate(self, issue_key: str) -> bool:
        """Check if issue key already tracked."""
        return any(
            link.get("issue_key") == issue_key for link in self.jira_links_tracker
        )

    async def process(self, macro_tag, page_id: str, space_id: str | None = None) -> None:
        """
        Process JIRA macro (Tier 1: Parameter extraction).

        Args:
            macro_tag: BeautifulSoup Tag for <ac:structured-macro ac:name="jira">
            page_id: Confluence page ID (for logging context)
            space_id: Confluence space ID (unused)

        Modifies:
            Replaces macro with markdown link or JQL table placeholder
        """
        try:
            # Extract key parameter (single issue)
            key_param = macro_tag.find("ac:parameter", {"ac:name": "key"})

            if key_param:
                issue_key = key_param.get_text().strip()

                # Add to tracker if not duplicate
                if not self._is_duplicate(issue_key):
                    self.jira_links_tracker.append({
                        "issue_key": issue_key,
                        "url": f"https://jira.example.com/browse/{issue_key}",  # Placeholder
                    })

                # Replace with markdown link
                markdown_link = f"[{issue_key}](JIRA_PLACEHOLDER_{issue_key})"
                macro_tag.replace_with(NavigableString(markdown_link))

                self.logger.debug(
                    f"Processed JIRA macro on page {page_id}: {issue_key}"
                )
                return

            # Check for JQL query parameter
            jql_param = macro_tag.find("ac:parameter", {"ac:name": "jqlQuery"})

            if jql_param:
                jql_query = jql_param.get_text().strip()

                if self.jira_client:
                    # Execute JQL and build table (placeholder for now)
                    markdown = f"<!-- JIRA Table: JQL Query: {jql_query} -->"
                    self.logger.debug(
                        f"JQL query on page {page_id} (execution not implemented)"
                    )
                else:
                    # No JIRA client - placeholder comment
                    markdown = f"<!-- JIRA Table (JQL): {jql_query} -->"

                macro_tag.replace_with(NavigableString(markdown))
                return

            # No recognized parameters
            self.logger.debug(
                f"JIRA macro on page {page_id} has no key or jqlQuery parameter"
            )
            macro_tag.replace_with(NavigableString("<!-- JIRA Macro (no parameters) -->"))

        except Exception as e:
            self.logger.error(
                f"Error processing JIRA macro on page {page_id}: {e}", exc_info=True
            )
            macro_tag.replace_with(NavigableString("<!-- JIRA macro processing failed -->"))
