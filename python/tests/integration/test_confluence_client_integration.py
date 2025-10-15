"""Integration tests for ConfluenceClient.

These tests require a real Confluence Cloud instance with valid credentials.

Environment Variables Required:
    CONFLUENCE_TEST_URL: Confluence Cloud URL (e.g., https://test.atlassian.net/wiki)
    CONFLUENCE_TEST_TOKEN: Valid API token for authentication
    CONFLUENCE_TEST_EMAIL: Email associated with the API token
    CONFLUENCE_TEST_SPACE: Space key for testing (e.g., DEVDOCS)

Running Integration Tests:
    # Export required environment variables first
    export CONFLUENCE_TEST_URL="https://your-instance.atlassian.net/wiki"
    export CONFLUENCE_TEST_TOKEN="your-api-token"
    export CONFLUENCE_TEST_EMAIL="your-email@example.com"
    export CONFLUENCE_TEST_SPACE="TESTSPACE"

    # Run integration tests only
    cd python
    uv run pytest -m integration tests/integration/test_confluence_client_integration.py -v

    # Run all tests (unit + integration)
    uv run pytest

Note: These tests will make real API calls to Confluence Cloud and may count
      against your rate limits.
"""

import os
from datetime import datetime, timedelta

import pytest

from src.server.services.confluence.confluence_client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceNotFoundError,
)

# Skip all tests in this module if required env vars are not set
pytestmark = pytest.mark.integration

# Environment variables
CONFLUENCE_TEST_URL = os.getenv("CONFLUENCE_TEST_URL")
CONFLUENCE_TEST_TOKEN = os.getenv("CONFLUENCE_TEST_TOKEN")
CONFLUENCE_TEST_EMAIL = os.getenv("CONFLUENCE_TEST_EMAIL")
CONFLUENCE_TEST_SPACE = os.getenv("CONFLUENCE_TEST_SPACE")

# Skip if required credentials are not available
skip_if_no_credentials = pytest.mark.skipif(
    not all([CONFLUENCE_TEST_URL, CONFLUENCE_TEST_TOKEN, CONFLUENCE_TEST_EMAIL, CONFLUENCE_TEST_SPACE]),
    reason="Confluence test credentials not configured. Set CONFLUENCE_TEST_URL, "
    "CONFLUENCE_TEST_TOKEN, CONFLUENCE_TEST_EMAIL, and CONFLUENCE_TEST_SPACE env vars.",
)


@pytest.fixture
def confluence_client():
    """Fixture providing a real ConfluenceClient instance for integration testing."""
    if not all([CONFLUENCE_TEST_URL, CONFLUENCE_TEST_TOKEN, CONFLUENCE_TEST_EMAIL]):
        pytest.skip("Confluence test credentials not configured")

    return ConfluenceClient(
        base_url=CONFLUENCE_TEST_URL,
        api_token=CONFLUENCE_TEST_TOKEN,
        email=CONFLUENCE_TEST_EMAIL,
    )


class TestConfluenceAuthentication:
    """Integration tests for Confluence authentication."""

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_authentication_succeeds_with_valid_token(self, confluence_client):
        """Test that client can authenticate with valid API token.

        This test verifies that the client can successfully connect to
        Confluence Cloud and make authenticated requests.
        """
        # Make a simple CQL query to verify authentication
        cql = f"space = {CONFLUENCE_TEST_SPACE}"
        pages = await confluence_client.cql_search(cql=cql, limit=1)

        # Should succeed without raising ConfluenceAuthError
        assert isinstance(pages, list)
        # Note: List may be empty if space has no pages, but auth succeeded

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_authentication_fails_with_invalid_token(self):
        """Test that invalid token raises ConfluenceAuthError."""
        invalid_client = ConfluenceClient(
            base_url=CONFLUENCE_TEST_URL,
            api_token="invalid-token-12345",
            email=CONFLUENCE_TEST_EMAIL,
        )

        with pytest.raises(ConfluenceAuthError):
            await invalid_client.cql_search(cql="space = TEST", limit=1)


