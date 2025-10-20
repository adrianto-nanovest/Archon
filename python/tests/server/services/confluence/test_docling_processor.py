"""
Comprehensive unit tests for DoclingProcessor service.

Tests cover all 11 Integration Verification (IV) items from Story 2.6:
- IV1: Format detection for 9 supported extensions
- IV2: File size limits enforced
- IV3: Image processing defaults to multimodal mode
- IV4: Multimodal capability check
- IV5: Docling OCR triggered for non-multimodal models
- IV6: Manual override via image_processing_mode
- IV7: Graceful fallback on processing failure
- IV8: Timeout enforced
- IV9: Temp files cleaned up
- IV10: Metadata extraction returns correct schema
- IV11: Concurrent processing limited by semaphore
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.server.services.confluence.docling_processor import DoclingProcessor


@pytest.fixture
def docling_processor():
    """Create DoclingProcessor instance with default settings."""
    return DoclingProcessor(
        docling_enabled=True,
        max_file_size_mb=50,
        timeout_seconds=60,
        max_concurrent=2,
        image_processing_mode="multimodal",
    )


@pytest.fixture
def mock_docling_document():
    """Create mock DoclingDocument with typical structure."""
    doc = MagicMock()
    doc.pages = [MagicMock(), MagicMock(), MagicMock()]  # 3 pages
    doc.tables = [MagicMock(), MagicMock()]  # 2 tables
    doc.pictures = [MagicMock()]  # 1 image

    # Mock text items with labels and levels
    # Create Mock objects with only required attributes (not MagicMock)
    section1 = Mock(spec=["label", "text", "level"])
    section1.label = "SECTION_HEADER"
    section1.text = "Introduction"
    section1.level = 1

    section2 = Mock(spec=["label", "text", "level"])
    section2.label = "SECTION_HEADER"
    section2.text = "Methods"
    section2.level = 2

    code1 = Mock(spec=["label", "text"])
    code1.label = "CODE"
    code1.text = "def foo(): pass"

    code2 = Mock(spec=["label", "text"])
    code2.label = "CODE"
    code2.text = "class Bar: pass"

    formula = Mock(spec=["label", "text"])
    formula.label = "FORMULA"
    formula.text = "x = y + z"

    text = Mock(spec=["label", "text"])
    text.label = "TEXT"
    text.text = "This is a paragraph"

    toc = Mock(spec=["label", "text"])
    toc.label = "TOC"
    toc.text = "Table of Contents"

    doc.texts = [code1, code2, formula, section1, section2, text, toc]

    # Mock export methods
    doc.export_to_markdown = Mock(
        side_effect=lambda strict_text=False: (
            "Document Title Content here" if strict_text else "# Document Title\n\nContent here"
        )
    )

    return doc


class TestFormatDetection:
    """Tests for IV1: Format detection for 9 supported extensions."""

    def test_document_formats_supported(self, docling_processor):
        """Test PDF, DOCX, PPTX, XLSX formats are detected as documents."""
        assert docling_processor._is_document_format(Path("test.pdf"))
        assert docling_processor._is_document_format(Path("test.docx"))
        assert docling_processor._is_document_format(Path("test.pptx"))
        assert docling_processor._is_document_format(Path("test.xlsx"))

        # Case insensitive
        assert docling_processor._is_document_format(Path("test.PDF"))
        assert docling_processor._is_document_format(Path("test.DocX"))

    def test_image_formats_supported(self, docling_processor):
        """Test PNG, JPG, JPEG, TIFF, WEBP formats are detected as images."""
        assert docling_processor._is_image_format(Path("test.png"))
        assert docling_processor._is_image_format(Path("test.jpg"))
        assert docling_processor._is_image_format(Path("test.jpeg"))
        assert docling_processor._is_image_format(Path("test.tiff"))
        assert docling_processor._is_image_format(Path("test.webp"))

        # Case insensitive
        assert docling_processor._is_image_format(Path("test.PNG"))
        assert docling_processor._is_image_format(Path("test.JpG"))

    def test_unsupported_formats_rejected(self, docling_processor):
        """Test unsupported formats return False."""
        assert not docling_processor._is_document_format(Path("test.doc"))
        assert not docling_processor._is_document_format(Path("test.txt"))
        assert not docling_processor._is_image_format(Path("test.gif"))
        assert not docling_processor._is_image_format(Path("test.bmp"))
        assert not docling_processor._is_supported_format(Path("test.zip"))

    def test_all_nine_extensions_supported(self, docling_processor):
        """Test all 9 supported extensions (4 documents + 5 images)."""
        documents = ["test.pdf", "test.docx", "test.pptx", "test.xlsx"]
        images = ["test.png", "test.jpg", "test.jpeg", "test.tiff", "test.webp"]

        for doc in documents:
            assert docling_processor._is_supported_format(Path(doc))

        for img in images:
            assert docling_processor._is_supported_format(Path(img))

        # Total 9 extensions
        assert len(documents) + len(images) == 9


class TestFileSizeLimits:
    """Tests for IV2: File size limits enforced."""

    @pytest.mark.asyncio
    async def test_file_size_under_limit_processes(self, docling_processor, tmp_path):
        """Test files under 50MB are processed."""
        # Create 45MB file
        test_file = tmp_path / "small.pdf"
        test_file.write_bytes(b"x" * (45 * 1024 * 1024))

        with patch.object(docling_processor, "_process_document_async", new=AsyncMock()) as mock_process:
            mock_process.return_value = {
                "success": True,
                "markdown": "test",
                "plain_text": "test",
                "metadata": {},
                "error": None,
            }

            result = await docling_processor.process_attachment(test_file)

            assert result["success"] is True
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_size_over_limit_rejected(self, docling_processor, tmp_path):
        """Test files over 50MB are rejected with warning."""
        # Create 55MB file
        test_file = tmp_path / "large.pdf"
        test_file.write_bytes(b"x" * (55 * 1024 * 1024))

        result = await docling_processor.process_attachment(test_file)

        assert result["success"] is False
        assert "too large" in result["error"].lower()
        assert "55" in result["error"]  # File size mentioned

    @pytest.mark.asyncio
    async def test_file_size_warning_logged(self, docling_processor, tmp_path, caplog):
        """Test oversized files log warning with filename and size."""
        test_file = tmp_path / "oversized.pdf"
        test_file.write_bytes(b"x" * (60 * 1024 * 1024))

        await docling_processor.process_attachment(test_file, page_id="12345")

        # Check warning was logged
        assert any("Skipping" in record.message for record in caplog.records)
        assert any("oversized.pdf" in record.message for record in caplog.records)


class TestImageProcessingMode:
    """Tests for IV3: Image processing defaults to multimodal mode."""

    def test_default_image_processing_mode(self):
        """Test image_processing_mode defaults to 'multimodal'."""
        processor = DoclingProcessor()
        assert processor.image_processing_mode == "multimodal"

    def test_image_processing_mode_configurable(self):
        """Test image_processing_mode can be configured."""
        processor = DoclingProcessor(image_processing_mode="docling_ocr")
        assert processor.image_processing_mode == "docling_ocr"

        processor = DoclingProcessor(image_processing_mode="none")
        assert processor.image_processing_mode == "none"


class TestMultimodalCapabilityDetection:
    """Tests for IV4: Multimodal capability check."""

    def test_gpt4o_detected_as_multimodal(self, docling_processor):
        """Test GPT-4o models support multimodal."""
        assert docling_processor._supports_multimodal("gpt-4o")
        assert docling_processor._supports_multimodal("gpt-4o-preview")
        assert docling_processor._supports_multimodal("gpt-4-vision")
        assert docling_processor._supports_multimodal("gpt-4-turbo")

    def test_claude_detected_as_multimodal(self, docling_processor):
        """Test Claude 3 models support multimodal."""
        assert docling_processor._supports_multimodal("claude-3-opus")
        assert docling_processor._supports_multimodal("claude-3-sonnet")
        assert docling_processor._supports_multimodal("claude-3-haiku")
        assert docling_processor._supports_multimodal("claude-3.5-sonnet")

    def test_gemini_detected_as_multimodal(self, docling_processor):
        """Test Gemini models support multimodal."""
        assert docling_processor._supports_multimodal("gemini-pro-vision")
        assert docling_processor._supports_multimodal("gemini-1.5-pro")
        assert docling_processor._supports_multimodal("gemini-2.0-flash")

    def test_non_multimodal_models_rejected(self, docling_processor):
        """Test non-vision models return False."""
        assert not docling_processor._supports_multimodal("gpt-3.5-turbo")
        assert not docling_processor._supports_multimodal("llama-3")
        assert not docling_processor._supports_multimodal("mistral-7b")

    def test_case_insensitive_detection(self, docling_processor):
        """Test multimodal detection is case-insensitive."""
        assert docling_processor._supports_multimodal("GPT-4O")
        assert docling_processor._supports_multimodal("Claude-3-Opus")
        assert docling_processor._supports_multimodal("GEMINI-PRO-VISION")


class TestDoclingOCRFallback:
    """Tests for IV5: Docling OCR triggered for non-multimodal models."""

    @pytest.mark.asyncio
    async def test_ocr_method_available(self, docling_processor, tmp_path):
        """Test process_image_ocr() method exists and is callable."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake image data")

        with patch.object(docling_processor, "_process_image_ocr_async", new=AsyncMock()) as mock_ocr:
            mock_ocr.return_value = {
                "success": True,
                "markdown": "OCR text",
                "plain_text": "OCR text",
                "metadata": {},
                "error": None,
            }

            result = await docling_processor.process_image_ocr(test_file)

            assert result["success"] is True
            assert result["metadata"]["ocr_enabled"] is True
            mock_ocr.assert_called_once()


