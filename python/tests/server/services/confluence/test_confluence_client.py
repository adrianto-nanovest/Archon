"""Unit tests for ConfluenceClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.server.services.confluence.confluence_client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceNotFoundError,
    ConfluenceRateLimitError,
)


@pytest.fixture
def mock_confluence_client():
    """Fixture providing a mocked atlassian.Confluence client."""
    with patch("src.server.services.confluence.confluence_client.Confluence") as mock:
        yield mock


@pytest.fixture
def confluence_client(mock_confluence_client):
    """Fixture providing a ConfluenceClient instance with mocked backend."""
    return ConfluenceClient(
        base_url="https://test.atlassian.net/wiki", api_token="test-token", email="test@example.com"
    )


class TestConfluenceClientInit:
    """Tests for ConfluenceClient initialization."""

    def test_constructor_initializes_with_valid_credentials(self, mock_confluence_client):
        """Test that constructor initializes with valid credentials."""
        client = ConfluenceClient(
            base_url="https://test.atlassian.net/wiki", api_token="test-token", email="test@example.com"
        )

        assert client.base_url == "https://test.atlassian.net/wiki"
        assert client.email == "test@example.com"
        mock_confluence_client.assert_called_once_with(
            url="https://test.atlassian.net/wiki", username="test@example.com", password="test-token", cloud=True
        )

    def test_constructor_stores_client_instance(self, confluence_client, mock_confluence_client):
        """Test that constructor stores the Confluence client instance."""
        assert confluence_client._client is not None
        assert confluence_client._client == mock_confluence_client.return_value


class TestCQLSearch:
    """Tests for cql_search method."""

    @pytest.mark.asyncio
    async def test_cql_search_returns_pages(self, confluence_client):
        """Test successful CQL search returns list of pages."""
        mock_results = {"results": [{"id": "123", "title": "Page 1"}, {"id": "456", "title": "Page 2"}]}
        confluence_client._client.cql = MagicMock(return_value=mock_results)

        pages = await confluence_client.cql_search(cql='space = DEV AND lastModified >= "2025-10-01"', expand="body.storage")

        assert len(pages) == 2
        assert pages[0]["id"] == "123"
        assert pages[1]["title"] == "Page 2"
        confluence_client._client.cql.assert_called_once_with(
            cql='space = DEV AND lastModified >= "2025-10-01"', expand="body.storage", limit=1000
        )

    @pytest.mark.asyncio
    async def test_cql_search_with_custom_limit(self, confluence_client):
        """Test CQL search respects custom limit parameter."""
        mock_results = {"results": [{"id": "123"}]}
        confluence_client._client.cql = MagicMock(return_value=mock_results)

        await confluence_client.cql_search(cql="space = DEV", limit=500)

        confluence_client._client.cql.assert_called_once_with(cql="space = DEV", expand=None, limit=500)

    @pytest.mark.asyncio
    async def test_cql_search_handles_empty_results(self, confluence_client):
        """Test CQL search handles empty results gracefully."""
        mock_results = {"results": []}
        confluence_client._client.cql = MagicMock(return_value=mock_results)

        pages = await confluence_client.cql_search(cql="space = NONEXISTENT")

        assert pages == []

    @pytest.mark.asyncio
    async def test_cql_search_raises_auth_error_on_401(self, confluence_client):
        """Test CQL search raises ConfluenceAuthError on 401."""
        confluence_client._client.cql = MagicMock(side_effect=Exception("401 Unauthorized"))

        with pytest.raises(ConfluenceAuthError) as exc_info:
            await confluence_client.cql_search(cql="space = DEV")

        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cql_search_raises_not_found_error_on_404(self, confluence_client):
        """Test CQL search raises ConfluenceNotFoundError on 404."""
        confluence_client._client.cql = MagicMock(side_effect=Exception("404 Not Found"))

        with pytest.raises(ConfluenceNotFoundError) as exc_info:
            await confluence_client.cql_search(cql="space = DEV")

        assert "Resource not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cql_search_raises_rate_limit_error_on_429(self, confluence_client):
        """Test CQL search raises ConfluenceRateLimitError on 429 after retries."""
        confluence_client._client.cql = MagicMock(side_effect=Exception("429 Too Many Requests"))

        with pytest.raises(ConfluenceRateLimitError) as exc_info:
            await confluence_client.cql_search(cql="space = DEV")

        assert "Rate limit exceeded" in str(exc_info.value)
        # Should have been called 4 times (1 initial + 3 retries)
        assert confluence_client._client.cql.call_count == 4


class TestGetPageById:
    """Tests for get_page_by_id method."""

    @pytest.mark.asyncio
    async def test_get_page_by_id_returns_page(self, confluence_client):
        """Test successful get_page_by_id returns page data."""
        mock_page = {"id": "123456", "title": "Test Page", "body": {"storage": {"value": "<p>Content</p>"}}}
        confluence_client._client.get_page_by_id = MagicMock(return_value=mock_page)

        page = await confluence_client.get_page_by_id(page_id="123456", expand="body.storage,version")

        assert page["id"] == "123456"
        assert page["title"] == "Test Page"
        confluence_client._client.get_page_by_id.assert_called_once_with(page_id="123456", expand="body.storage,version")

    @pytest.mark.asyncio
    async def test_get_page_by_id_without_expand(self, confluence_client):
        """Test get_page_by_id works without expand parameter."""
        mock_page = {"id": "123456", "title": "Test Page"}
        confluence_client._client.get_page_by_id = MagicMock(return_value=mock_page)

        page = await confluence_client.get_page_by_id(page_id="123456")

        assert page["id"] == "123456"
        confluence_client._client.get_page_by_id.assert_called_once_with(page_id="123456", expand=None)

    @pytest.mark.asyncio
    async def test_get_page_by_id_raises_not_found_error(self, confluence_client):
        """Test get_page_by_id raises ConfluenceNotFoundError when page doesn't exist."""
        confluence_client._client.get_page_by_id = MagicMock(side_effect=Exception("404 Page not found"))

        with pytest.raises(ConfluenceNotFoundError) as exc_info:
            await confluence_client.get_page_by_id(page_id="999999")

        assert "Resource not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_page_by_id_raises_auth_error(self, confluence_client):
        """Test get_page_by_id raises ConfluenceAuthError on auth failure."""
        confluence_client._client.get_page_by_id = MagicMock(side_effect=Exception("401 Unauthorized"))

        with pytest.raises(ConfluenceAuthError):
            await confluence_client.get_page_by_id(page_id="123456")