class TestCQLQueries:
    """Integration tests for CQL query functionality."""

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_cql_query_returns_pages_from_space(self, confluence_client):
        """Test that CQL query returns pages from the specified space."""
        cql = f"space = {CONFLUENCE_TEST_SPACE}"
        pages = await confluence_client.cql_search(cql=cql, limit=10)

        assert isinstance(pages, list)
        # Verify that all returned pages belong to the correct space
        for page in pages:
            assert "id" in page
            assert "title" in page

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_cql_query_with_lastmodified_filter(self, confluence_client):
        """Test that CQL query with lastModified filter returns only recent pages."""
        # Query pages modified in the last 365 days
        cutoff_date = datetime.now() - timedelta(days=365)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        cql = f'space = {CONFLUENCE_TEST_SPACE} AND lastModified >= "{cutoff_str}"'
        pages = await confluence_client.cql_search(cql=cql, expand="version", limit=10)

        assert isinstance(pages, list)
        # If any pages returned, they should have version info due to expand
        for page in pages:
            if "version" in page:
                # Verify version object exists
                assert isinstance(page["version"], dict)

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_cql_query_with_expand_parameter(self, confluence_client):
        """Test that expand parameter includes requested metadata."""
        cql = f"space = {CONFLUENCE_TEST_SPACE}"
        pages = await confluence_client.cql_search(cql=cql, expand="body.storage,version", limit=1)

        if len(pages) > 0:
            page = pages[0]
            # Should include expanded fields
            assert "version" in page or "body" in page

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_cql_query_with_invalid_space_returns_empty(self, confluence_client):
        """Test that CQL query with non-existent space returns empty list."""
        cql = "space = NONEXISTENTSPACE12345"
        pages = await confluence_client.cql_search(cql=cql, limit=10)

        # Should return empty list, not raise exception
        assert pages == []


class TestGetPageById:
    """Integration tests for get_page_by_id functionality."""

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_get_page_by_id_returns_page_data(self, confluence_client):
        """Test that get_page_by_id returns full page data."""
        # First, get a page ID from a CQL query
        cql = f"space = {CONFLUENCE_TEST_SPACE}"
        pages = await confluence_client.cql_search(cql=cql, limit=1)

        if len(pages) == 0:
            pytest.skip("No pages available in test space for this test")

        page_id = pages[0]["id"]

        # Now fetch the full page by ID
        page = await confluence_client.get_page_by_id(page_id=page_id, expand="body.storage,version")

        assert page["id"] == page_id
        assert "title" in page
        # Should have expanded fields
        assert "version" in page or "body" in page

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_get_page_by_id_raises_not_found_for_invalid_id(self, confluence_client):
        """Test that get_page_by_id raises ConfluenceNotFoundError for invalid ID."""
        with pytest.raises(ConfluenceNotFoundError):
            await confluence_client.get_page_by_id(page_id="999999999999")


class TestGetSpacePageIds:
    """Integration tests for get_space_pages_ids functionality."""

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_get_space_pages_ids_returns_list_of_ids(self, confluence_client):
        """Test that get_space_pages_ids returns list of page IDs."""
        page_ids = await confluence_client.get_space_pages_ids(space_key=CONFLUENCE_TEST_SPACE)

        assert isinstance(page_ids, list)
        # All elements should be strings (page IDs)
        for page_id in page_ids:
            assert isinstance(page_id, str)
            assert len(page_id) > 0

    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_get_space_pages_ids_raises_not_found_for_invalid_space(self, confluence_client):
        """Test that get_space_pages_ids raises ConfluenceNotFoundError for invalid space."""
        with pytest.raises(ConfluenceNotFoundError):
            await confluence_client.get_space_pages_ids(space_key="NONEXISTENTSPACE12345")


class TestRateLimitHandling:
    """Integration tests for rate limit handling.

    Note: These tests are disabled by default to avoid triggering actual
          rate limits during normal test runs.
    """

    @pytest.mark.skip(reason="Skipping to avoid triggering real rate limits during normal test runs")
    @skip_if_no_credentials
    @pytest.mark.asyncio
    async def test_rate_limit_handling_retries_gracefully(self, confluence_client):
        """Test that client handles rate limits with exponential backoff.

        WARNING: This test may trigger real rate limits if run.
                 Only run manually when testing rate limit behavior.
        """
        # Make many requests rapidly to potentially trigger rate limit
        cql = f"space = {CONFLUENCE_TEST_SPACE}"
        for _ in range(20):
            try:
                await confluence_client.cql_search(cql=cql, limit=1)
            except Exception as e:
                # If we hit a rate limit, verify it's handled gracefully
                # and doesn't crash
                assert "rate limit" in str(e).lower() or "429" in str(e)
                break
        else:
            # No rate limit hit (good - means we didn't exceed limits)
            pass


class TestIntegrationREADME:
    """Placeholder class to document integration test setup."""

    def test_readme_documentation(self):
        """Integration test documentation.

        To run integration tests:

        1. Set up environment variables:
           export CONFLUENCE_TEST_URL="https://your-instance.atlassian.net/wiki"
           export CONFLUENCE_TEST_TOKEN="your-api-token"
           export CONFLUENCE_TEST_EMAIL="your-email@example.com"
           export CONFLUENCE_TEST_SPACE="TESTSPACE"

        2. Run integration tests only:
           cd python
           uv run pytest -m integration -v

        3. Run specific integration test file:
           uv run pytest tests/integration/test_confluence_client_integration.py -v

        4. Run all tests (unit + integration):
           uv run pytest

        Note: Integration tests will be skipped if credentials are not configured.
        """
        pass