class TestManualOCROverride:
    """Tests for IV6: Manual override via image_processing_mode='docling_ocr'."""

    def test_manual_ocr_mode_set(self):
        """Test image_processing_mode can be set to 'docling_ocr'."""
        processor = DoclingProcessor(image_processing_mode="docling_ocr")
        assert processor.image_processing_mode == "docling_ocr"

    def test_ocr_available_regardless_of_model(self, docling_processor):
        """Test OCR method available even if model supports multimodal."""
        # Story 2.6 only implements method, not decision logic
        # Decision logic (when to use OCR) is in ImageHandler (Story 2.3)
        assert hasattr(docling_processor, "process_image_ocr")
        assert callable(docling_processor.process_image_ocr)


class TestGracefulErrorHandling:
    """Tests for IV7: Graceful fallback on processing failure."""

    @pytest.mark.asyncio
    async def test_docling_exception_caught(self, docling_processor, tmp_path):
        """Test Docling exceptions are caught and returned as error dict."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf")

        with patch.object(docling_processor, "_process_document_async", new=AsyncMock()) as mock_process:
            mock_process.side_effect = Exception("Docling internal error")

            result = await docling_processor.process_attachment(test_file)

            assert result["success"] is False
            assert "Docling internal error" in result["error"]
            assert result["markdown"] == ""
            assert result["plain_text"] == ""

    @pytest.mark.asyncio
    async def test_no_exception_raised_to_caller(self, docling_processor, tmp_path):
        """Test exceptions don't propagate to caller."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf")

        with patch.object(docling_processor, "_process_document_async", new=AsyncMock()) as mock_process:
            mock_process.side_effect = RuntimeError("Critical error")

            # Should not raise exception
            result = await docling_processor.process_attachment(test_file)

            assert result["success"] is False
            assert result["error"] is not None


