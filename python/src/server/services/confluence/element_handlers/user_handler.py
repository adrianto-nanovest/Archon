"""User Handler for Confluence Storage Format HTML elements.

Processes user mentions with bulk API optimization.
Implements three-phase processing to avoid N+1 query anti-pattern.
"""

from typing import Any

# BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
# but it's available at runtime via bs4/__init__.py import from bs4.element.
# See: https://github.com/python/typeshed/issues/4968
from bs4 import BeautifulSoup, NavigableString  # type: ignore[attr-defined]

from .base import BaseElementHandler


class UserHandler(BaseElementHandler):
    """
    Handler for Confluence user mentions (<ri:user>).

    Implements three-phase bulk processing:
    - Phase 1: Collect all unique account IDs
    - Phase 2: Bulk API call for user resolution (single call)
    - Phase 3: Process user mention elements

    Features:
    - Bulk user account ID resolution (single API call for N users)
    - Deduplication of user mentions
    - Graceful fallback to account ID when API unavailable
    """

    def __init__(self, confluence_client: object | None = None, user_mentions_tracker: list | None = None) -> None:
        """
        Initialize User Handler.

        Args:
            confluence_client: Optional ConfluenceClient for bulk user resolution
            user_mentions_tracker: Shared list for user mention metadata
        """
        super().__init__()
        self.confluence_client = confluence_client
        self.user_mentions_tracker = (
            user_mentions_tracker if user_mentions_tracker is not None else []
        )

    def _is_duplicate(self, account_id: str) -> bool:
        """Check if account ID already in tracker (deduplication helper)."""
        return any(
            user.get("account_id") == account_id for user in self.user_mentions_tracker
        )

    async def process(self, soup: BeautifulSoup, space_id: str | None = None, **kwargs: Any) -> None:
        """
        Process all user mentions in the document using bulk API optimization.

        Implements three-phase processing:
        1. Collect unique account IDs
        2. Bulk resolve account IDs to user info (single API call)
        3. Replace user mention elements with markdown

        Args:
            soup: BeautifulSoup object (modified in-place)
            space_id: Confluence space ID (unused for user mentions)
            **kwargs: Additional arguments (confluence_client override)
        """
        # Allow confluence_client override from kwargs
        confluence_client = kwargs.get("confluence_client", self.confluence_client)

        # Phase 1: Collect all unique account IDs from user mentions
        user_elements = soup.find_all("ri:user")
        account_ids = set()

        for user_elem in user_elements:
            account_id = user_elem.get("ri:account-id")
            if account_id:
                account_ids.add(account_id)

        if not account_ids:
            self.logger.debug("No user mentions found")
            return

        # Phase 2: Bulk API call for user resolution
        user_mapping = {}
        if confluence_client and account_ids:
            try:
                user_mapping = await confluence_client.get_users_by_account_ids(
                    list(account_ids)
                )
                self.logger.debug(
                    f"Bulk resolved {len(account_ids)} account IDs (found: {sum(1 for v in user_mapping.values() if v['display_name'])})"
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to resolve user account IDs in bulk: {e}. Using account IDs as fallback."
                )
                # Create placeholder mapping
                user_mapping = {
                    account_id: {
                        "display_name": account_id,
                        "email": None,
                        "profile_url": None,
                    }
                    for account_id in account_ids
                }
        else:
            # No client - create placeholder mapping with account IDs
            user_mapping = {
                account_id: {
                    "display_name": account_id,
                    "email": None,
                    "profile_url": None,
                }
                for account_id in account_ids
            }

        # Phase 3: Process user mention elements
        for user_elem in user_elements:
            account_id = user_elem.get("ri:account-id", "unknown")

            # Look up user info from bulk API result
            user_info = user_mapping.get(
                account_id,
                {"display_name": account_id, "email": None, "profile_url": None},
            )
            display_name = user_info.get("display_name") or account_id

            # Add to user mentions tracker (skip duplicates)
            if not self._is_duplicate(account_id):
                self.user_mentions_tracker.append(
                    {
                        "account_id": account_id,
                        "display_name": display_name,
                        "profile_url": user_info.get("profile_url"),
                    }
                )

            # Replace with markdown mention
            markdown_mention = f"@{display_name}"
            user_elem.replace_with(NavigableString(markdown_mention))

        self.logger.debug(
            f"Processed {len(user_elements)} user mentions ({len(self.user_mentions_tracker)} unique users)"
        )