class TestGetSpacePageIds:
    """Tests for get_space_pages_ids method."""

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_returns_ids(self, confluence_client):
        """Test successful get_space_pages_ids returns list of page IDs."""
        mock_pages = [{"id": "123"}, {"id": "456"}, {"id": "789"}]
        confluence_client._client.get_all_pages_from_space = MagicMock(return_value=mock_pages)

        page_ids = await confluence_client.get_space_pages_ids(space_key="DEVDOCS")

        assert page_ids == ["123", "456", "789"]
        confluence_client._client.get_all_pages_from_space.assert_called_once_with(
            space="DEVDOCS", expand=None, status=None, limit=1000
        )

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_handles_large_space(self, confluence_client):
        """Test get_space_pages_ids handles spaces with 1000+ pages."""
        # Simulate a space with 1500 pages
        mock_pages = [{"id": str(i)} for i in range(1500)]
        confluence_client._client.get_all_pages_from_space = MagicMock(return_value=mock_pages)

        page_ids = await confluence_client.get_space_pages_ids(space_key="BIGSPACE")

        assert len(page_ids) == 1500
        assert page_ids[0] == "0"
        assert page_ids[-1] == "1499"

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_handles_empty_space(self, confluence_client):
        """Test get_space_pages_ids handles empty space."""
        confluence_client._client.get_all_pages_from_space = MagicMock(return_value=[])

        page_ids = await confluence_client.get_space_pages_ids(space_key="EMPTY")

        assert page_ids == []

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_raises_not_found_error(self, confluence_client):
        """Test get_space_pages_ids raises ConfluenceNotFoundError for missing space."""
        confluence_client._client.get_all_pages_from_space = MagicMock(side_effect=Exception("404 Space not found"))

        with pytest.raises(ConfluenceNotFoundError) as exc_info:
            await confluence_client.get_space_pages_ids(space_key="NONEXISTENT")

        assert "Resource not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_filters_malformed_pages(self, confluence_client):
        """Test get_space_pages_ids filters out pages without ID field."""
        mock_pages = [{"id": "123"}, {"title": "No ID"}, {"id": "456"}]
        confluence_client._client.get_all_pages_from_space = MagicMock(return_value=mock_pages)

        page_ids = await confluence_client.get_space_pages_ids(space_key="DEVDOCS")

        assert page_ids == ["123", "456"]


