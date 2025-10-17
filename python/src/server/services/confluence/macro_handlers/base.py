"""
Base class for Confluence macro handlers with error isolation.

This module provides the abstract base class that all macro handlers must extend.
The orchestrator wraps all handler calls in try-except blocks for graceful degradation.
"""

import logging
from abc import ABC, abstractmethod

from bs4 import Tag


class BaseMacroHandler(ABC):
    """
    Base class for Confluence macro handlers with error isolation.

    Subclasses implement specific macro processing logic (code, panel, JIRA, etc.).
    The ConfluenceProcessor orchestrator wraps all handler calls in try-except blocks
    for graceful degradation, ensuring that a failure in one handler doesn't crash
    the entire conversion process.

    Example usage:
        ```python
        from .base import BaseMacroHandler

        class CodeMacroHandler(BaseMacroHandler):
            async def process(self, macro_tag, page_id, space_id=None):
                # Extract language parameter
                language = macro_tag.find('ac:parameter', {'ac:name': 'language'})
                language_value = language.get_text() if language else ''

                # Extract code content from CDATA
                code_body = macro_tag.find('ac:plain-text-body')
                code_content = code_body.get_text(strip=False) if code_body else ''

                # Replace macro with markdown code block
                from bs4 import NavigableString
                markdown_code = f"```{language_value}\\n{code_content}\\n```"
                macro_tag.replace_with(NavigableString(markdown_code))
        ```

    Logging:
        Handlers can use self.logger to log macro-specific events. The orchestrator
        provides comprehensive error logging with page_id context when handlers fail.
    """

    def __init__(self):
        """Initialize the handler with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def process(self, macro_tag: Tag, page_id: str, space_id: str = None) -> None:
        """
        Process a single Confluence macro tag.

        This method must be implemented by all subclasses. It should modify the
        macro_tag in-place using BeautifulSoup operations (e.g., replace_with,
        decompose, insert_after, etc.).

        Args:
            macro_tag: BeautifulSoup Tag object representing <ac:structured-macro>
            page_id: Confluence page ID for logging context
            space_id: Confluence space ID (optional, for API calls to resolve links)

        Returns:
            None (modifies macro_tag in-place via BeautifulSoup)

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement process() method"
        )
