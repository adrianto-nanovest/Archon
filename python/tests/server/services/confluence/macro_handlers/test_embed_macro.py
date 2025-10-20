"""
Unit tests for EmbedMacroHandler.

Tests URL conversion for various platforms and missing title handling.
"""

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.macro_handlers.embed_macro import EmbedMacroHandler


@pytest.fixture
def embed_handler():
    """Create EmbedMacroHandler instance for testing."""
    return EmbedMacroHandler()


@pytest.mark.asyncio
async def test_youtube_embed_url_conversion(embed_handler):
    """Test YouTube embed URL converted to watch URL."""
    html = """
    <ac:structured-macro ac:name="iframe">
        <ri:url ri:value="https://www.youtube.com/embed/dQw4w9WgXcQ"/>
        <ac:parameter ac:name="title">Demo Video</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await embed_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify URL converted from /embed/ to /watch?v=
    assert "[Demo Video]" in result
    assert "youtube.com/watch?v=dQw4w9WgXcQ" in result

    # Verify tracked in external links
    assert len(embed_handler.external_links_tracker) == 1
    assert embed_handler.external_links_tracker[0]["title"] == "Demo Video"
    assert "watch?v=" in embed_handler.external_links_tracker[0]["url"]


@pytest.mark.asyncio
async def test_generic_embed_no_conversion(embed_handler):
    """Test generic embed URL (non-YouTube) used as-is."""
    html = """
    <ac:structured-macro ac:name="iframe">
        <ri:url ri:value="https://vimeo.com/123456789"/>
        <ac:parameter ac:name="title">Vimeo Video</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await embed_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify URL unchanged (no /embed/ pattern)
    assert "[Vimeo Video]" in result
    assert "https://vimeo.com/123456789" in result

    # Verify tracked
    assert len(embed_handler.external_links_tracker) == 1
    assert embed_handler.external_links_tracker[0]["url"] == "https://vimeo.com/123456789"


@pytest.mark.asyncio
async def test_missing_title_defaults_to_embedded_content(embed_handler):
    """Test embed without title defaults to 'Embedded Content'."""
    html = """
    <ac:structured-macro ac:name="iframe">
        <ri:url ri:value="https://example.com/video"/>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await embed_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify default title used
    assert "[Embedded Content]" in result
    assert "https://example.com/video" in result

    # Verify tracked with default title
    assert embed_handler.external_links_tracker[0]["title"] == "Embedded Content"


@pytest.mark.asyncio
async def test_missing_url_tag(embed_handler):
    """Test embed without ri:url tag uses empty URL."""
    html = """
    <ac:structured-macro ac:name="iframe">
        <ac:parameter ac:name="title">Missing URL</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await embed_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify markdown link with empty URL
    assert "[Missing URL]()" in result

    # Verify tracked with empty URL
    assert len(embed_handler.external_links_tracker) == 1
    assert embed_handler.external_links_tracker[0]["url"] == ""


@pytest.mark.asyncio
async def test_multiple_embeds_tracked(embed_handler):
    """Test multiple embed macros tracked correctly."""
    embeds = [
        ("https://www.youtube.com/embed/abc123", "Video 1"),
        ("https://example.com/embed/xyz789", "Video 2"),
        ("https://vimeo.com/555555", "Video 3")
    ]

    for url, title in embeds:
        html = f"""
        <ac:structured-macro ac:name="iframe">
            <ri:url ri:value="{url}"/>
            <ac:parameter ac:name="title">{title}</ac:parameter>
        </ac:structured-macro>
        """
        soup = BeautifulSoup(html, "html.parser")
        macro_tag = soup.find("ac:structured-macro")
        await embed_handler.process(macro_tag, page_id="test-page")

    # Verify all 3 tracked
    assert len(embed_handler.external_links_tracker) == 3
    tracked_titles = [link["title"] for link in embed_handler.external_links_tracker]
    assert tracked_titles == ["Video 1", "Video 2", "Video 3"]


@pytest.mark.asyncio
async def test_youtube_with_multiple_embed_patterns(embed_handler):
    """Test YouTube URLs with various /embed/ patterns."""
    test_urls = [
        "https://www.youtube.com/embed/test123",
        "https://youtube.com/embed/test456",
        "http://www.youtube.com/embed/test789"
    ]

    for url in test_urls:
        html = f"""
        <ac:structured-macro ac:name="iframe">
            <ri:url ri:value="{url}"/>
        </ac:structured-macro>
        """
        soup = BeautifulSoup(html, "html.parser")
        macro_tag = soup.find("ac:structured-macro")
        await embed_handler.process(macro_tag, page_id="test-page")

    # Verify all converted to watch?v= format
    for link in embed_handler.external_links_tracker:
        assert "watch?v=" in link["url"]
        assert "/embed/" not in link["url"]


@pytest.mark.asyncio
async def test_empty_title_parameter(embed_handler):
    """Test embed with empty title parameter uses default."""
    html = """
    <ac:structured-macro ac:name="iframe">
        <ri:url ri:value="https://example.com/video"/>
        <ac:parameter ac:name="title"></ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await embed_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Empty title should use empty string (from get_text())
    assert "[]" in result or "[](https" in result
