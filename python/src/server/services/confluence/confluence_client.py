"""Confluence Cloud API client wrapper.

This module provides a wrapper around the atlassian-python-api SDK for interacting
with Confluence Cloud REST API v2. It handles authentication, rate limiting,
and provides methods for CQL queries and page retrieval.

Example CQL queries:
    - Recent changes: 'space = DEVDOCS AND lastModified >= "2025-10-01 10:00"'
    - By label: 'space = DEVDOCS AND label = "api-docs"'
    - By type: 'space = DEVDOCS AND type = page'

Example expand parameters:
    - Full content: 'body.storage,version,ancestors'
    - Metadata only: 'version,space'
    - Minimal: None (IDs only)
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from atlassian import Confluence

T = TypeVar("T")

logger = logging.getLogger(__name__)


class ConfluenceAuthError(Exception):
    """Raised when authentication with Confluence fails (HTTP 401)."""

    pass


class ConfluenceRateLimitError(Exception):
    """Raised when Confluence rate limit is exceeded (HTTP 429)."""

    pass


class ConfluenceNotFoundError(Exception):
    """Raised when a requested Confluence resource is not found (HTTP 404)."""

    pass


class ConfluenceClient:
    """Client for interacting with Confluence Cloud REST API v2.

    This client wraps the atlassian-python-api SDK and provides:
    - Token-based authentication for Confluence Cloud
    - CQL query support for incremental syncs
    - Page retrieval with configurable metadata expansion
    - Exponential backoff retry logic for rate limits
    - Custom exception handling for common error scenarios

    Args:
        base_url: Confluence Cloud URL (e.g., 'https://company.atlassian.net/wiki')
        api_token: Atlassian API token for authentication
        email: Email associated with the API token (required for Cloud)

    Example:
        >>> client = ConfluenceClient(
        ...     base_url='https://mycompany.atlassian.net/wiki',
        ...     api_token='ATATT3xFfGF0...',
        ...     email='user@company.com'
        ... )
        >>> pages = await client.cql_search(
        ...     cql='space = DEV AND lastModified >= "2025-10-01"',
        ...     expand='body.storage,version'
        ... )
    """

    def __init__(self, base_url: str, api_token: str, email: str):
        """Initialize Confluence client with authentication credentials.

        Args:
            base_url: Confluence Cloud URL
            api_token: Atlassian API token
            email: Email associated with the API token
        """
        self.base_url = base_url
        self.email = email
        self._client = Confluence(url=base_url, username=email, password=api_token, cloud=True)
        logger.debug("ConfluenceClient initialized", extra={"base_url": base_url, "email": email})

    async def cql_search(self, cql: str, expand: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
        """Search for pages using Confluence Query Language (CQL).

        CQL allows filtering by space, lastModified date, labels, and more.
        This method handles pagination automatically up to the specified limit.

        Args:
            cql: CQL query string (e.g., 'space = DEV AND lastModified >= "2025-10-01"')
            expand: Comma-separated list of fields to expand (e.g., 'body.storage,version,ancestors')
            limit: Maximum number of results to return (default: 1000)

        Returns:
            List of page dictionaries with requested expanded fields

        Raises:
            ConfluenceAuthError: If authentication fails (401)
            ConfluenceRateLimitError: If rate limit exceeded after retries (429)
            ConfluenceNotFoundError: If space or resource not found (404)

        Example:
            >>> pages = await client.cql_search(
            ...     cql='space = DEVDOCS AND lastModified >= "2025-10-01 10:00"',
            ...     expand='body.storage,version,ancestors',
            ...     limit=500
            ... )
        """
        logger.debug("CQL search", extra={"cql": cql, "expand": expand, "limit": limit})

        async def _search() -> list[dict[str, Any]]:
            try:
                # atlassian-python-api's cql method is synchronous, run in executor
                results = await asyncio.to_thread(self._client.cql, cql=cql, expand=expand, limit=limit)
                pages: list[dict[str, Any]] = results.get("results", [])
                logger.debug("CQL search succeeded", extra={"cql": cql, "page_count": len(pages)})
                return pages
            except Exception as e:
                self._handle_api_error(e, operation="cql_search", context={"cql": cql, "expand": expand})
                raise  # For type checker - _handle_api_error always raises

        return await self._retry_with_backoff(_search)

    async def get_page_by_id(self, page_id: str, expand: str | None = None) -> dict[str, Any]:
        """Retrieve a single page by its ID with optional metadata expansion.

        Args:
            page_id: Confluence page ID
            expand: Comma-separated list of fields to expand (e.g., 'body.storage,version,ancestors')

        Returns:
            Page dictionary with full metadata

        Raises:
            ConfluenceAuthError: If authentication fails (401)
            ConfluenceRateLimitError: If rate limit exceeded after retries (429)
            ConfluenceNotFoundError: If page does not exist (404)

        Example:
            >>> page = await client.get_page_by_id(
            ...     page_id='123456789',
            ...     expand='body.storage,version'
            ... )
        """
        logger.debug("Get page by ID", extra={"page_id": page_id, "expand": expand})

        async def _get_page() -> dict[str, Any]:
            try:
                page: dict[str, Any] = await asyncio.to_thread(self._client.get_page_by_id, page_id=page_id, expand=expand)
                logger.debug("Get page by ID succeeded", extra={"page_id": page_id})
                return page
            except Exception as e:
                self._handle_api_error(e, operation="get_page_by_id", context={"page_id": page_id, "expand": expand})
                raise  # For type checker - _handle_api_error always raises

        return await self._retry_with_backoff(_get_page)

    async def get_space_pages_ids(self, space_key: str) -> list[str]:
        """Get list of all page IDs in a space (lightweight, for deletion detection).

        This method fetches only page IDs without content or metadata to minimize
        API overhead. Useful for deletion detection by comparing with local database.

        Args:
            space_key: Confluence space key (e.g., 'DEVDOCS')

        Returns:
            List of page ID strings

        Raises:
            ConfluenceAuthError: If authentication fails (401)
            ConfluenceRateLimitError: If rate limit exceeded after retries (429)
            ConfluenceNotFoundError: If space not found (404)

        Example:
            >>> page_ids = await client.get_space_pages_ids('DEVDOCS')
            >>> # Returns: ['123456', '789012', ...]
        """
        logger.debug("Get space page IDs", extra={"space_key": space_key})

        async def _get_page_ids() -> list[str]:
            try:
                # Fetch all pages with no expansion (lightweight)
                pages: list[dict[str, Any]] = await asyncio.to_thread(
                    self._client.get_all_pages_from_space, space=space_key, expand=None, status=None, limit=1000
                )
                page_ids = [str(page["id"]) for page in pages if "id" in page]
                logger.debug("Get space page IDs succeeded", extra={"space_key": space_key, "count": len(page_ids)})
                return page_ids
            except Exception as e:
                self._handle_api_error(e, operation="get_space_pages_ids", context={"space_key": space_key})
                raise  # For type checker - _handle_api_error always raises

        return await self._retry_with_backoff(_get_page_ids)

    async def _retry_with_backoff(self, func: Callable[[], Awaitable[T]], max_retries: int = 3) -> T:
        """Retry a function with exponential backoff on rate limit errors.

        Implements exponential backoff with delays: 1s, 2s, 4s for max 3 retries.
        Only retries on ConfluenceRateLimitError (HTTP 429).

        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Result from successful function call

        Raises:
            ConfluenceRateLimitError: If max retries exceeded
            Other exceptions: Propagated immediately without retry
        """
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except ConfluenceRateLimitError:
                if attempt >= max_retries:
                    logger.error(
                        "Max retries exceeded for rate limit",
                        extra={"attempt": attempt + 1, "max_retries": max_retries},
                        exc_info=True,
                    )
                    raise

                delay = 2**attempt  # 1s, 2s, 4s
                logger.warning(
                    "Rate limit hit, retrying",
                    extra={"attempt": attempt + 1, "delay_seconds": delay, "max_retries": max_retries},
                )
                await asyncio.sleep(delay)

        # This line should never be reached due to the raise in the except block
        raise RuntimeError("Unexpected end of retry loop")

    def _handle_api_error(self, error: Exception, operation: str, context: dict[str, Any]) -> None:
        """Map API errors to custom exceptions with detailed context.

        Args:
            error: Original exception from API call
            operation: Name of the operation that failed
            context: Additional context for debugging (CQL query, page_id, etc.)

        Raises:
            ConfluenceAuthError: For 401 authentication errors
            ConfluenceRateLimitError: For 429 rate limit errors
            ConfluenceNotFoundError: For 404 not found errors
            Exception: Re-raises original error if not a recognized status code
        """
        error_msg = str(error)
        error_context = {
            "operation": operation,
            "base_url": self.base_url,
            "error": error_msg,
            **context,
        }

        # Check for HTTP status codes in error message
        if "401" in error_msg or "Unauthorized" in error_msg:
            logger.error("Confluence authentication failed", extra=error_context, exc_info=True)
            raise ConfluenceAuthError(f"Authentication failed for {self.base_url}: {error_msg}") from error

        if "429" in error_msg or "rate limit" in error_msg.lower():
            logger.warning("Confluence rate limit hit", extra=error_context, exc_info=True)
            raise ConfluenceRateLimitError(f"Rate limit exceeded for {self.base_url}: {error_msg}") from error

        if "404" in error_msg or "Not Found" in error_msg:
            logger.error("Confluence resource not found", extra=error_context, exc_info=True)
            raise ConfluenceNotFoundError(f"Resource not found: {error_msg}") from error

        # Unknown error - log and re-raise original error
        logger.error("Confluence API error", extra=error_context, exc_info=True)
        raise error
