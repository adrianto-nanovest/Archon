"""Embed Macro Handler for Confluence Storage Format."""

# BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
# but it's available at runtime via bs4/__init__.py import from bs4.element.
# See: https://github.com/python/typeshed/issues/4968
from bs4 import NavigableString  # type: ignore[attr-defined]

from ..utils.url_converter import convert_embed_url
from .base import BaseMacroHandler


class EmbedMacroHandler(BaseMacroHandler):
    """Handler for Confluence iframe/embed macros."""

    def __init__(self, external_links_tracker: list | None = None) -> None:
        super().__init__()
        self.external_links_tracker = external_links_tracker if external_links_tracker is not None else []

    async def process(self, macro_tag, page_id: str, space_id: str | None = None) -> None:
        try:
            url_tag = macro_tag.find("ri:url")
            embed_url = url_tag.get("ri:value") if url_tag else ""

            title_param = macro_tag.find("ac:parameter", {"ac:name": "title"})
            title = title_param.get_text() if title_param else "Embedded Content"

            converted_url = convert_embed_url(embed_url)

            self.external_links_tracker.append({"title": title, "url": converted_url})

            markdown_link = f"[{title}]({converted_url})"
            macro_tag.replace_with(NavigableString(markdown_link))

        except Exception as e:
            self.logger.error(f"Error processing embed macro on page {page_id}: {e}")
            macro_tag.replace_with(NavigableString("<!-- Embed macro processing failed -->"))
