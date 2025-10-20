"""Unit tests for PanelMacroHandler."""

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.macro_handlers.panel_macro import PanelMacroHandler


@pytest.fixture
def panel_handler():
    return PanelMacroHandler()


@pytest.mark.asyncio
async def test_info_panel_with_emoji(panel_handler):
    html = '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>Info text</p></ac:rich-text-body></ac:structured-macro>'
    soup = BeautifulSoup(html, "html.parser")
    await panel_handler.process(soup.find("ac:structured-macro"), "test-page")
    # BeautifulSoup escapes > to &gt;
    assert "&gt; ℹ️" in str(soup) or "> ℹ️" in soup.get_text()


@pytest.mark.asyncio
async def test_tip_panel_with_emoji(panel_handler):
    html = '<ac:structured-macro ac:name="tip"><ac:rich-text-body><p>Tip text</p></ac:rich-text-body></ac:structured-macro>'
    soup = BeautifulSoup(html, "html.parser")
    await panel_handler.process(soup.find("ac:structured-macro"), "test-page")
    assert "&gt; ✅" in str(soup)


@pytest.mark.asyncio
async def test_warning_panel_with_emoji(panel_handler):
    html = '<ac:structured-macro ac:name="warning"><ac:rich-text-body><p>Warning text</p></ac:rich-text-body></ac:structured-macro>'
    soup = BeautifulSoup(html, "html.parser")
    await panel_handler.process(soup.find("ac:structured-macro"), "test-page")
    assert "&gt; ⚠️" in str(soup)


@pytest.mark.asyncio
async def test_note_panel_with_emoji(panel_handler):
    html = '<ac:structured-macro ac:name="note"><ac:rich-text-body><p>Note text</p></ac:rich-text-body></ac:structured-macro>'
    soup = BeautifulSoup(html, "html.parser")
    await panel_handler.process(soup.find("ac:structured-macro"), "test-page")
    assert "&gt; ❌" in str(soup)


@pytest.mark.asyncio
async def test_generic_panel_no_emoji(panel_handler):
    html = '<ac:structured-macro ac:name="panel"><ac:rich-text-body><p>Panel text</p></ac:rich-text-body></ac:structured-macro>'
    soup = BeautifulSoup(html, "html.parser")
    await panel_handler.process(soup.find("ac:structured-macro"), "test-page")
    result = str(soup)
    assert result.startswith("&gt;")
    assert "ℹ️" not in result and "✅" not in result


@pytest.mark.asyncio
async def test_panel_with_nested_formatting(panel_handler):
    html = '<ac:structured-macro ac:name="info"><ac:rich-text-body><p><strong>bold</strong> and <em>italic</em></p></ac:rich-text-body></ac:structured-macro>'
    soup = BeautifulSoup(html, "html.parser")
    await panel_handler.process(soup.find("ac:structured-macro"), "test-page")
    result = str(soup)
    assert "**bold**" in result
    assert "*italic*" in result


@pytest.mark.asyncio
async def test_multiline_panel(panel_handler):
    html = '<ac:structured-macro ac:name="warning"><ac:rich-text-body><p>Line 1</p><p>Line 2</p></ac:rich-text-body></ac:structured-macro>'
    soup = BeautifulSoup(html, "html.parser")
    await panel_handler.process(soup.find("ac:structured-macro"), "test-page")
    result = str(soup)
    lines = result.split("\n")
    assert all(line.startswith("&gt;") for line in lines if line.strip())
    assert lines[0].startswith("&gt; ⚠️")
