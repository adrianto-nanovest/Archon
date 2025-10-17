"""
Unit tests for BaseMacroHandler abstract class.

Tests verify that the base class enforces implementation of the process() method
and provides proper initialization with logging support.
"""

import pytest
from bs4 import BeautifulSoup, Tag
from src.server.services.confluence.macro_handlers.base import BaseMacroHandler


class ConcreteMacroHandler(BaseMacroHandler):
    """Concrete implementation for testing."""

    async def process(self, macro_tag: Tag, page_id: str, space_id: str = None) -> None:
        """Test implementation that does nothing."""
        pass


class IncompleteHandler(BaseMacroHandler):
    """Handler that doesn't implement process() - should fail."""

    pass


@pytest.mark.asyncio
class TestBaseMacroHandler:
    """Test suite for BaseMacroHandler abstract class."""

    async def test_abstract_class_cannot_be_instantiated(self):
        """Test that BaseMacroHandler cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseMacroHandler()

    async def test_incomplete_handler_raises_not_implemented_error(self):
        """Test that handler without process() implementation raises NotImplementedError."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteHandler()

    async def test_concrete_handler_can_be_instantiated(self):
        """Test that a properly implemented handler can be instantiated."""
        handler = ConcreteMacroHandler()
        assert handler is not None
        assert hasattr(handler, "logger")
        assert handler.logger.name == "ConcreteMacroHandler"

    async def test_handler_logger_initialization(self):
        """Test that handler initializes with correct logger name."""
        handler = ConcreteMacroHandler()
        assert handler.logger.name == "ConcreteMacroHandler"

    async def test_process_method_signature(self):
        """Test that process() method has correct signature."""
        handler = ConcreteMacroHandler()

        # Create a mock macro tag
        html = '<ac:structured-macro ac:name="code"></ac:structured-macro>'
        soup = BeautifulSoup(html, "html.parser")
        macro_tag = soup.find("ac:structured-macro")

        # Should not raise any errors
        await handler.process(macro_tag, "12345678")
        await handler.process(macro_tag, "12345678", "DEVDOCS")

    async def test_base_class_forces_implementation(self):
        """Test that base class enforces process() implementation."""

        class BadHandler(BaseMacroHandler):
            """Handler that calls super().process() - should fail."""

            async def process(
                self, macro_tag: Tag, page_id: str, space_id: str = None
            ) -> None:
                await super().process(macro_tag, page_id, space_id)

        handler = BadHandler()
        html = '<ac:structured-macro ac:name="test"></ac:structured-macro>'
        soup = BeautifulSoup(html, "html.parser")
        macro_tag = soup.find("ac:structured-macro")

        with pytest.raises(NotImplementedError, match="must implement process"):
            await handler.process(macro_tag, "12345678")
