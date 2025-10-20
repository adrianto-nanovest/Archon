"""
Unit tests for AttachmentMacroHandler.

Tests file icon mapping, Docling integration, file size limits, and graceful fallback.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.macro_handlers.attachment_macro import AttachmentMacroHandler


@pytest.fixture
def attachment_handler():
    """Create AttachmentMacroHandler without Docling integration."""
    mock_client = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.docling_enabled = False
    return AttachmentMacroHandler(
        confluence_client=mock_client,
        docling_processor=None,
        asset_links_tracker=[],
        settings=mock_settings
    )


@pytest.fixture
def attachment_handler_with_docling():
    """Create AttachmentMacroHandler with mocked Docling processor."""
    mock_client = AsyncMock()
    mock_docling = AsyncMock()
    mock_settings = MagicMock()
    mock_settings.docling_enabled = True
    mock_settings.docling_max_file_size_mb = 50

    handler = AttachmentMacroHandler(
        confluence_client=mock_client,
        docling_processor=mock_docling,
        asset_links_tracker=[],
        settings=mock_settings
    )
    handler.mock_docling = mock_docling
    handler.mock_client = mock_client
    return handler


@pytest.mark.asyncio
async def test_file_icon_mapping_pdf(attachment_handler):
    """Test PDF file icon mapping."""
    assert attachment_handler._get_file_icon("document.pdf") == "📄"


@pytest.mark.asyncio
async def test_file_icon_mapping_word(attachment_handler):
    """Test Word file icon mapping (doc, docx)."""
    assert attachment_handler._get_file_icon("document.doc") == "📝"
    assert attachment_handler._get_file_icon("document.docx") == "📝"


@pytest.mark.asyncio
async def test_file_icon_mapping_excel(attachment_handler):
    """Test Excel file icon mapping (xls, xlsx)."""
    assert attachment_handler._get_file_icon("spreadsheet.xls") == "📊"
    assert attachment_handler._get_file_icon("spreadsheet.xlsx") == "📊"


@pytest.mark.asyncio
async def test_file_icon_mapping_powerpoint(attachment_handler):
    """Test PowerPoint file icon mapping (ppt, pptx)."""
    assert attachment_handler._get_file_icon("presentation.ppt") == "📊"
    assert attachment_handler._get_file_icon("presentation.pptx") == "📊"


@pytest.mark.asyncio
async def test_file_icon_mapping_text(attachment_handler):
    """Test text file icon mapping."""
    assert attachment_handler._get_file_icon("readme.txt") == "📄"
    assert attachment_handler._get_file_icon("notes.md") == "📄"


@pytest.mark.asyncio
async def test_file_icon_mapping_archive(attachment_handler):
    """Test archive file icon mapping."""
    assert attachment_handler._get_file_icon("backup.zip") == "📦"
    assert attachment_handler._get_file_icon("backup.tar") == "📦"
    assert attachment_handler._get_file_icon("backup.gz") == "📦"


@pytest.mark.asyncio
async def test_file_icon_mapping_unknown(attachment_handler):
    """Test unknown file extension defaults to generic icon."""
    assert attachment_handler._get_file_icon("file.xyz") == "📎"


@pytest.mark.asyncio
async def test_is_docling_supported_formats(attachment_handler):
    """Test Docling format detection for supported formats."""
    assert attachment_handler._is_docling_supported("document.pdf") is True
    assert attachment_handler._is_docling_supported("document.docx") is True
    assert attachment_handler._is_docling_supported("presentation.pptx") is True
    assert attachment_handler._is_docling_supported("spreadsheet.xlsx") is True


@pytest.mark.asyncio
async def test_is_docling_supported_unsupported_formats(attachment_handler):
    """Test Docling format detection for unsupported formats."""
    assert attachment_handler._is_docling_supported("image.png") is False
    assert attachment_handler._is_docling_supported("video.mp4") is False
    assert attachment_handler._is_docling_supported("readme.txt") is False


@pytest.mark.asyncio
async def test_attachment_without_docling(attachment_handler):
    """Test attachment processing without Docling enabled."""
    html = """
    <ac:structured-macro ac:name="view-file">
        <ri:attachment ri:filename="document.pdf"/>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await attachment_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify file link markdown
    assert "📄 document.pdf" in result
    assert "ATTACHMENT_PLACEHOLDER_document.pdf" in result

    # Verify metadata tracked
    assert len(attachment_handler.asset_links_tracker) == 1
    assert attachment_handler.asset_links_tracker[0]["filename"] == "document.pdf"
    assert attachment_handler.asset_links_tracker[0]["processed"] is False


