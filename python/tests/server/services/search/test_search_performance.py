"""
Unit Tests for Search Performance Optimization (Story 4.3)

Tests cover:
1. ETag caching behavior (AC: 4)
2. Pagination parameters validation (AC: 5)
3. Slow query logging threshold (AC: 6)
4. Limit validation constraints
5. Integration with existing Confluence filters

Test execution:
    cd python
    uv run pytest tests/server/services/search/test_search_performance.py -v
"""

import hashlib
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError


class TestRagQueryRequestPagination:
    """Tests for RagQueryRequest pagination parameter validation (AC: 5)."""

    def test_default_pagination_values(self) -> None:
        """Test that default pagination values are applied correctly."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        request = RagQueryRequest(query="test query")

        assert request.offset == 0
        assert request.limit == 50

    def test_custom_pagination_values(self) -> None:
        """Test that custom pagination values are accepted."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        request = RagQueryRequest(query="test", offset=10, limit=25)

        assert request.offset == 10
        assert request.limit == 25

    def test_limit_validation_rejects_values_over_100(self) -> None:
        """Test that limit values over 100 are rejected."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        with pytest.raises(ValidationError) as exc_info:
            RagQueryRequest(query="test", limit=150)

        assert "less than or equal to 100" in str(exc_info.value).lower()

    def test_limit_validation_rejects_zero(self) -> None:
        """Test that limit of 0 is rejected."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        with pytest.raises(ValidationError) as exc_info:
            RagQueryRequest(query="test", limit=0)

        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_limit_validation_rejects_negative(self) -> None:
        """Test that negative limit values are rejected."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        with pytest.raises(ValidationError) as exc_info:
            RagQueryRequest(query="test", limit=-5)

        assert "greater than or equal to 1" in str(exc_info.value).lower()

    def test_offset_validation_rejects_negative(self) -> None:
        """Test that negative offset values are rejected."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        with pytest.raises(ValidationError) as exc_info:
            RagQueryRequest(query="test", offset=-1)

        assert "greater than or equal to 0" in str(exc_info.value).lower()

    def test_offset_zero_is_valid(self) -> None:
        """Test that offset of 0 is valid (first page)."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        request = RagQueryRequest(query="test", offset=0)

        assert request.offset == 0

    def test_pagination_with_confluence_filters(self) -> None:
        """Test that pagination works alongside Confluence filters."""
        from src.server.api_routes.knowledge_api import RagQueryRequest

        request = RagQueryRequest(
            query="test",
            space_key="DEVDOCS",
            jira_issue="PROJ-123",
            offset=20,
            limit=10,
        )

        assert request.space_key == "DEVDOCS"
        assert request.jira_issue == "PROJ-123"
        assert request.offset == 20
        assert request.limit == 10


class TestETagCaching:
    """Tests for ETag caching functionality (AC: 4)."""

    def test_generate_etag_returns_quoted_string(self) -> None:
        """Test that generate_etag returns properly quoted ETag."""
        from src.server.utils.etag_utils import generate_etag

        data = {"results": [{"id": "1", "content": "test"}]}
        etag = generate_etag(data)

        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_generate_etag_is_consistent(self) -> None:
        """Test that same data produces same ETag."""
        from src.server.utils.etag_utils import generate_etag

        data = {"results": [{"id": "1", "content": "test"}]}

        etag1 = generate_etag(data)
        etag2 = generate_etag(data)

        assert etag1 == etag2

    def test_generate_etag_differs_for_different_data(self) -> None:
        """Test that different data produces different ETags."""
        from src.server.utils.etag_utils import generate_etag

        data1 = {"results": [{"id": "1", "content": "test1"}]}
        data2 = {"results": [{"id": "1", "content": "test2"}]}

        etag1 = generate_etag(data1)
        etag2 = generate_etag(data2)

        assert etag1 != etag2

    def test_check_etag_returns_true_on_match(self) -> None:
        """Test that check_etag returns True when ETags match."""
        from src.server.utils.etag_utils import check_etag, generate_etag

        data = {"results": [{"id": "1"}]}
        etag = generate_etag(data)

        assert check_etag(etag, etag) is True

    def test_check_etag_returns_false_on_mismatch(self) -> None:
        """Test that check_etag returns False when ETags don't match."""
        from src.server.utils.etag_utils import check_etag

        assert check_etag('"abc123"', '"def456"') is False

    def test_check_etag_returns_false_when_request_etag_is_none(self) -> None:
        """Test that check_etag returns False when request ETag is None."""
        from src.server.utils.etag_utils import check_etag

        assert check_etag(None, '"abc123"') is False


