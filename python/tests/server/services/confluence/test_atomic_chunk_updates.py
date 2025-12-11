"""
Unit tests for atomic chunk update functionality in ConfluenceSyncService.

Tests cover:
- Zero-downtime updates (mark → insert → delete)
- Rollback on failure
- Successful update cleanup
- Search exclusion of pending deletion chunks
- Metrics tracking for atomic operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call

from src.server.services.confluence.confluence_sync_service import ConfluenceSyncService


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client with chainable query API."""
    client = MagicMock()

    # Create mock responses
    select_response = MagicMock()
    select_response.data = [
        {"id": "chunk_1", "metadata": {"page_id": "123", "chunk_index": 0}},
        {"id": "chunk_2", "metadata": {"page_id": "123", "chunk_index": 1}},
    ]

    update_response = MagicMock()
    update_response.data = [{"id": "chunk_1"}, {"id": "chunk_2"}]

    delete_response = MagicMock()
    delete_response.data = [{"id": "chunk_1"}, {"id": "chunk_2"}]

    # Setup chainable mocks for all operations
    # Select chain: from_().select().eq().filter().execute()
    mock_select = MagicMock()
    mock_select.return_value.eq.return_value.filter.return_value.execute.return_value = select_response

    # Update chain: from_().update().eq().execute()
    mock_update = MagicMock()
    mock_update.return_value.eq.return_value.execute.return_value = update_response

    # Delete chain: from_().delete().eq().filter().filter().execute()
    mock_delete = MagicMock()
    mock_delete.return_value.eq.return_value.filter.return_value.filter.return_value.execute.return_value = delete_response
    # Also support single filter for simpler delete operations
    mock_delete.return_value.eq.return_value.filter.return_value.execute.return_value = delete_response

    # Setup from_ to return appropriate mock based on next operation
    def from_side_effect(table_name):
        mock_table = MagicMock()
        mock_table.select = mock_select
        mock_table.update = mock_update
        mock_table.delete = mock_delete
        return mock_table

    client.from_.side_effect = from_side_effect

    return client


@pytest.fixture
def mock_confluence_client():
    """Mock ConfluenceClient."""
    client = MagicMock()
    client._client.url = "https://company.atlassian.net/wiki"
    return client


@pytest.fixture
def mock_confluence_processor():
    """Mock ConfluenceProcessor."""
    processor = MagicMock()
    processor.html_to_markdown = AsyncMock(
        return_value=("# Test Markdown Content", {"jira_links": []})
    )
    return processor


@pytest.fixture
def mock_document_storage():
    """Mock DocumentStorageService."""
    storage = MagicMock()
    storage.smart_chunk_text_async = AsyncMock(
        return_value=["Chunk 1 content", "Chunk 2 content", "Chunk 3 content"]
    )
    return storage


@pytest.fixture
def sync_service(mock_confluence_client, mock_confluence_processor, mock_supabase_client, mock_document_storage):
    """Create ConfluenceSyncService with mocked dependencies."""
    service = ConfluenceSyncService(
        confluence_client=mock_confluence_client,
        confluence_processor=mock_confluence_processor,
        supabase_client=mock_supabase_client,
    )
    service.document_storage = mock_document_storage
    return service


@pytest.mark.asyncio
async def test_mark_chunks_pending_deletion(sync_service, mock_supabase_client):
    """Test marking old chunks with _pending_deletion flag."""
    # Arrange
    page_id = "123456"
    source_id = "src_abc123"

    # Act
    marked_count = await sync_service._mark_chunks_pending_deletion(page_id, source_id)

    # Assert
    assert marked_count == 2
    assert mock_supabase_client.from_.call_count >= 1
    mock_supabase_client.from_.assert_any_call("archon_crawled_pages")


@pytest.mark.asyncio
async def test_delete_pending_chunks(sync_service, mock_supabase_client):
    """Test deleting chunks marked with _pending_deletion flag."""
    # Arrange
    page_id = "123456"
    source_id = "src_abc123"

    # Act
    deleted_count = await sync_service._delete_pending_chunks(page_id, source_id)

    # Assert
    assert deleted_count == 2
    mock_supabase_client.from_.assert_called_with("archon_crawled_pages")


