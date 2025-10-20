"""
Complete unit tests for CodeMacroHandler including all edge cases from story.
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

    result = str(soup).strip()
    assert "```python" in result
    assert "    print(" in result
    assert "    return True" in result
    assert result.count("```") == 2


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
    assert "class Example:" in result
    assert "    def __init__(self):" in result
    assert "        self.value = 42" in result
    assert "            return True" in result


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
    assert "```java\n\n```" in result


@pytest.mark.asyncio
async def test_code_with_special_characters(code_handler):
    """Test code containing special characters (HTML-escaped by BeautifulSoup)."""
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
    assert "#!/bin/bash" in result
    # BeautifulSoup HTML-escapes these characters
    assert '"Hello &amp; goodbye &lt;test&gt;"' in result
    assert 'grep -r "pattern.*"' in result
