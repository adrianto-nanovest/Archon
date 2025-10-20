"""Unit tests for Simple Elements Handler."""

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.element_handlers.simple_elements import (
    SimpleElementsHandler,
)


@pytest.mark.asyncio
async def test_emoticon_with_fallback():
    """Test emoticon processing with fallback attribute."""
    handler = SimpleElementsHandler()

    html = """
    <p>Hello <ac:emoticon ac:name="smile" ac:emoji-fallback="😊"/> world!</p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup)

    result = str(soup)
    assert "😊" in result
    assert "ac:emoticon" not in result


@pytest.mark.asyncio
async def test_emoticon_without_fallback():
    """Test emoticon processing without fallback (uses shortcode)."""
    handler = SimpleElementsHandler()

    html = """
    <p>Hello <ac:emoticon ac:name="smile"/> world!</p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup)

    result = str(soup)
    assert ":smile:" in result
    assert "ac:emoticon" not in result


@pytest.mark.asyncio
async def test_inline_comment_marker_stripping():
    """Test inline comment marker stripping (keeps inner text)."""
    handler = SimpleElementsHandler()

    html = """
    <p>This is <ac:inline-comment-marker ac:ref="comment-1">important</ac:inline-comment-marker> text.</p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup)

    result = str(soup)
    assert "important" in result  # Inner text kept
    assert "ac:inline-comment-marker" not in result  # Marker removed
    assert "ac:ref" not in result


@pytest.mark.asyncio
async def test_inline_comment_marker_empty():
    """Test inline comment marker with no inner text (removes entirely)."""
    handler = SimpleElementsHandler()

    html = """
    <p>Before<ac:inline-comment-marker ac:ref="comment-1"></ac:inline-comment-marker>After</p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup)

    result = str(soup)
    assert "BeforeAfter" in result or ("Before" in result and "After" in result)
    assert "ac:inline-comment-marker" not in result


@pytest.mark.asyncio
async def test_time_element_text_extraction():
    """Test time element text extraction (human-readable format)."""
    handler = SimpleElementsHandler()

    html = """
    <p>Last updated: <time datetime="2025-10-20T10:30:00Z">October 20, 2025</time></p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup)

    result = str(soup)
    assert "October 20, 2025" in result  # Human-readable text used
    assert "time" not in result  # <time> tag removed
    # ISO datetime should NOT be in result (we use text content)
    assert "2025-10-20T10:30:00Z" not in result


@pytest.mark.asyncio
async def test_time_element_fallback_to_datetime():
    """Test time element fallback to datetime attribute when no text."""
    handler = SimpleElementsHandler()

    html = """
    <p>Last updated: <time datetime="2025-10-20T10:30:00Z"></time></p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup)

    result = str(soup)
    # When no text content, fallback to datetime attribute
    assert "2025-10-20T10:30:00Z" in result


@pytest.mark.asyncio
async def test_all_simple_elements_together():
    """Test processing all simple elements together."""
    handler = SimpleElementsHandler()

    html = """
    <p>
        This is a test <ac:emoticon ac:name="smile" ac:emoji-fallback="😊"/>.
        Some <ac:inline-comment-marker ac:ref="c1">commented text</ac:inline-comment-marker> here.
        Updated on <time datetime="2025-10-20">Oct 20, 2025</time>.
    </p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup)

    result = str(soup)

    # Verify all elements processed correctly
    assert "😊" in result
    assert "commented text" in result
    assert "Oct 20, 2025" in result

    # Verify no special element tags remain
    assert "ac:emoticon" not in result
    assert "ac:inline-comment-marker" not in result
    assert "<time" not in result
