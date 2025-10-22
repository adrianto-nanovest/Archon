"""
Tests for ConfluenceSyncService - CQL-Based Incremental Sync

This test suite validates the ConfluenceSyncService implementation including:
- CQL query construction and execution
- Page change detection (creates, updates, deletes)
- ConfluenceProcessor integration
- document_storage_service integration
- Sync metrics tracking
- ProgressTracker integration
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.server.services.confluence.confluence_sync_service import ConfluenceSyncService


# Mock document storage service
@pytest.fixture(autouse=True)
def mock_document_storage(mock_supabase_client):
    """Mock document storage operations."""
    with patch("src.server.services.confluence.confluence_sync_service.add_documents_to_supabase") as mock_add_docs:
        mock_add_docs.return_value = {"chunks_stored": 5}
        yield mock_add_docs


@pytest.fixture
def mock_confluence_client():
    """Mock ConfluenceClient with cql_search method."""
    client = MagicMock()
    client.cql_search = AsyncMock(return_value=[
        {
            "id": "123",
            "title": "Test Page",
            "version": {"number": 5},
            "history": {"lastUpdated": {"when": "2025-10-20T10:00:00Z"}},
            "body": {"storage": {"value": "<html><p>Test content</p></html>"}},
            "ancestors": [],
        }
    ])
    return client


@pytest.fixture
def mock_confluence_processor():
    """Mock ConfluenceProcessor with html_to_markdown method."""
    processor = MagicMock()
    processor.html_to_markdown = AsyncMock(return_value=(
        "# Test Page\n\nTest content",
        {
            "jira_issue_links": [],
            "user_mentions": [],
            "word_count": 150,
        }
    ))
    return processor


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client with chainable query API."""
    client = MagicMock()

    # Mock chainable query pattern for SELECT
    select_chain = MagicMock()
    eq_chain = MagicMock()
    execute_mock = MagicMock()
    execute_mock.execute = MagicMock(return_value=MagicMock(
        data=[{"metadata": {"last_sync_timestamp": "2025-10-01T00:00:00Z"}}]
    ))

    eq_chain.execute = execute_mock.execute
    select_chain.eq = MagicMock(return_value=eq_chain)
    client.from_ = MagicMock(return_value=MagicMock(select=MagicMock(return_value=select_chain)))

    return client


@pytest.fixture
def sync_service(mock_confluence_client, mock_confluence_processor, mock_supabase_client):
    """Create ConfluenceSyncService instance with mocked dependencies."""
    service = ConfluenceSyncService(
        confluence_client=mock_confluence_client,
        confluence_processor=mock_confluence_processor,
        supabase_client=mock_supabase_client,
    )
    # Mock document_storage.smart_chunk_text_async
    service.document_storage.smart_chunk_text_async = AsyncMock(
        return_value=["chunk1", "chunk2", "chunk3"]  # Return sample chunks
    )
    return service


class TestConfluenceSyncServiceInitialization:
    """Test ConfluenceSyncService initialization and configuration."""

    def test_initialization_with_all_dependencies(
        self, mock_confluence_client, mock_confluence_processor, mock_supabase_client
    ):
        """Test service initializes correctly with all dependencies."""
        service = ConfluenceSyncService(
            confluence_client=mock_confluence_client,
            confluence_processor=mock_confluence_processor,
            supabase_client=mock_supabase_client,
        )

        assert service.confluence_client == mock_confluence_client
        assert service.confluence_processor == mock_confluence_processor
        assert service.supabase_client == mock_supabase_client
        assert service.logger is not None

    def test_initialization_without_supabase_client(
        self, mock_confluence_client, mock_confluence_processor
    ):
        """Test service initializes with get_supabase_client() when client not provided."""
        with patch("src.server.services.confluence.confluence_sync_service.get_supabase_client") as mock_get_client:
            mock_get_client.return_value = MagicMock()

            service = ConfluenceSyncService(
                confluence_client=mock_confluence_client,
                confluence_processor=mock_confluence_processor,
            )

            assert service.supabase_client is not None
            mock_get_client.assert_called_once()


