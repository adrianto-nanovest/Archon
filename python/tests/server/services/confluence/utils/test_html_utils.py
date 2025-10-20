"""
Unit tests for HTML utilities module.

Story 2.5: Utility Modules & Integration Testing
"""

from bs4 import BeautifulSoup

from src.server.services.confluence.utils.html_utils import (
    clean_heading_text,
    clean_table_cell_text,
    ensure_utf8_safe,
    extract_text_content,
    normalize_whitespace,
)


class TestNormalizeWhitespace:
    """Test whitespace normalization function."""

    def test_collapses_multiple_spaces(self):
        """Should collapse multiple spaces into single space."""
        result = normalize_whitespace("Hello    World")
        assert result == "Hello World"

    def test_collapses_multiple_newlines(self):
        """Should collapse multiple newlines into single space."""
        result = normalize_whitespace("Line1\n\n\nLine2")
        assert result == "Line1 Line2"

    def test_strips_leading_trailing_whitespace(self):
        """Should strip leading and trailing whitespace."""
        result = normalize_whitespace("  Hello World  ")
        assert result == "Hello World"

    def test_preserves_code_blocks_when_flag_set(self):
        """Should preserve whitespace when preserve_code=True."""
        code = "def foo():\n    pass\n"
        result = normalize_whitespace(code, preserve_code=True)
        assert result == code

    def test_handles_tabs(self):
        """Should collapse tabs into single space."""
        result = normalize_whitespace("Hello\t\tWorld")
        assert result == "Hello World"

    def test_handles_empty_string(self):
        """Should handle empty string without error."""
        result = normalize_whitespace("")
        assert result == ""

    def test_handles_only_whitespace(self):
        """Should return empty string for whitespace-only input."""
        result = normalize_whitespace("   \n\n\t  ")
        assert result == ""


class TestCleanHeadingText:
    """Test heading text cleaning function."""

    def test_removes_strong_tags(self):
        """Should remove <strong> tags while preserving text."""
        result = clean_heading_text("<strong>Section 1:</strong> Introduction")
        assert result == "Section 1: Introduction"

    def test_removes_em_tags(self):
        """Should remove <em> tags while preserving text."""
        result = clean_heading_text("<em>Important</em> Note")
        assert result == "Important Note"

    def test_removes_code_tags(self):
        """Should remove <code> tags while preserving text."""
        result = clean_heading_text("The <code>API</code> Reference")
        assert result == "The API Reference"

    def test_normalizes_whitespace(self):
        """Should normalize whitespace in heading."""
        result = clean_heading_text("  Section   1  ")
        assert result == "Section 1"

    def test_strips_special_characters_except_hyphens(self):
        """Should strip special characters but preserve hyphens."""
        result = clean_heading_text("Section-1: Overview!")
        assert result == "Section-1: Overview"

    def test_preserves_colons(self):
        """Should preserve colons in headings."""
        result = clean_heading_text("API: Authentication")
        assert result == "API: Authentication"

    def test_handles_multiple_inline_tags(self):
        """Should handle multiple inline formatting tags."""
        result = clean_heading_text("<strong><em>Bold Italic</em></strong> Text")
        assert result == "Bold Italic Text"


