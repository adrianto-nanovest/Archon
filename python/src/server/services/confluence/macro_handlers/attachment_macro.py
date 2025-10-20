"""
Attachment Macro Handler with Docling Integration.

Processes PDF/Office attachments with full-text extraction via Docling.
"""

import tempfile
from pathlib import Path

from bs4 import NavigableString

from .base import BaseMacroHandler


class AttachmentMacroHandler(BaseMacroHandler):
    """Handler for Confluence attachment (view-file) macros."""

    DOCLING_SUPPORTED_FORMATS = {".pdf", ".docx", ".pptx", ".xlsx"}

    def __init__(self, confluence_client, docling_processor, asset_links_tracker=None, settings=None):
        super().__init__()
        self.confluence_client = confluence_client
        self.docling_processor = docling_processor
        self.asset_links_tracker = asset_links_tracker if asset_links_tracker is not None else []
        self.settings = settings

    def _get_file_icon(self, filename: str) -> str:
        """Map file extension to emoji icon."""
        ext = Path(filename).suffix.lower()
        icon_map = {
            '.pdf': '📄', '.doc': '📝', '.docx': '📝',
            '.xls': '📊', '.xlsx': '📊', '.ppt': '📊', '.pptx': '📊',
            '.txt': '📄', '.md': '📄', '.json': '📄', '.xml': '📄',
            '.zip': '📦', '.rar': '📦', '.tar': '📦', '.gz': '📦'
        }
        return icon_map.get(ext, '📎')

    def _is_docling_supported(self, filename: str) -> bool:
        """Check if file format is supported by Docling."""
        ext = Path(filename).suffix.lower()
        return ext in self.DOCLING_SUPPORTED_FORMATS

    async def _process_attachment_with_docling(self, page_id, filename):
        """
        Process attachment with Docling for full-text extraction.

        Returns:
            dict: {"success": bool, "markdown": str, "metadata": dict, "error": str | None}
        """
        temp_file = None
        try:
            # Create temp file for download
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as f:
                temp_file = Path(f.name)

            # Download attachment from Confluence
            await self.confluence_client.download_attachment(page_id, filename, str(temp_file))

            # Check file size limit
            file_size_mb = temp_file.stat().st_size / (1024 * 1024)
            if self.settings and hasattr(self.settings, 'docling_max_file_size_mb'):
                max_size = self.settings.docling_max_file_size_mb
                if file_size_mb > max_size:
                    self.logger.warning(
                        f"Skipping {filename}: file size {file_size_mb:.2f}MB exceeds limit {max_size}MB"
                    )
                    return {
                        "success": False,
                        "markdown": "",
                        "metadata": {},
                        "error": f"File too large ({file_size_mb:.2f}MB)"
                    }

            # Process with Docling
            result = await self.docling_processor.process_attachment(temp_file, page_id)
            return result

        except Exception as e:
            self.logger.error(f"Docling processing failed for {filename} on page {page_id}: {e}", exc_info=True)
            return {"success": False, "markdown": "", "metadata": {}, "error": str(e)}

        finally:
            # Clean up temp file
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temp file {temp_file}: {e}")

    async def process(self, macro_tag, page_id, space_id=None):
        """
        Process attachment macro.

        Args:
            macro_tag: BeautifulSoup Tag for <ac:structured-macro ac:name="view-file">
            page_id: Confluence page ID
            space_id: Confluence space ID (unused)
        """
        try:
            # Extract filename from ri:attachment tag
            attachment_tag = macro_tag.find("ri:attachment")
            filename = attachment_tag.get("ri:filename") if attachment_tag else "unknown_file"

            # Add to asset_links metadata tracker
            self.asset_links_tracker.append({
                "filename": filename,
                "file_type": Path(filename).suffix.lower().lstrip('.'),
                "processed": False
            })

            # Get file icon
            icon = self._get_file_icon(filename)

            # Check if Docling processing should be attempted
            docling_enabled = self.settings and getattr(self.settings, 'docling_enabled', False)

            if (docling_enabled and
                self._is_docling_supported(filename) and
                page_id):

                # Attempt Docling processing
                result = await self._process_attachment_with_docling(page_id, filename)

                if result["success"]:
                    # Update metadata with Docling results
                    self.asset_links_tracker[-1].update({
                        "processed": True,
                        "page_count": result["metadata"].get("page_count"),
                        "table_count": result["metadata"].get("table_count"),
                        "word_count": result["metadata"].get("word_count")
                    })

                    # Embed full-text content
                    markdown = f"\n\n<!-- ATTACHMENT: {filename} -->\n{result['markdown']}\n"
                    macro_tag.replace_with(NavigableString(markdown))
                    return
                else:
                    # Graceful fallback to file link
                    self.logger.warning(
                        f"Docling processing failed for {filename}, falling back to file link"
                    )

            # Fallback: File link markdown
            markdown_link = f"[{icon} {filename}](ATTACHMENT_PLACEHOLDER_{filename})"
            macro_tag.replace_with(NavigableString(markdown_link))

            self.logger.debug(f"Processed attachment macro on page {page_id}: {filename}")

        except Exception as e:
            self.logger.error(f"Error processing attachment macro on page {page_id}: {e}", exc_info=True)
            macro_tag.replace_with(NavigableString("<!-- Attachment macro processing failed -->"))