class TestSlowQueryLogging:
    """Tests for slow query logging functionality (AC: 6)."""

    @pytest.mark.asyncio
    async def test_slow_query_logging_threshold(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that queries exceeding 1000ms trigger warning log."""
        import time

        from src.server.services.search.hybrid_search_strategy import (
            SLOW_QUERY_THRESHOLD_MS,
            HybridSearchStrategy,
        )

        # Verify threshold is 1000ms
        assert SLOW_QUERY_THRESHOLD_MS == 1000

        # Create mock Supabase client
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "1",
                "url": "https://example.com/page1",
                "chunk_number": 1,
                "content": "Test content",
                "metadata": {},
                "source_id": "source1",
                "similarity": 0.9,
                "match_type": "vector",
            }
        ]

        # Simulate slow response using synchronous sleep in execute()
        def slow_execute() -> MagicMock:
            time.sleep(1.1)  # 1.1 seconds > 1000ms threshold
            return mock_response

        mock_rpc_chain = MagicMock()
        mock_rpc_chain.execute = slow_execute
        mock_supabase.rpc.return_value = mock_rpc_chain

        # Create strategy and execute search
        strategy = HybridSearchStrategy(mock_supabase, MagicMock())

        with caplog.at_level(logging.WARNING):
            await strategy.search_documents_hybrid(
                query="test query",
                query_embedding=[0.1] * 1536,
                match_count=10,
                filter_metadata=None,
                confluence_filters=None,
            )

        # Verify warning was logged
        assert "Slow search query detected" in caplog.text

    @pytest.mark.asyncio
    async def test_fast_query_does_not_log_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that fast queries don't trigger warning log."""
        from src.server.services.search.hybrid_search_strategy import HybridSearchStrategy

        # Create mock Supabase client with immediate response
        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "1",
                "url": "https://example.com/page1",
                "chunk_number": 1,
                "content": "Test content",
                "metadata": {},
                "source_id": "source1",
                "similarity": 0.9,
                "match_type": "vector",
            }
        ]

        # Fast response (no delay)
        mock_rpc_chain = MagicMock()
        mock_rpc_chain.execute.return_value = mock_response
        mock_supabase.rpc.return_value = mock_rpc_chain

        strategy = HybridSearchStrategy(mock_supabase, MagicMock())

        with caplog.at_level(logging.WARNING):
            await strategy.search_documents_hybrid(
                query="test query",
                query_embedding=[0.1] * 1536,
                match_count=10,
                filter_metadata=None,
                confluence_filters=None,
            )

        # Verify no warning was logged
        assert "Slow search query detected" not in caplog.text

    def test_query_fingerprint_generation(self) -> None:
        """Test that query fingerprint is generated consistently."""
        from src.server.services.search.hybrid_search_strategy import ConfluenceSearchFilters

        query = "test query"
        filters = ConfluenceSearchFilters(space_key="DEVDOCS")
        filter_str = str(filters)

        # Generate fingerprint using same logic as in hybrid_search_strategy.py
        fingerprint = hashlib.md5(f"{query}|{filter_str}".encode()).hexdigest()[:8]

        # Verify it's 8 characters
        assert len(fingerprint) == 8

        # Verify consistency
        fingerprint2 = hashlib.md5(f"{query}|{filter_str}".encode()).hexdigest()[:8]
        assert fingerprint == fingerprint2


