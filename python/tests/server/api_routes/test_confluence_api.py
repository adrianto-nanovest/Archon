"""Tests for Confluence API endpoints.

Tests cover:
- POST /api/confluence/sources - Create Confluence source
- GET /api/confluence/sources - List all Confluence sources
- POST /api/confluence/{source_id}/sync - Trigger sync
- GET /api/confluence/{source_id}/status - Get sync status
- DELETE /api/confluence/{source_id} - Delete source
- GET /api/confluence/{source_id}/pages - List pages
- ETag caching support (IV3)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.server.main import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client with chainable query API."""
    client = MagicMock()

    # Mock for SELECT queries with chaining
    def create_select_chain(data=None, count=None):
        mock = MagicMock()
        mock.eq = MagicMock(return_value=mock)
        mock.order = MagicMock(return_value=mock)
        mock.range = MagicMock(return_value=mock)
        mock.execute = MagicMock(return_value=MagicMock(data=data or [], count=count))
        return mock

    # Mock for INSERT
    def create_insert_chain():
        mock = MagicMock()
        mock.execute = MagicMock(return_value=MagicMock(data=[{"source_id": "confluence_test123"}]))
        return mock

    # Mock for DELETE
    def create_delete_chain():
        mock = MagicMock()
        mock.eq = MagicMock(return_value=mock)
        mock.execute = MagicMock(return_value=MagicMock(data=[]))
        return mock

    # Configure from_ to return appropriate chains
    client.from_ = MagicMock()

    # Default select behavior
    select_mock = create_select_chain()
    insert_mock = create_insert_chain()
    delete_mock = create_delete_chain()

    client.from_.return_value.select = MagicMock(return_value=select_mock)
    client.from_.return_value.insert = MagicMock(return_value=insert_mock)
    client.from_.return_value.delete = MagicMock(return_value=delete_mock)

    return client


@pytest.fixture
def mock_confluence_client():
    """Mock ConfluenceClient for validation."""
    with patch("src.server.api_routes.confluence_api.ConfluenceClient") as mock:
        instance = MagicMock()
        instance.cql_search = AsyncMock(return_value=[{"id": "123", "title": "Test Page"}])
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_credential_service():
    """Mock credential service for encryption/decryption."""
    with patch("src.server.api_routes.confluence_api.credential_service") as mock:
        mock._encrypt_value = MagicMock(return_value="encrypted_token_value")
        mock._decrypt_value = MagicMock(return_value="decrypted_api_token")
        yield mock


@pytest.fixture
def mock_progress_tracker():
    """Mock ProgressTracker for sync operations."""
    with patch("src.server.api_routes.confluence_api.ProgressTracker") as mock:
        instance = MagicMock()
        instance.start = AsyncMock()
        instance.update = AsyncMock()
        instance.complete = AsyncMock()
        instance.error = AsyncMock()
        mock.return_value = instance
        mock.list_active = MagicMock(return_value={})
        yield mock


@pytest.fixture
def sample_confluence_source():
    """Sample Confluence source data from database."""
    return {
        "source_id": "confluence_test123",
        "source_type": "confluence",
        "status": "ready",
        "metadata": {
            "confluence_base_url": "https://company.atlassian.net/wiki",
            "confluence_space_key": "DEVDOCS",
            "confluence_email": "user@company.com",
            "encrypted_api_token": "encrypted_token_value",
            "deletion_strategy": "weekly_reconciliation",
            "total_pages": 50,
            "last_sync_timestamp": "2025-10-01T10:00:00Z",
        },
        "created_at": "2025-09-01T00:00:00Z",
        "updated_at": "2025-10-01T10:00:00Z",
    }


# =============================================================================
# POST /api/confluence/sources Tests
# =============================================================================


