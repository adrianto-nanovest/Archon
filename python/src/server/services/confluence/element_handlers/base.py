"""
Base class for special HTML element handlers with graceful degradation.

This module provides the abstract base class that all element handlers must extend.
Element handlers process non-macro elements (users, links, images, emoticons, etc.)
and implement graceful degradation to ensure processing continues on failures.
"""

import logging
from abc import ABC, abstractmethod

from bs4 import BeautifulSoup


class BaseElementHandler(ABC):
    """
    Base class for special HTML element handlers with graceful degradation.

    Handlers process non-macro elements (users, links, images, emoticons, etc.)
    after macro expansion has been completed. The ConfluenceProcessor orchestrator
    wraps all handler calls in try-except blocks for graceful degradation.

    Element handlers operate on the entire BeautifulSoup document and can find/replace
    multiple elements in a single pass. This is more efficient than processing elements
    one-by-one, especially when bulk API calls are needed (e.g., resolving user mentions).

    Example usage:
        ```python
        from .base import BaseElementHandler

        class UserHandler(BaseElementHandler):
            def process(self, soup, **kwargs):
                try:
                    # Extract user account IDs
                    user_links = soup.find_all('ri:user')
                    if not user_links:
                        return

                    # Bulk API call to resolve users (if confluence_client available)
                    account_ids = [link.get('ri:account-id') for link in user_links]
                    # user_data = confluence_client.get_users_bulk(account_ids)

                    # Replace user tags with mentions
                    for user_link in user_links:
                        account_id = user_link.get('ri:account-id', 'unknown')
                        # username = user_data.get(account_id, {}).get('displayName', account_id)
                        from bs4 import NavigableString
                        user_link.replace_with(NavigableString(f"@{account_id}"))

                except Exception as e:
                    self.logger.warning(f"Failed to resolve user mentions: {e}")
                    # Graceful degradation: replace with placeholder
                    for user_link in soup.find_all('ri:user'):
                        account_id = user_link.get('ri:account-id', 'unknown')
                        from bs4 import NavigableString
                        user_link.replace_with(NavigableString(f"[@user:{account_id}]"))
        ```

    Logging:
        Handlers can use self.logger to log element-specific events. The orchestrator
        provides comprehensive error logging when handlers fail, but handlers should
        implement internal try-except for graceful degradation with placeholder content.
    """

    def __init__(self):
        """Initialize the handler with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def process(self, soup: BeautifulSoup, **kwargs) -> None:
        """
        Process special HTML elements in the document.

        This method must be implemented by all subclasses. It should modify the
        soup object in-place using BeautifulSoup operations to replace special
        elements with Markdown-compatible content.

        Args:
            soup: BeautifulSoup object containing parsed HTML document
            **kwargs: Handler-specific arguments (e.g., space_id for link resolution,
                     confluence_client for bulk API calls)

        Returns:
            None (modifies soup in-place)

        Raises:
            NotImplementedError: If subclass doesn't implement this method

        Note:
            Handlers should implement internal error handling for graceful degradation.
            On failure, replace elements with placeholder content rather than raising.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement process() method"
        )
