"""Generic Macro Handler for unknown Confluence macros."""

import markdownify

# BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
# but it's available at runtime via bs4/__init__.py import from bs4.element.
# See: https://github.com/python/typeshed/issues/4968
from bs4 import NavigableString  # type: ignore[attr-defined]

from .base import BaseMacroHandler


class GenericMacroHandler(BaseMacroHandler):
    """Fallback handler for unknown macro types."""

    async def process(self, macro_tag, page_id: str, space_id: str | None = None) -> None:
        try:
            macro_name = macro_tag.get("ac:name", "unknown")

            # Extract parameters
            params = {}
            for param in macro_tag.find_all("ac:parameter"):
                param_name = param.get("ac:name")
                param_value = param.get_text()
                if param_name:
                    params[param_name] = param_value

            param_str = " ".join(f'{k}="{v}"' for k, v in params.items())

            # Try to extract rich text content
            rich_text_body = macro_tag.find("ac:rich-text-body")

            if rich_text_body:
                content = markdownify.markdownify(str(rich_text_body), heading_style="atx").strip()
                markdown = (
                    f"<!-- Unsupported Confluence Macro: {macro_name} {param_str} -->\n\n"
                    f"**{macro_name} Macro Content:**\n\n{content}\n"
                )
            else:
                markdown = f"<!-- Unsupported Confluence Macro: {macro_name} {param_str} -->"

            macro_tag.replace_with(NavigableString(markdown))

            self.logger.debug(f"Processed unknown macro '{macro_name}' on page {page_id}")

        except Exception as e:
            self.logger.error(f"Error in generic macro handler on page {page_id}: {e}")
            macro_tag.replace_with(NavigableString("<!-- Macro processing failed -->"))
