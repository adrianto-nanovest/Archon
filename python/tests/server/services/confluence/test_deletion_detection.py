"""
Tests for Confluence Deletion Detection Strategies (Story 3.3)

This test suite validates the deletion detection implementation including:
- DeletionStrategy enum and _get_deletion_strategy method
- Weekly reconciliation strategy (7-day check interval)
- Every sync strategy (immediate detection)
- On-demand strategy (manual trigger only)
- Page deletion handler (_mark_pages_deleted)
- Deletion event logging
- Integration with sync_space()
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.server.services.confluence.confluence_sync_service import (
    ConfluenceSyncService,
    DeletionEvent,
    DeletionStrategy,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_confluence_client():
    """Mock ConfluenceClient with required methods."""
    client = MagicMock()
    client.cql_search = AsyncMock(return_value=[])
    client.get_space_pages_ids = AsyncMock(return_value=["page_1", "page_2", "page_3"])
    client._client = MagicMock()
    client._client.url = "https://company.atlassian.net/wiki"
    return client


@pytest.fixture
def mock_confluence_processor():
    """Mock ConfluenceProcessor."""
    processor = MagicMock()
    processor.html_to_markdown = AsyncMock(return_value=(
        "# Test Page\n\nContent",
        {"jira_issue_links": [], "word_count": 10}
    ))
    return processor


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client with chainable query API."""
    client = MagicMock()

    # Default response for metadata queries
    default_response = MagicMock()
    default_response.data = [{"metadata": {}}]

    # Set up chainable pattern
    select_chain = MagicMock()
    eq_chain = MagicMock()
    eq_chain.execute = MagicMock(return_value=default_response)
    eq_chain.eq = MagicMock(return_value=eq_chain)
    eq_chain.filter = MagicMock(return_value=eq_chain)
    select_chain.eq = MagicMock(return_value=eq_chain)

    table_mock = MagicMock()
    table_mock.select = MagicMock(return_value=select_chain)
    table_mock.update = MagicMock(return_value=MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock()))))
    table_mock.delete = MagicMock(return_value=MagicMock(
        eq=MagicMock(return_value=MagicMock(
            filter=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[]))))
        ))
    ))
    table_mock.upsert = MagicMock(return_value=MagicMock(execute=MagicMock()))

    client.from_ = MagicMock(return_value=table_mock)

    return client


@pytest.fixture
def sync_service(mock_confluence_client, mock_confluence_processor, mock_supabase_client):
    """Create ConfluenceSyncService with mocked dependencies."""
    service = ConfluenceSyncService(
        confluence_client=mock_confluence_client,
        confluence_processor=mock_confluence_processor,
        supabase_client=mock_supabase_client,
    )
    # Mock document_storage
    service.document_storage.smart_chunk_text_async = AsyncMock(return_value=["chunk1", "chunk2"])
    return service


# ============================================================================
# Test DeletionStrategy Enum (Task 1)
# ============================================================================


class TestDeletionStrategyEnum:
    """Tests for DeletionStrategy enum."""

    def test_weekly_reconciliation_value(self):
        """Test WEEKLY_RECONCILIATION has correct string value."""
        assert DeletionStrategy.WEEKLY_RECONCILIATION.value == "weekly_reconciliation"

    def test_every_sync_value(self):
        """Test EVERY_SYNC has correct string value."""
        assert DeletionStrategy.EVERY_SYNC.value == "every_sync"

    def test_on_demand_value(self):
        """Test ON_DEMAND has correct string value."""
        assert DeletionStrategy.ON_DEMAND.value == "on_demand"

    def test_strategy_from_string(self):
        """Test creating enum from string value."""
        assert DeletionStrategy("weekly_reconciliation") == DeletionStrategy.WEEKLY_RECONCILIATION
        assert DeletionStrategy("every_sync") == DeletionStrategy.EVERY_SYNC
        assert DeletionStrategy("on_demand") == DeletionStrategy.ON_DEMAND

    def test_invalid_strategy_raises(self):
        """Test invalid strategy string raises ValueError."""
        with pytest.raises(ValueError):
            DeletionStrategy("invalid_strategy")


