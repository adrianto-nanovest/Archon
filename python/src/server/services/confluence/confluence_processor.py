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
        self,
        confluence_client: object | None = None,
        jira_client: object | None = None,
        docling_processor: object | None = None,
        settings: object | None = None,
    ):
        """
        Initialize processor with optional Confluence/JIRA clients.

        Args:
            confluence_client: Used for bulk API calls (user/page resolution)
            jira_client: Optional, used for JQL query execution in JIRA macros
            docling_processor: Optional, used for PDF/Office attachment processing
            settings: Optional, configuration settings for feature flags
        """
        self.confluence_client = confluence_client
        self.jira_client = jira_client
        self.docling_processor = docling_processor
        self.settings = settings
        self.logger = logging.getLogger("ConfluenceProcessor")

        # Initialize shared metadata trackers for deduplication
        self.jira_links_tracker = []
        self.asset_links_tracker = []
        self.external_links_tracker = []
        self.internal_links_tracker = []
        self.user_mentions_tracker = []

        # Import macro handlers
        from .macro_handlers.attachment_macro import AttachmentMacroHandler
        from .macro_handlers.code_macro import CodeMacroHandler
        from .macro_handlers.embed_macro import EmbedMacroHandler
        from .macro_handlers.generic_macro import GenericMacroHandler
        from .macro_handlers.jira_macro import JiraMacroHandler
        from .macro_handlers.panel_macro import PanelMacroHandler

        # Instantiate handlers with dependency injection
        code_handler = CodeMacroHandler()
        panel_handler = PanelMacroHandler()
        jira_handler = JiraMacroHandler(
            jira_client=self.jira_client, jira_links_tracker=self.jira_links_tracker
        )
        attachment_handler = AttachmentMacroHandler(
            confluence_client=self.confluence_client,
            docling_processor=self.docling_processor,
            asset_links_tracker=self.asset_links_tracker,
            settings=self.settings,
        )
        embed_handler = EmbedMacroHandler(
            external_links_tracker=self.external_links_tracker
        )
        generic_handler = GenericMacroHandler()

        # Register handlers in macro_handlers dictionary
        self.macro_handlers: dict[str, object] = {
            "code": code_handler,
            "panel": panel_handler,
            "info": panel_handler,  # Same handler for all panel types
            "note": panel_handler,
            "warning": panel_handler,
            "tip": panel_handler,
            "jira": jira_handler,
            "view-file": attachment_handler,
            "iframe": embed_handler,
        }

        # Set generic fallback handler for unknown macros
        self.generic_macro_handler = generic_handler

        # Import element handlers (Story 2.3)
        from .element_handlers.image_handler import ImageHandler
        from .element_handlers.link_handler import LinkHandler
        from .element_handlers.simple_elements import SimpleElementsHandler
        from .element_handlers.user_handler import UserHandler

        # Instantiate element handlers with dependency injection (Story 2.3)
        link_handler = LinkHandler(
            confluence_client=self.confluence_client,
            internal_links_tracker=self.internal_links_tracker,
            external_links_tracker=self.external_links_tracker,
            jira_links_tracker=self.jira_links_tracker,  # For JIRA deduplication (Tier 2)
        )
        user_handler = UserHandler(
            confluence_client=self.confluence_client,
            user_mentions_tracker=self.user_mentions_tracker,
        )
        image_handler = ImageHandler(
            confluence_client=self.confluence_client,
            docling_processor=self.docling_processor,
            asset_links_tracker=self.asset_links_tracker,
            settings=self.settings,
            model_choice=getattr(self.settings, "model_choice", None) if self.settings else None,
        )
        simple_elements_handler = SimpleElementsHandler()

        # Register element handlers in processing order (list, not dict)
        self.element_handlers = [
            link_handler,
            user_handler,
            image_handler,
            simple_elements_handler,
        ]

        # Import table processor and metadata extractor (Story 2.4)
        from .table_processor import TableProcessor
        from .metadata_extractor import MetadataExtractor

        # Instantiate table processor and metadata extractor (Story 2.4)
        self.table_processor = TableProcessor()
        self.metadata_extractor = MetadataExtractor()

        self.logger.info(
            f"ConfluenceProcessor initialized with {len(self.macro_handlers)} macro handlers and {len(self.element_handlers)} element handlers"
        )

    async def html_to_markdown(
        self, html: str, page_id: str, space_id: str | None = None
    ) -> tuple[str, dict]:
        """
        Convert Confluence HTML to RAG-optimized Markdown.

        Implements a three-pass processing pipeline:
        1. Pass 1: Process Confluence macros (macro expansion)
        2. Pass 2: Process special HTML elements (user mentions, links, images)
        3. Pass 3: Process tables (hierarchical markdown conversion)
        4. Pass 4: Convert to Markdown using markdownify
        5. Pass 5: Extract metadata (JIRA, users, links, assets, content metrics)

        Args:
            html: Confluence Storage Format HTML
            page_id: Confluence page ID (for logging context)
            space_id: Confluence space ID (for page link resolution)

        Returns:
            Tuple of (markdown_content, metadata_dict)
            - markdown_content: RAG-optimized Markdown string
            - metadata_dict: Extracted metadata with JIRA links, user mentions, etc.

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
            await self._process_special_elements(soup, page_id, space_id)

            # Pass 3: Process tables (Story 2.4)
            await self._process_tables(soup)

            # Pass 4: Convert to Markdown
            markdown_content = markdownify.markdownify(
                str(soup), heading_style="atx", escape_underscores=False
            )

            # Pass 5: Extract metadata (Story 2.4)
            metadata = self.metadata_extractor.extract_metadata(
                jira_links_tracker=self.jira_links_tracker,
                user_mentions_tracker=self.user_mentions_tracker,
                internal_links_tracker=self.internal_links_tracker,
                external_links_tracker=self.external_links_tracker,
                asset_links_tracker=self.asset_links_tracker,
                markdown_content=markdown_content,
            )

            self.logger.info(
                f"Completed conversion for page {page_id} "
                f"(output: {len(markdown_content)} characters, "
                f"metadata: {len(metadata.get('jira_issue_links', []))} JIRA links, "
                f"{len(metadata.get('user_mentions', []))} user mentions, "
                f"{len(metadata.get('asset_links', []))} assets)"
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
        self, soup: BeautifulSoup, page_id: str, space_id: str | None = None
    ) -> None:
        """
        Process special HTML elements in the document (Pass 2).

        Calls registered element handlers in sequence. Each handler is wrapped
        in try-except for graceful degradation. Handlers process elements like
        user mentions, page links, images, emoticons, etc.

        Args:
            soup: BeautifulSoup object (modified in-place)
            page_id: Confluence page ID (for logging context and image downloads)
            space_id: Confluence space ID (optional, for link resolution)

        Note:
            Element handlers are processed in order: links, users, images, simple elements.
        """
        if not self.element_handlers:
            self.logger.debug("No element handlers registered")
            return

        self.logger.debug(
            f"Processing special elements with {len(self.element_handlers)} handlers"
        )

        handlers_processed = 0
        handlers_failed = 0

        for handler in self.element_handlers:
            handler_name = handler.__class__.__name__
            try:
                self.logger.debug(f"Running {handler_name} element handler")
                await handler.process(
                    soup, page_id=page_id, space_id=space_id, confluence_client=self.confluence_client
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

    async def _process_tables(self, soup: BeautifulSoup) -> None:
        """
        Process tables into hierarchical markdown format (Pass 3).

        Finds all <table> elements and converts them to hierarchical markdown using
        ## Row → ### Column structure. Each table is wrapped in try-except for error
        isolation.

        Args:
            soup: BeautifulSoup object (modified in-place)

        Note:
            Story 2.4: Tables are converted to hierarchical format optimized for RAG.
            Standard markdown tables have critical limitations for Confluence content.
        """
        # Find all table elements
        tables = soup.find_all("table")

        if not tables:
            self.logger.debug("No tables found in document")
            return

        self.logger.info(f"Processing {len(tables)} tables")

        tables_processed = 0
        tables_failed = 0

        for table in tables:
            try:
                # Convert table to hierarchical markdown
                hierarchical_markdown = self.table_processor.process_table(table, soup)

                # Replace table element with hierarchical markdown
                # BeautifulSoup4 doesn't explicitly export NavigableString in type stubs,
                # but it's available at runtime via bs4/__init__.py import from bs4.element.
                # See: https://github.com/python/typeshed/issues/4968
                from bs4 import NavigableString  # type: ignore[attr-defined]

                table.replace_with(NavigableString(hierarchical_markdown))

                tables_processed += 1

            except Exception as e:
                tables_failed += 1
                self.logger.error(f"Error processing table: {e}", exc_info=True)
                # Continue processing other tables (error isolation)

        self.logger.info(
            f"Table processing complete: "
            f"{tables_processed} processed, {tables_failed} failed"
        )
