"""
Unit tests for BaseElementHandler abstract class.

Tests verify that the base class enforces implementation of the process() method
and provides proper initialization with logging support for graceful degradation.
"""

import pytest
from bs4 import BeautifulSoup
from src.server.services.confluence.element_handlers.base import BaseElementHandler


class ConcreteElementHandler(BaseElementHandler):
    """Concrete implementation for testing."""

    def process(self, soup: BeautifulSoup, **kwargs) -> None:
        """Test implementation that does nothing."""
        pass


class GracefulDegradationHandler(BaseElementHandler):
    """Handler that demonstrates graceful degradation pattern."""

    def process(self, soup: BeautifulSoup, **kwargs) -> None:
        """Process with internal error handling."""
        try:
            # Simulate some processing that might fail
            elements = soup.find_all("test-element")
            for elem in elements:
                elem.replace_with(f"Processed: {elem.get_text()}")
        except Exception as e:
            self.logger.warning(f"Processing failed: {e}")
            # Graceful degradation: replace with placeholder
            for elem in soup.find_all("test-element"):
                elem.replace_with("[placeholder]")


class IncompleteHandler(BaseElementHandler):
    """Handler that doesn't implement process() - should fail."""

    pass


class TestBaseElementHandler:
    """Test suite for BaseElementHandler abstract class."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that BaseElementHandler cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseElementHandler()

    def test_incomplete_handler_raises_not_implemented_error(self):
        """Test that handler without process() implementation cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteHandler()

    def test_concrete_handler_can_be_instantiated(self):
        """Test that a properly implemented handler can be instantiated."""
        handler = ConcreteElementHandler()
        assert handler is not None
        assert hasattr(handler, "logger")
        assert handler.logger.name == "ConcreteElementHandler"

    def test_handler_logger_initialization(self):
        """Test that handler initializes with correct logger name."""
        handler = ConcreteElementHandler()
        assert handler.logger.name == "ConcreteElementHandler"

    def test_process_method_signature(self):
        """Test that process() method has correct signature and accepts kwargs."""
        handler = ConcreteElementHandler()
        html = "<html><body><p>Test</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        # Should not raise any errors
        handler.process(soup)
        handler.process(soup, space_id="DEVDOCS")
        handler.process(soup, space_id="DEVDOCS", confluence_client=None)

    def test_base_class_forces_implementation(self):
        """Test that base class enforces process() implementation."""

        class BadHandler(BaseElementHandler):
            """Handler that calls super().process() - should fail."""

            def process(self, soup: BeautifulSoup, **kwargs) -> None:
                super().process(soup, **kwargs)

        handler = BadHandler()
        html = "<html><body><p>Test</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        with pytest.raises(NotImplementedError, match="must implement process"):
            handler.process(soup)

    def test_graceful_degradation_pattern(self):
        """Test that handlers can implement graceful degradation."""
        handler = GracefulDegradationHandler()
        html = "<html><body><test-element>Content</test-element></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        # Should process successfully
        handler.process(soup)

        # Verify element was processed (either successfully or with placeholder)
        assert "test-element" not in str(soup)

    def test_handler_modifies_soup_in_place(self):
        """Test that handlers modify the soup object in-place."""

        class ModifyingHandler(BaseElementHandler):
            def process(self, soup: BeautifulSoup, **kwargs) -> None:
                for tag in soup.find_all("remove-me"):
                    tag.decompose()

        handler = ModifyingHandler()
        html = "<html><body><p>Keep</p><remove-me>Remove</remove-me></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        handler.process(soup)

        # Verify modification happened in-place
        assert "remove-me" not in str(soup)
        assert "Keep" in str(soup)
        assert "Remove" not in str(soup)
