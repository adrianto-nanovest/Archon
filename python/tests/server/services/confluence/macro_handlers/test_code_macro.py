"""
Unit tests for CodeMacroHandler.

Tests whitespace preservation, language tag handling, and edge cases.
"""

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.macro_handlers.code_macro import CodeMacroHandler


@pytest.fixture
def code_handler():
    """Create CodeMacroHandler instance for testing."""
    return CodeMacroHandler()


@pytest.mark.asyncio
async def test_python_code_block_with_whitespace_preservation(code_handler):
    """Test Python code block preserves whitespace and indentation."""
    html = """
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">python</ac:parameter>
        <ac:plain-text-body><![CDATA[def hello():
    print("Hello World")
    return True]]></ac:plain-text-body>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await code_handler.process(macro_tag, page_id="test-page")

    # Verify macro replaced with Markdown code block
    result = str(soup).strip()

    # Check language tag
    assert "```python" in result
    # Check indentation preserved (4 spaces)
    assert "    print(" in result
    assert "    return True" in result
    # Check closing fence
    assert "```" in result.split("python")[1]  # Closing ``` after language tag


@pytest.mark.asyncio
async def test_missing_language_parameter(code_handler):
    """Test code macro without language parameter defaults to empty string."""
    html = """
    <ac:structured-macro ac:name="code">
        <ac:plain-text-body><![CDATA[const x = 42;]]></ac:plain-text-body>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await code_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Should have empty language (```\n not ```language\n)
    assert result.startswith("```\n")
    assert "const x = 42;" in result
    assert result.endswith("```")


@pytest.mark.asyncio
async def test_empty_cdata(code_handler):
    """Test code macro with empty CDATA produces empty code block."""
    html = """
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">javascript</ac:parameter>
        <ac:plain-text-body></ac:plain-text-body>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await code_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Should have empty content between fences
    assert "```javascript\n\n```" in result


@pytest.mark.asyncio
async def test_multiline_code_with_indentation(code_handler):
    """Test multi-line code with various indentation levels."""
    html = """
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">python</ac:parameter>
        <ac:plain-text-body><![CDATA[class Example:
    def __init__(self):
        self.value = 42

    def method(self):
        if self.value > 0:
            return True
        return False]]></ac:plain-text-body>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await code_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify all indentation levels preserved
    assert "class Example:" in result
    assert "    def __init__(self):" in result  # 4 spaces
    assert "        self.value = 42" in result  # 8 spaces
    assert "            return True" in result  # 12 spaces


@pytest.mark.asyncio
async def test_missing_plain_text_body(code_handler):
    """Test code macro without <ac:plain-text-body> element."""
    html = """
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">java</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await code_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Should produce empty code block
    assert "```java\n\n```" in result


@pytest.mark.asyncio
async def test_code_with_special_characters(code_handler):
    """Test code containing special characters and symbols."""
    html = """
    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">bash</ac:parameter>
        <ac:plain-text-body><![CDATA[#!/bin/bash
echo "Hello & goodbye <test>"
grep -r "pattern.*" /path/to/files
exit 0]]></ac:plain-text-body>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await code_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify special characters preserved (HTML-escaped by BeautifulSoup)
    assert "#!/bin/bash" in result
    assert '"Hello &amp; goodbye &lt;test&gt;"' in result
    assert 'grep -r "pattern.*"' in result