class TestSyncSpaceMethod:
    """Test sync_space method signature and basic structure."""

    @pytest.mark.asyncio
    async def test_sync_space_returns_metrics(self, sync_service):
        """Test sync_space returns required metrics dict."""
        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS",
        )

        # Verify required metrics keys
        assert "pages_added" in metrics
        assert "pages_updated" in metrics
        assert "pages_deleted" in metrics
        assert "duration_seconds" in metrics
        assert "api_calls_made" in metrics
        assert "last_sync_timestamp" in metrics
        assert "status" in metrics

        # Verify metric types
        assert isinstance(metrics["pages_added"], int)
        assert isinstance(metrics["pages_updated"], int)
        assert isinstance(metrics["pages_deleted"], int)
        assert isinstance(metrics["duration_seconds"], float)
        assert isinstance(metrics["api_calls_made"], int)
        assert isinstance(metrics["last_sync_timestamp"], str)
        assert isinstance(metrics["status"], str)

    @pytest.mark.asyncio
    async def test_sync_space_with_progress_tracker(self, sync_service):
        """Test sync_space accepts optional progress_tracker parameter."""
        mock_progress_tracker = MagicMock()
        mock_progress_tracker.update = AsyncMock()
        mock_progress_tracker.complete = AsyncMock()

        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS",
            progress_tracker=mock_progress_tracker,
        )

        assert metrics is not None

    @pytest.mark.asyncio
    async def test_sync_space_duration_tracking(self, sync_service):
        """Test sync_space tracks duration correctly."""
        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS",
        )

        # Duration should be small but non-zero for quick test execution
        assert metrics["duration_seconds"] >= 0.0
        assert metrics["duration_seconds"] < 10.0  # Should complete in under 10 seconds

    @pytest.mark.asyncio
    async def test_sync_space_timestamp_format(self, sync_service):
        """Test sync_space generates valid ISO 8601 timestamp."""
        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS",
        )

        # Verify timestamp is valid ISO 8601
        timestamp = metrics["last_sync_timestamp"]
        parsed = datetime.fromisoformat(timestamp)
        assert parsed.tzinfo is not None  # Should have timezone info
        assert parsed.year == datetime.now(UTC).year  # Should be current year


# Tests for Task 2: CQL-based changed page detection
class TestCQLQueryConstruction:
    """Tests for Task 2: CQL-based changed page detection."""

    @pytest.mark.asyncio
    async def test_first_sync_uses_epoch_timestamp(self, sync_service, mock_confluence_client):
        """Test first sync (NULL last_sync_timestamp) fetches all pages since epoch."""
        # Mock empty metadata (first sync)
        sync_service.supabase_client.from_ = MagicMock(return_value=MagicMock(
            select=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    execute=MagicMock(return_value=MagicMock(
                        data=[{"metadata": {}}]  # No last_sync_timestamp
                    ))
                ))
            ))
        ))

        # Mock CQL search to return empty results
        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify CQL query used epoch timestamp
        mock_confluence_client.cql_search.assert_called_once()
        cql_query = mock_confluence_client.cql_search.call_args[1]["cql"]
        assert "1970-01-01T00:00:00Z" in cql_query
        assert "space = DEVDOCS" in cql_query

    @pytest.mark.asyncio
    async def test_incremental_sync_uses_last_timestamp(self, sync_service, mock_confluence_client):
        """Test incremental sync uses last_sync_timestamp from previous sync."""
        # Mock existing last_sync_timestamp
        test_timestamp = "2025-10-15T10:00:00Z"
        sync_service.supabase_client.from_ = MagicMock(return_value=MagicMock(
            select=MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(
                    execute=MagicMock(return_value=MagicMock(
                        data=[{"metadata": {"last_sync_timestamp": test_timestamp}}]
                    ))
                ))
            ))
        ))

        # Mock CQL search
        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify CQL query used stored timestamp
        mock_confluence_client.cql_search.assert_called_once()
        cql_query = mock_confluence_client.cql_search.call_args[1]["cql"]
        assert test_timestamp in cql_query
        assert "space = DEVDOCS" in cql_query

    @pytest.mark.asyncio
    async def test_cql_query_format(self, sync_service, mock_confluence_client):
        """Test CQL query format matches expected pattern."""
        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        await sync_service.sync_space(
            source_id="src_123",
            space_key="TESTSPACE"
        )

        # Verify CQL query format
        cql_query = mock_confluence_client.cql_search.call_args[1]["cql"]
        assert 'space = TESTSPACE AND lastModified >= "' in cql_query

    @pytest.mark.asyncio
    async def test_cql_search_expansion_parameters(self, sync_service, mock_confluence_client):
        """Test CQL search uses correct expansion parameters."""
        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify expansion parameters
        mock_confluence_client.cql_search.assert_called_once()
        call_args = mock_confluence_client.cql_search.call_args[1]
        assert call_args["expand"] == "body.storage,version,ancestors"
        assert call_args["limit"] == 10000

    @pytest.mark.asyncio
    async def test_api_calls_tracked(self, sync_service, mock_confluence_client):
        """Test API calls are tracked in metrics."""
        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify API call counter incremented
        assert metrics["api_calls_made"] >= 1

    @pytest.mark.asyncio
    async def test_timestamp_stored_after_successful_sync(self, sync_service, mock_confluence_client):
        """Test new timestamp is stored in archon_sources after sync."""
        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        # Mock update method
        update_mock = MagicMock()
        eq_mock = MagicMock()
        execute_mock = MagicMock(return_value=MagicMock(data=[]))
        eq_mock.execute = execute_mock
        update_mock.eq = MagicMock(return_value=eq_mock)

        # Override from_ to return our mock chain
        original_from = sync_service.supabase_client.from_

        def mock_from(table):
            if table == "archon_sources":
                # Return different mocks for select vs update
                call_count = [0]

                class MockTable:
                    def select(self, *args):
                        return original_from(table).select(*args)

                    def update(self, data):
                        call_count[0] += 1
                        # Store update data for verification
                        self._update_data = data
                        return update_mock

                return MockTable()
            return original_from(table)

        sync_service.supabase_client.from_ = mock_from

        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify update was called with new timestamp
        update_mock.eq.assert_called_once_with("source_id", "src_123")
        assert metrics["last_sync_timestamp"] is not None
        assert "T" in metrics["last_sync_timestamp"]  # ISO 8601 format

    @pytest.mark.asyncio
    async def test_changed_pages_logged(self, sync_service, mock_confluence_client, caplog):
        """Test number of changed pages is logged."""
        test_pages = [
            {"id": "1", "title": "Page 1"},
            {"id": "2", "title": "Page 2"},
            {"id": "3", "title": "Page 3"},
        ]
        mock_confluence_client.cql_search = AsyncMock(return_value=test_pages)

        with caplog.at_level("INFO"):
            await sync_service.sync_space(
                source_id="src_123",
                space_key="DEVDOCS"
            )

        # Verify logging
        assert "3 changed pages" in caplog.text or "CQL search returned 3" in caplog.text