class TestGetDeletionStrategy:
    """Tests for _get_deletion_strategy method."""

    @pytest.mark.asyncio
    async def test_returns_configured_strategy(self, sync_service, mock_supabase_client):
        """Test returns configured strategy from metadata."""
        # Mock metadata with every_sync strategy
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {"deletion_strategy": "every_sync"}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        strategy = await sync_service._get_deletion_strategy("src_123")

        assert strategy == DeletionStrategy.EVERY_SYNC

    @pytest.mark.asyncio
    async def test_defaults_to_weekly_when_not_configured(self, sync_service, mock_supabase_client):
        """Test defaults to WEEKLY_RECONCILIATION when metadata empty."""
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        strategy = await sync_service._get_deletion_strategy("src_123")

        assert strategy == DeletionStrategy.WEEKLY_RECONCILIATION

    @pytest.mark.asyncio
    async def test_defaults_to_weekly_when_invalid_strategy(self, sync_service, mock_supabase_client):
        """Test defaults to WEEKLY_RECONCILIATION for invalid strategy value."""
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {"deletion_strategy": "invalid_value"}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        strategy = await sync_service._get_deletion_strategy("src_123")

        assert strategy == DeletionStrategy.WEEKLY_RECONCILIATION

    @pytest.mark.asyncio
    async def test_defaults_to_weekly_on_db_error(self, sync_service, mock_supabase_client):
        """Test defaults to WEEKLY_RECONCILIATION when database query fails."""
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        strategy = await sync_service._get_deletion_strategy("src_123")

        assert strategy == DeletionStrategy.WEEKLY_RECONCILIATION


# ============================================================================
# Test Weekly Reconciliation Strategy (Task 2)
# ============================================================================


class TestWeeklyReconciliation:
    """Tests for _check_weekly_reconciliation method."""

    @pytest.mark.asyncio
    async def test_returns_true_when_no_last_check(self, sync_service, mock_supabase_client):
        """Test returns True when last_deletion_check is NULL (first check)."""
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        should_check = await sync_service._check_weekly_reconciliation("src_123", "DEVDOCS")

        assert should_check is True

    @pytest.mark.asyncio
    async def test_returns_true_when_check_older_than_7_days(self, sync_service, mock_supabase_client):
        """Test returns True when last check was >= 7 days ago."""
        eight_days_ago = (datetime.now(UTC) - timedelta(days=8)).isoformat()
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {"last_deletion_check": eight_days_ago}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        should_check = await sync_service._check_weekly_reconciliation("src_123", "DEVDOCS")

        assert should_check is True

    @pytest.mark.asyncio
    async def test_returns_false_when_check_within_7_days(self, sync_service, mock_supabase_client):
        """Test returns False when last check was < 7 days ago."""
        three_days_ago = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {"last_deletion_check": three_days_ago}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        should_check = await sync_service._check_weekly_reconciliation("src_123", "DEVDOCS")

        assert should_check is False

    @pytest.mark.asyncio
    async def test_returns_true_for_invalid_timestamp(self, sync_service, mock_supabase_client):
        """Test returns True when last_deletion_check is invalid (forces check)."""
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {"last_deletion_check": "invalid-timestamp"}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        should_check = await sync_service._check_weekly_reconciliation("src_123", "DEVDOCS")

        assert should_check is True

    @pytest.mark.asyncio
    async def test_returns_false_on_db_error(self, sync_service, mock_supabase_client):
        """Test returns False on database error to avoid disruption."""
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        should_check = await sync_service._check_weekly_reconciliation("src_123", "DEVDOCS")

        assert should_check is False