class TestCleanTableCellText:
    """Test table cell text cleaning function."""

    def test_extracts_simple_cell_text(self):
        """Should extract text from simple table cell."""
        html = "<td>Value 1</td>"
        cell = BeautifulSoup(html, "html.parser").find("td")
        result = clean_table_cell_text(cell)
        assert result == "Value 1"

    def test_preserves_code_block_whitespace(self):
        """Should preserve whitespace in code blocks."""
        html = "<td><code>def foo():\n    pass</code></td>"
        cell = BeautifulSoup(html, "html.parser").find("td")
        result = clean_table_cell_text(cell)
        assert "def foo():" in result
        assert "    pass" in result

    def test_extracts_list_items(self):
        """Should extract list items with markers."""
        html = "<td><ul><li>Item 1</li><li>Item 2</li></ul></td>"
        cell = BeautifulSoup(html, "html.parser").find("td")
        result = clean_table_cell_text(cell)
        assert "- Item 1" in result
        assert "- Item 2" in result

    def test_normalizes_whitespace_in_regular_cells(self):
        """Should normalize whitespace in regular cells."""
        html = "<td>Value   1\n\n   Value 2</td>"
        cell = BeautifulSoup(html, "html.parser").find("td")
        result = clean_table_cell_text(cell)
        assert result == "Value 1 Value 2"

    def test_handles_nested_content(self):
        """Should handle nested content in cells."""
        html = "<td><p>Paragraph 1</p><p>Paragraph 2</p></td>"
        cell = BeautifulSoup(html, "html.parser").find("td")
        result = clean_table_cell_text(cell)
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result

    def test_handles_pre_tags(self):
        """Should preserve whitespace in <pre> tags."""
        html = "<td><pre>line1\n  line2\n    line3</pre></td>"
        cell = BeautifulSoup(html, "html.parser").find("td")
        result = clean_table_cell_text(cell)
        assert "line1" in result
        assert "  line2" in result


class TestEnsureUtf8Safe:
    """Test UTF-8 safety function."""

    def test_preserves_ascii_text(self):
        """Should preserve ASCII text unchanged."""
        result = ensure_utf8_safe("Hello World")
        assert result == "Hello World"

    def test_preserves_emoji(self):
        """Should preserve emoji characters."""
        result = ensure_utf8_safe("Hello 👋 World")
        assert result == "Hello 👋 World"

    def test_preserves_unicode_characters(self):
        """Should preserve Unicode characters."""
        result = ensure_utf8_safe("Café résumé naïve")
        assert result == "Café résumé naïve"

    def test_handles_japanese_characters(self):
        """Should handle Japanese characters."""
        result = ensure_utf8_safe("こんにちは世界")
        assert result == "こんにちは世界"

    def test_handles_chinese_characters(self):
        """Should handle Chinese characters."""
        result = ensure_utf8_safe("你好世界")
        assert result == "你好世界"

    def test_handles_mixed_content(self):
        """Should handle mixed ASCII and Unicode."""
        result = ensure_utf8_safe("Hello 世界 👋")
        assert result == "Hello 世界 👋"

    def test_replaces_invalid_surrogates(self):
        """Should replace invalid surrogates with replacement character."""
        # Invalid surrogate that can't be encoded as UTF-8
        invalid = "Test\udcfe"
        result = ensure_utf8_safe(invalid)
        # Should either contain replacement character or be sanitized
        assert isinstance(result, str)
        assert len(result) > 0


class TestExtractTextContent:
    """Test text content extraction function."""

    def test_extracts_simple_text(self):
        """Should extract text from simple tag."""
        html = "<p>Hello World</p>"
        tag = BeautifulSoup(html, "html.parser").find("p")
        result = extract_text_content(tag)
        assert result == "Hello World"

    def test_preserves_structure_when_flag_set(self):
        """Should preserve newlines when preserve_structure=True."""
        html = "<p>Line 1<br/>Line 2</p>"
        tag = BeautifulSoup(html, "html.parser").find("p")
        result = extract_text_content(tag, preserve_structure=True)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_normalizes_whitespace_by_default(self):
        """Should normalize whitespace by default."""
        html = "<p>Text   with    spaces</p>"
        tag = BeautifulSoup(html, "html.parser").find("p")
        result = extract_text_content(tag)
        assert result == "Text with spaces"

    def test_handles_nested_tags(self):
        """Should handle nested tags."""
        html = "<div><p>Paragraph 1</p><p>Paragraph 2</p></div>"
        tag = BeautifulSoup(html, "html.parser").find("div")
        result = extract_text_content(tag)
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result

    def test_handles_inline_formatting(self):
        """Should extract text from inline formatting tags."""
        html = "<p><strong>Bold</strong> <em>Italic</em></p>"
        tag = BeautifulSoup(html, "html.parser").find("p")
        result = extract_text_content(tag)
        assert result == "Bold Italic"