class TestPaginationIntegration:
    """Integration tests for pagination with RAG query endpoint."""

    @pytest.mark.asyncio
    async def test_pagination_applies_after_filtering(self) -> None:
        """Test that pagination is applied after Confluence filters."""
        from src.server.api_routes.knowledge_api import RagQueryRequest, perform_rag_query

        # Create mock results
        mock_results = [{"id": f"result_{i}", "content": f"Content {i}"} for i in range(25)]

        with patch("src.server.api_routes.knowledge_api.RAGService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.perform_rag_query = AsyncMock(
                return_value=(
                    True,
                    {
                        "results": mock_results,
                        "query": "test",
                        "total_found": 25,
                    },
                )
            )
            mock_service_class.return_value = mock_service

            with patch("src.server.api_routes.knowledge_api.get_supabase_client"):
                request = RagQueryRequest(query="test", offset=5, limit=10)
                response = await perform_rag_query(request, if_none_match=None)

                # Response should be JSONResponse - extract content
                assert response.status_code == 200
                import json

                body = json.loads(response.body)

                # Should have pagination info
                assert "pagination" in body
                assert body["pagination"]["offset"] == 5
                assert body["pagination"]["limit"] == 10
                assert body["pagination"]["total"] == 25
                assert body["pagination"]["has_more"] is True

                # Results should be sliced
                assert len(body["results"]) == 10

    @pytest.mark.asyncio
    async def test_pagination_has_more_false_when_at_end(self) -> None:
        """Test that has_more is False when at end of results."""
        from src.server.api_routes.knowledge_api import RagQueryRequest, perform_rag_query

        # Create mock results
        mock_results = [{"id": f"result_{i}", "content": f"Content {i}"} for i in range(15)]

        with patch("src.server.api_routes.knowledge_api.RAGService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.perform_rag_query = AsyncMock(
                return_value=(
                    True,
                    {
                        "results": mock_results,
                        "query": "test",
                        "total_found": 15,
                    },
                )
            )
            mock_service_class.return_value = mock_service

            with patch("src.server.api_routes.knowledge_api.get_supabase_client"):
                request = RagQueryRequest(query="test", offset=10, limit=10)
                response = await perform_rag_query(request, if_none_match=None)

                import json

                body = json.loads(response.body)

                # Only 5 results left, has_more should be False
                assert body["pagination"]["has_more"] is False
                assert len(body["results"]) == 5

    @pytest.mark.asyncio
    async def test_etag_returns_304_on_unchanged_results(self) -> None:
        """Test that unchanged search results return 304 with valid ETag."""
        from src.server.api_routes.knowledge_api import RagQueryRequest, perform_rag_query

        mock_results = [{"id": "1", "content": "Test"}]

        with patch("src.server.api_routes.knowledge_api.RAGService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.perform_rag_query = AsyncMock(
                return_value=(
                    True,
                    {
                        "results": mock_results,
                        "query": "test",
                        "total_found": 1,
                    },
                )
            )
            mock_service_class.return_value = mock_service

            with patch("src.server.api_routes.knowledge_api.get_supabase_client"):
                # First request - get ETag
                request = RagQueryRequest(query="test")
                response1 = await perform_rag_query(request, if_none_match=None)

                assert response1.status_code == 200
                etag = response1.headers.get("etag")
                assert etag is not None

                # Second request with If-None-Match - should return 304
                response2 = await perform_rag_query(request, if_none_match=etag)

                assert response2.status_code == 304


class TestSlowQueryThreshold:
    """Tests for slow query threshold constant."""

    def test_slow_query_threshold_is_1000ms(self) -> None:
        """Test that SLOW_QUERY_THRESHOLD_MS is set to 1000."""
        from src.server.services.search.hybrid_search_strategy import SLOW_QUERY_THRESHOLD_MS

        assert SLOW_QUERY_THRESHOLD_MS == 1000


class TestConfluenceSearchFiltersWithPagination:
    """Tests for Confluence filters combined with pagination."""

    def test_confluence_filters_dataclass_creation(self) -> None:
        """Test that ConfluenceSearchFilters can be created with all parameters."""
        from src.server.services.search.hybrid_search_strategy import ConfluenceSearchFilters

        filters = ConfluenceSearchFilters(
            space_key="DEVDOCS",
            jira_issue="PROJ-123",
            hierarchy_path="/parent/",
            mentioned_user="user123",
        )

        assert filters.space_key == "DEVDOCS"
        assert filters.jira_issue == "PROJ-123"
        assert filters.hierarchy_path == "/parent/"
        assert filters.mentioned_user == "user123"

    def test_has_any_filter_returns_true_when_filter_set(self) -> None:
        """Test that has_any_filter returns True when any filter is set."""
        from src.server.services.search.hybrid_search_strategy import ConfluenceSearchFilters

        filters = ConfluenceSearchFilters(space_key="DEVDOCS")
        assert filters.has_any_filter() is True

    def test_has_any_filter_returns_false_when_no_filters(self) -> None:
        """Test that has_any_filter returns False when no filters are set."""
        from src.server.services.search.hybrid_search_strategy import ConfluenceSearchFilters

        filters = ConfluenceSearchFilters()
        assert filters.has_any_filter() is False