class TestUpdateLastDeletionCheck:
    """Tests for _update_last_deletion_check method."""

    @pytest.mark.asyncio
    async def test_updates_timestamp_preserving_existing_metadata(self, sync_service, mock_supabase_client):
        """Test updates last_deletion_check while preserving other metadata."""
        existing_metadata = {"deletion_strategy": "every_sync", "other_field": "value"}
        mock_response = MagicMock()
        mock_response.data = [{"metadata": existing_metadata}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        update_mock = MagicMock()
        eq_mock = MagicMock()
        eq_mock.execute = MagicMock()
        update_mock.eq = MagicMock(return_value=eq_mock)
        mock_supabase_client.from_.return_value.update = MagicMock(return_value=update_mock)

        await sync_service._update_last_deletion_check("src_123")

        # Verify update was called
        mock_supabase_client.from_.return_value.update.assert_called_once()
        update_call_args = mock_supabase_client.from_.return_value.update.call_args[0][0]
        assert "last_deletion_check" in update_call_args["metadata"]
        assert update_call_args["metadata"]["deletion_strategy"] == "every_sync"
        assert update_call_args["metadata"]["other_field"] == "value"


# ============================================================================
# Test Every Sync Strategy (Task 3)
# ============================================================================


class TestDetectDeletedPagesEverySync:
    """Tests for _detect_deleted_pages_every_sync method."""

    @pytest.mark.asyncio
    async def test_detects_deleted_pages(self, sync_service, mock_confluence_client, mock_supabase_client):
        """Test detects pages in DB but not in Confluence API."""
        # API returns 2 pages
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1", "page_2"])

        # DB has 3 pages (page_3 was deleted)
        db_response = MagicMock()
        db_response.data = [
            {"page_id": "page_1"},
            {"page_id": "page_2"},
            {"page_id": "page_3"},
        ]

        # Set up query chain for confluence_pages select
        eq_chain = MagicMock()
        eq_chain.eq = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_response)))
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value = eq_chain

        deleted_ids = await sync_service._detect_deleted_pages_every_sync("src_123", "DEVDOCS")

        assert "page_3" in deleted_ids
        assert len(deleted_ids) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_deletions(self, sync_service, mock_confluence_client, mock_supabase_client):
        """Test returns empty list when all DB pages exist in API."""
        # API returns all pages
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1", "page_2"])

        # DB has same pages
        db_response = MagicMock()
        db_response.data = [
            {"page_id": "page_1"},
            {"page_id": "page_2"},
        ]

        eq_chain = MagicMock()
        eq_chain.eq = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_response)))
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value = eq_chain

        deleted_ids = await sync_service._detect_deleted_pages_every_sync("src_123", "DEVDOCS")

        assert deleted_ids == []

    @pytest.mark.asyncio
    async def test_handles_empty_db(self, sync_service, mock_confluence_client, mock_supabase_client):
        """Test handles case where DB has no pages."""
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1"])

        db_response = MagicMock()
        db_response.data = []

        eq_chain = MagicMock()
        eq_chain.eq = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_response)))
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value = eq_chain

        deleted_ids = await sync_service._detect_deleted_pages_every_sync("src_123", "DEVDOCS")

        assert deleted_ids == []

    @pytest.mark.asyncio
    async def test_raises_on_api_error(self, sync_service, mock_confluence_client):
        """Test raises exception when API call fails."""
        mock_confluence_client.get_space_pages_ids = AsyncMock(side_effect=Exception("API error"))

        with pytest.raises(Exception, match="API error"):
            await sync_service._detect_deleted_pages_every_sync("src_123", "DEVDOCS")


# ============================================================================
# Test On-Demand Strategy (Task 4)
# ============================================================================


class TestCheckDeletionsOnDemand:
    """Tests for check_deletions_on_demand method."""

    @pytest.mark.asyncio
    async def test_runs_deletion_detection_regardless_of_strategy(self, sync_service, mock_confluence_client, mock_supabase_client):
        """Test always runs deletion detection even if on_demand strategy."""
        # Set up mocks
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1"])

        # DB has pages
        db_response = MagicMock()
        db_response.data = [{"page_id": "page_1"}, {"page_id": "page_2"}]

        eq_chain = MagicMock()
        eq_chain.eq = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_response)))
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value = eq_chain

        # Mock _mark_pages_deleted
        sync_service._mark_pages_deleted = AsyncMock(return_value=1)
        sync_service._update_last_deletion_check = AsyncMock()

        result = await sync_service.check_deletions_on_demand("src_123", "DEVDOCS")

        assert result["pages_deleted"] == 1
        assert "page_2" in result["page_ids"]
        sync_service._mark_pages_deleted.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_last_deletion_check_timestamp(self, sync_service, mock_confluence_client, mock_supabase_client):
        """Test updates last_deletion_check after on-demand detection."""
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1"])

        db_response = MagicMock()
        db_response.data = [{"page_id": "page_1"}]

        eq_chain = MagicMock()
        eq_chain.eq = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_response)))
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value = eq_chain

        sync_service._update_last_deletion_check = AsyncMock()

        await sync_service.check_deletions_on_demand("src_123", "DEVDOCS")

        sync_service._update_last_deletion_check.assert_called_once_with("src_123")

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_deletions(self, sync_service, mock_confluence_client, mock_supabase_client):
        """Test returns zero when no pages deleted."""
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1"])

        db_response = MagicMock()
        db_response.data = [{"page_id": "page_1"}]

        eq_chain = MagicMock()
        eq_chain.eq = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_response)))
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value = eq_chain

        sync_service._update_last_deletion_check = AsyncMock()

        result = await sync_service.check_deletions_on_demand("src_123", "DEVDOCS")

        assert result["pages_deleted"] == 0
        assert result["page_ids"] == []


