"""
HTML Utilities for Confluence Content Processing.

Provides BeautifulSoup helper functions, whitespace normalization,
and UTF-8 encoding safety for emoji and special characters.

Story 2.5: Utility Modules & Integration Testing
"""

import logging
import re

from bs4 import Tag

logger = logging.getLogger(__name__)


def normalize_whitespace(text: str, preserve_code: bool = False) -> str:
    """
    Normalize whitespace in text content.

    Collapses multiple spaces/newlines into single space and strips
    leading/trailing whitespace. Preserves whitespace in code blocks.

    Args:
        text: Input text with potentially excessive whitespace
        preserve_code: If True, skip normalization (for code blocks)

    Returns:
        Text with normalized whitespace

    Examples:
        >>> normalize_whitespace("Hello    World\\n\\n  Foo")
        "Hello World Foo"
        >>> normalize_whitespace("  def foo():\\n    pass  ", preserve_code=True)
        "  def foo():\\n    pass  "
    """
    if preserve_code:
        return text  # Don't modify code block whitespace

    # Collapse multiple spaces/newlines into single space
    normalized = re.sub(r"\s+", " ", text)

    # Strip leading/trailing whitespace
    return normalized.strip()


def clean_heading_text(text: str) -> str:
    """
    Clean heading text by removing inline formatting.

    Removes <strong>, <em>, <code> tags while preserving text content.
    Normalizes whitespace and strips special characters except hyphens.

    Args:
        text: Heading text potentially containing inline formatting

    Returns:
        Cleaned heading text suitable for markdown headers

    Examples:
        >>> clean_heading_text("<strong>Section 1:</strong> Introduction")
        "Section 1: Introduction"
        >>> clean_heading_text("  API Reference  ")
        "API Reference"
    """
    # Remove common inline formatting tags (preserve text content)
    cleaned = re.sub(r"</?(?:strong|em|code|b|i)>", "", text)

    # Normalize whitespace
    cleaned = normalize_whitespace(cleaned)

    # Strip special characters except hyphens, alphanumeric, spaces, colons
    cleaned = re.sub(r"[^\w\s\-:]", "", cleaned)

    return cleaned.strip()


def clean_table_cell_text(cell: Tag) -> str:
    """
    Extract text from table cell preserving structure.

    Handles nested lists and code blocks while normalizing whitespace.
    Preserves meaningful whitespace in code but collapses elsewhere.

    Args:
        cell: BeautifulSoup Tag representing table cell (td or th)

    Returns:
        Cleaned cell text with structure preserved

    Examples:
        >>> from bs4 import BeautifulSoup
        >>> html = "<td>Value 1</td>"
        >>> cell = BeautifulSoup(html, "html.parser").find("td")
        >>> clean_table_cell_text(cell)
        "Value 1"
    """
    # Check if cell contains code block
    code_block = cell.find("code") or cell.find("pre")
    if code_block:
        # Preserve whitespace in code
        return code_block.get_text(strip=False)

    # Check if cell contains list
    list_element = cell.find("ul") or cell.find("ol")
    if list_element:
        # Extract list items with markers
        items = list_element.find_all("li")
        list_text = "\n".join(f"- {item.get_text(strip=True)}" for item in items)
        return list_text

    # Regular cell - normalize whitespace
    cell_text = cell.get_text(separator=" ", strip=True)
    return normalize_whitespace(cell_text)


def ensure_utf8_safe(text: str) -> str:
    """
    Ensure text is UTF-8 safe for emoji and special characters.

    Attempts to encode/decode text to catch problematic characters.
    Replaces non-UTF8 characters with Unicode replacement character.

    Args:
        text: Input text potentially containing problematic characters

    Returns:
        UTF-8 safe text with problematic characters replaced

    Examples:
        >>> ensure_utf8_safe("Hello 👋 World")
        "Hello 👋 World"
        >>> ensure_utf8_safe("Test\\udcfe")  # Invalid surrogate
        "Test�"
    """
    try:
        # Attempt encode/decode round-trip
        return text.encode("utf-8", errors="replace").decode("utf-8")
    except Exception as e:
        logger.warning(f"UTF-8 encoding issue: {e}")
        # Fallback: replace all non-ASCII with replacement character
        return text.encode("ascii", errors="replace").decode("ascii")


def extract_text_content(tag: Tag, preserve_structure: bool = False) -> str:
    """
    Extract text content from BeautifulSoup tag.

    Utility function for consistent text extraction across handlers.

    Args:
        tag: BeautifulSoup Tag to extract text from
        preserve_structure: If True, preserve newlines and structure

    Returns:
        Extracted text content

    Examples:
        >>> from bs4 import BeautifulSoup
        >>> html = "<p>Line 1<br/>Line 2</p>"
        >>> tag = BeautifulSoup(html, "html.parser").find("p")
        >>> extract_text_content(tag, preserve_structure=True)
        "Line 1\\nLine 2"
    """
    if preserve_structure:
        # Use get_text with separator to preserve structure
        return tag.get_text(separator="\n", strip=False)
    else:
        # Normalize whitespace for regular content
        text = tag.get_text(separator=" ", strip=True)
        return normalize_whitespace(text)
