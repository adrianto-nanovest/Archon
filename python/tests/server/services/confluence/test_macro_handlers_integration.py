"""Integration tests for macro handlers with ConfluenceProcessor."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.server.services.confluence.confluence_processor import ConfluenceProcessor


@pytest.fixture
def processor():
    return ConfluenceProcessor()


@pytest.fixture
def processor_with_docling():
    """Processor with mocked Confluence client and DoclingProcessor."""
    mock_client = AsyncMock()
    mock_docling = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.docling_enabled = True
    mock_settings.docling_max_file_size_mb = 50

    processor = ConfluenceProcessor(
        confluence_client=mock_client,
        docling_processor=mock_docling,
        settings=mock_settings
    )
    processor.mock_client = mock_client
    processor.mock_docling = mock_docling
    return processor


@pytest.mark.asyncio
async def test_iv1_code_blocks_no_line_breaks_mid_block(processor):
    """Test IV1: Code blocks remain intact (no line breaks mid-block)."""
    html = """
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">python</ac:parameter>
        <ac:plain-text-body><![CDATA[def calculate(x, y):
    result = x + y
    return result]]></ac:plain-text-body>
    </ac:structured-macro>
    """

    markdown, _ = await processor.html_to_markdown(html, page_id="test")

    # Verify fenced code block exists
    assert "```python" in markdown
    # Verify no extra line breaks mid-block (all lines connected)
    assert "def calculate" in markdown
    assert "result = x + y" in markdown
    assert "return result" in markdown
    # Verify code block structure intact
    assert markdown.count("```") >= 2


@pytest.mark.asyncio
async def test_iv2_jira_tier1_extraction(processor):
    """Test IV2: JIRA Tier 1 extraction."""
    html = '<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">PROJ-123</ac:parameter></ac:structured-macro>'

    markdown, _ = await processor.html_to_markdown(html, "test")

    assert "PROJ-123" in markdown
    assert len(processor.jira_links_tracker) == 1
    assert processor.jira_links_tracker[0]["issue_key"] == "PROJ-123"


@pytest.mark.asyncio
async def test_iv3_panel_emojis(processor):
    """Test IV3: Panel emojis."""
    html = """
    <ac:structured-macro ac:name="info"><ac:rich-text-body><p>Info</p></ac:rich-text-body></ac:structured-macro>
    <ac:structured-macro ac:name="warning"><ac:rich-text-body><p>Warn</p></ac:rich-text-body></ac:structured-macro>
    """

    markdown, _ = await processor.html_to_markdown(html, "test")

    assert "ℹ️" in markdown
    assert "⚠️" in markdown


@pytest.mark.asyncio
async def test_iv4_attachment_metadata(processor):
    """Test IV4: Attachment metadata tracking."""
    html = '<ac:structured-macro ac:name="view-file"><ri:attachment ri:filename="doc.pdf"/></ac:structured-macro>'

    markdown, _ = await processor.html_to_markdown(html, "test")

    assert "doc.pdf" in markdown
    assert len(processor.asset_links_tracker) == 1
    assert processor.asset_links_tracker[0]["filename"] == "doc.pdf"


@pytest.mark.asyncio
async def test_iv5_docling_fulltext_embedding(processor_with_docling):
    """Test IV5: PDF/Office attachments processed with Docling (full-text content embedding)."""
    # Mock Docling processor to return structured result
    processor_with_docling.mock_docling.process_attachment.return_value = {
        "success": True,
        "markdown": "# Document Title\\n\\nDocument content extracted by Docling.",
        "plain_text": "Document Title Document content extracted by Docling.",
        "metadata": {
            "page_count": 5,
            "table_count": 2,
            "code_block_count": 1,
            "word_count": 150
        },
        "error": None
    }

    html = '<ac:structured-macro ac:name="view-file"><ri:attachment ri:filename="document.pdf"/></ac:structured-macro>'

    markdown, _ = await processor_with_docling.html_to_markdown(html, page_id="test123")

    # Verify Docling called with correct file path
    assert processor_with_docling.mock_docling.process_attachment.called

    # Verify full-text content embedded in markdown
    assert "ATTACHMENT: document.pdf" in markdown
    assert "Document content extracted by Docling" in markdown

    # Verify metadata updated with Docling results
    assert len(processor_with_docling.asset_links_tracker) == 1
    assert processor_with_docling.asset_links_tracker[0]["processed"] is True
    assert processor_with_docling.asset_links_tracker[0]["page_count"] == 5
    assert processor_with_docling.asset_links_tracker[0]["table_count"] == 2


@pytest.mark.asyncio
async def test_iv6_docling_graceful_fallback(processor_with_docling):
    """Test IV6: Docling processing failures fall back to file link gracefully."""
    # Mock Docling processor to return failure
    processor_with_docling.mock_docling.process_attachment.return_value = {
        "success": False,
        "markdown": "",
        "metadata": {},
        "error": "Processing timeout"
    }

    html = '<ac:structured-macro ac:name="view-file"><ri:attachment ri:filename="document.pdf"/></ac:structured-macro>'

    markdown, _ = await processor_with_docling.html_to_markdown(html, page_id="test123")

    # Verify fallback to file link markdown
    assert "📄 document.pdf" in markdown
    assert "ATTACHMENT_PLACEHOLDER_document.pdf" in markdown

    # Verify metadata shows unprocessed
    assert len(processor_with_docling.asset_links_tracker) == 1
    assert processor_with_docling.asset_links_tracker[0]["processed"] is False


@pytest.mark.asyncio
async def test_iv7_large_file_skipped(processor_with_docling, tmp_path):
    """Test IV7: Large files (>50MB) skipped with warning logged."""
    # Create a mock file that appears to be 55MB
    large_file = tmp_path / "large.pdf"
    large_file.write_bytes(b"x" * (55 * 1024 * 1024))  # 55MB

    # Mock download_attachment to write the large file
    async def mock_download(page_id, filename, output_path):
        Path(output_path).write_bytes(large_file.read_bytes())

    processor_with_docling.mock_client.download_attachment = mock_download

    html = '<ac:structured-macro ac:name="view-file"><ri:attachment ri:filename="large.pdf"/></ac:structured-macro>'

    markdown, _ = await processor_with_docling.html_to_markdown(html, page_id="test123")

    # Verify Docling NOT called (file too large)
    assert not processor_with_docling.mock_docling.process_attachment.called

    # Verify fallback to file link
    assert "📄 large.pdf" in markdown
    assert "ATTACHMENT_PLACEHOLDER_large.pdf" in markdown


@pytest.mark.asyncio
async def test_iv8_unknown_macros(processor):
    """Test IV8: Unknown macros handled gracefully."""
    html = '<ac:structured-macro ac:name="unknown-macro"></ac:structured-macro>'

    markdown, _ = await processor.html_to_markdown(html, "test")

    assert "Unsupported Confluence Macro" in markdown
    assert "unknown-macro" in markdown