# ============================================================================
# Test Page Deletion Handler (Task 5)
# ============================================================================


class TestMarkPagesDeleted:
    """Tests for _mark_pages_deleted method."""

    @pytest.mark.asyncio
    async def test_marks_page_as_deleted(self, sync_service, mock_supabase_client):
        """Test marks page with is_deleted = TRUE."""
        # Mock getting page title
        title_response = MagicMock()
        title_response.data = [{"title": "Test Page"}]

        # Set up mock chain
        def from_mock(table):
            if table == "confluence_pages":
                mock_table = MagicMock()
                mock_table.select = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=title_response)))
                ))
                mock_table.update = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                ))
                return mock_table
            elif table == "archon_crawled_pages":
                mock_table = MagicMock()
                mock_table.delete = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        filter=MagicMock(return_value=MagicMock(execute=MagicMock()))
                    ))
                ))
                return mock_table
            return MagicMock()

        mock_supabase_client.from_ = from_mock

        deleted_count = await sync_service._mark_pages_deleted(["page_123"], "src_abc", "DEVDOCS")

        assert deleted_count == 1

    @pytest.mark.asyncio
    async def test_deletes_chunks_for_page(self, sync_service, mock_supabase_client):
        """Test deletes chunks from archon_crawled_pages."""
        title_response = MagicMock()
        title_response.data = [{"title": "Test Page"}]

        delete_mock = MagicMock()
        eq_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.execute = MagicMock()
        eq_mock.filter = MagicMock(return_value=filter_mock)
        delete_mock.eq = MagicMock(return_value=eq_mock)

        def from_mock(table):
            if table == "confluence_pages":
                mock_table = MagicMock()
                mock_table.select = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=title_response)))
                ))
                mock_table.update = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                ))
                return mock_table
            elif table == "archon_crawled_pages":
                mock_table = MagicMock()
                mock_table.delete = MagicMock(return_value=delete_mock)
                return mock_table
            return MagicMock()

        mock_supabase_client.from_ = from_mock

        await sync_service._mark_pages_deleted(["page_123"], "src_abc", "DEVDOCS")

        # Verify delete was called with correct filters
        delete_mock.eq.assert_called_with("source_id", "src_abc")
        eq_mock.filter.assert_called_with("metadata->>page_id", "eq", "page_123")

    @pytest.mark.asyncio
    async def test_continues_on_individual_page_failure(self, sync_service, mock_supabase_client):
        """Test continues processing other pages if one fails."""
        call_count = [0]

        def from_mock(table):
            if table == "confluence_pages":
                call_count[0] += 1
                if call_count[0] == 1:
                    # First page fails on select
                    raise Exception("DB error")
                # Second page succeeds
                mock_table = MagicMock()
                mock_table.select = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"title": "Page 2"}]))))
                ))
                mock_table.update = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                ))
                return mock_table
            elif table == "archon_crawled_pages":
                mock_table = MagicMock()
                mock_table.delete = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        filter=MagicMock(return_value=MagicMock(execute=MagicMock()))
                    ))
                ))
                return mock_table
            return MagicMock()

        mock_supabase_client.from_ = from_mock

        # Should not raise, should return 1 (second page succeeded)
        deleted_count = await sync_service._mark_pages_deleted(["page_1", "page_2"], "src_abc", "DEVDOCS")

        assert deleted_count == 1  # Only page_2 succeeded


# ============================================================================
# Test Deletion Event Logging (Task 6)
# ============================================================================