class TestTimeoutEnforcement:
    """Tests for IV8: Timeout enforced."""

    @pytest.mark.asyncio
    async def test_timeout_after_60_seconds(self, tmp_path):
        """Test processing times out after configured timeout_seconds."""
        processor = DoclingProcessor(timeout_seconds=1)  # 1 second timeout
        test_file = tmp_path / "slow.pdf"
        test_file.write_bytes(b"fake pdf")

        async def slow_process(file_path):
            await asyncio.sleep(5)  # Simulate slow processing
            return {"success": True}

        with patch.object(processor, "_process_document_async", new=slow_process):
            result = await processor.process_attachment(test_file)

            assert result["success"] is False
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_fast_processing_completes(self, tmp_path):
        """Test processing under timeout limit succeeds."""
        processor = DoclingProcessor(timeout_seconds=60)
        test_file = tmp_path / "fast.pdf"
        test_file.write_bytes(b"fake pdf")

        async def fast_process(file_path):
            await asyncio.sleep(0.1)  # Fast processing
            return {
                "success": True,
                "markdown": "test",
                "plain_text": "test",
                "metadata": {},
                "error": None,
            }

        with patch.object(processor, "_process_document_async", new=fast_process):
            result = await processor.process_attachment(test_file)

            assert result["success"] is True


