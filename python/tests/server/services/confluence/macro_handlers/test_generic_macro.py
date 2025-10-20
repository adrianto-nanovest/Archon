"""
Unit tests for GenericMacroHandler.

Tests handling of unknown macros with parameters, rich text body, and no content.
"""

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.macro_handlers.generic_macro import GenericMacroHandler


@pytest.fixture
def generic_handler():
    """Create GenericMacroHandler instance for testing."""
    return GenericMacroHandler()


@pytest.mark.asyncio
async def test_unknown_macro_with_parameters(generic_handler):
    """Test unknown macro with parameters extracted."""
    html = """
    <ac:structured-macro ac:name="custom-widget">
        <ac:parameter ac:name="width">300</ac:parameter>
        <ac:parameter ac:name="height">200</ac:parameter>
        <ac:parameter ac:name="color">blue</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify comment placeholder with macro name (HTML-escaped by BeautifulSoup)
    assert "Unsupported Confluence Macro: custom-widget" in result

    # Verify parameters extracted
    assert 'width="300"' in result
    assert 'height="200"' in result
    assert 'color="blue"' in result


@pytest.mark.asyncio
async def test_unknown_macro_with_rich_text_body(generic_handler):
    """Test unknown macro with rich text body converted to markdown."""
    html = """
    <ac:structured-macro ac:name="fancy-note">
        <ac:parameter ac:name="style">warning</ac:parameter>
        <ac:rich-text-body>
            <p>This is a <strong>fancy note</strong> with <em>formatted</em> content.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </ac:rich-text-body>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify comment header (HTML-escaped by BeautifulSoup)
    assert "Unsupported Confluence Macro: fancy-note" in result

    # Verify content section header
    assert "**fancy-note Macro Content:**" in result

    # Verify markdown conversion (markdownify converts rich text)
    assert "fancy note" in result  # Bold text preserved
    assert "formatted" in result  # Italic text preserved


@pytest.mark.asyncio
async def test_unknown_macro_with_no_content(generic_handler):
    """Test unknown macro with no parameters or content."""
    html = """
    <ac:structured-macro ac:name="empty-widget">
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify simple comment placeholder (no content section, HTML-escaped by BeautifulSoup)
    assert "Unsupported Confluence Macro: empty-widget" in result
    assert "Macro Content:" not in result


@pytest.mark.asyncio
async def test_macro_name_fallback_to_unknown(generic_handler):
    """Test macro without ac:name attribute defaults to 'unknown'."""
    html = """
    <ac:structured-macro>
        <ac:parameter ac:name="test">value</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify defaults to 'unknown' (HTML-escaped by BeautifulSoup)
    assert "Unsupported Confluence Macro: unknown" in result


@pytest.mark.asyncio
async def test_parameters_without_ac_name_ignored(generic_handler):
    """Test parameters without ac:name attribute are ignored."""
    html = """
    <ac:structured-macro ac:name="test-macro">
        <ac:parameter ac:name="valid">included</ac:parameter>
        <ac:parameter>ignored</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify only valid parameter included
    assert 'valid="included"' in result
    assert "ignored" not in result


@pytest.mark.asyncio
async def test_nested_html_in_rich_text_body(generic_handler):
    """Test rich text body with nested HTML elements."""
    html = """
    <ac:structured-macro ac:name="complex-note">
        <ac:rich-text-body>
            <h3>Heading</h3>
            <p>Paragraph with <a href="https://example.com">link</a>.</p>
            <table>
                <tr><td>Cell 1</td><td>Cell 2</td></tr>
            </table>
        </ac:rich-text-body>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify content section exists
    assert "**complex-note Macro Content:**" in result

    # Verify markdown conversion (markdownify handles nested HTML)
    assert "Heading" in result
    assert "Paragraph" in result


@pytest.mark.asyncio
async def test_multiple_parameters_order_preserved(generic_handler):
    """Test multiple parameters maintain their order."""
    html = """
    <ac:structured-macro ac:name="ordered-macro">
        <ac:parameter ac:name="first">1</ac:parameter>
        <ac:parameter ac:name="second">2</ac:parameter>
        <ac:parameter ac:name="third">3</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify all parameters present (order may vary due to dict)
    assert 'first="1"' in result
    assert 'second="2"' in result
    assert 'third="3"' in result


@pytest.mark.asyncio
async def test_special_characters_in_parameters(generic_handler):
    """Test parameters with special characters are handled correctly."""
    html = """
    <ac:structured-macro ac:name="special-macro">
        <ac:parameter ac:name="url">https://example.com?key=value&amp;foo=bar</ac:parameter>
        <ac:parameter ac:name="message">Hello &lt;World&gt;</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await generic_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify special characters preserved (HTML-escaped by BeautifulSoup)
    assert "url=" in result
    assert "message=" in result
