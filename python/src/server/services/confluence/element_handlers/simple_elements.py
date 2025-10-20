"""Simple Elements Handler for Confluence Storage Format HTML elements.

Processes emoticons, inline comments, and time elements with simplified logic.
"""

from typing import Any

# BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
# but it's available at runtime via bs4/__init__.py import from bs4.element.
# See: https://github.com/python/typeshed/issues/4968
from bs4 import BeautifulSoup, NavigableString  # type: ignore[attr-defined]

from .base import BaseElementHandler


class SimpleElementsHandler(BaseElementHandler):
    """
    Handler for simple Confluence elements.

    Processes:
    - Emoticons: Use fallback emoji attribute only (skip complex shortname processing)
    - Inline comments: Strip entirely (collaborative metadata, not content)
    - Time elements: Use text content only (skip ISO datetime parsing)

    This handler uses simplified logic (60% fewer lines vs full implementation)
    to focus on high-value RAG content extraction.
    """

    async def process(self, soup: BeautifulSoup, **kwargs: Any) -> None:
        """
        Process simple HTML elements in the document.

        Args:
            soup: BeautifulSoup object (modified in-place)
            **kwargs: Additional arguments (unused)
        """
        # Process emoticons
        self._process_emoticons(soup)

        # Process inline comments
        self._process_inline_comments(soup)

        # Process time elements
        self._process_time_elements(soup)

        self.logger.debug("Processed simple elements (emoticons, inline comments, time)")

    def _process_emoticons(self, soup: BeautifulSoup) -> None:
        """
        Process emoticon elements.

        Uses fallback emoji attribute for simple conversion.
        Skips complex shortname processing (low RAG value).

        Args:
            soup: BeautifulSoup object (modified in-place)
        """
        emoticon_elements = soup.find_all("ac:emoticon")

        for emoticon_elem in emoticon_elements:
            try:
                # Try to get fallback emoji first (preferred)
                fallback = emoticon_elem.get("ac:emoji-fallback")

                if fallback:
                    # Use Unicode emoji fallback
                    emoticon_elem.replace_with(NavigableString(fallback))
                else:
                    # Use shortcode as fallback (e.g., :smile:)
                    shortname = emoticon_elem.get("ac:name", "emoji")
                    emoticon_elem.replace_with(NavigableString(f":{shortname}:"))

            except Exception as e:
                self.logger.warning(f"Error processing emoticon: {e}")
                # Graceful fallback - remove element
                emoticon_elem.decompose()

        self.logger.debug(f"Processed {len(emoticon_elements)} emoticons")

    def _process_inline_comments(self, soup: BeautifulSoup) -> None:
        """
        Process inline comment markers.

        Strips markers entirely (collaborative metadata, not document content).
        Keeps inner text content if any.

        Args:
            soup: BeautifulSoup object (modified in-place)
        """
        comment_markers = soup.find_all("ac:inline-comment-marker")

        for marker in comment_markers:
            try:
                # Extract inner text if any
                inner_text = marker.get_text(strip=True)

                if inner_text:
                    # Keep the text content, remove the marker wrapper
                    marker.replace_with(NavigableString(inner_text))
                else:
                    # No text content - remove entirely
                    marker.decompose()

            except Exception as e:
                self.logger.warning(f"Error processing inline comment marker: {e}")
                # Graceful fallback - remove element
                marker.decompose()

        self.logger.debug(f"Processed {len(comment_markers)} inline comment markers")

    def _process_time_elements(self, soup: BeautifulSoup) -> None:
        """
        Process time elements.

        Uses text content only (human-readable format).
        Skips ISO datetime parsing (minimal RAG value).

        Args:
            soup: BeautifulSoup object (modified in-place)
        """
        time_elements = soup.find_all("time")

        for time_elem in time_elements:
            try:
                # Extract text content (human-readable date/time)
                text_content = time_elem.get_text(strip=True)

                if text_content:
                    # Use human-readable text
                    time_elem.replace_with(NavigableString(text_content))
                else:
                    # Fallback to datetime attribute if no text
                    datetime_value = time_elem.get("datetime", "")
                    if datetime_value:
                        time_elem.replace_with(NavigableString(datetime_value))
                    else:
                        # No content - remove element
                        time_elem.decompose()

            except Exception as e:
                self.logger.warning(f"Error processing time element: {e}")
                # Graceful fallback - remove element
                time_elem.decompose()

        self.logger.debug(f"Processed {len(time_elements)} time elements")