class TestRetryWithBackoff:
    """Tests for exponential backoff retry logic."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_first_attempt(self, confluence_client):
        """Test retry succeeds immediately if no error occurs."""
        mock_func = AsyncMock(return_value="success")

        result = await confluence_client._retry_with_backoff(mock_func)

        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_rate_limit(self, confluence_client):
        """Test retry succeeds after transient rate limit error."""
        mock_func = AsyncMock(side_effect=[ConfluenceRateLimitError("429"), "success"])

        result = await confluence_client._retry_with_backoff(mock_func, max_retries=3)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_retries(self, confluence_client):
        """Test retry fails after max retries exceeded."""
        mock_func = AsyncMock(side_effect=ConfluenceRateLimitError("429"))

        with pytest.raises(ConfluenceRateLimitError):
            await confluence_client._retry_with_backoff(mock_func, max_retries=3)

        # Should be called 4 times (1 initial + 3 retries)
        assert mock_func.call_count == 4

    @pytest.mark.asyncio
    async def test_retry_uses_exponential_backoff(self, confluence_client):
        """Test retry uses exponential backoff delays (1s, 2s, 4s)."""
        mock_func = AsyncMock(side_effect=ConfluenceRateLimitError("429"))

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(ConfluenceRateLimitError):
                await confluence_client._retry_with_backoff(mock_func, max_retries=3)

            # Should sleep 3 times with exponential delays
            assert mock_sleep.call_count == 3
            mock_sleep.assert_any_call(1)  # 2^0
            mock_sleep.assert_any_call(2)  # 2^1
            mock_sleep.assert_any_call(4)  # 2^2

    @pytest.mark.asyncio
    async def test_retry_does_not_retry_auth_errors(self, confluence_client):
        """Test retry does not retry authentication errors."""
        mock_func = AsyncMock(side_effect=ConfluenceAuthError("401"))

        with pytest.raises(ConfluenceAuthError):
            await confluence_client._retry_with_backoff(mock_func, max_retries=3)

        # Should only be called once (no retries)
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_does_not_retry_not_found_errors(self, confluence_client):
        """Test retry does not retry not found errors."""
        mock_func = AsyncMock(side_effect=ConfluenceNotFoundError("404"))

        with pytest.raises(ConfluenceNotFoundError):
            await confluence_client._retry_with_backoff(mock_func, max_retries=3)

        # Should only be called once (no retries)
        mock_func.assert_called_once()


class TestHandleApiError:
    """Tests for API error handling."""

    def test_handle_api_error_maps_401_to_auth_error(self, confluence_client):
        """Test that 401 errors are mapped to ConfluenceAuthError."""
        error = Exception("401 Unauthorized")

        with pytest.raises(ConfluenceAuthError) as exc_info:
            confluence_client._handle_api_error(error, operation="test_op", context={"test": "context"})

        assert "Authentication failed" in str(exc_info.value)

    def test_handle_api_error_maps_429_to_rate_limit_error(self, confluence_client):
        """Test that 429 errors are mapped to ConfluenceRateLimitError."""
        error = Exception("429 Too Many Requests")

        with pytest.raises(ConfluenceRateLimitError) as exc_info:
            confluence_client._handle_api_error(error, operation="test_op", context={"test": "context"})

        assert "Rate limit exceeded" in str(exc_info.value)

    def test_handle_api_error_maps_404_to_not_found_error(self, confluence_client):
        """Test that 404 errors are mapped to ConfluenceNotFoundError."""
        error = Exception("404 Not Found")

        with pytest.raises(ConfluenceNotFoundError) as exc_info:
            confluence_client._handle_api_error(error, operation="test_op", context={"test": "context"})

        assert "Resource not found" in str(exc_info.value)

    def test_handle_api_error_re_raises_unknown_errors(self, confluence_client):
        """Test that unknown errors are re-raised as-is."""
        error = Exception("500 Internal Server Error")

        with pytest.raises(Exception) as exc_info:
            confluence_client._handle_api_error(error, operation="test_op", context={"test": "context"})

        assert "500 Internal Server Error" in str(exc_info.value)

    def test_handle_api_error_includes_context_in_message(self, confluence_client):
        """Test that error context is included in exception messages."""
        error = Exception("401 Unauthorized")

        with pytest.raises(ConfluenceAuthError) as exc_info:
            confluence_client._handle_api_error(error, operation="cql_search", context={"cql": "space = DEV"})

        assert "https://test.atlassian.net/wiki" in str(exc_info.value)