class TestPageProcessing:
    """Tests for Task 3: Process changed pages with ConfluenceProcessor."""

    @pytest.mark.asyncio
    async def test_processes_page_with_confluence_processor(self, sync_service, mock_confluence_client, mock_confluence_processor):
        """Test page HTML is processed with ConfluenceProcessor."""
        test_page = {
            "id": "123",
            "title": "Test Page",
            "version": {"number": 5},
            "history": {"lastUpdated": {"when": "2025-10-20T10:00:00Z"}},
            "body": {"storage": {"value": "<html><p>Test content</p></html>"}},
            "ancestors": [],
        }
        mock_confluence_client.cql_search = AsyncMock(return_value=[test_page])

        await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify processor was called with correct arguments
        mock_confluence_processor.html_to_markdown.assert_called_once()
        call_args = mock_confluence_processor.html_to_markdown.call_args[1]
        assert call_args["html"] == "<html><p>Test content</p></html>"
        assert call_args["page_id"] == "123"
        assert call_args["space_id"] == "DEVDOCS"

    @pytest.mark.asyncio
    async def test_stores_metadata_in_confluence_pages_table(self, sync_service, mock_confluence_client, mock_confluence_processor):
        """Test page metadata is stored in confluence_pages table."""
        test_page = {
            "id": "123",
            "title": "Test Page",
            "version": {"number": 5},
            "history": {"lastUpdated": {"when": "2025-10-20T10:00:00Z"}},
            "body": {"storage": {"value": "<p>Content</p>"}},
            "ancestors": [{"id": "parent123"}],
        }
        mock_confluence_client.cql_search = AsyncMock(return_value=[test_page])

        # Mock upsert for confluence_pages
        upsert_mock = MagicMock()
        execute_mock = MagicMock(return_value=MagicMock(data=[]))
        upsert_mock.execute = execute_mock

        # Track table operations
        upsert_data = {}

        def track_upsert(table):
            class MockTable:
                def upsert(self, data, **kwargs):
                    nonlocal upsert_data
                    upsert_data[table] = data
                    return upsert_mock

                def select(self, *args):
                    # Mock version check for new pages
                    return MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            execute=MagicMock(return_value=MagicMock(data=[]))  # No existing page
                        ))
                    )

                def update(self, *args):
                    return sync_service.supabase_client.from_(table).update(*args)

                def delete(self):
                    return MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                        ))
                    )

            return MockTable()

        def mock_from_wrapper(table):
            if table == "confluence_pages":
                return track_upsert(table)
            elif table == "archon_crawled_pages":
                # Mock delete for chunks
                return MagicMock(
                    delete=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                        ))
                    ))
                )
            else:
                return original_from(table)

        original_from = sync_service.supabase_client.from_
        sync_service.supabase_client.from_ = mock_from_wrapper

        await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify confluence_pages was upserted
        assert "confluence_pages" in upsert_data
        page_data = upsert_data["confluence_pages"]
        assert page_data["page_id"] == "123"
        assert page_data["source_id"] == "src_123"
        assert page_data["space_key"] == "DEVDOCS"
        assert page_data["title"] == "Test Page"
        assert page_data["version"] == 5
        assert page_data["is_deleted"] is False
        assert page_data["path"] == "/parent123/123"  # Materialized path from ancestors
        assert "metadata" in page_data

    @pytest.mark.asyncio
    async def test_materialized_path_computation(self, sync_service, mock_confluence_client, mock_confluence_processor):
        """Test materialized path is computed correctly from ancestors."""
        test_page = {
            "id": "page3",
            "title": "Child Page",
            "version": {"number": 1},
            "history": {"lastUpdated": {"when": "2025-10-20T10:00:00Z"}},
            "body": {"storage": {"value": "<p>Content</p>"}},
            "ancestors": [{"id": "root"}, {"id": "parent"}],
        }
        mock_confluence_client.cql_search = AsyncMock(return_value=[test_page])

        upsert_data = {}

        def track_upsert(table):
            class MockTable:
                def upsert(self, data, **kwargs):
                    upsert_data[table] = data
                    return MagicMock(execute=MagicMock(return_value=MagicMock(data=[])))

                def select(self, *args):
                    # Mock version check for new pages
                    return MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            execute=MagicMock(return_value=MagicMock(data=[]))
                        ))
                    )

                def update(self, *args):
                    return sync_service.supabase_client.from_(table).update(*args)

                def delete(self):
                    return MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                        ))
                    )

            return MockTable()

        def mock_from_wrapper(table):
            if table == "confluence_pages":
                return track_upsert(table)
            elif table == "archon_crawled_pages":
                # Mock delete for chunks
                return MagicMock(
                    delete=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(
                            eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                        ))
                    ))
                )
            else:
                return original_from(table)

        original_from = sync_service.supabase_client.from_
        sync_service.supabase_client.from_ = mock_from_wrapper

        await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify materialized path format
        assert "confluence_pages" in upsert_data
        assert upsert_data["confluence_pages"]["path"] == "/root/parent/page3"

    @pytest.mark.asyncio
    async def test_skips_pages_without_html_content(self, sync_service, mock_confluence_client, mock_confluence_processor, caplog):
        """Test pages without HTML content are skipped with warning."""
        test_pages = [
            {
                "id": "empty_page",
                "title": "Empty Page",
                "version": {"number": 1},
                "history": {"lastUpdated": {"when": "2025-10-20T10:00:00Z"}},
                "body": {},  # No storage/value
                "ancestors": [],
            },
            {
                "id": "valid_page",
                "title": "Valid Page",
                "version": {"number": 1},
                "history": {"lastUpdated": {"when": "2025-10-20T10:00:00Z"}},
                "body": {"storage": {"value": "<p>Content</p>"}},
                "ancestors": [],
            }
        ]
        mock_confluence_client.cql_search = AsyncMock(return_value=test_pages)

        with caplog.at_level("WARNING"):
            await sync_service.sync_space(
                source_id="src_123",
                space_key="DEVDOCS"
            )

        # Verify warning logged for empty page
        assert "empty_page" in caplog.text and "no HTML content" in caplog.text

        # Verify processor only called once (for valid page)
        assert mock_confluence_processor.html_to_markdown.call_count == 1


class TestDocumentStorage:
    """Tests for Task 4: Call document_storage_service for chunking."""
    pass


class TestPageChangeDetection:
    """Tests for Task 5: Handle page creates, updates, deletes."""
    pass


class TestMetricsTracking:
    """Tests for Task 6: Track sync metrics."""
    pass


class TestProgressIntegration:
    """Tests for Task 7: Integrate with ProgressTracker."""
    pass