class TestTempFileCleanup:
    """Tests for IV9: Temp files cleaned up."""

    @pytest.mark.asyncio
    async def test_temp_directory_created_and_removed(self, docling_processor):
        """Test temp directory is created and cleaned up after processing."""
        mock_client = MagicMock()
        mock_client.download_attachment = AsyncMock(return_value=b"fake file data")

        temp_dirs_created = []

        original_mkdtemp = tempfile.mkdtemp

        def track_mkdtemp(*args, **kwargs):
            temp_dir = original_mkdtemp(*args, **kwargs)
            temp_dirs_created.append(temp_dir)
            return temp_dir

        with patch("tempfile.mkdtemp", side_effect=track_mkdtemp):
            async with docling_processor.download_and_cleanup(
                mock_client, "12345", "test.pdf"
            ) as file_path:
                assert file_path.exists()
                assert file_path.name == "test.pdf"
                temp_dir = file_path.parent

            # After context manager exits, temp directory should be removed
            assert not Path(temp_dir).exists()

    @pytest.mark.asyncio
    async def test_cleanup_happens_on_exception(self, docling_processor):
        """Test temp directory cleaned up even if exception occurs."""
        mock_client = MagicMock()
        mock_client.download_attachment = AsyncMock(return_value=b"fake file data")

        temp_dir_path = None

        try:
            async with docling_processor.download_and_cleanup(
                mock_client, "12345", "test.pdf"
            ) as file_path:
                temp_dir_path = file_path.parent
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Temp directory should still be cleaned up
        assert temp_dir_path is not None
        assert not Path(temp_dir_path).exists()


class TestMetadataExtraction:
    """Tests for IV10: Metadata extraction returns correct schema."""

    def test_metadata_contains_required_fields(self, docling_processor, mock_docling_document):
        """Test metadata contains all 6+ required fields."""
        metadata = docling_processor._extract_metadata(mock_docling_document)

        # Required fields
        assert "page_count" in metadata
        assert "table_count" in metadata
        assert "code_block_count" in metadata
        assert "image_count" in metadata
        assert "has_code" in metadata
        assert "has_formulas" in metadata
        assert "document_structure" in metadata
        assert "word_count" in metadata

        # At least 8 fields
        assert len(metadata) >= 8

    def test_metadata_page_count_correct(self, docling_processor, mock_docling_document):
        """Test page_count extracted correctly (3 pages)."""
        metadata = docling_processor._extract_metadata(mock_docling_document)
        assert metadata["page_count"] == 3

    def test_metadata_table_count_correct(self, docling_processor, mock_docling_document):
        """Test table_count extracted correctly (2 tables)."""
        metadata = docling_processor._extract_metadata(mock_docling_document)
        assert metadata["table_count"] == 2

    def test_metadata_code_detection(self, docling_processor, mock_docling_document):
        """Test code blocks detected (2 CODE items)."""
        metadata = docling_processor._extract_metadata(mock_docling_document)
        assert metadata["code_block_count"] == 2
        assert metadata["has_code"] is True

    def test_metadata_formula_detection(self, docling_processor, mock_docling_document):
        """Test formulas detected (1 FORMULA item)."""
        metadata = docling_processor._extract_metadata(mock_docling_document)
        assert metadata["has_formulas"] is True

    def test_metadata_document_structure(self, docling_processor, mock_docling_document):
        """Test document structure extracted (sections, TOC)."""
        metadata = docling_processor._extract_metadata(mock_docling_document)

        assert "document_structure" in metadata
        structure = metadata["document_structure"]

        assert structure["section_count"] == 2  # 2 SECTION_HEADER items
        assert structure["has_toc"] is True  # TOC item present

    def test_metadata_no_code_no_formulas(self, docling_processor):
        """Test has_code and has_formulas are False when absent."""
        doc = MagicMock()
        doc.pages = [MagicMock()]
        doc.tables = []
        doc.pictures = []
        doc.texts = [MagicMock(label="TEXT", text="Plain text")]
        doc.export_to_markdown = Mock(return_value="Plain text")

        metadata = docling_processor._extract_metadata(doc)

        assert metadata["code_block_count"] == 0
        assert metadata["has_code"] is False
        assert metadata["has_formulas"] is False


