"""
Main orchestrator for Confluence Storage Format HTML → Markdown conversion.

This module provides the ConfluenceProcessor class that coordinates macro and element handlers
to convert Confluence HTML into RAG-optimized Markdown. The processor implements a two-pass
pipeline: macro expansion followed by HTML element conversion.
"""

import logging

import markdownify
from bs4 import BeautifulSoup


class ConfluenceProcessor:
    """
    Main orchestrator for Confluence Storage Format HTML → Markdown conversion.

    Optimized for RAG retrieval:
    - Preserves semantic structure (hierarchical tables, code blocks)
    - Extracts metadata for filtered search (JIRA links, users, pages)
    - Skips UI-only elements (TOC, inline comments)

    The processor implements a two-pass processing pipeline:
    1. Macro expansion: Converts Confluence macros (<ac:structured-macro>) to Markdown
    2. Element conversion: Processes special HTML elements (users, links, images)

    Error isolation ensures that failures in individual handlers don't crash the
    entire conversion process. Each handler is wrapped in try-except blocks with
    comprehensive logging.

    Example usage:
        ```python
        from confluence_client import ConfluenceClient

        client = ConfluenceClient(base_url, email, token)
        processor = ConfluenceProcessor(confluence_client=client)

        html = client.get_page_content(page_id)
        markdown, metadata = await processor.html_to_markdown(
            html=html,
            page_id=page_id,
            space_id="DEVDOCS"
        )
        ```
    """

    def __init__(
        self, confluence_client: object | None = None, jira_client: object | None = None
    ):
        """
        Initialize processor with optional Confluence/JIRA clients.

        Args:
            confluence_client: Used for bulk API calls (user/page resolution)
                             Story 2.3 will use this for element handlers
            jira_client: Optional, used for JQL query execution in JIRA macros
                        Story 2.2 will use this for JIRA macro handler
        """
        self.confluence_client = confluence_client
        self.jira_client = jira_client
        self.logger = logging.getLogger("ConfluenceProcessor")

        # Handler registries (will be populated by future stories)
        # Story 2.2 will register macro handlers here
        self.macro_handlers: dict[str, object] = {}
        # Story 2.3 will register element handlers here
        self.element_handlers: dict[str, object] = {}
        # Story 2.2 will set this for unknown macros
        self.generic_macro_handler: object | None = None

        self.logger.info("ConfluenceProcessor initialized")

    async def html_to_markdown(
        self, html: str, page_id: str, space_id: str | None = None
    ) -> tuple[str, dict]:
        """
        Convert Confluence HTML to RAG-optimized Markdown.

        Implements a two-pass processing pipeline:
        1. Pass 1: Process Confluence macros (macro expansion)
        2. Pass 2: Process special HTML elements (user mentions, links, images)
        3. Pass 3: Convert to Markdown using markdownify
        4. Pass 4: Extract metadata (future Story 2.4)

        Args:
            html: Confluence Storage Format HTML
            page_id: Confluence page ID (for logging context)
            space_id: Confluence space ID (for page link resolution)

        Returns:
            Tuple of (markdown_content, metadata_dict)
            - markdown_content: RAG-optimized Markdown string
            - metadata_dict: Extracted metadata (empty dict for Story 2.1)

        Raises:
            Exception: Only if fatal error prevents processing
                      (e.g., invalid HTML structure). Individual handler
                      failures are logged but don't raise.
        """
        self.logger.info(f"Starting HTML→Markdown conversion for page {page_id}")

        try:
            # Parse HTML with lenient html.parser (handles malformed HTML)
            soup = BeautifulSoup(html, "html.parser")

            # Pass 1: Process Confluence macros
            await self._process_macros(soup, page_id, space_id)

            # Pass 2: Process special HTML elements
            await self._process_special_elements(soup, space_id)

            # Pass 3: Convert to Markdown
            # Future stories will add table processing before this step
            markdown_content = markdownify.markdownify(
                str(soup), heading_style="atx", escape_underscores=False
            )

            # Pass 4: Extract metadata (future Story 2.4)
            metadata = {}

            self.logger.info(
                f"Completed conversion for page {page_id} "
                f"(output: {len(markdown_content)} characters)"
            )

            return markdown_content, metadata

        except Exception as e:
            self.logger.error(
                f"Fatal error processing page {page_id}: {e}", exc_info=True
            )
            raise

    async def _process_macros(
        self, soup: BeautifulSoup, page_id: str, space_id: str | None = None
    ) -> None:
        """
        Process Confluence macros in the HTML document (Pass 1).

        Finds all <ac:structured-macro> tags and delegates to registered handlers.
        Each handler is wrapped in try-except for error isolation. Unknown macros
        are passed to generic fallback handler.

        Args:
            soup: BeautifulSoup object (modified in-place)
            page_id: Confluence page ID (for logging context)
            space_id: Confluence space ID (optional)

        Note:
            Story 2.2 will populate self.macro_handlers with concrete implementations.
            For Story 2.1, this method logs but performs no actual transformations.
        """
        # Find all Confluence macro tags
        macro_tags = soup.find_all("ac:structured-macro")

        if not macro_tags:
            self.logger.debug(f"No macros found on page {page_id}")
            return

        self.logger.info(f"Processing {len(macro_tags)} macros for page {page_id}")

        macros_processed = 0
        macros_failed = 0

        for macro_tag in macro_tags:
            macro_name = macro_tag.get("ac:name", "unknown")

            try:
                # Look up handler for this macro type
                handler = self.macro_handlers.get(macro_name)

                if handler:
                    # Registered handler found
                    self.logger.debug(
                        f"Processing {macro_name} macro on page {page_id}"
                    )
                    await handler.process(macro_tag, page_id, space_id)
                    macros_processed += 1
                elif self.generic_macro_handler:
                    # Use generic fallback for unknown macros
                    self.logger.debug(
                        f"Using generic handler for {macro_name} macro on page {page_id}"
                    )
                    await self.generic_macro_handler.process(
                        macro_tag, page_id, space_id
                    )
                    macros_processed += 1
                else:
                    # No handler available (Story 2.1 state)
                    self.logger.debug(
                        f"No handler registered for {macro_name} macro (will be added in Story 2.2)"
                    )

            except Exception as e:
                macros_failed += 1
                self.logger.error(
                    f"Error processing {macro_name} macro on page {page_id}: {e}",
                    exc_info=True,
                )
                # Continue processing other macros (error isolation)

        self.logger.info(
            f"Macro processing complete for page {page_id}: "
            f"{macros_processed} processed, {macros_failed} failed"
        )

    async def _process_special_elements(
        self, soup: BeautifulSoup, space_id: str | None = None
    ) -> None:
        """
        Process special HTML elements in the document (Pass 2).

        Calls registered element handlers in sequence. Each handler is wrapped
        in try-except for graceful degradation. Handlers process elements like
        user mentions, page links, images, emoticons, etc.

        Args:
            soup: BeautifulSoup object (modified in-place)
            space_id: Confluence space ID (optional, for link resolution)

        Note:
            Story 2.3 will populate self.element_handlers with concrete implementations.
            For Story 2.1, this method logs but performs no actual transformations.
        """
        if not self.element_handlers:
            self.logger.debug(
                "No element handlers registered (will be added in Story 2.3)"
            )
            return

        self.logger.debug(
            f"Processing special elements with {len(self.element_handlers)} handlers"
        )

        handlers_processed = 0
        handlers_failed = 0

        for handler_name, handler in self.element_handlers.items():
            try:
                self.logger.debug(f"Running {handler_name} element handler")
                handler.process(
                    soup, space_id=space_id, confluence_client=self.confluence_client
                )
                handlers_processed += 1

            except Exception as e:
                handlers_failed += 1
                self.logger.error(
                    f"Error in {handler_name} element handler: {e}", exc_info=True
                )
                # Continue with other handlers (graceful degradation)

        self.logger.debug(
            f"Element processing complete: "
            f"{handlers_processed} handlers succeeded, {handlers_failed} failed"
        )
