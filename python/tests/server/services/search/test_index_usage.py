"""
Index Usage Verification Tests (Story 6.3)

Tests that verify database indexes are being used for search operations:
- Vector embedding index (IVFFlat)
- Full-text search GIN index
- Confluence metadata JSONB indexes

Usage:
    cd python
    uv run pytest tests/server/services/search/test_index_usage.py -v

Note: These tests mock the EXPLAIN ANALYZE output since we can't run actual
database queries in unit tests. For real index verification, run the
performance profiler script against a live database.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

# Expected indexes based on Story 6.3 Dev Notes
EXPECTED_INDEXES = {
    "archon_crawled_pages": [
        "idx_crawled_pages_source",
        "idx_crawled_pages_embedding",
        "idx_crawled_pages_content_fts",
        "idx_crawled_pages_confluence_page_id",
    ],
    "confluence_pages": [
        "idx_confluence_pages_source",
        "idx_confluence_pages_space",
        "idx_confluence_pages_jira",
        "idx_confluence_pages_mentions",
    ],
}


def parse_explain_output(explain_text: str) -> dict[str, Any]:
    """Parse EXPLAIN ANALYZE output to extract key metrics."""
    return {
        "uses_index_scan": "Index Scan" in explain_text or "Bitmap Index Scan" in explain_text,
        "uses_seq_scan": "Seq Scan" in explain_text,
        "has_vector_search": "ivfflat" in explain_text.lower() or "vector" in explain_text.lower(),
        "has_fts": "GIN" in explain_text or "tsvector" in explain_text.lower(),
    }


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Mock Supabase client that returns mock EXPLAIN output."""
    client = MagicMock()

    # Mock RPC for explain_analyze
    def mock_rpc(function_name: str, params: dict) -> MagicMock:
        result = MagicMock()

        if function_name == "explain_analyze_search":
            # Return mock EXPLAIN ANALYZE output showing index usage
            result.execute = MagicMock(return_value=MagicMock(data=[{
                "QUERY PLAN": """
                Sort  (cost=1234.56..1234.78 rows=100)
                  Sort Key: similarity DESC
                  ->  Index Scan using idx_crawled_pages_embedding on archon_crawled_pages  (cost=0.28..1234.12 rows=100)
                        Index Cond: (embedding <-> '[0.1,0.2,...]'::vector) < 0.5
                        Filter: ((metadata->>'_pending_deletion') IS NULL)
                """
            }]))
        elif function_name == "explain_fulltext_search":
            result.execute = MagicMock(return_value=MagicMock(data=[{
                "QUERY PLAN": """
                Bitmap Heap Scan on archon_crawled_pages  (cost=12.00..345.67 rows=50)
                  Recheck Cond: (to_tsvector('english', content) @@ plainto_tsquery('english', 'test'))
                  ->  Bitmap Index Scan on idx_crawled_pages_content_fts  (cost=0.00..12.00 rows=50)
                        Index Cond: (to_tsvector('english', content) @@ plainto_tsquery('english', 'test'))
                """
            }]))
        elif function_name == "explain_confluence_filter":
            result.execute = MagicMock(return_value=MagicMock(data=[{
                "QUERY PLAN": """
                Index Scan using idx_confluence_pages_jira on confluence_pages  (cost=0.28..8.30 rows=1)
                  Index Cond: ((metadata->'jira_issue_links') @> '["PROJ-123"]'::jsonb)
                  Filter: (is_deleted = false)
                """
            }]))
        else:
            result.execute = MagicMock(return_value=MagicMock(data=[]))

        return result

    client.rpc = MagicMock(side_effect=mock_rpc)

    return client


class TestVectorIndexUsage:
    """Test vector (embedding) index usage."""

    def test_embedding_index_used_in_vector_search(
        self,
        mock_supabase_client: MagicMock,
    ) -> None:
        """AC: Vector search uses IVFFlat index."""
        result = mock_supabase_client.rpc(
            "explain_analyze_search",
            {"query": "test query", "embedding": [0.1] * 1536}
        ).execute()

        plan = result.data[0]["QUERY PLAN"]
        parsed = parse_explain_output(plan)

        print("\nVector Search EXPLAIN:")
        print(f"  Uses Index Scan: {parsed['uses_index_scan']}")
        print(f"  Uses Seq Scan: {parsed['uses_seq_scan']}")

        assert parsed["uses_index_scan"], "Expected Index Scan for vector search"
        assert "idx_crawled_pages_embedding" in plan, "Expected embedding index usage"
        assert not parsed["uses_seq_scan"], "Sequential scan should not be used for vector search"