class TestConcurrencyLimiting:
    """Tests for IV11: Concurrent processing limited by semaphore."""

    @pytest.mark.asyncio
    async def test_max_concurrent_processes(self, tmp_path):
        """Test only 2 processes run concurrently (semaphore limit)."""
        processor = DoclingProcessor(max_concurrent=2, timeout_seconds=60)

        # Track concurrent execution count
        concurrent_count = 0
        max_concurrent = 0

        async def tracked_process(file_path):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.2)  # Simulate processing time
            concurrent_count -= 1
            return {
                "success": True,
                "markdown": "test",
                "plain_text": "test",
                "metadata": {},
                "error": None,
            }

        # Create 10 test files
        files = []
        for i in range(10):
            test_file = tmp_path / f"test{i}.pdf"
            test_file.write_bytes(b"fake pdf")
            files.append(test_file)

        with patch.object(processor, "_process_document_async", side_effect=tracked_process):
            # Process all files concurrently
            tasks = [processor.process_attachment(f) for f in files]
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(r["success"] for r in results)

            # Max concurrent should not exceed 2
            assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_semaphore_queues_excess_calls(self, tmp_path):
        """Test calls queue up when semaphore is exhausted."""
        processor = DoclingProcessor(max_concurrent=1, timeout_seconds=60)

        call_times = []

        async def timed_process(file_path):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)
            return {
                "success": True,
                "markdown": "test",
                "plain_text": "test",
                "metadata": {},
                "error": None,
            }

        files = [tmp_path / f"test{i}.pdf" for i in range(3)]
        for f in files:
            f.write_bytes(b"fake pdf")

        with patch.object(processor, "_process_document_async", side_effect=timed_process):
            tasks = [processor.process_attachment(f) for f in files]
            await asyncio.gather(*tasks)

            # With max_concurrent=1, calls should be sequential (time gaps between calls)
            assert len(call_times) == 3
            # Check calls weren't all simultaneous (some delay between them)
            time_diffs = [call_times[i + 1] - call_times[i] for i in range(len(call_times) - 1)]
            assert any(diff > 0.05 for diff in time_diffs)  # At least some delay


class TestMemoryErrorHandling:
    """Additional test for MemoryError handling."""

    @pytest.mark.asyncio
    async def test_memory_error_caught(self, docling_processor, tmp_path):
        """Test MemoryError is caught and logged with exc_info."""
        test_file = tmp_path / "huge.pdf"
        test_file.write_bytes(b"fake pdf")

        with patch.object(docling_processor, "_process_document_async", new=AsyncMock()) as mock_process:
            mock_process.side_effect = MemoryError("Out of memory")

            result = await docling_processor.process_attachment(test_file)

            assert result["success"] is False
            assert "memory exhausted" in result["error"].lower()