class TestDeletionEventLogging:
    """Tests for DeletionEvent and _log_deletion_event."""

    def test_deletion_event_dataclass(self):
        """Test DeletionEvent dataclass structure."""
        event = DeletionEvent(
            page_id="page_123",
            title="Test Page",
            deletion_timestamp="2025-10-20T10:00:00Z",
            source_id="src_abc",
            space_key="DEVDOCS",
        )

        assert event.page_id == "page_123"
        assert event.title == "Test Page"
        assert event.deletion_timestamp == "2025-10-20T10:00:00Z"
        assert event.source_id == "src_abc"
        assert event.space_key == "DEVDOCS"

    def test_log_deletion_event_logs_info(self, sync_service, caplog):
        """Test _log_deletion_event emits INFO log with correct message."""
        event = DeletionEvent(
            page_id="page_123",
            title="Test Page",
            deletion_timestamp="2025-10-20T10:00:00Z",
            source_id="src_abc",
            space_key="DEVDOCS",
        )

        with caplog.at_level("INFO"):
            sync_service._log_deletion_event(event)

        assert "Confluence page deleted" in caplog.text
        assert "Test Page" in caplog.text
        assert "page_123" in caplog.text


# ============================================================================
# Test Integration with sync_space (Task 7)
# ============================================================================


@pytest.fixture
def mock_document_storage(mock_supabase_client):
    """Mock document storage for sync_space tests."""
    with patch("src.server.services.confluence.confluence_sync_service.add_documents_to_supabase") as mock_add_docs:
        mock_add_docs.return_value = {"chunks_stored": 3}
        yield mock_add_docs


class TestSyncSpaceWithDeletionDetection:
    """Integration tests for deletion detection in sync_space."""

    @pytest.mark.asyncio
    async def test_sync_space_runs_every_sync_detection(
        self, sync_service, mock_confluence_client, mock_supabase_client, mock_document_storage
    ):
        """Test sync_space runs deletion detection with every_sync strategy."""
        # Configure every_sync strategy
        strategy_response = MagicMock()
        strategy_response.data = [{"metadata": {"deletion_strategy": "every_sync"}}]

        # Mock for detection: API returns 1 page, DB has 2 pages
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1"])
        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        # Track from_ calls to return appropriate responses
        def from_mock(table):
            mock_table = MagicMock()
            if table == "archon_sources":
                mock_table.select = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=strategy_response)))
                ))
                mock_table.update = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                ))
            elif table == "confluence_pages":
                db_pages_response = MagicMock()
                db_pages_response.data = [{"page_id": "page_1"}, {"page_id": "page_2"}]
                mock_table.select = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_pages_response)))
                    ))
                ))
                mock_table.update = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                ))
            elif table == "archon_crawled_pages":
                mock_table.delete = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(
                        filter=MagicMock(return_value=MagicMock(execute=MagicMock()))
                    ))
                ))
            return mock_table

        mock_supabase_client.from_ = from_mock

        # Mock the internal methods to avoid complex mocking
        sync_service._detect_deleted_pages_every_sync = AsyncMock(return_value=["page_2"])
        sync_service._mark_pages_deleted = AsyncMock(return_value=1)
        sync_service._update_last_deletion_check = AsyncMock()

        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        assert metrics["deletion_strategy"] == "every_sync"
        assert metrics["deletion_check_performed"] is True
        assert metrics["pages_deleted"] == 1

    @pytest.mark.asyncio
    async def test_sync_space_skips_deletion_with_on_demand_strategy(
        self, sync_service, mock_confluence_client, mock_supabase_client, mock_document_storage
    ):
        """Test sync_space skips deletion detection with on_demand strategy."""
        strategy_response = MagicMock()
        strategy_response.data = [{"metadata": {"deletion_strategy": "on_demand"}}]

        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        def from_mock(table):
            mock_table = MagicMock()
            mock_table.select = MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=strategy_response)))
            ))
            mock_table.update = MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
            ))
            return mock_table

        mock_supabase_client.from_ = from_mock

        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        assert metrics["deletion_strategy"] == "on_demand"
        assert metrics["deletion_check_performed"] is False
        assert metrics["pages_deleted"] == 0


# ============================================================================
# Test SyncMetrics Deletion Fields (Task 8)
# ============================================================================