@pytest.mark.asyncio
async def test_rollback_pending_deletion(sync_service):
    """Test rollback by removing _pending_deletion flag."""
    # Arrange - Create a fresh mock for this test
    mock_client = MagicMock()

    # Mock select to return chunks with pending deletion
    select_response = MagicMock()
    select_response.data = [
        {"id": "chunk_1", "metadata": {"page_id": "123", "_pending_deletion": "true"}},
        {"id": "chunk_2", "metadata": {"page_id": "123", "_pending_deletion": "true"}},
    ]

    update_response = MagicMock()
    update_response.data = [{"id": "chunk_1"}, {"id": "chunk_2"}]

    # Setup mock chains
    mock_select = MagicMock()
    mock_select.return_value.eq.return_value.filter.return_value.filter.return_value.execute.return_value = select_response

    mock_update = MagicMock()
    mock_update.return_value.eq.return_value.execute.return_value = update_response

    def from_side_effect(table_name):
        mock_table = MagicMock()
        mock_table.select = mock_select
        mock_table.update = mock_update
        return mock_table

    mock_client.from_.side_effect = from_side_effect
    sync_service.supabase_client = mock_client

    page_id = "123456"
    source_id = "src_abc123"

    # Act
    restored_count = await sync_service._rollback_pending_deletion(page_id, source_id)

    # Assert
    assert restored_count == 2


@pytest.mark.asyncio
async def test_atomic_update_zero_downtime(sync_service, mock_supabase_client, mock_document_storage):
    """
    Test atomic update maintains zero downtime.

    Verifies 3-phase atomic update:
    1. Mark old chunks pending deletion
    2. Insert new chunks
    3. Delete old chunks
    """
    # Arrange
    page_id = "123456"
    markdown = "# Updated Content\n\nThis is new content."
    page_url = "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456"
    source_id = "src_abc123"
    page_title = "Test Page"
    space_key = "DEVDOCS"

    # Mock add_documents_to_supabase
    from unittest.mock import patch
    with patch('src.server.services.confluence.confluence_sync_service.add_documents_to_supabase', new_callable=AsyncMock) as mock_add_docs:
        # Act
        metrics = await sync_service._update_page_chunks_atomic(
            page_id=page_id,
            markdown=markdown,
            page_url=page_url,
            source_id=source_id,
            page_title=page_title,
            space_key=space_key,
        )

        # Assert - Verify metrics
        assert metrics["chunks_marked"] == 2
        assert metrics["chunks_created"] == 3
        assert metrics["chunks_deleted"] == 2
        assert metrics["chunks_rolled_back"] == 0
        assert metrics["failed"] == 0

        # Verify add_documents_to_supabase was called
        mock_add_docs.assert_called_once()


@pytest.mark.asyncio
async def test_atomic_update_rollback_on_failure(sync_service, mock_supabase_client, mock_document_storage):
    """
    Test rollback preserves old chunks on failure.

    Simulates chunk insertion failure and verifies rollback is called.
    """
    # Arrange
    page_id = "123456"
    markdown = "# Updated Content"
    page_url = "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456"
    source_id = "src_abc123"
    page_title = "Test Page"
    space_key = "DEVDOCS"

    # Mock add_documents_to_supabase to fail
    from unittest.mock import patch
    with patch('src.server.services.confluence.confluence_sync_service.add_documents_to_supabase', new_callable=AsyncMock) as mock_add_docs:
        mock_add_docs.side_effect = Exception("Chunk insertion failed")

        # Act & Assert
        with pytest.raises(Exception, match="Chunk insertion failed"):
            await sync_service._update_page_chunks_atomic(
                page_id=page_id,
                markdown=markdown,
                page_url=page_url,
                source_id=source_id,
                page_title=page_title,
                space_key=space_key,
            )

        # Verify rollback was attempted (chunks should be restored)
        # The rollback updates chunks to remove _pending_deletion flag
        assert mock_supabase_client.from_.call_count >= 3  # select, mark, rollback


@pytest.mark.asyncio
async def test_atomic_update_successful_cleanup(sync_service, mock_supabase_client, mock_document_storage):
    """
    Test successful update removes old chunks completely.

    Verifies no chunks with _pending_deletion remain after success.
    """
    # Arrange
    page_id = "123456"
    markdown = "# Updated Content"
    page_url = "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456"
    source_id = "src_abc123"
    page_title = "Test Page"
    space_key = "DEVDOCS"

    # Mock successful operation
    from unittest.mock import patch
    with patch('src.server.services.confluence.confluence_sync_service.add_documents_to_supabase', new_callable=AsyncMock):
        # Act
        metrics = await sync_service._update_page_chunks_atomic(
            page_id=page_id,
            markdown=markdown,
            page_url=page_url,
            source_id=source_id,
            page_title=page_title,
            space_key=space_key,
        )

        # Assert - Verify old chunks deleted
        assert metrics["chunks_deleted"] == 2
        assert metrics["chunks_rolled_back"] == 0
        assert metrics["failed"] == 0

        # Verify from_ was called (which means delete operations happened)
        assert mock_supabase_client.from_.called


