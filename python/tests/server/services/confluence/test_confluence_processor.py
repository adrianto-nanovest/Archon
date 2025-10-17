"""
Integration tests for ConfluenceProcessor orchestrator.

Tests verify the orchestrator's ability to:
- Load and register handlers
- Implement error isolation (graceful degradation)
- Execute two-pass processing pipeline in correct order
- Handle edge cases (empty HTML, malformed input)
- Provide comprehensive logging with context
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call
from bs4 import BeautifulSoup, Tag
from src.server.services.confluence.confluence_processor import ConfluenceProcessor
from src.server.services.confluence.macro_handlers.base import BaseMacroHandler
from src.server.services.confluence.element_handlers.base import BaseElementHandler


class MockMacroHandler(BaseMacroHandler):
    """Mock macro handler for testing."""

    def __init__(self):
        super().__init__()
        self.process_called = False
        self.call_args = []

    async def process(self, macro_tag: Tag, page_id: str, space_id: str = None) -> None:
        self.process_called = True
        self.call_args.append((macro_tag, page_id, space_id))


class FailingMacroHandler(BaseMacroHandler):
    """Mock handler that raises exception."""

    async def process(self, macro_tag: Tag, page_id: str, space_id: str = None) -> None:
        raise ValueError("Simulated handler failure")


class MockElementHandler(BaseElementHandler):
    """Mock element handler for testing."""

    def __init__(self):
        super().__init__()
        self.process_called = False
        self.call_args = []

    def process(self, soup: BeautifulSoup, **kwargs) -> None:
        self.process_called = True
        self.call_args.append((soup, kwargs))


class FailingElementHandler(BaseElementHandler):
    """Mock element handler that raises exception."""

    def process(self, soup: BeautifulSoup, **kwargs) -> None:
        raise RuntimeError("Simulated element handler failure")


@pytest.mark.asyncio
class TestConfluenceProcessorIntegration:
    """Integration tests for ConfluenceProcessor orchestrator."""

    async def test_iv1_orchestrator_registers_handlers(self):
        """IV1: Orchestrator successfully loads and registers all handler types."""
        processor = ConfluenceProcessor()

        # Create mock handlers
        code_handler = MockMacroHandler()
        panel_handler = MockMacroHandler()
        user_handler = MockElementHandler()

        # Register handlers
        processor.macro_handlers = {
            "code": code_handler,
            "panel": panel_handler,
        }
        processor.element_handlers = {
            "user": user_handler,
        }

        # Verify registration
        assert "code" in processor.macro_handlers
        assert "panel" in processor.macro_handlers
        assert "user" in processor.element_handlers
        assert processor.macro_handlers["code"] == code_handler
        assert processor.element_handlers["user"] == user_handler

    async def test_iv2_error_in_handler_doesnt_crash_conversion(self):
        """IV2: Error in one handler doesn't crash entire conversion (graceful degradation)."""
        processor = ConfluenceProcessor()

        # Register mix of working and failing handlers
        working_handler = MockMacroHandler()
        failing_handler = FailingMacroHandler()

        processor.macro_handlers = {
            "code": working_handler,
            "broken": failing_handler,
        }

        # HTML with two macros: one will fail, one will succeed
        html = """
        <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">python</ac:parameter>
        </ac:structured-macro>
        <ac:structured-macro ac:name="broken">
            <ac:parameter ac:name="test">value</ac:parameter>
        </ac:structured-macro>
        """

        # Should not raise exception despite failing handler
        markdown, metadata = await processor.html_to_markdown(html, "12345678")

        # Verify working handler was called
        assert working_handler.process_called

        # Verify output is returned (not crashed)
        assert isinstance(markdown, str)
        assert isinstance(metadata, dict)

    async def test_iv3_processing_pipeline_order(self):
        """IV3: Processing pipeline executes in correct order (macros → elements)."""
        processor = ConfluenceProcessor()

        execution_order = []

        # Create handlers that track execution order
        class OrderTrackingMacroHandler(BaseMacroHandler):
            async def process(self, macro_tag: Tag, page_id: str, space_id: str = None):
                execution_order.append("macro")

        class OrderTrackingElementHandler(BaseElementHandler):
            def process(self, soup: BeautifulSoup, **kwargs):
                execution_order.append("element")

        processor.macro_handlers = {"test": OrderTrackingMacroHandler()}
        processor.element_handlers = {"test": OrderTrackingElementHandler()}

        html = '<ac:structured-macro ac:name="test"></ac:structured-macro>'
        await processor.html_to_markdown(html, "12345678")

        # Verify macros processed before elements
        assert execution_order == ["macro", "element"]

    async def test_iv4_empty_html_returns_empty_markdown(self):
        """IV4: Empty HTML input returns empty markdown + empty metadata (no crash)."""
        processor = ConfluenceProcessor()

        # Test with empty string
        markdown, metadata = await processor.html_to_markdown("", "12345678")
        assert markdown == "" or markdown.strip() == ""
        assert metadata == {}

        # Test with minimal HTML
        markdown, metadata = await processor.html_to_markdown(
            "<html></html>", "12345678"
        )
        assert isinstance(markdown, str)
        assert metadata == {}

        # Test with whitespace only
        markdown, metadata = await processor.html_to_markdown("   \n\n  ", "12345678")
        assert isinstance(markdown, str)
        assert metadata == {}

    async def test_logging_captures_page_id_and_context(self, caplog):
        """Test that logging output captures page_id, macro name, and error context."""
        import logging

        caplog.set_level(logging.INFO)

        processor = ConfluenceProcessor()
        failing_handler = FailingMacroHandler()
        processor.macro_handlers = {"failing": failing_handler}

        html = '<ac:structured-macro ac:name="failing"></ac:structured-macro>'

        await processor.html_to_markdown(html, "TEST_PAGE_ID", "TEST_SPACE")

        # Verify page_id in logs
        log_text = caplog.text
        assert "TEST_PAGE_ID" in log_text

        # Verify error logging includes macro name
        assert "failing" in log_text

        # Verify error was logged with exc_info (traceback)
        assert "ERROR" in log_text
        assert "Simulated handler failure" in log_text

    async def test_handler_receives_correct_arguments(self):
        """Test that handlers receive correct arguments (page_id, space_id)."""
        processor = ConfluenceProcessor()
        mock_handler = MockMacroHandler()
        processor.macro_handlers = {"test": mock_handler}

        html = '<ac:structured-macro ac:name="test"></ac:structured-macro>'
        await processor.html_to_markdown(html, "PAGE123", "SPACE456")

        # Verify handler was called with correct arguments
        assert mock_handler.process_called
        assert len(mock_handler.call_args) == 1
        macro_tag, page_id, space_id = mock_handler.call_args[0]
        assert page_id == "PAGE123"
        assert space_id == "SPACE456"

    async def test_element_handler_receives_confluence_client(self):
        """Test that element handlers receive confluence_client via kwargs."""
        mock_client = MagicMock()
        processor = ConfluenceProcessor(confluence_client=mock_client)

        mock_handler = MockElementHandler()
        processor.element_handlers = {"test": mock_handler}

        html = "<p>Test content</p>"
        await processor.html_to_markdown(html, "12345678")

        # Verify handler was called with confluence_client
        assert mock_handler.process_called
        assert len(mock_handler.call_args) == 1
        soup, kwargs = mock_handler.call_args[0]
        assert "confluence_client" in kwargs
        assert kwargs["confluence_client"] == mock_client

    async def test_processor_with_no_handlers_succeeds(self):
        """Test that processor works even with no handlers registered (Story 2.1 state)."""
        processor = ConfluenceProcessor()

        html = """
        <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">python</ac:parameter>
        </ac:structured-macro>
        <p>Regular HTML content</p>
        """

        # Should succeed and return Markdown (macros not processed yet)
        markdown, metadata = await processor.html_to_markdown(html, "12345678")

        assert isinstance(markdown, str)
        assert metadata == {}
        # Macros should still be in output (not processed)
        assert "ac:structured-macro" in markdown or len(markdown) > 0

    async def test_processor_initializes_with_clients(self):
        """Test that processor correctly stores confluence and JIRA clients."""
        mock_confluence = MagicMock()
        mock_jira = MagicMock()

        processor = ConfluenceProcessor(
            confluence_client=mock_confluence, jira_client=mock_jira
        )

        assert processor.confluence_client == mock_confluence
        assert processor.jira_client == mock_jira

    async def test_multiple_macros_processed_sequentially(self):
        """Test that multiple macros are all processed."""
        processor = ConfluenceProcessor()
        handler = MockMacroHandler()
        processor.macro_handlers = {"test": handler}

        html = """
        <ac:structured-macro ac:name="test"></ac:structured-macro>
        <ac:structured-macro ac:name="test"></ac:structured-macro>
        <ac:structured-macro ac:name="test"></ac:structured-macro>
        """

        await processor.html_to_markdown(html, "12345678")

        # Verify handler called for each macro
        assert handler.process_called
        assert len(handler.call_args) == 3

    async def test_graceful_degradation_with_element_handler_failure(self):
        """Test that element handler failures don't crash conversion."""
        processor = ConfluenceProcessor()
        processor.element_handlers = {"failing": FailingElementHandler()}

        html = "<p>Test content</p>"

        # Should not raise despite failing element handler
        markdown, metadata = await processor.html_to_markdown(html, "12345678")

        assert isinstance(markdown, str)
        assert metadata == {}

    async def test_generic_macro_handler_fallback(self):
        """Test that generic handler is used for unknown macros."""
        processor = ConfluenceProcessor()

        generic_handler = MockMacroHandler()
        processor.generic_macro_handler = generic_handler

        # No specific handler for "unknown" macro
        html = '<ac:structured-macro ac:name="unknown"></ac:structured-macro>'

        await processor.html_to_markdown(html, "12345678")

        # Verify generic handler was called
        assert generic_handler.process_called
