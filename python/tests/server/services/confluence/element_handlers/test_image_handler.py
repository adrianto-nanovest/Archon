"""Unit tests for Image Handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.element_handlers.image_handler import ImageHandler


def test_check_multimodal_capability():
    """Test multimodal capability detection for known models."""
    # OpenAI models
    assert ImageHandler._check_multimodal_capability("gpt-4o") is True
    assert ImageHandler._check_multimodal_capability("gpt-4-turbo") is True
    assert ImageHandler._check_multimodal_capability("gpt-4-vision-preview") is True
    assert ImageHandler._check_multimodal_capability("gpt-3.5-turbo") is False

    # Anthropic models
    assert ImageHandler._check_multimodal_capability("claude-3-opus-20240229") is True
    assert ImageHandler._check_multimodal_capability("claude-3-sonnet-20240229") is True
    assert ImageHandler._check_multimodal_capability("claude-3-haiku-20240307") is True
    assert ImageHandler._check_multimodal_capability("claude-3-5-sonnet-20240620") is True
    assert ImageHandler._check_multimodal_capability("claude-2") is False

    # Google models
    assert ImageHandler._check_multimodal_capability("gemini-pro-vision") is True
    assert ImageHandler._check_multimodal_capability("gemini-1.5-pro") is True
    assert ImageHandler._check_multimodal_capability("gemini-1.5-flash") is True
    assert ImageHandler._check_multimodal_capability("gemini-2.0-flash-exp") is True
    assert ImageHandler._check_multimodal_capability("gemini-pro") is False

    # Edge cases
    assert ImageHandler._check_multimodal_capability(None) is False
    assert ImageHandler._check_multimodal_capability("") is False
    assert ImageHandler._check_multimodal_capability("unknown-model") is False


def test_get_image_type_icon():
    """Test image type detection and icon assignment."""
    # Image types
    icon, img_type = ImageHandler._get_image_type_icon("screenshot.png")
    assert icon == "🖼️"
    assert img_type == "image"

    icon, img_type = ImageHandler._get_image_type_icon("diagram.jpg")
    assert icon == "🖼️"
    assert img_type == "image"

    icon, img_type = ImageHandler._get_image_type_icon("chart.svg")
    assert icon == "🖼️"
    assert img_type == "image"

    # Video types
    icon, img_type = ImageHandler._get_image_type_icon("demo.mp4")
    assert icon == "🎬"
    assert img_type == "video"

    icon, img_type = ImageHandler._get_image_type_icon("recording.mov")
    assert icon == "🎬"
    assert img_type == "video"

    # Other types
    icon, img_type = ImageHandler._get_image_type_icon("document.pdf")
    assert icon == "📎"
    assert img_type == "other"

    icon, img_type = ImageHandler._get_image_type_icon("data.csv")
    assert icon == "📎"
    assert img_type == "other"

    # Edge cases
    icon, img_type = ImageHandler._get_image_type_icon("")
    assert icon == "📎"
    assert img_type == "other"


@pytest.mark.asyncio
async def test_multimodal_llm_processing():
    """Test multimodal LLM processing (mocked LLM provider)."""
    # Create mocks
    mock_client = MagicMock()
    mock_client.download_attachment = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.image_processing_mode = "multimodal"

    asset_links_tracker = []

    handler = ImageHandler(
        confluence_client=mock_client,
        asset_links_tracker=asset_links_tracker,
        settings=mock_settings,
        model_choice="gpt-4o",
    )

    html = """
    <ac:image>
        <ri:attachment ri:filename="chart.png"/>
    </ac:image>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Mock file operations
    with patch("tempfile.NamedTemporaryFile"), patch("os.path.exists", return_value=True), patch("os.remove"):
        await handler.process(soup, page_id="123", space_id=None)

    # Verify multimodal capability check passed
    result = str(soup)
    assert "chart.png" in result
    assert "🖼️" in result  # Image icon

    # Verify asset tracker updated
    assert len(asset_links_tracker) == 1
    assert asset_links_tracker[0]["filename"] == "chart.png"
    assert asset_links_tracker[0]["processed"] is True
    assert asset_links_tracker[0]["processor"] == "multimodal_llm"
    assert asset_links_tracker[0]["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_automatic_docling_ocr_fallback():
    """Test automatic Docling OCR fallback when MODEL_CHOICE lacks vision."""
    # Create mocks
    mock_client = MagicMock()
    mock_client.download_attachment = AsyncMock()

    mock_docling = MagicMock()
    mock_docling.process_image_ocr = AsyncMock(
        return_value={"success": True, "extracted_text": "OCR extracted text"}
    )

    mock_settings = MagicMock()
    mock_settings.image_processing_mode = "multimodal"

    asset_links_tracker = []

    handler = ImageHandler(
        confluence_client=mock_client,
        docling_processor=mock_docling,
        asset_links_tracker=asset_links_tracker,
        settings=mock_settings,
        model_choice="gpt-3.5-turbo",  # NOT multimodal
    )

    html = """
    <ac:image>
        <ri:attachment ri:filename="screenshot.png"/>
    </ac:image>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Mock file operations
    with patch("tempfile.NamedTemporaryFile"), patch("os.path.exists", return_value=True), patch("os.remove"):
        await handler.process(soup, page_id="123", space_id=None)

    # Verify Docling OCR called
    mock_docling.process_image_ocr.assert_called_once()

    # Verify asset tracker shows docling_ocr processor
    assert len(asset_links_tracker) == 1
    assert asset_links_tracker[0]["processor"] == "docling_ocr"


@pytest.mark.asyncio
async def test_forced_docling_ocr_mode():
    """Test forced Docling OCR mode (image_processing_mode = 'docling_ocr')."""
    # Create mocks
    mock_client = MagicMock()
    mock_client.download_attachment = AsyncMock()

    mock_docling = MagicMock()
    mock_docling.process_image_ocr = AsyncMock(
        return_value={"success": True, "extracted_text": "Forced OCR text"}
    )

    mock_settings = MagicMock()
    mock_settings.image_processing_mode = "docling_ocr"  # Force Docling OCR

    asset_links_tracker = []

    handler = ImageHandler(
        confluence_client=mock_client,
        docling_processor=mock_docling,
        asset_links_tracker=asset_links_tracker,
        settings=mock_settings,
        model_choice="gpt-4o",  # Multimodal available, but forced to use OCR
    )

    html = """
    <ac:image>
        <ri:attachment ri:filename="image.jpg"/>
    </ac:image>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Mock file operations
    with patch("tempfile.NamedTemporaryFile"), patch("os.path.exists", return_value=True), patch("os.remove"):
        await handler.process(soup, page_id="123", space_id=None)

    # Verify Docling OCR called despite multimodal capability
    mock_docling.process_image_ocr.assert_called_once()

    # Verify asset tracker
    assert asset_links_tracker[0]["processor"] == "docling_ocr"


@pytest.mark.asyncio
async def test_graceful_fallback_on_processing_failure():
    """Test graceful fallback to standard image markdown on processing failures."""
    # Create mocks that fail
    mock_client = MagicMock()
    mock_client.download_attachment = AsyncMock(side_effect=Exception("Download failed"))

    mock_settings = MagicMock()
    mock_settings.image_processing_mode = "multimodal"

    asset_links_tracker = []

    handler = ImageHandler(
        confluence_client=mock_client,
        asset_links_tracker=asset_links_tracker,
        settings=mock_settings,
        model_choice="gpt-4o",
    )

    html = """
    <ac:image>
        <ri:attachment ri:filename="broken.png"/>
    </ac:image>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Process should not raise exception
    await handler.process(soup, page_id="123", space_id=None)

    # Verify fallback to standard image markdown
    result = str(soup)
    assert "broken.png" in result
    assert "PLACEHOLDER_broken.png" in result


@pytest.mark.asyncio
async def test_asset_links_tracker_metadata_enrichment():
    """Test asset_links_tracker metadata enrichment."""
    # Create mocks
    mock_client = MagicMock()
    mock_client.download_attachment = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.image_processing_mode = "multimodal"

    asset_links_tracker = []

    handler = ImageHandler(
        confluence_client=mock_client,
        asset_links_tracker=asset_links_tracker,
        settings=mock_settings,
        model_choice="gpt-4o",
    )

    html = """
    <ac:image>
        <ri:attachment ri:filename="diagram.png"/>
    </ac:image>
    <ac:image>
        <ri:url ri:value="https://example.com/external.jpg"/>
    </ac:image>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Mock file operations
    with patch("tempfile.NamedTemporaryFile"), patch("os.path.exists", return_value=True), patch("os.remove"):
        await handler.process(soup, page_id="123", space_id=None)

    # Verify asset tracker enriched with metadata
    assert len(asset_links_tracker) == 2

    # First image (attachment)
    assert asset_links_tracker[0]["filename"] == "diagram.png"
    assert asset_links_tracker[0]["source"] == "attachment"
    assert asset_links_tracker[0]["type"] == "image"
    assert "processed" in asset_links_tracker[0]

    # Second image (external URL)
    assert asset_links_tracker[1]["filename"] == "https://example.com/external.jpg"
    assert asset_links_tracker[1]["source"] == "url"


@pytest.mark.asyncio
async def test_markdown_comment_embedding():
    """Test markdown comment embedding for searchability."""
    # Create mocks
    mock_client = MagicMock()
    mock_client.download_attachment = AsyncMock()

    mock_settings = MagicMock()
    mock_settings.image_processing_mode = "multimodal"

    handler = ImageHandler(
        confluence_client=mock_client,
        settings=mock_settings,
        model_choice="gpt-4o",
    )

    html = """
    <ac:image>
        <ri:attachment ri:filename="chart.png"/>
    </ac:image>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Mock file operations
    with patch("tempfile.NamedTemporaryFile"), patch("os.path.exists", return_value=True), patch("os.remove"):
        await handler.process(soup, page_id="123", space_id=None)

    result = str(soup)

    # Verify markdown comment present
    assert "<!-- IMAGE: chart.png" in result
    assert "Type:" in result
    assert "Text:" in result
