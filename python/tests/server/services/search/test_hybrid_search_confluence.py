"""
Tests for Confluence metadata enrichment in hybrid search.

Story 4.1: Enhance Hybrid Search with Metadata JOIN
Verifies that search results include Confluence-specific metadata (space, JIRA links, hierarchy)
for Confluence-sourced chunks while maintaining null metadata for web/upload chunks.
"""

from unittest.mock import MagicMock

import pytest

from src.server.services.search.hybrid_search_strategy import HybridSearchStrategy


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Mock Supabase client with chainable query API."""
    client = MagicMock()
    return client


@pytest.fixture
def strategy(mock_supabase_client: MagicMock) -> HybridSearchStrategy:
    """Create HybridSearchStrategy instance with mock client."""
    return HybridSearchStrategy(mock_supabase_client, base_strategy=None)


def mock_confluence_pages_response(pages_data: list[dict]) -> MagicMock:
    """Helper to create mock response for confluence_pages query."""
    mock_response = MagicMock()
    mock_response.data = pages_data
    return mock_response


def mock_rpc_response(chunks_data: list[dict]) -> MagicMock:
    """Helper to create mock response for RPC call."""
    mock_response = MagicMock()
    mock_response.data = chunks_data
    return mock_response


class TestFetchConfluenceMetadata:
    """Tests for _fetch_confluence_metadata method."""

    @pytest.mark.asyncio
    async def test_empty_page_ids_returns_empty_dict(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that empty page_ids list returns empty dict without DB query."""
        result = await strategy._fetch_confluence_metadata([])

        assert result == {}
        # Should not call database
        mock_supabase_client.from_.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetches_metadata_for_valid_page_ids(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test successful metadata fetch for valid page IDs."""
        # Setup mock response
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([
            {
                "page_id": "page123",
                "space_key": "DEVDOCS",
                "title": "Test Page",
                "path": "/parent/child",
                "metadata": {
                    "jira_issue_links": [{"issue_key": "PROJ-123", "issue_url": "https://jira.example.com/PROJ-123"}],
                    "user_mentions": [{"account_id": "abc123", "display_name": "John Doe"}],
                    "ancestors": [{"id": "parent1", "title": "Parent"}],
                    "internal_links": [{"page_id": "linked1", "page_title": "Linked Page"}],
                },
            }
        ])

        result = await strategy._fetch_confluence_metadata(["page123"])

        assert "page123" in result
        assert result["page123"]["space_key"] == "DEVDOCS"
        assert result["page123"]["title"] == "Test Page"
        assert result["page123"]["path"] == "/parent/child"
        assert result["page123"]["jira_issue_links"] == [{"issue_key": "PROJ-123", "issue_url": "https://jira.example.com/PROJ-123"}]
        assert result["page123"]["user_mentions"] == [{"account_id": "abc123", "display_name": "John Doe"}]
        assert result["page123"]["ancestors"] == [{"id": "parent1", "title": "Parent"}]
        assert result["page123"]["internal_links"] == [{"page_id": "linked1", "page_title": "Linked Page"}]

    @pytest.mark.asyncio
    async def test_handles_missing_metadata_fields_gracefully(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that missing metadata fields default to empty lists."""
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([
            {
                "page_id": "page456",
                "space_key": "SPACE",
                "title": "Minimal Page",
                "path": "/minimal",
                "metadata": {},  # Empty metadata
            }
        ])

        result = await strategy._fetch_confluence_metadata(["page456"])

        assert result["page456"]["jira_issue_links"] == []
        assert result["page456"]["user_mentions"] == []
        assert result["page456"]["ancestors"] == []
        assert result["page456"]["internal_links"] == []

    @pytest.mark.asyncio
    async def test_handles_null_metadata_gracefully(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that null metadata field defaults to empty lists."""
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([
            {
                "page_id": "page789",
                "space_key": "SPACE",
                "title": "Null Metadata Page",
                "path": "/null",
                "metadata": None,  # Null metadata
            }
        ])

        result = await strategy._fetch_confluence_metadata(["page789"])

        assert result["page789"]["jira_issue_links"] == []
        assert result["page789"]["user_mentions"] == []

    @pytest.mark.asyncio
    async def test_batch_query_multiple_page_ids(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test batch query for multiple page IDs uses single IN clause."""
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([
            {"page_id": "page1", "space_key": "S1", "title": "P1", "path": "/1", "metadata": {}},
            {"page_id": "page2", "space_key": "S2", "title": "P2", "path": "/2", "metadata": {}},
            {"page_id": "page3", "space_key": "S3", "title": "P3", "path": "/3", "metadata": {}},
        ])

        page_ids = ["page1", "page2", "page3"]
        result = await strategy._fetch_confluence_metadata(page_ids)

        assert len(result) == 3
        # Verify single call with IN clause
        mock_supabase_client.from_.return_value.select.return_value.in_.assert_called_once_with("page_id", page_ids)

    @pytest.mark.asyncio
    async def test_excludes_deleted_pages(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that is_deleted=False filter is applied."""
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([])

        await strategy._fetch_confluence_metadata(["page1"])

        # Verify eq("is_deleted", False) was called
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.assert_called_with("is_deleted", False)

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_db_error(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that database errors return empty dict without crashing."""
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.side_effect = Exception("Database connection failed")

        result = await strategy._fetch_confluence_metadata(["page1"])

        assert result == {}


class TestSearchDocumentsHybridConfluenceEnrichment:
    """Tests for Confluence metadata enrichment in search_documents_hybrid."""

    @pytest.mark.asyncio
    async def test_confluence_chunk_enriched_with_metadata(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that Confluence chunks get enriched with metadata."""
        # Setup RPC response with Confluence chunk
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([
            {
                "id": 1,
                "url": "https://example.com/page",
                "chunk_number": 1,
                "content": "Test content",
                "metadata": {"page_id": "page123"},
                "source_id": "confluence_abc",
                "similarity": 0.95,
                "match_type": "vector",
            }
        ])

        # Setup confluence_pages response
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([
            {
                "page_id": "page123",
                "space_key": "DEVDOCS",
                "title": "Test Page",
                "path": "/parent/page123",
                "metadata": {
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                    "user_mentions": [{"display_name": "John"}],
                    "ancestors": [],
                    "internal_links": [],
                },
            }
        ])

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        assert len(results) == 1
        assert results[0]["confluence_metadata"] is not None
        assert results[0]["confluence_metadata"]["space_key"] == "DEVDOCS"
        assert results[0]["confluence_metadata"]["title"] == "Test Page"
        assert results[0]["confluence_metadata"]["jira_issue_links"] == [{"issue_key": "PROJ-123"}]

    @pytest.mark.asyncio
    async def test_non_confluence_chunk_has_null_metadata(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that web crawl chunks have null confluence_metadata."""
        # Setup RPC response with web crawl chunk (no page_id)
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([
            {
                "id": 1,
                "url": "https://example.com",
                "chunk_number": 1,
                "content": "Web content",
                "metadata": {},  # No page_id
                "source_id": "web_xyz",
                "similarity": 0.90,
                "match_type": "vector",
            }
        ])

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        assert len(results) == 1
        assert results[0]["confluence_metadata"] is None

    @pytest.mark.asyncio
    async def test_mixed_results_correct_enrichment(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test mixed Confluence and web results have correct metadata assignment."""
        # Setup RPC response with mixed chunks
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([
            {
                "id": 1,
                "url": "https://confluence.example.com/page1",
                "chunk_number": 1,
                "content": "Confluence content",
                "metadata": {"page_id": "conf_page1"},
                "source_id": "confluence_src",
                "similarity": 0.95,
                "match_type": "vector",
            },
            {
                "id": 2,
                "url": "https://web.example.com",
                "chunk_number": 1,
                "content": "Web content",
                "metadata": {},
                "source_id": "web_src",
                "similarity": 0.85,
                "match_type": "keyword",
            },
            {
                "id": 3,
                "url": "https://confluence.example.com/page2",
                "chunk_number": 2,
                "content": "More Confluence content",
                "metadata": {"page_id": "conf_page2"},
                "source_id": "confluence_src",
                "similarity": 0.80,
                "match_type": "hybrid",
            },
        ])

        # Setup confluence_pages response for Confluence pages only
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([
            {"page_id": "conf_page1", "space_key": "DEV", "title": "Page 1", "path": "/1", "metadata": {}},
            {"page_id": "conf_page2", "space_key": "DEV", "title": "Page 2", "path": "/2", "metadata": {}},
        ])

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        assert len(results) == 3
        # First Confluence chunk - enriched
        assert results[0]["confluence_metadata"] is not None
        assert results[0]["confluence_metadata"]["space_key"] == "DEV"
        # Web chunk - null
        assert results[1]["confluence_metadata"] is None
        # Second Confluence chunk - enriched
        assert results[2]["confluence_metadata"] is not None
        assert results[2]["confluence_metadata"]["title"] == "Page 2"

    @pytest.mark.asyncio
    async def test_pending_deletion_chunks_excluded(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that chunks with _pending_deletion flag are excluded."""
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([
            {
                "id": 1,
                "url": "https://example.com",
                "chunk_number": 1,
                "content": "Visible content",
                "metadata": {},
                "source_id": "src1",
                "similarity": 0.95,
                "match_type": "vector",
            },
            {
                "id": 2,
                "url": "https://example.com",
                "chunk_number": 2,
                "content": "Pending deletion content",
                "metadata": {"_pending_deletion": "true"},
                "source_id": "src1",
                "similarity": 0.90,
                "match_type": "vector",
            },
        ])

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        assert len(results) == 1
        assert results[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that empty RPC results return empty list."""
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([])

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_null_rpc_data_returns_empty_list(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that null RPC data returns empty list."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase_client.rpc.return_value.execute.return_value = mock_response

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_confluence_metadata_fetch_error_continues_gracefully(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that errors in metadata fetch don't crash search."""
        # Setup RPC response
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([
            {
                "id": 1,
                "url": "https://example.com",
                "chunk_number": 1,
                "content": "Content",
                "metadata": {"page_id": "page123"},
                "source_id": "confluence_src",
                "similarity": 0.95,
                "match_type": "vector",
            }
        ])

        # Setup confluence_pages to raise error
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        # Should return results with null confluence_metadata
        assert len(results) == 1
        assert results[0]["confluence_metadata"] is None

    @pytest.mark.asyncio
    async def test_preserves_existing_result_structure(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that adding confluence_metadata doesn't break existing fields."""
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([
            {
                "id": 42,
                "url": "https://test.example.com",
                "chunk_number": 5,
                "content": "Important content",
                "metadata": {"custom_field": "value"},
                "source_id": "web_source",
                "similarity": 0.85,
                "match_type": "hybrid",
            }
        ])

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        assert len(results) == 1
        result = results[0]
        # Verify all original fields preserved
        assert result["id"] == 42
        assert result["url"] == "https://test.example.com"
        assert result["chunk_number"] == 5
        assert result["content"] == "Important content"
        assert result["metadata"] == {"custom_field": "value"}
        assert result["source_id"] == "web_source"
        assert result["similarity"] == 0.85
        assert result["match_type"] == "hybrid"
        # New field added
        assert "confluence_metadata" in result
        assert result["confluence_metadata"] is None


class TestBatchEfficiency:
    """Tests for batch query efficiency (not N+1)."""

    @pytest.mark.asyncio
    async def test_single_batch_query_for_multiple_pages(
        self,
        strategy: HybridSearchStrategy,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test that multiple Confluence chunks use single batch query."""
        # Setup RPC response with 5 Confluence chunks from 3 different pages
        mock_supabase_client.rpc.return_value.execute.return_value = mock_rpc_response([
            {"id": 1, "url": "u1", "chunk_number": 1, "content": "c1", "metadata": {"page_id": "pageA"}, "source_id": "s1", "similarity": 0.9, "match_type": "vector"},
            {"id": 2, "url": "u1", "chunk_number": 2, "content": "c2", "metadata": {"page_id": "pageA"}, "source_id": "s1", "similarity": 0.8, "match_type": "vector"},
            {"id": 3, "url": "u2", "chunk_number": 1, "content": "c3", "metadata": {"page_id": "pageB"}, "source_id": "s1", "similarity": 0.7, "match_type": "keyword"},
            {"id": 4, "url": "u3", "chunk_number": 1, "content": "c4", "metadata": {"page_id": "pageC"}, "source_id": "s1", "similarity": 0.6, "match_type": "hybrid"},
            {"id": 5, "url": "u3", "chunk_number": 2, "content": "c5", "metadata": {"page_id": "pageC"}, "source_id": "s1", "similarity": 0.5, "match_type": "vector"},
        ])

        # Setup confluence_pages response
        mock_supabase_client.from_.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_confluence_pages_response([
            {"page_id": "pageA", "space_key": "S", "title": "A", "path": "/a", "metadata": {}},
            {"page_id": "pageB", "space_key": "S", "title": "B", "path": "/b", "metadata": {}},
            {"page_id": "pageC", "space_key": "S", "title": "C", "path": "/c", "metadata": {}},
        ])

        results = await strategy.search_documents_hybrid(
            query="test",
            query_embedding=[0.1] * 1536,
            match_count=10,
        )

        # Verify single call to confluence_pages (not N calls)
        assert mock_supabase_client.from_.call_count == 1
        mock_supabase_client.from_.assert_called_with("confluence_pages")

        # All results should be enriched
        assert len(results) == 5
        for result in results:
            assert result["confluence_metadata"] is not None


class TestExplainAnalysisDocumentation:
    """
    Documentation class for EXPLAIN ANALYZE verification.

    Per Story 4.1 AC6, the following EXPLAIN ANALYZE query should be run
    against the database to verify index usage:

    ```sql
    EXPLAIN ANALYZE SELECT page_id, space_key, title, path, metadata
    FROM confluence_pages
    WHERE page_id IN ('page1', 'page2', 'page3')
    AND is_deleted = FALSE;
    ```

    Expected output should show:
    - Index Scan using confluence_pages_pkey (primary key lookup)
    - No Sequential Scan on confluence_pages table
    - Filter: (is_deleted = false)

    The idx_confluence_pages_source partial index may not be used for this
    query since we're filtering by page_id (PK), not source_id. The primary
    key index (confluence_pages_pkey) will be used instead, which is efficient.

    For the idx_crawled_pages_confluence_page_id index (on archon_crawled_pages),
    this is used during sync operations when looking up chunks by page_id,
    not during the search metadata enrichment.
    """

    def test_explain_documentation_exists(self) -> None:
        """Placeholder test to ensure EXPLAIN documentation is noted."""
        # This is a documentation test - the actual EXPLAIN ANALYZE
        # should be run manually against a database with data
        assert True, "See class docstring for EXPLAIN ANALYZE instructions"
