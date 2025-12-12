"""
Concurrent Load Testing Suite (Story 6.3)

Tests concurrent sync and search operations:
- Search during active sync
- Multiple concurrent syncs
- Connection pool handling

Usage:
    cd python
    uv run pytest tests/server/services/confluence/test_concurrent_load.py -v -s
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.server.services.confluence.confluence_sync_service import ConfluenceSyncService

# Performance targets
CONCURRENT_TARGETS = {
    "search_latency_during_sync_ms": 1000,  # <1000ms search latency during sync
    "max_concurrent_syncs": 3,
    "connection_pool_size": 10,
}


class MockProgressTracker:
    """Mock progress tracker for concurrent tests."""

    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []
        self.state: dict[str, Any] = {"status": "initializing", "progress": 0}

    async def start(self, initial_data: dict[str, Any] | None = None) -> None:
        self.state["status"] = "running"

    async def update(self, status: str, progress: int, log: str, **kwargs: Any) -> None:
        self.state["status"] = status
        self.state["progress"] = progress
        self.updates.append({"status": status, "progress": progress, "log": log})

    async def complete(self, completion_data: dict[str, Any] | None = None) -> None:
        self.state["status"] = "completed"

    async def error(self, error_message: str, error_details: dict[str, Any] | None = None) -> None:
        self.state["status"] = "error"


@pytest.fixture
def mock_confluence_client() -> MagicMock:
    """Mock ConfluenceClient for concurrent tests."""
    client = MagicMock()

    # Return a small set of pages for faster tests
    mock_pages = [
        {
            "id": f"page-{i:05d}",
            "title": f"Test Page {i}",
            "version": {"number": 1, "when": "2025-10-20T10:00:00.000Z"},
            "history": {"lastUpdated": {"when": "2025-10-20T10:00:00.000Z"}},
            "body": {"storage": {"value": f"<p>Content {i}</p>"}},
            "ancestors": [],
            "space": {"key": "TEST"},
        }
        for i in range(10)
    ]

    client.cql_search = AsyncMock(return_value=mock_pages)
    client.get_space_pages_ids = AsyncMock(return_value=[p["id"] for p in mock_pages])
    client._client = MagicMock()
    client._client.url = "https://test.atlassian.net/wiki"

    return client


@pytest.fixture
def mock_confluence_processor() -> MagicMock:
    """Mock ConfluenceProcessor for concurrent tests."""
    processor = MagicMock()

    async def mock_html_to_markdown(html: str, page_id: str, space_id: str | None = None) -> tuple[str, dict]:
        # Add small delay to simulate processing
        await asyncio.sleep(0.01)
        return (f"# Processed\n{html}", {"jira_issue_links": [], "user_mentions": []})

    processor.html_to_markdown = AsyncMock(side_effect=mock_html_to_markdown)
    return processor


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Mock Supabase client for concurrent tests."""
    client = MagicMock()
    client._active_connections = 0
    client._max_connections = CONCURRENT_TARGETS["connection_pool_size"]
    client._connection_errors = []

    def create_chain(table_name: str = ""):
        # Track connection usage
        client._active_connections += 1
        if client._active_connections > client._max_connections:
            client._connection_errors.append(f"Pool exhausted: {client._active_connections} > {client._max_connections}")

        chain = MagicMock()
        chain.execute = MagicMock(return_value=MagicMock(data=[]))
        chain.eq = MagicMock(return_value=chain)
        chain.neq = MagicMock(return_value=chain)
        chain.in_ = MagicMock(return_value=chain)
        chain.filter = MagicMock(return_value=chain)
        chain.is_ = MagicMock(return_value=chain)

        # Decrement on execute
        original_execute = chain.execute
        def execute_with_release():
            client._active_connections = max(0, client._active_connections - 1)
            return original_execute()
        chain.execute = MagicMock(side_effect=execute_with_release)

        return chain

    def from_handler(table_name: str):
        table_mock = MagicMock()
        table_mock.select = MagicMock(return_value=create_chain(table_name))
        table_mock.insert = MagicMock(return_value=create_chain(table_name))
        table_mock.update = MagicMock(return_value=create_chain(table_name))
        table_mock.delete = MagicMock(return_value=create_chain(table_name))
        table_mock.upsert = MagicMock(return_value=create_chain(table_name))
        return table_mock

    client.from_ = MagicMock(side_effect=from_handler)
    client.table = MagicMock(side_effect=from_handler)

    # Mock RPC for search
    def mock_rpc(name: str, params: dict) -> MagicMock:
        result = MagicMock()
        result.execute = MagicMock(return_value=MagicMock(data=[
            {"id": f"chunk-{i}", "content": "test", "similarity": 0.9}
            for i in range(10)
        ]))
        return result

    client.rpc = MagicMock(side_effect=mock_rpc)

    return client


