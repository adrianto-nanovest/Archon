"""
Confluence Cloud API integration and HTML processing services.

This module provides the complete Confluence integration stack:

1. **API Client** (`ConfluenceClient`):
   - Wrapper for Confluence Cloud REST API v2
   - Authentication, rate limiting, error handling
   - Uses atlassian-python-api SDK

2. **HTML Processor** (`ConfluenceProcessor`):
   - Converts Confluence Storage Format HTML to RAG-optimized Markdown
   - Two-pass pipeline: macro expansion → element conversion
   - Error isolation with graceful degradation

3. **Handler Base Classes**:
   - `BaseMacroHandler`: Extend to create custom macro handlers
   - `BaseElementHandler`: Extend to create custom element handlers

Example usage:
    ```python
    from server.services.confluence import (
        ConfluenceClient,
        ConfluenceProcessor,
        BaseMacroHandler,
    )

    # Initialize client and processor
    client = ConfluenceClient(base_url, email, token)
    processor = ConfluenceProcessor(confluence_client=client)

    # Fetch and convert page content
    html = client.get_page_content(page_id="12345678")
    markdown, metadata = await processor.html_to_markdown(
        html=html,
        page_id="12345678",
        space_id="DEVDOCS"
    )

    # Create custom macro handler (Story 2.2+)
    class CustomMacroHandler(BaseMacroHandler):
        async def process(self, macro_tag, page_id, space_id=None):
            # Custom processing logic
            pass
    ```
"""

from .confluence_client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceNotFoundError,
    ConfluenceRateLimitError,
)
from .confluence_processor import ConfluenceProcessor
from .element_handlers.base import BaseElementHandler
from .macro_handlers.base import BaseMacroHandler

__all__ = [
    # API Client
    "ConfluenceClient",
    "ConfluenceAuthError",
    "ConfluenceRateLimitError",
    "ConfluenceNotFoundError",
    # HTML Processor
    "ConfluenceProcessor",
    # Handler Base Classes
    "BaseMacroHandler",
    "BaseElementHandler",
]
