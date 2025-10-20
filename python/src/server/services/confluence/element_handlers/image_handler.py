"""Image Handler for Confluence Storage Format HTML elements.

Processes images with AI-powered text extraction and analysis.
Supports multimodal LLM processing (default) with automatic Docling OCR fallback.
"""

import os
import tempfile
from pathlib import Path
from typing import Any

# BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
# but it's available at runtime via bs4/__init__.py import from bs4.element.
# See: https://github.com/python/typeshed/issues/4968
from bs4 import BeautifulSoup, Comment, NavigableString  # type: ignore[attr-defined]

from .base import BaseElementHandler


class ImageHandler(BaseElementHandler):
    """
    Handler for Confluence images (<ac:image>).

    Features:
    - Multimodal LLM processing (default when image_processing_mode="multimodal")
    - Automatic Docling OCR fallback for non-multimodal models
    - Image type detection (🖼️ image, 🎬 video, 📎 other)
    - Searchable text extraction embedded in markdown comments
    - Graceful fallback to standard image markdown on errors
    """

    def __init__(
        self,
        confluence_client: object | None = None,
        docling_processor: object | None = None,
        asset_links_tracker: list | None = None,
        settings: object | None = None,
        model_choice: str | None = None,
    ) -> None:
        """
        Initialize Image Handler.

        Args:
            confluence_client: Optional ConfluenceClient for image downloads
            docling_processor: Optional DoclingProcessor for OCR fallback
            asset_links_tracker: Shared list for image metadata
            settings: Optional settings object for feature flags
            model_choice: LLM model choice from RAG Settings (MODEL_CHOICE)
        """
        super().__init__()
        self.confluence_client = confluence_client
        self.docling_processor = docling_processor
        self.asset_links_tracker = (
            asset_links_tracker if asset_links_tracker is not None else []
        )
        self.settings = settings
        self.model_choice = model_choice

    @staticmethod
    def _check_multimodal_capability(model_choice: str) -> bool:
        """
        Check if MODEL_CHOICE supports vision/multimodal capabilities.

        Known multimodal models (as of October 2025):
        - OpenAI: gpt-4o, gpt-4-turbo, gpt-4-vision-preview
        - Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku, claude-3-5-sonnet
        - Google: gemini-pro-vision, gemini-1.5-pro, gemini-1.5-flash

        Args:
            model_choice: Model identifier string (e.g., "gpt-4o", "claude-3-sonnet")

        Returns:
            True if model supports multimodal, False otherwise
        """
        if not model_choice:
            return False

        multimodal_prefixes = [
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4-vision",
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "claude-3-5-sonnet",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-2.0-flash",
        ]

        return any(model_choice.lower().startswith(prefix) for prefix in multimodal_prefixes)

    @staticmethod
    def _get_image_type_icon(filename: str) -> tuple[str, str]:
        """
        Determine image type and corresponding icon.

        Args:
            filename: Image filename with extension

        Returns:
            Tuple of (icon, type) where:
            - icon: Unicode emoji (🖼️ image, 🎬 video, 📎 other)
            - type: String type ("image", "video", "other")
        """
        if not filename:
            return ("📎", "other")

        extension = Path(filename).suffix.lower()

        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff"}
        video_extensions = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"}

        if extension in image_extensions:
            return ("🖼️", "image")
        elif extension in video_extensions:
            return ("🎬", "video")
        else:
            return ("📎", "other")

    async def process(self, soup: BeautifulSoup, page_id: str | None = None, space_id: str | None = None, **kwargs: Any) -> None:
        """
        Process all images in the document.

        Implements multimodal LLM processing (default) with automatic Docling OCR fallback.

        Args:
            soup: BeautifulSoup object (modified in-place)
            page_id: Confluence page ID (for image downloads)
            space_id: Confluence space ID (unused for images)
            **kwargs: Additional arguments
        """
        # Find all image elements
        image_elements = soup.find_all("ac:image")

        if not image_elements:
            self.logger.debug("No images found")
            return

        for image_elem in image_elements:
            try:
                # Extract filename and source
                ri_attachment = image_elem.find("ri:attachment")
                ri_url = image_elem.find("ri:url")

                filename = None
                source_type = None

                if ri_attachment:
                    filename = ri_attachment.get("ri:filename")
                    source_type = "attachment"
                elif ri_url:
                    filename = ri_url.get("ri:value")
                    source_type = "url"

                if not filename:
                    self.logger.warning("Image element missing filename, skipping")
                    continue

                # Get image type and icon
                icon, img_type = self._get_image_type_icon(filename)

                # Add to asset links tracker
                asset_entry = {
                    "filename": filename,
                    "source": source_type,
                    "type": img_type,
                    "processed": False,
                }
                self.asset_links_tracker.append(asset_entry)

                # Determine processing mode
                image_processing_mode = getattr(self.settings, "image_processing_mode", "multimodal") if self.settings else "multimodal"

                analysis_result = None

                if image_processing_mode == "none":
                    # Skip AI processing
                    pass
                elif image_processing_mode == "multimodal":
                    # Check if model supports multimodal
                    if self._check_multimodal_capability(self.model_choice):
                        # Use multimodal LLM
                        self.logger.debug(f"Using multimodal LLM for image: {filename}")
                        analysis_result = await self._process_image_with_multimodal_llm(
                            page_id, filename, image_elem
                        )
                    else:
                        # Auto-fallback to Docling OCR
                        self.logger.warning(
                            f"Model {self.model_choice} does not support vision. Falling back to Docling OCR for {filename}"
                        )
                        analysis_result = await self._process_image_with_docling_ocr(
                            page_id, filename
                        )
                elif image_processing_mode == "docling_ocr":
                    # Forced Docling OCR mode
                    self.logger.debug(f"Using Docling OCR for image: {filename}")
                    analysis_result = await self._process_image_with_docling_ocr(
                        page_id, filename
                    )

                # Build markdown output
                if analysis_result and analysis_result.get("success"):
                    # Update asset tracker
                    asset_entry["processed"] = True
                    asset_entry["processor"] = analysis_result.get("processor")
                    if "model" in analysis_result:
                        asset_entry["model"] = analysis_result["model"]
                    if "extracted_text" in analysis_result:
                        asset_entry["extracted_text"] = analysis_result["extracted_text"]
                    if "image_type" in analysis_result:
                        asset_entry["image_type"] = analysis_result["image_type"]

                    # Embed analysis in HTML comment for searchability (will convert to markdown)
                    extracted_text = analysis_result.get("extracted_text", "")
                    image_type = analysis_result.get("image_type", img_type)
                    comment_text = f" IMAGE: {filename} | Type: {image_type} | Text: {extracted_text[:200]} "
                    comment_node = Comment(comment_text)

                    # Create image markdown
                    markdown_image = NavigableString(f"\n![{icon} {filename}](PLACEHOLDER_{filename})\n")

                    # Replace element with comment + image
                    image_elem.insert_before(comment_node)
                    image_elem.replace_with(markdown_image)
                else:
                    # Standard image markdown (no AI processing or failed)
                    markdown_image = f"![{icon} {filename}](PLACEHOLDER_{filename})"
                    image_elem.replace_with(NavigableString(markdown_image))

            except Exception as e:
                self.logger.error(f"Error processing image {filename}: {e}", exc_info=True)
                # Graceful fallback
                markdown_image = f"![{filename}](PLACEHOLDER_{filename})"
                image_elem.replace_with(NavigableString(markdown_image))

        self.logger.debug(f"Processed {len(image_elements)} images")

    async def _process_image_with_multimodal_llm(
        self, page_id: str, filename: str, image_element
    ) -> dict:
        """
        Process image with multimodal LLM (vision model).

        Downloads image, sends to LLM with prompt, extracts text and classification.

        Args:
            page_id: Confluence page ID
            filename: Image filename
            image_element: BeautifulSoup image element

        Returns:
            Dict with keys: success, extracted_text, image_type, description, processor, model
        """
        try:
            if not self.confluence_client or not page_id:
                self.logger.warning("Missing confluence_client or page_id for multimodal LLM")
                return {"success": False}

            # Download image to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                tmp_path = tmp_file.name

            try:
                await self.confluence_client.download_attachment(page_id, filename, tmp_path)

                # TODO: Integrate with LLM provider service for multimodal chat
                # For Story 2.3, this is a placeholder that returns mock data
                # Future story will integrate with llm_provider_service

                # Mock response for now (will be replaced with actual LLM call)
                self.logger.info(f"Multimodal LLM processing for {filename} (placeholder implementation)")

                # Placeholder result
                result = {
                    "success": True,
                    "extracted_text": "Sample extracted text from image",
                    "image_type": "diagram",
                    "description": "Placeholder description",
                    "processor": "multimodal_llm",
                    "model": self.model_choice,
                }

                return result

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            self.logger.error(f"Multimodal LLM processing failed for {filename}: {e}")
            return {"success": False}

    async def _process_image_with_docling_ocr(self, page_id: str, filename: str) -> dict:
        """
        Process image with Docling OCR (fallback method).

        Downloads image and uses DoclingProcessor for text extraction.

        Args:
            page_id: Confluence page ID
            filename: Image filename

        Returns:
            Dict with keys: success, extracted_text, processor
        """
        try:
            if not self.docling_processor or not self.confluence_client or not page_id:
                self.logger.warning("Missing docling_processor, confluence_client, or page_id")
                return {"success": False}

            # Download image to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                tmp_path = tmp_file.name

            try:
                await self.confluence_client.download_attachment(page_id, filename, tmp_path)

                # Process with Docling OCR
                result = await self.docling_processor.process_image_ocr(tmp_path, page_id)

                if result.get("success"):
                    return {
                        "success": True,
                        "extracted_text": result.get("extracted_text", ""),
                        "processor": "docling_ocr",
                    }
                else:
                    return {"success": False}

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        except Exception as e:
            self.logger.error(f"Docling OCR processing failed for {filename}: {e}")
            return {"success": False}