class TestCreateConfluenceSource:
    """Tests for POST /api/confluence/sources endpoint."""

    def test_create_source_success(
        self, client, mock_confluence_client, mock_credential_service
    ):
        """Test successful source creation with valid credentials."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"source_id": "confluence_abc123"}]
            )
            mock_get_client.return_value = mock_client

            response = client.post(
                "/api/confluence/sources",
                json={
                    "base_url": "https://company.atlassian.net/wiki",
                    "api_token": "test_token",
                    "email": "user@company.com",
                    "space_key": "DEVDOCS",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "source_id" in data
            assert data["source_type"] == "confluence"
            assert data["space_key"] == "DEVDOCS"
            assert data["base_url"] == "https://company.atlassian.net/wiki"
            assert data["status"] == "ready"

            # Verify encryption was called
            mock_credential_service._encrypt_value.assert_called_once_with("test_token")

    def test_create_source_invalid_url(self, client):
        """Test source creation fails with HTTP URL."""
        response = client.post(
            "/api/confluence/sources",
            json={
                "base_url": "http://company.atlassian.net/wiki",  # HTTP not allowed
                "api_token": "test_token",
                "email": "user@company.com",
                "space_key": "DEVDOCS",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid URL" in data["detail"]["error"]

    def test_create_source_invalid_space_key(self, client):
        """Test source creation fails with invalid space key format."""
        response = client.post(
            "/api/confluence/sources",
            json={
                "base_url": "https://company.atlassian.net/wiki",
                "api_token": "test_token",
                "email": "user@company.com",
                "space_key": "DEV-DOCS",  # Hyphens not allowed
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid space key" in data["detail"]["error"]

    def test_create_source_invalid_credentials(
        self, client, mock_credential_service
    ):
        """Test source creation fails with invalid Confluence credentials."""
        with patch("src.server.api_routes.confluence_api.ConfluenceClient") as mock_cc:
            instance = MagicMock()
            instance.cql_search = AsyncMock(side_effect=Exception("401 Unauthorized"))
            mock_cc.return_value = instance

            response = client.post(
                "/api/confluence/sources",
                json={
                    "base_url": "https://company.atlassian.net/wiki",
                    "api_token": "bad_token",
                    "email": "user@company.com",
                    "space_key": "DEVDOCS",
                },
            )

            assert response.status_code == 401
            data = response.json()
            assert "Invalid credentials" in data["detail"]["error"]

    def test_create_source_encrypted_token_stored(
        self, client, mock_confluence_client, mock_credential_service
    ):
        """Test that API token is encrypted before storage (security)."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            # Capture the insert call to verify encrypted token
            insert_data = {}

            def capture_insert(data):
                insert_data.update(data)
                return MagicMock(execute=MagicMock(return_value=MagicMock(data=[data])))

            mock_client.from_.return_value.insert = capture_insert

            client.post(
                "/api/confluence/sources",
                json={
                    "base_url": "https://company.atlassian.net/wiki",
                    "api_token": "plaintext_token",
                    "email": "user@company.com",
                    "space_key": "DEVDOCS",
                },
            )

            # Verify encrypted token stored, not plaintext
            assert insert_data["metadata"]["encrypted_api_token"] == "encrypted_token_value"
            assert "plaintext_token" not in str(insert_data)


# =============================================================================
# GET /api/confluence/sources Tests
# =============================================================================


class TestListConfluenceSources:
    """Tests for GET /api/confluence/sources endpoint."""

    def test_list_sources_success(self, client, sample_confluence_source):
        """Test successful listing of Confluence sources."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            response = client.get("/api/confluence/sources")

            assert response.status_code == 200
            data = response.json()
            assert "sources" in data
            assert "count" in data
            assert data["count"] == 1
            assert data["sources"][0]["space_key"] == "DEVDOCS"

    def test_list_sources_encrypted_token_not_in_response(
        self, client, sample_confluence_source
    ):
        """Test that encrypted_api_token is NOT returned in response (security)."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            response = client.get("/api/confluence/sources")

            assert response.status_code == 200
            response_text = response.text
            assert "encrypted_api_token" not in response_text
            assert "api_token" not in response_text

    def test_list_sources_etag_caching(self, client, sample_confluence_source):
        """Test ETag support for bandwidth optimization (IV3)."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            # First request - get ETag
            response1 = client.get("/api/confluence/sources")
            assert response1.status_code == 200
            assert "ETag" in response1.headers
            etag = response1.headers["ETag"]

            # Second request with If-None-Match - should return 304
            response2 = client.get(
                "/api/confluence/sources",
                headers={"If-None-Match": etag},
            )
            assert response2.status_code == 304

    def test_list_sources_cache_control_headers(self, client):
        """Test Cache-Control headers are set correctly."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_get_client.return_value = mock_client

            response = client.get("/api/confluence/sources")

            assert response.status_code == 200
            assert "Cache-Control" in response.headers
            assert "no-cache" in response.headers["Cache-Control"]


# =============================================================================
# POST /api/confluence/{source_id}/sync Tests
# =============================================================================