@pytest.mark.asyncio
async def test_attachment_with_docling_success(attachment_handler_with_docling, tmp_path):
    """Test attachment processing with Docling integration (success path)."""
    # Mock successful Docling processing
    attachment_handler_with_docling.mock_docling.process_attachment.return_value = {
        "success": True,
        "markdown": "# Document Content\n\nExtracted text.",
        "metadata": {
            "page_count": 5,
            "table_count": 2,
            "word_count": 150
        },
        "error": None
    }

    # Mock file download
    test_file = tmp_path / "document.pdf"
    test_file.write_bytes(b"PDF content" * 100)  # Small file

    async def mock_download(page_id, filename, output_path):
        Path(output_path).write_bytes(test_file.read_bytes())

    attachment_handler_with_docling.mock_client.download_attachment = mock_download

    html = """
    <ac:structured-macro ac:name="view-file">
        <ri:attachment ri:filename="document.pdf"/>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await attachment_handler_with_docling.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify Docling content embedded
    assert "ATTACHMENT: document.pdf" in result
    assert "Document Content" in result
    assert "Extracted text" in result

    # Verify metadata updated
    assert len(attachment_handler_with_docling.asset_links_tracker) == 1
    assert attachment_handler_with_docling.asset_links_tracker[0]["processed"] is True
    assert attachment_handler_with_docling.asset_links_tracker[0]["page_count"] == 5


@pytest.mark.asyncio
async def test_attachment_with_docling_failure(attachment_handler_with_docling, tmp_path):
    """Test graceful fallback when Docling processing fails."""
    # Mock Docling failure
    attachment_handler_with_docling.mock_docling.process_attachment.return_value = {
        "success": False,
        "markdown": "",
        "metadata": {},
        "error": "Processing timeout"
    }

    # Mock file download
    test_file = tmp_path / "document.pdf"
    test_file.write_bytes(b"PDF content" * 100)

    async def mock_download(page_id, filename, output_path):
        Path(output_path).write_bytes(test_file.read_bytes())

    attachment_handler_with_docling.mock_client.download_attachment = mock_download

    html = """
    <ac:structured-macro ac:name="view-file">
        <ri:attachment ri:filename="document.pdf"/>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await attachment_handler_with_docling.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify fallback to file link
    assert "📄 document.pdf" in result
    assert "ATTACHMENT_PLACEHOLDER_document.pdf" in result

    # Verify metadata shows unprocessed
    assert attachment_handler_with_docling.asset_links_tracker[0]["processed"] is False


@pytest.mark.asyncio
async def test_attachment_file_size_limit(attachment_handler_with_docling, tmp_path):
    """Test file size limit enforcement (>50MB skipped)."""
    # Create large file (55MB)
    large_file = tmp_path / "large.pdf"
    large_file.write_bytes(b"x" * (55 * 1024 * 1024))

    async def mock_download(page_id, filename, output_path):
        Path(output_path).write_bytes(large_file.read_bytes())

    attachment_handler_with_docling.mock_client.download_attachment = mock_download

    html = """
    <ac:structured-macro ac:name="view-file">
        <ri:attachment ri:filename="large.pdf"/>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await attachment_handler_with_docling.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify Docling NOT called
    assert not attachment_handler_with_docling.mock_docling.process_attachment.called

    # Verify fallback to file link
    assert "📄 large.pdf" in result
    assert "ATTACHMENT_PLACEHOLDER_large.pdf" in result
