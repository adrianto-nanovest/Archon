"""
Docling document processing service for Confluence attachments.

This module provides the DoclingProcessor class that handles PDF, Office documents,
and image OCR processing using the Docling library. The processor is optimized for
RAG ingestion with metadata extraction and graceful error handling.

Primary use: PDF/Office document processing (DOCX, PPTX, XLSX)
Secondary use: Image OCR fallback (when multimodal LLM unavailable)
"""

import asyncio
import logging
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import DoclingDocument
from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter


class DoclingProcessor:
    """
    Docling document processing service for PDF/Office documents and image OCR.

    Handles document conversion with:
    - Optimized pipeline options (table extraction, code blocks)
    - Concurrency limiting via semaphore (prevent memory exhaustion)
    - Timeout protection per file
    - Comprehensive error handling with graceful degradation
    - Metadata extraction for RAG optimization

    Example usage:
        ```python
        from config.config import get_config

        config = get_config()
        processor = DoclingProcessor(
            docling_enabled=True,
            max_file_size_mb=50,
            timeout_seconds=60,
            max_concurrent=2,
            image_processing_mode="multimodal"
        )

        # Process PDF/Office document
        result = await processor.process_attachment(file_path, page_id="12345")
        if result["success"]:
            markdown = result["markdown"]
            metadata = result["metadata"]

        # Process image with OCR (fallback)
        result = await processor.process_image_ocr(image_path, page_id="12345")
        ```
    """

    # Supported document formats (primary use case)
    SUPPORTED_DOCUMENT_FORMATS = {".pdf", ".docx", ".pptx", ".xlsx"}

    # Supported image formats (secondary use - OCR fallback)
    SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".tiff", ".webp"}

    # Multimodal models (for image processing capability detection)
    MULTIMODAL_MODELS = {
        "gpt-4o",
        "gpt-4-vision",
        "gpt-4-turbo",
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "claude-3.5-sonnet",
        "claude-3-5-sonnet",
        "gemini-pro-vision",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
    }

    def __init__(
        self,
        docling_enabled: bool = True,
        max_file_size_mb: int = 50,
        timeout_seconds: int = 60,
        max_concurrent: int = 2,
        image_processing_mode: str = "multimodal",
    ):
        """
        Initialize DoclingProcessor with configuration settings.

        Args:
            docling_enabled: Master feature flag for PDF/Office processing
            max_file_size_mb: Skip files larger than this (memory protection)
            timeout_seconds: Processing timeout per file (prevent infinite processing)
            max_concurrent: Limit parallel Docling processes (memory management)
            image_processing_mode: Image processing strategy
                - "multimodal": Use multimodal LLM (default, checks MODEL_CHOICE)
                - "docling_ocr": Force Docling OCR (bypass multimodal LLM)
                - "none": Skip image processing
        """
        self.logger = logging.getLogger("DoclingProcessor")

        # Configuration
        self.docling_enabled = docling_enabled
        self.max_file_size_mb = max_file_size_mb
        self.timeout_seconds = timeout_seconds
        self.max_concurrent = max_concurrent
        self.image_processing_mode = image_processing_mode

        # Concurrency control (prevent memory exhaustion)
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Initialize DocumentConverter with optimized pipeline options
        # Primary use: PDF/Office document processing
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False  # Disable OCR by default (expensive)
        pipeline_options.do_table_structure = True  # Enable table extraction
        pipeline_options.do_code_enrichment = True  # Enable code block detection

        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: pipeline_options}
        )

        # Separate converter for OCR (images only)
        # Secondary use: Image OCR fallback
        ocr_pipeline_options = PdfPipelineOptions()
        ocr_pipeline_options.do_ocr = True
        ocr_pipeline_options.ocr_options = EasyOcrOptions()

        self.ocr_converter = DocumentConverter(
            format_options={InputFormat.PDF: ocr_pipeline_options}
        )

        self.logger.info(
            f"DoclingProcessor initialized (enabled={docling_enabled}, "
            f"max_file_size={max_file_size_mb}MB, timeout={timeout_seconds}s, "
            f"max_concurrent={max_concurrent}, image_mode={image_processing_mode})"
        )

    async def process_attachment(
        self, file_path: Path, page_id: str | None = None
    ) -> dict:
        """
        Process PDF/Office document attachment using Docling.

        Primary use case for document processing (DOCX, PPTX, XLSX, PDF).
        Extracts markdown, plain text, and metadata for RAG ingestion.

        Args:
            file_path: Path to the document file
            page_id: Confluence page ID (for logging context)

        Returns:
            dict with keys:
                - success (bool): True if processing succeeded
                - markdown (str): Markdown representation of document
                - plain_text (str): Plain text (strict mode, no formatting)
                - metadata (dict): Extracted metadata (page_count, tables, etc)
                - error (str | None): Error message if success=False

        Error handling:
            - File too large: Returns error without processing
            - Timeout: Returns error after timeout_seconds
            - Memory exhausted: Returns error and logs with exc_info
            - Any exception: Returns error with detailed logging
        """
        self.logger.info(
            f"Starting Docling processing for {file_path.name} (page_id={page_id})"
        )

        try:
            # Check if format is supported
            if not self._is_document_format(file_path):
                self.logger.warning(
                    f"Unsupported document format: {file_path.suffix} (file: {file_path.name})"
                )
                return {
                    "success": False,
                    "markdown": "",
                    "plain_text": "",
                    "metadata": {},
                    "error": f"Unsupported format: {file_path.suffix}",
                }

            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                self.logger.warning(
                    f"Skipping {file_path.name}: file size {file_size_mb:.2f}MB "
                    f"exceeds limit {self.max_file_size_mb}MB (page_id={page_id})"
                )
                return {
                    "success": False,
                    "markdown": "",
                    "plain_text": "",
                    "metadata": {},
                    "error": f"File too large ({file_size_mb:.2f}MB)",
                }

            # Process with concurrency limiting
            async with self._semaphore:
                # Add timeout protection
                result = await asyncio.wait_for(
                    self._process_document_async(file_path), timeout=self.timeout_seconds
                )

            self.logger.info(
                f"Completed Docling processing for {file_path.name} (page_id={page_id})"
            )
            return result

        except TimeoutError:
            self.logger.warning(
                f"Timeout processing {file_path.name} after {self.timeout_seconds}s (page_id={page_id})"
            )
            return {
                "success": False,
                "markdown": "",
                "plain_text": "",
                "metadata": {},
                "error": "Processing timeout",
            }

        except MemoryError:
            self.logger.error(
                f"Memory exhausted processing {file_path.name} (page_id={page_id})",
                exc_info=True,
            )
            return {
                "success": False,
                "markdown": "",
                "plain_text": "",
                "metadata": {},
                "error": "Memory exhausted",
            }

        except Exception as e:
            self.logger.error(
                f"Failed to process {file_path.name} (page_id={page_id}): {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "markdown": "",
                "plain_text": "",
                "metadata": {},
                "error": str(e),
            }

    async def process_image_ocr(
        self, file_path: Path, page_id: str | None = None
    ) -> dict:
        """
        Process image with OCR using Docling (fallback only).

        Secondary use case when multimodal LLM is unavailable or forced via
        image_processing_mode="docling_ocr". Uses EasyOCR for text extraction.

        Args:
            file_path: Path to the image file
            page_id: Confluence page ID (for logging context)

        Returns:
            dict with keys:
                - success (bool): True if OCR succeeded
                - markdown (str): OCR text in markdown format
                - plain_text (str): OCR text (strict mode)
                - metadata (dict): Extracted metadata with ocr_enabled=True flag
                - error (str | None): Error message if success=False
        """
        self.logger.info(
            f"Starting Docling OCR for {file_path.name} (page_id={page_id})"
        )

        try:
            # Check if format is supported
            if not self._is_image_format(file_path):
                self.logger.warning(
                    f"Unsupported image format: {file_path.suffix} (file: {file_path.name})"
                )
                return {
                    "success": False,
                    "markdown": "",
                    "plain_text": "",
                    "metadata": {},
                    "error": f"Unsupported format: {file_path.suffix}",
                }

            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                self.logger.warning(
                    f"Skipping {file_path.name}: file size {file_size_mb:.2f}MB "
                    f"exceeds limit {self.max_file_size_mb}MB (page_id={page_id})"
                )
                return {
                    "success": False,
                    "markdown": "",
                    "plain_text": "",
                    "metadata": {},
                    "error": f"File too large ({file_size_mb:.2f}MB)",
                }

            # Process with concurrency limiting
            async with self._semaphore:
                # Add timeout protection
                result = await asyncio.wait_for(
                    self._process_image_ocr_async(file_path), timeout=self.timeout_seconds
                )

            # Add OCR flag to metadata
            result["metadata"]["ocr_enabled"] = True

            self.logger.info(
                f"Completed Docling OCR for {file_path.name} (page_id={page_id})"
            )
            return result

        except TimeoutError:
            self.logger.warning(
                f"Timeout processing OCR for {file_path.name} after {self.timeout_seconds}s (page_id={page_id})"
            )
            return {
                "success": False,
                "markdown": "",
                "plain_text": "",
                "metadata": {},
                "error": "Processing timeout",
            }

        except MemoryError:
            self.logger.error(
                f"Memory exhausted processing OCR for {file_path.name} (page_id={page_id})",
                exc_info=True,
            )
            return {
                "success": False,
                "markdown": "",
                "plain_text": "",
                "metadata": {},
                "error": "Memory exhausted",
            }

        except Exception as e:
            self.logger.error(
                f"Failed to process OCR for {file_path.name} (page_id={page_id}): {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "markdown": "",
                "plain_text": "",
                "metadata": {},
                "error": str(e),
            }

    async def _process_document_async(self, file_path: Path) -> dict:
        """
        Process document in thread pool executor (CPU-bound operation).

        Args:
            file_path: Path to the document file

        Returns:
            dict with success, markdown, plain_text, metadata, error keys
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process_document_sync, file_path)

    def _process_document_sync(self, file_path: Path) -> dict:
        """
        Synchronous document processing (runs in thread pool).

        Args:
            file_path: Path to the document file

        Returns:
            dict with processing results
        """
        result = self.converter.convert(str(file_path))
        document = result.document

        markdown = document.export_to_markdown()
        plain_text = document.export_to_markdown(strict_text=True)
        metadata = self._extract_metadata(document)

        return {
            "success": True,
            "markdown": markdown,
            "plain_text": plain_text,
            "metadata": metadata,
            "error": None,
        }

    async def _process_image_ocr_async(self, file_path: Path) -> dict:
        """
        Process image with OCR in thread pool executor (CPU-bound operation).

        Args:
            file_path: Path to the image file

        Returns:
            dict with success, markdown, plain_text, metadata, error keys
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._process_image_ocr_sync, file_path)

    def _process_image_ocr_sync(self, file_path: Path) -> dict:
        """
        Synchronous image OCR processing (runs in thread pool).

        Args:
            file_path: Path to the image file

        Returns:
            dict with processing results
        """
        result = self.ocr_converter.convert(str(file_path))
        document = result.document

        # Extract OCR text
        plain_text = document.export_to_markdown(strict_text=True)
        markdown = document.export_to_markdown()
        metadata = self._extract_metadata(document)

        return {
            "success": True,
            "markdown": markdown,
            "plain_text": plain_text,
            "metadata": metadata,
            "error": None,
        }

    def _extract_metadata(self, doc: DoclingDocument) -> dict:
        """
        Extract metadata from DoclingDocument for RAG optimization.

        Extracts document structure, content analysis, and statistics that
        help with RAG retrieval and filtering.

        Args:
            doc: Processed DoclingDocument

        Returns:
            dict with metadata fields:
                - page_count (int): Number of pages
                - table_count (int): Number of tables
                - code_block_count (int): Number of code blocks
                - image_count (int): Number of images
                - has_code (bool): Contains code blocks
                - has_formulas (bool): Contains formulas
                - word_count (int): Total words
                - document_structure (dict): Sections, headings, TOC info
        """
        metadata = {}

        # Page count
        metadata["page_count"] = len(doc.pages) if hasattr(doc, "pages") else 1

        # Table count
        metadata["table_count"] = len(doc.tables) if hasattr(doc, "tables") else 0

        # Code block count and detection
        if hasattr(doc, "texts"):
            code_blocks = [item for item in doc.texts if hasattr(item, "label") and item.label == "CODE"]
            metadata["code_block_count"] = len(code_blocks)
            metadata["has_code"] = len(code_blocks) > 0

            # Formula detection
            formulas = [item for item in doc.texts if hasattr(item, "label") and item.label == "FORMULA"]
            metadata["has_formulas"] = len(formulas) > 0

            # Document structure
            sections = [item for item in doc.texts if hasattr(item, "label") and item.label == "SECTION_HEADER"]
            metadata["document_structure"] = {
                "section_count": len(sections),
                "has_toc": any(hasattr(item, "label") and item.label == "TOC" for item in doc.texts),
            }

            # Calculate max heading level if available
            heading_levels = [
                item.level for item in doc.texts if hasattr(item, "level") and hasattr(item, "label")
            ]
            if heading_levels:
                metadata["document_structure"]["max_heading_level"] = max(heading_levels)
        else:
            metadata["code_block_count"] = 0
            metadata["has_code"] = False
            metadata["has_formulas"] = False
            metadata["document_structure"] = {
                "section_count": 0,
                "has_toc": False,
            }

        # Image count
        metadata["image_count"] = len(doc.pictures) if hasattr(doc, "pictures") else 0

        # Word count
        plain_text = doc.export_to_markdown(strict_text=True)
        metadata["word_count"] = len(plain_text.split())

        return metadata

    def _is_document_format(self, file_path: Path) -> bool:
        """
        Check if file format is supported for document processing.

        Supported: PDF, DOCX, PPTX, XLSX

        Args:
            file_path: Path to the file

        Returns:
            True if format is supported
        """
        return file_path.suffix.lower() in self.SUPPORTED_DOCUMENT_FORMATS

    def _is_image_format(self, file_path: Path) -> bool:
        """
        Check if file format is supported for image OCR processing.

        Supported: PNG, JPG, JPEG, TIFF, WEBP

        Args:
            file_path: Path to the file

        Returns:
            True if format is supported
        """
        return file_path.suffix.lower() in self.SUPPORTED_IMAGE_FORMATS

    def _is_supported_format(self, file_path: Path) -> bool:
        """
        Check if file format is supported (documents or images).

        Args:
            file_path: Path to the file

        Returns:
            True if format is supported
        """
        return self._is_document_format(file_path) or self._is_image_format(file_path)

    def _supports_multimodal(self, model_choice: str) -> bool:
        """
        Check if MODEL_CHOICE supports vision/multimodal capabilities.

        This method detects whether the configured LLM model supports image
        processing. Used by ImageHandler (Story 2.3) to decide whether to
        use multimodal LLM or fall back to Docling OCR.

        Args:
            model_choice: The MODEL_CHOICE from RAG Settings

        Returns:
            True if model supports multimodal (vision) processing
        """
        model_lower = model_choice.lower()
        return any(model in model_lower for model in self.MULTIMODAL_MODELS)

    @asynccontextmanager
    async def download_and_cleanup(
        self, confluence_client: object, page_id: str, filename: str
    ):
        """
        Download attachment and automatically clean up temp files.

        Context manager that downloads a Confluence attachment to a temporary
        directory, yields the file path for processing, and ensures cleanup
        even if an exception occurs.

        Args:
            confluence_client: ConfluenceClient instance
            page_id: Confluence page ID containing the attachment
            filename: Attachment filename

        Yields:
            Path: Path to the downloaded temporary file

        Example:
            ```python
            async with processor.download_and_cleanup(client, "12345", "doc.pdf") as file_path:
                result = await processor.process_attachment(file_path)
            # Temp directory automatically cleaned up here
            ```
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="archon_confluence_"))
        temp_file = None

        try:
            # Download attachment
            attachment_data = await confluence_client.download_attachment(page_id, filename)

            # Write to temp file
            temp_file = temp_dir / filename
            temp_file.write_bytes(attachment_data)

            yield temp_file

        finally:
            # Clean up temp directory (even if exception occurred)
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