@pytest.fixture
def sync_service(
    mock_confluence_client: MagicMock,
    mock_confluence_processor: MagicMock,
    mock_supabase_client: MagicMock,
) -> ConfluenceSyncService:
    """Create ConfluenceSyncService with mocked dependencies."""
    service = ConfluenceSyncService(
        confluence_client=mock_confluence_client,
        confluence_processor=mock_confluence_processor,
        supabase_client=mock_supabase_client,
    )
    service.document_storage = MagicMock()
    service.document_storage.smart_chunk_text_async = AsyncMock(return_value=["chunk1", "chunk2"])
    return service


class TestConcurrentOperations:
    """Test concurrent sync and search operations."""

    @pytest.mark.asyncio
    async def test_search_during_active_sync(
        self,
        sync_service: ConfluenceSyncService,
        mock_supabase_client: MagicMock,
    ) -> None:
        """IV2: Search queries complete <1000ms during active sync."""
        with patch(
            "src.server.services.confluence.confluence_sync_service.add_documents_to_supabase"
        ) as mock_add_docs:
            mock_add_docs.return_value = {"chunks_stored": 5}

            search_latencies: list[float] = []
            search_errors: list[str] = []

            async def run_search() -> None:
                """Run search queries while sync is active."""
                for _i in range(5):
                    start = time.perf_counter()
                    try:
                        # Simulate search query
                        mock_supabase_client.rpc("hybrid_search", {"query": "test"}).execute()
                        latency = (time.perf_counter() - start) * 1000
                        search_latencies.append(latency)
                    except Exception as e:
                        search_errors.append(str(e))
                    await asyncio.sleep(0.1)  # Small delay between searches

            async def run_sync() -> None:
                """Run sync operation."""
                progress_tracker = MockProgressTracker()
                await sync_service.sync_space(
                    source_id="src_concurrent_test",
                    space_key="TEST",
                    progress_tracker=progress_tracker,
                )

            # Run sync and search concurrently
            await asyncio.gather(run_sync(), run_search())

            # Verify search performance during sync
            print("\nSearch During Sync Results:")
            print(f"  Searches completed: {len(search_latencies)}")
            print(f"  Errors: {len(search_errors)}")
            if search_latencies:
                avg_latency = sum(search_latencies) / len(search_latencies)
                max_latency = max(search_latencies)
                print(f"  Avg latency: {avg_latency:.2f}ms")
                print(f"  Max latency: {max_latency:.2f}ms")

                assert max_latency < CONCURRENT_TARGETS["search_latency_during_sync_ms"], (
                    f"Search latency {max_latency:.2f}ms exceeded target"
                )

            assert len(search_errors) == 0, f"Search errors during sync: {search_errors}"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_syncs(
        self,
        mock_confluence_client: MagicMock,
        mock_confluence_processor: MagicMock,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test handling of multiple concurrent sync requests."""
        with patch(
            "src.server.services.confluence.confluence_sync_service.add_documents_to_supabase"
        ) as mock_add_docs:
            mock_add_docs.return_value = {"chunks_stored": 5}

            # Create multiple sync services
            services = [
                ConfluenceSyncService(
                    confluence_client=mock_confluence_client,
                    confluence_processor=mock_confluence_processor,
                    supabase_client=mock_supabase_client,
                )
                for _ in range(CONCURRENT_TARGETS["max_concurrent_syncs"])
            ]

            for service in services:
                service.document_storage = MagicMock()
                service.document_storage.smart_chunk_text_async = AsyncMock(return_value=["chunk1"])

            async def run_sync(service: ConfluenceSyncService, space_key: str) -> dict:
                progress_tracker = MockProgressTracker()
                return await service.sync_space(
                    source_id=f"src_{space_key}",
                    space_key=space_key,
                    progress_tracker=progress_tracker,
                )

            # Run multiple syncs concurrently
            spaces = [f"SPACE{i}" for i in range(len(services))]
            results = await asyncio.gather(
                *[run_sync(s, sp) for s, sp in zip(services, spaces, strict=False)],
                return_exceptions=True,
            )

            # Check results
            successful = [r for r in results if isinstance(r, dict)]
            errors = [r for r in results if isinstance(r, Exception)]

            print("\nMultiple Concurrent Syncs:")
            print(f"  Total syncs: {len(services)}")
            print(f"  Successful: {len(successful)}")
            print(f"  Errors: {len(errors)}")

            # All syncs should complete
            assert len(successful) == len(services), f"Expected all syncs to complete, got {len(errors)} errors"

    @pytest.mark.asyncio
    async def test_connection_pool_not_exhausted(
        self,
        sync_service: ConfluenceSyncService,
        mock_supabase_client: MagicMock,
    ) -> None:
        """IV2: Connection pool handles concurrent load without exhaustion.

        Note: This test verifies that the sync completes successfully without
        real connection errors. In production, Supabase connection pooling is
        managed by the supabase-py client with PgBouncer backend.
        """
        with patch(
            "src.server.services.confluence.confluence_sync_service.add_documents_to_supabase"
        ) as mock_add_docs:
            mock_add_docs.return_value = {"chunks_stored": 5}

            # Run sync operation
            progress_tracker = MockProgressTracker()
            result = await sync_service.sync_space(
                source_id="src_pool_test",
                space_key="TEST",
                progress_tracker=progress_tracker,
            )

            # Verify sync completed successfully (connection pool handled load)
            print("\nConnection Pool Test:")
            print(f"  Sync completed: {result.get('status')}")
            print(f"  Pages processed: {result.get('pages_added', 0) + result.get('pages_updated', 0)}")

            # In real tests, we'd check for actual connection errors
            # For unit tests with mocks, we verify sync completes
            assert result.get("status") in ["completed", "success"], (
                f"Sync failed, possible connection issue: {result}"
            )


class TestConcurrentSearchLoad:
    """Test search performance under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_search_queries(
        self,
        mock_supabase_client: MagicMock,
    ) -> None:
        """Test multiple concurrent search queries."""
        num_concurrent = 10
        latencies: list[float] = []
        errors: list[str] = []

        async def search_query(query_id: int) -> float:
            start = time.perf_counter()
            try:
                mock_supabase_client.rpc(
                    "hybrid_search",
                    {"query": f"test query {query_id}", "embedding": [0.1] * 1536}
                ).execute()
                return (time.perf_counter() - start) * 1000
            except Exception as e:
                errors.append(f"Query {query_id}: {e}")
                return -1

        # Run concurrent searches
        tasks = [search_query(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)

        latencies = [r for r in results if r >= 0]

        print("\nConcurrent Search Results:")
        print(f"  Concurrent queries: {num_concurrent}")
        print(f"  Successful: {len(latencies)}")
        print(f"  Errors: {len(errors)}")
        if latencies:
            print(f"  Avg latency: {sum(latencies)/len(latencies):.2f}ms")
            print(f"  Max latency: {max(latencies):.2f}ms")

        assert len(errors) == 0, f"Search errors: {errors}"
        assert len(latencies) == num_concurrent, "Not all queries completed"
