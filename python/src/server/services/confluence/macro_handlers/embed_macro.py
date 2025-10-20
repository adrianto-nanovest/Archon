"""Embed Macro Handler for Confluence Storage Format."""

from bs4 import NavigableString

from .base import BaseMacroHandler


class EmbedMacroHandler(BaseMacroHandler):
    """Handler for Confluence iframe/embed macros."""

    def __init__(self, external_links_tracker=None):
        super().__init__()
        self.external_links_tracker = external_links_tracker if external_links_tracker is not None else []

    def _convert_embed_url(self, embed_url: str) -> str:
        """Convert embed URL to original URL."""
        # Simplified conversion - full implementation in integration
        return embed_url.replace("/embed/", "/watch?v=") if "youtube" in embed_url else embed_url

    async def process(self, macro_tag, page_id, space_id=None):
        try:
            url_tag = macro_tag.find("ri:url")
            embed_url = url_tag.get("ri:value") if url_tag else ""

            title_param = macro_tag.find("ac:parameter", {"ac:name": "title"})
            title = title_param.get_text() if title_param else "Embedded Content"

            converted_url = self._convert_embed_url(embed_url)

            self.external_links_tracker.append({"title": title, "url": converted_url})

            markdown_link = f"[{title}]({converted_url})"
            macro_tag.replace_with(NavigableString(markdown_link))

        except Exception as e:
            self.logger.error(f"Error processing embed macro on page {page_id}: {e}")
            macro_tag.replace_with(NavigableString("<!-- Embed macro processing failed -->"))