class TestSyncMetricsDeletionFields:
    """Tests for deletion metrics in SyncMetrics."""

    @pytest.mark.asyncio
    async def test_sync_metrics_includes_deletion_fields(
        self, sync_service, mock_confluence_client, mock_supabase_client, mock_document_storage
    ):
        """Test SyncMetrics includes deletion_strategy, deletion_check_performed, last_deletion_check."""
        strategy_response = MagicMock()
        strategy_response.data = [{"metadata": {"deletion_strategy": "weekly_reconciliation"}}]

        mock_confluence_client.cql_search = AsyncMock(return_value=[])

        # Mock _check_weekly_reconciliation to return False (skip check)
        sync_service._check_weekly_reconciliation = AsyncMock(return_value=False)

        def from_mock(table):
            mock_table = MagicMock()
            mock_table.select = MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=strategy_response)))
            ))
            mock_table.update = MagicMock(return_value=MagicMock(
                eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
            ))
            return mock_table

        mock_supabase_client.from_ = from_mock

        metrics = await sync_service.sync_space(
            source_id="src_123",
            space_key="DEVDOCS"
        )

        # Verify new deletion metrics fields exist
        assert "deletion_strategy" in metrics
        assert "deletion_check_performed" in metrics
        assert "last_deletion_check" in metrics
        assert metrics["deletion_strategy"] == "weekly_reconciliation"


# ============================================================================
# Integration Verification Tests (IV1, IV2, IV3)
# ============================================================================


class TestIntegrationVerification:
    """Integration verification tests from Story 3.3."""

    @pytest.mark.asyncio
    async def test_iv1_weekly_strategy_respects_7_day_interval(self, sync_service, mock_supabase_client):
        """IV1: Weekly strategy only calls deletion check API once per 7 days."""
        # Set up last_deletion_check to 3 days ago
        three_days_ago = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        mock_response = MagicMock()
        mock_response.data = [{"metadata": {"last_deletion_check": three_days_ago}}]

        mock_supabase_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        # Should return False (skip check)
        should_check = await sync_service._check_weekly_reconciliation("src_123", "DEVDOCS")

        assert should_check is False

    @pytest.mark.asyncio
    async def test_iv2_every_sync_detects_deletions_immediately(
        self, sync_service, mock_confluence_client, mock_supabase_client
    ):
        """IV2: Every_sync strategy detects deletions within one sync cycle."""
        # API returns 2 pages, DB has 3
        mock_confluence_client.get_space_pages_ids = AsyncMock(return_value=["page_1", "page_2"])

        db_response = MagicMock()
        db_response.data = [{"page_id": "page_1"}, {"page_id": "page_2"}, {"page_id": "page_3"}]

        eq_chain = MagicMock()
        eq_chain.eq = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=db_response)))
        mock_supabase_client.from_.return_value.select.return_value.eq.return_value = eq_chain

        deleted_ids = await sync_service._detect_deleted_pages_every_sync("src_123", "DEVDOCS")

        # page_3 should be detected immediately
        assert "page_3" in deleted_ids
        assert len(deleted_ids) == 1

    @pytest.mark.asyncio
    async def test_iv3_deleted_page_chunks_removed(self, sync_service, mock_supabase_client):
        """IV3: Deleted page chunks removed from archon_crawled_pages."""
        title_response = MagicMock()
        title_response.data = [{"title": "Deleted Page"}]

        delete_call_tracker = []

        def from_mock(table):
            if table == "confluence_pages":
                mock_table = MagicMock()
                mock_table.select = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=title_response)))
                ))
                mock_table.update = MagicMock(return_value=MagicMock(
                    eq=MagicMock(return_value=MagicMock(execute=MagicMock()))
                ))
                return mock_table
            elif table == "archon_crawled_pages":
                mock_table = MagicMock()

                def track_delete():
                    delete_mock = MagicMock()
                    eq_mock = MagicMock()
                    filter_mock = MagicMock()

                    def track_filter(*args):
                        delete_call_tracker.append({"table": table, "filter_args": args})
                        return MagicMock(execute=MagicMock())

                    filter_mock.return_value = MagicMock(execute=MagicMock())
                    eq_mock.filter = track_filter
                    delete_mock.eq = MagicMock(return_value=eq_mock)
                    return delete_mock

                mock_table.delete = track_delete
                return mock_table
            return MagicMock()

        mock_supabase_client.from_ = from_mock

        await sync_service._mark_pages_deleted(["page_123"], "src_abc", "DEVDOCS")

        # Verify delete was called on archon_crawled_pages
        assert len(delete_call_tracker) == 1
        assert delete_call_tracker[0]["filter_args"] == ("metadata->>page_id", "eq", "page_123")