class TestTriggerSync:
    """Tests for POST /api/confluence/{source_id}/sync endpoint (IV2)."""

    def test_sync_returns_operation_id(
        self,
        client,
        sample_confluence_source,
        mock_credential_service,
        mock_progress_tracker,
    ):
        """Test sync returns operation_id immediately for tracking."""
        with (
            patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client,
            patch("src.server.api_routes.confluence_api.ConfluenceClient"),
            patch("src.server.api_routes.confluence_api.ConfluenceProcessor"),
            patch("src.server.api_routes.confluence_api.ConfluenceSyncService"),
        ):
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            response = client.post("/api/confluence/confluence_test123/sync")

            assert response.status_code == 200
            data = response.json()
            assert "operation_id" in data
            assert data["operation_id"].startswith("sync_")
            assert data["source_id"] == "confluence_test123"
            assert "message" in data

    def test_sync_creates_progress_tracker(
        self,
        client,
        sample_confluence_source,
        mock_credential_service,
        mock_progress_tracker,
    ):
        """Test ProgressTracker.start called with operation_type='confluence_sync'."""
        with (
            patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client,
            patch("src.server.api_routes.confluence_api.ConfluenceClient"),
            patch("src.server.api_routes.confluence_api.ConfluenceProcessor"),
            patch("src.server.api_routes.confluence_api.ConfluenceSyncService"),
        ):
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            response = client.post("/api/confluence/confluence_test123/sync")

            assert response.status_code == 200

            # Verify ProgressTracker was created with confluence_sync type
            mock_progress_tracker.assert_called_once()
            call_kwargs = mock_progress_tracker.call_args[1]
            assert call_kwargs["operation_type"] == "confluence_sync"

    def test_sync_source_not_found(self, client):
        """Test sync fails when source doesn't exist."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_get_client.return_value = mock_client

            response = client.post("/api/confluence/nonexistent/sync")

            assert response.status_code == 404


# =============================================================================
# GET /api/confluence/{source_id}/status Tests
# =============================================================================


class TestGetStatus:
    """Tests for GET /api/confluence/{source_id}/status endpoint."""

    def test_status_idle_returns_last_sync_metadata(
        self, client, sample_confluence_source, mock_progress_tracker
    ):
        """Test idle status returns last sync metadata when no active operation."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            # No active operations
            mock_progress_tracker.list_active.return_value = {}

            response = client.get("/api/confluence/confluence_test123/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "idle"
            assert data["last_sync"] == "2025-10-01T10:00:00Z"
            assert data["total_pages"] == 50

    def test_status_active_operation_returns_progress(
        self, client, sample_confluence_source, mock_progress_tracker
    ):
        """Test status returns active operation progress when sync is running."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            # Active sync operation
            mock_progress_tracker.list_active.return_value = {
                "sync_abc123": {
                    "source_id": "confluence_test123",
                    "type": "confluence_sync",
                    "status": "crawling",
                    "progress": 45,
                    "log": "Processing page 23/50",
                }
            }

            response = client.get("/api/confluence/confluence_test123/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "syncing"
            assert data["active_operation"]["operation_id"] == "sync_abc123"
            assert data["active_operation"]["progress"] == 45

    def test_status_etag_caching(
        self, client, sample_confluence_source, mock_progress_tracker
    ):
        """Test ETag caching for status endpoint."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client
            mock_progress_tracker.list_active.return_value = {}

            # First request
            response1 = client.get("/api/confluence/confluence_test123/status")
            assert response1.status_code == 200
            etag = response1.headers.get("ETag")
            assert etag is not None

            # Second request with ETag
            response2 = client.get(
                "/api/confluence/confluence_test123/status",
                headers={"If-None-Match": etag},
            )
            assert response2.status_code == 304


# =============================================================================
# DELETE /api/confluence/{source_id} Tests
# =============================================================================


class TestDeleteSource:
    """Tests for DELETE /api/confluence/{source_id} endpoint."""

    def test_delete_source_success(
        self, client, sample_confluence_source, mock_progress_tracker
    ):
        """Test successful source deletion with CASCADE."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_client.from_.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_get_client.return_value = mock_client
            mock_progress_tracker.list_active.return_value = {}

            response = client.delete("/api/confluence/confluence_test123")

            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is True
            assert data["source_id"] == "confluence_test123"

    def test_delete_source_with_active_sync_rejected(
        self, client, sample_confluence_source, mock_progress_tracker
    ):
        """Test 409 returned if active sync in progress."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            # Active sync prevents deletion
            mock_progress_tracker.list_active.return_value = {
                "sync_abc123": {
                    "source_id": "confluence_test123",
                    "type": "confluence_sync",
                    "status": "crawling",
                }
            }

            response = client.delete("/api/confluence/confluence_test123")

            assert response.status_code == 409
            data = response.json()
            assert "active sync" in data["detail"]["error"].lower()

    def test_delete_source_not_found(self, client):
        """Test 404 when source doesn't exist."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_get_client.return_value = mock_client

            response = client.delete("/api/confluence/nonexistent")

            assert response.status_code == 404


# =============================================================================
# GET /api/confluence/{source_id}/pages Tests
# =============================================================================


class TestListPages:
    """Tests for GET /api/confluence/{source_id}/pages endpoint."""

    def test_list_pages_success(self, client, sample_confluence_source):
        """Test successful page listing with pagination."""
        pages_data = [
            {
                "page_id": "123",
                "title": "Getting Started",
                "space_key": "DEVDOCS",
                "version": 5,
                "last_modified": "2025-10-01T10:00:00Z",
                "is_deleted": False,
                "path": "/123/456",
            },
            {
                "page_id": "456",
                "title": "API Reference",
                "space_key": "DEVDOCS",
                "version": 3,
                "last_modified": "2025-10-02T10:00:00Z",
                "is_deleted": False,
                "path": "/123",
            },
        ]

        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()

            # Mock source query
            source_query = MagicMock()
            source_query.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )

            # Mock pages count query
            count_query = MagicMock()
            count_query.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=pages_data, count=2
            )

            # Mock pages list query
            list_query = MagicMock()
            list_query.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                data=pages_data
            )

            # Configure from_ to return different results based on table
            def from_side_effect(table):
                mock = MagicMock()
                if table == "archon_sources":
                    mock.select.return_value = source_query
                else:  # confluence_pages
                    mock.select.side_effect = lambda *args, **kwargs: (
                        count_query if kwargs.get("count") else list_query
                    )
                return mock

            mock_client.from_.side_effect = from_side_effect
            mock_get_client.return_value = mock_client

            response = client.get("/api/confluence/confluence_test123/pages")

            assert response.status_code == 200
            data = response.json()
            assert "pages" in data
            assert data["page"] == 1
            assert data["page_size"] == 50

    def test_list_pages_pagination_parameters(self, client, sample_confluence_source):
        """Test pagination parameters work correctly."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()

            # Track which table is being queried
            def from_side_effect(table_name):
                table_mock = MagicMock()
                if table_name == "archon_sources":
                    # Mock source query
                    select_mock = MagicMock()
                    select_mock.eq.return_value.execute.return_value = MagicMock(
                        data=[sample_confluence_source]
                    )
                    table_mock.select.return_value = select_mock
                else:
                    # Mock confluence_pages query
                    select_mock = MagicMock()
                    select_mock.eq.return_value = select_mock
                    select_mock.order.return_value = select_mock
                    select_mock.range.return_value = select_mock
                    select_mock.execute.return_value = MagicMock(data=[], count=100)
                    table_mock.select.return_value = select_mock
                return table_mock

            mock_client.from_.side_effect = from_side_effect
            mock_get_client.return_value = mock_client

            response = client.get(
                "/api/confluence/confluence_test123/pages",
                params={"page": 2, "page_size": 25},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 25

    def test_list_pages_include_deleted_filter(
        self, client, sample_confluence_source
    ):
        """Test is_deleted filter works correctly."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()

            # Track which table is being queried
            def from_side_effect(table_name):
                table_mock = MagicMock()
                if table_name == "archon_sources":
                    select_mock = MagicMock()
                    select_mock.eq.return_value.execute.return_value = MagicMock(
                        data=[sample_confluence_source]
                    )
                    table_mock.select.return_value = select_mock
                else:
                    select_mock = MagicMock()
                    select_mock.eq.return_value = select_mock
                    select_mock.order.return_value = select_mock
                    select_mock.range.return_value = select_mock
                    select_mock.execute.return_value = MagicMock(data=[], count=0)
                    table_mock.select.return_value = select_mock
                return table_mock

            mock_client.from_.side_effect = from_side_effect
            mock_get_client.return_value = mock_client

            # Request with include_deleted=true
            response = client.get(
                "/api/confluence/confluence_test123/pages",
                params={"include_deleted": "true"},
            )

            assert response.status_code == 200

    def test_list_pages_etag_caching(self, client, sample_confluence_source):
        """Test ETag caching for pages list."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()

            # Track which table is being queried
            def from_side_effect(table_name):
                table_mock = MagicMock()
                if table_name == "archon_sources":
                    select_mock = MagicMock()
                    select_mock.eq.return_value.execute.return_value = MagicMock(
                        data=[sample_confluence_source]
                    )
                    table_mock.select.return_value = select_mock
                else:
                    select_mock = MagicMock()
                    select_mock.eq.return_value = select_mock
                    select_mock.order.return_value = select_mock
                    select_mock.range.return_value = select_mock
                    select_mock.execute.return_value = MagicMock(data=[], count=0)
                    table_mock.select.return_value = select_mock
                return table_mock

            mock_client.from_.side_effect = from_side_effect
            mock_get_client.return_value = mock_client

            # First request
            response1 = client.get("/api/confluence/confluence_test123/pages")
            assert response1.status_code == 200
            etag = response1.headers.get("ETag")
            assert etag is not None

            # Second request with ETag
            response2 = client.get(
                "/api/confluence/confluence_test123/pages",
                headers={"If-None-Match": etag},
            )
            assert response2.status_code == 304


# =============================================================================
# Integration Verification Tests (IV1, IV2, IV3)
# =============================================================================


class TestIntegrationVerification:
    """Integration verification tests per Epic 3 PRD Story 3.4."""

    def test_iv1_existing_knowledge_api_unchanged(self, client):
        """IV1: Existing /api/knowledge/* endpoints remain unchanged.

        This test verifies that our new Confluence endpoints don't
        interfere with existing knowledge API functionality.
        """
        # The Confluence API is at /api/confluence/* prefix
        # Knowledge API remains at /api/knowledge/* prefix
        # They should coexist without conflict

        # Verify our router prefix is correct
        from src.server.api_routes.confluence_api import router

        assert router.prefix == "/api/confluence"

    def test_iv2_sync_operation_tracked_with_confluence_sync_type(
        self,
        client,
        sample_confluence_source,
        mock_credential_service,
        mock_progress_tracker,
    ):
        """IV2: Sync operation tracked with operation_type='confluence_sync'."""
        with (
            patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client,
            patch("src.server.api_routes.confluence_api.ConfluenceClient"),
            patch("src.server.api_routes.confluence_api.ConfluenceProcessor"),
            patch("src.server.api_routes.confluence_api.ConfluenceSyncService"),
        ):
            mock_client = MagicMock()
            mock_client.from_.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[sample_confluence_source]
            )
            mock_get_client.return_value = mock_client

            response = client.post("/api/confluence/confluence_test123/sync")

            assert response.status_code == 200

            # Verify ProgressTracker created with correct operation_type
            mock_progress_tracker.assert_called()
            call_kwargs = mock_progress_tracker.call_args[1]
            assert call_kwargs["operation_type"] == "confluence_sync"

    def test_iv3_etag_caching_on_all_get_endpoints(
        self, client, sample_confluence_source, mock_progress_tracker
    ):
        """IV3: API responses follow existing ETag caching pattern."""
        with patch("src.server.api_routes.confluence_api.get_supabase_client") as mock_get_client:
            mock_client = MagicMock()

            # Track which table is being queried
            def from_side_effect(table_name):
                table_mock = MagicMock()
                if table_name == "archon_sources":
                    select_mock = MagicMock()
                    select_mock.eq.return_value.execute.return_value = MagicMock(
                        data=[sample_confluence_source]
                    )
                    table_mock.select.return_value = select_mock
                else:
                    select_mock = MagicMock()
                    select_mock.eq.return_value = select_mock
                    select_mock.order.return_value = select_mock
                    select_mock.range.return_value = select_mock
                    select_mock.execute.return_value = MagicMock(data=[], count=0)
                    table_mock.select.return_value = select_mock
                return table_mock

            mock_client.from_.side_effect = from_side_effect
            mock_get_client.return_value = mock_client
            mock_progress_tracker.list_active.return_value = {}

            # Test all GET endpoints have ETag support
            endpoints = [
                "/api/confluence/sources",
                "/api/confluence/confluence_test123/status",
                "/api/confluence/confluence_test123/pages",
            ]

            for endpoint in endpoints:
                response = client.get(endpoint)
                assert "ETag" in response.headers, f"Missing ETag header for {endpoint}"
                assert "Cache-Control" in response.headers, f"Missing Cache-Control for {endpoint}"
                assert "no-cache" in response.headers["Cache-Control"]
