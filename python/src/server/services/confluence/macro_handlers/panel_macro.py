"""
Panel Macro Handler for Confluence Storage Format.

Converts Confluence panel macros (info, note, warning, tip, panel) to Markdown
blockquotes with emoji prefixes for visual distinction.
"""

import markdownify
from bs4 import NavigableString

from .base import BaseMacroHandler


class PanelMacroHandler(BaseMacroHandler):
    """
    Handler for Confluence panel macros.

    Supported panel types:
    - info: ℹ️ Information panel (blue in Confluence)
    - tip: ✅ Success/tip panel (green in Confluence)
    - warning: ⚠️ Warning panel (yellow in Confluence)
    - note: ❌ Note/error panel (red in Confluence)
    - panel: Generic panel (no emoji prefix)

    Converts panels to Markdown blockquotes with emoji prefixes on first line.

    Example input:
        ```xml
        <ac:structured-macro ac:name="info">
            <ac:rich-text-body>
                <p>This is an <strong>important</strong> note.</p>
            </ac:rich-text-body>
        </ac:structured-macro>
        ```

    Example output:
        ```markdown
        > ℹ️ This is an **important** note.
        ```
    """

    # Emoji mapping for panel types
    PANEL_EMOJI_MAP = {
        "info": "ℹ️",
        "tip": "✅",
        "warning": "⚠️",
        "note": "❌",
        "panel": "",  # Generic panel - no emoji
    }

    async def process(self, macro_tag, page_id, space_id=None):
        """
        Process a Confluence panel macro and convert to Markdown blockquote.

        Args:
            macro_tag: BeautifulSoup Tag for <ac:structured-macro ac:name="panel/info/note/...">
            page_id: Confluence page ID (for logging context)
            space_id: Confluence space ID (unused for panels)

        Modifies:
            Replaces macro_tag in-place with NavigableString containing Markdown blockquote
        """
        try:
            # Extract panel type from macro name
            panel_type = macro_tag.get("ac:name", "panel")

            # Get emoji prefix for this panel type
            emoji_prefix = self.PANEL_EMOJI_MAP.get(panel_type, "")

            # Extract rich text body
            rich_text_body = macro_tag.find("ac:rich-text-body")

            if rich_text_body:
                # Convert rich text HTML to Markdown
                # markdownify preserves formatting (bold, italic, links)
                content_html = str(rich_text_body)
                content_markdown = markdownify.markdownify(
                    content_html, heading_style="atx", escape_underscores=False
                ).strip()
            else:
                # Empty panel
                content_markdown = ""
                self.logger.debug(
                    f"Panel macro ({panel_type}) on page {page_id} has no content"
                )

            # Build blockquote with emoji prefix
            if content_markdown:
                # Split content by newlines and prefix each line with "> "
                lines = content_markdown.split("\n")

                # Add emoji to first line if emoji exists
                if emoji_prefix:
                    lines[0] = f"{emoji_prefix} {lines[0]}"

                # Prefix all lines with blockquote marker
                blockquote_lines = [f"> {line}" for line in lines]
                markdown_blockquote = "\n".join(blockquote_lines)
            else:
                # Empty panel with emoji only
                if emoji_prefix:
                    markdown_blockquote = f"> {emoji_prefix}"
                else:
                    markdown_blockquote = ">"

            # Replace macro tag in-place with Markdown blockquote
            macro_tag.replace_with(NavigableString(markdown_blockquote))

            self.logger.debug(
                f"Processed {panel_type} panel on page {page_id} "
                f"({len(content_markdown)} chars → {len(markdown_blockquote)} chars)"
            )

        except Exception as e:
            self.logger.error(
                f"Error processing panel macro on page {page_id}: {e}", exc_info=True
            )
            # Graceful degradation: Replace with comment placeholder
            panel_type = macro_tag.get("ac:name", "panel")
            macro_tag.replace_with(
                NavigableString(f"<!-- {panel_type.capitalize()} panel processing failed -->")
            )
