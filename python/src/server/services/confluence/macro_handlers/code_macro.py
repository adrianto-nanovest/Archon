"""
Code Macro Handler for Confluence Storage Format.

Extracts language-tagged code blocks from Confluence code macros and converts them
to Markdown fenced code blocks while preserving all whitespace and indentation.
"""

from bs4 import NavigableString

from .base import BaseMacroHandler


class CodeMacroHandler(BaseMacroHandler):
    """
    Handler for Confluence code macros (<ac:structured-macro ac:name="code">).

    Converts Confluence code blocks to Markdown fenced code blocks with:
    - Language tag preservation (syntax highlighting)
    - Whitespace preservation (NO strip - critical for code correctness)
    - CDATA unwrapping (handles Confluence's XML structure)

    Example input:
        ```xml
        <ac:structured-macro ac:name="code">
            <ac:parameter ac:name="language">python</ac:parameter>
            <ac:plain-text-body><![CDATA[def hello():
    print("Hello World")]]></ac:plain-text-body>
        </ac:structured-macro>
        ```

    Example output:
        ```markdown
        ```python
        def hello():
            print("Hello World")
        ```
        ```
    """

    async def process(self, macro_tag, page_id, space_id=None):
        """
        Process a Confluence code macro and convert to Markdown fenced code block.

        Args:
            macro_tag: BeautifulSoup Tag for <ac:structured-macro ac:name="code">
            page_id: Confluence page ID (for logging context)
            space_id: Confluence space ID (unused for code macros)

        Modifies:
            Replaces macro_tag in-place with NavigableString containing Markdown code block
        """
        try:
            # Extract language parameter (default to empty string if missing)
            language_param = macro_tag.find("ac:parameter", {"ac:name": "language"})
            language = language_param.get_text() if language_param else ""

            # Extract code content from CDATA section
            code_body = macro_tag.find("ac:plain-text-body")

            if code_body:
                # CRITICAL: Use strip=False to preserve all whitespace
                # Code indentation and blank lines must be preserved for correctness
                code_content = code_body.get_text(strip=False)
            else:
                # Handle missing CDATA (empty code block)
                code_content = ""
                self.logger.debug(
                    f"Code macro on page {page_id} has no CDATA content (empty code block)"
                )

            # Build Markdown fenced code block
            # Format: ```{language}\n{code}\n```
            markdown_code = f"```{language}\n{code_content}\n```"

            # Replace macro tag in-place with Markdown code block
            macro_tag.replace_with(NavigableString(markdown_code))

            self.logger.debug(
                f"Processed code macro on page {page_id} "
                f"(language: {language or 'none'}, {len(code_content)} chars)"
            )

        except Exception as e:
            self.logger.error(
                f"Error processing code macro on page {page_id}: {e}", exc_info=True
            )
            # Graceful degradation: Replace with comment placeholder
            macro_tag.replace_with(
                NavigableString("<!-- Code macro processing failed -->")
            )