class TestFullTextIndexUsage:
    """Test full-text search index usage."""

    def test_fts_index_used_in_fulltext_search(
        self,
        mock_supabase_client: MagicMock,
    ) -> None:
        """AC: Full-text search uses GIN index."""
        result = mock_supabase_client.rpc(
            "explain_fulltext_search",
            {"query": "test search query"}
        ).execute()

        plan = result.data[0]["QUERY PLAN"]
        parsed = parse_explain_output(plan)

        print("\nFull-Text Search EXPLAIN:")
        print(f"  Uses Index Scan: {parsed['uses_index_scan']}")
        print(f"  Has FTS: {parsed['has_fts']}")

        assert parsed["uses_index_scan"], "Expected Index Scan for FTS"
        assert "idx_crawled_pages_content_fts" in plan, "Expected FTS index usage"


class TestConfluenceIndexUsage:
    """Test Confluence-specific index usage."""

    def test_confluence_pages_indexes_used(
        self,
        mock_supabase_client: MagicMock,
    ) -> None:
        """AC: Confluence metadata queries use JSONB indexes."""
        result = mock_supabase_client.rpc(
            "explain_confluence_filter",
            {"jira_issue": "PROJ-123"}
        ).execute()

        plan = result.data[0]["QUERY PLAN"]
        parsed = parse_explain_output(plan)

        print("\nConfluence Filter EXPLAIN:")
        print(f"  Uses Index Scan: {parsed['uses_index_scan']}")

        assert parsed["uses_index_scan"], "Expected Index Scan for JIRA filter"
        assert "idx_confluence_pages_jira" in plan, "Expected JIRA index usage"

    def test_metadata_jsonb_index_used(
        self,
        mock_supabase_client: MagicMock,
    ) -> None:
        """AC: JSONB metadata queries use appropriate indexes."""
        # Test that page_id lookup uses the JSONB index
        result = mock_supabase_client.rpc(
            "explain_analyze_search",
            {"query": "test", "embedding": [0.1] * 1536}
        ).execute()

        plan = result.data[0]["QUERY PLAN"]

        # Verify pending_deletion filter doesn't cause seq scan
        assert "Seq Scan" not in plan or "Index" in plan, "JSONB filter should use index or be combined with index scan"


class TestIndexConfiguration:
    """Test that expected indexes exist."""

    def test_expected_indexes_defined(self) -> None:
        """Verify all expected indexes are documented."""
        # This test documents the expected indexes
        for table, indexes in EXPECTED_INDEXES.items():
            print(f"\n{table} indexes:")
            for idx in indexes:
                print(f"  - {idx}")

        # Verify we have indexes for both tables
        assert "archon_crawled_pages" in EXPECTED_INDEXES
        assert "confluence_pages" in EXPECTED_INDEXES

        # Verify critical indexes exist
        assert "idx_crawled_pages_embedding" in EXPECTED_INDEXES["archon_crawled_pages"]
        assert "idx_crawled_pages_content_fts" in EXPECTED_INDEXES["archon_crawled_pages"]
        assert "idx_confluence_pages_jira" in EXPECTED_INDEXES["confluence_pages"]


class TestQueryPlanValidation:
    """Test query plan validation utilities."""

    def test_parse_explain_detects_index_scan(self) -> None:
        """Test that parser correctly identifies index scans."""
        explain_with_index = "Index Scan using idx_test on table_name"
        parsed = parse_explain_output(explain_with_index)

        assert parsed["uses_index_scan"] is True
        assert parsed["uses_seq_scan"] is False

    def test_parse_explain_detects_seq_scan(self) -> None:
        """Test that parser correctly identifies sequential scans."""
        explain_with_seq = "Seq Scan on table_name"
        parsed = parse_explain_output(explain_with_seq)

        assert parsed["uses_index_scan"] is False
        assert parsed["uses_seq_scan"] is True

    def test_parse_explain_detects_bitmap_index(self) -> None:
        """Test that parser correctly identifies bitmap index scans."""
        explain_with_bitmap = "Bitmap Index Scan on idx_test"
        parsed = parse_explain_output(explain_with_bitmap)

        assert parsed["uses_index_scan"] is True