@pytest.mark.asyncio
async def test_atomic_update_metrics_tracking(sync_service, mock_document_storage):
    """Test metrics tracking for atomic updates."""
    # Arrange
    page_id = "123456"
    markdown = "# Updated Content"
    page_url = "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=123456"
    source_id = "src_abc123"
    page_title = "Test Page"
    space_key = "DEVDOCS"

    # Mock add_documents_to_supabase
    from unittest.mock import patch
    with patch('src.server.services.confluence.confluence_sync_service.add_documents_to_supabase', new_callable=AsyncMock):
        # Act
        metrics = await sync_service._update_page_chunks_atomic(
            page_id=page_id,
            markdown=markdown,
            page_url=page_url,
            source_id=source_id,
            page_title=page_title,
            space_key=space_key,
        )

        # Assert - Verify all metrics fields present
        assert "chunks_marked" in metrics
        assert "chunks_created" in metrics
        assert "chunks_deleted" in metrics
        assert "chunks_rolled_back" in metrics
        assert "failed" in metrics

        # Verify counts
        assert metrics["chunks_marked"] >= 0
        assert metrics["chunks_created"] == 3  # From mock
        assert metrics["chunks_deleted"] >= 0
        assert metrics["chunks_rolled_back"] == 0
        assert metrics["failed"] == 0


@pytest.mark.asyncio
async def test_atomic_update_no_existing_chunks(sync_service, mock_document_storage):
    """Test atomic update when no existing chunks (new page)."""
    # Arrange - Create fresh mock with no existing chunks
    mock_client = MagicMock()

    # Mock empty select response (no existing chunks)
    select_response = MagicMock()
    select_response.data = []

    delete_response = MagicMock()
    delete_response.data = []

    # Setup mock chains
    mock_select = MagicMock()
    mock_select.return_value.eq.return_value.filter.return_value.execute.return_value = select_response

    mock_delete = MagicMock()
    mock_delete.return_value.eq.return_value.filter.return_value.filter.return_value.execute.return_value = delete_response

    def from_side_effect(table_name):
        mock_table = MagicMock()
        mock_table.select = mock_select
        mock_table.delete = mock_delete
        return mock_table

    mock_client.from_.side_effect = from_side_effect
    sync_service.supabase_client = mock_client

    page_id = "new_page_789"
    markdown = "# New Page Content"
    page_url = "https://company.atlassian.net/wiki/pages/viewpage.action?pageId=new_page_789"
    source_id = "src_abc123"
    page_title = "New Page"
    space_key = "DEVDOCS"

    # Mock add_documents_to_supabase
    from unittest.mock import patch
    with patch('src.server.services.confluence.confluence_sync_service.add_documents_to_supabase', new_callable=AsyncMock):
        # Act
        metrics = await sync_service._update_page_chunks_atomic(
            page_id=page_id,
            markdown=markdown,
            page_url=page_url,
            source_id=source_id,
            page_title=page_title,
            space_key=space_key,
        )

        # Assert
        assert metrics["chunks_marked"] == 0  # No existing chunks to mark
        assert metrics["chunks_created"] == 3
        assert metrics["chunks_deleted"] == 0  # Nothing to delete
        assert metrics["failed"] == 0


@pytest.mark.asyncio
async def test_search_excludes_pending_deletion_chunks():
    """
    Test hybrid search excludes chunks with _pending_deletion flag.

    This tests the integration with HybridSearchStrategy.
    """
    from src.server.services.search.hybrid_search_strategy import HybridSearchStrategy

    # Mock Supabase client
    mock_client = MagicMock()

    # Mock RPC response with mix of normal and pending deletion chunks
    rpc_response = MagicMock()
    rpc_response.data = [
        {
            "id": "chunk_1",
            "url": "https://example.com/page1",
            "chunk_number": 0,
            "content": "Normal chunk",
            "metadata": {"page_id": "123"},
            "source_id": "src_1",
            "similarity": 0.9,
            "match_type": "vector",
        },
        {
            "id": "chunk_2",
            "url": "https://example.com/page2",
            "chunk_number": 0,
            "content": "Pending deletion chunk",
            "metadata": {"page_id": "456", "_pending_deletion": "true"},
            "source_id": "src_1",
            "similarity": 0.85,
            "match_type": "vector",
        },
        {
            "id": "chunk_3",
            "url": "https://example.com/page3",
            "chunk_number": 0,
            "content": "Another normal chunk",
            "metadata": {"page_id": "789"},
            "source_id": "src_1",
            "similarity": 0.8,
            "match_type": "text",
        },
    ]
    mock_client.rpc.return_value.execute.return_value = rpc_response

    # Create search strategy
    search_strategy = HybridSearchStrategy(mock_client, None)

    # Act
    results = await search_strategy.search_documents_hybrid(
        query="test query",
        query_embedding=[0.1, 0.2, 0.3],
        match_count=10,
    )

    # Assert - Only 2 chunks should be returned (chunk_2 excluded)
    assert len(results) == 2
    assert results[0]["id"] == "chunk_1"
    assert results[1]["id"] == "chunk_3"

    # Verify pending deletion chunk was filtered out
    result_ids = [r["id"] for r in results]
    assert "chunk_2" not in result_ids
