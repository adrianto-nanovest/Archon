"""Integration tests for CQL injection prevention in ConfluenceClient.

These tests verify that the production ConfluenceClient correctly calls
the validate_space_key() function to prevent CQL injection attacks.

This addresses QA gate SEC-001: Ensuring validation is integrated into
production code paths, not just tested in isolation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.server.services.confluence.confluence_client import ConfluenceClient


class TestConfluenceClientValidationIntegration:
    """Integration tests verifying CQL injection prevention in production code."""

    @pytest.fixture
    def mock_confluence_api(self):
        """Mock the underlying atlassian-python-api SDK."""
        with patch("src.server.services.confluence.confluence_client.Confluence") as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_confluence_api):
        """Create ConfluenceClient with mocked API."""
        return ConfluenceClient(
            base_url="https://test.atlassian.net/wiki", api_token="test-token", email="test@example.com"
        )

    @pytest.mark.asyncio
    async def test_cql_search_validates_space_key(self, client, mock_confluence_api):
        """Verify cql_search() calls validate_space_key() for valid space keys."""
        # Mock successful API response
        mock_confluence_api.return_value.cql = MagicMock(return_value={"results": [{"id": "123"}]})

        # Valid CQL query with valid space key
        cql = "space = DEVDOCS AND lastModified >= '2025-10-01'"

        # Should succeed without raising ValueError
        pages = await client.cql_search(cql=cql)
        assert isinstance(pages, list)

    @pytest.mark.asyncio
    async def test_cql_search_rejects_invalid_space_key(self, client, mock_confluence_api):
        """Verify cql_search() rejects CQL with invalid space keys."""
        # Mock API (won't be called due to validation failure)
        mock_confluence_api.return_value.cql = MagicMock()

        # Malicious CQL injection attempt - special characters in space key value
        malicious_cql = "space = SPACE';DROP TABLE pages-- AND lastModified >= '2025-10-01'"

        # Should raise ValueError before making API call
        with pytest.raises(ValueError) as exc_info:
            await client.cql_search(cql=malicious_cql)

        assert "Invalid space key format" in str(exc_info.value)
        # Verify API was NOT called (validation blocked it)
        mock_confluence_api.return_value.cql.assert_not_called()

    @pytest.mark.asyncio
    async def test_cql_search_rejects_lowercase_space_key(self, client, mock_confluence_api):
        """Verify cql_search() rejects lowercase space keys."""
        mock_confluence_api.return_value.cql = MagicMock()

        # Lowercase space key
        cql = "space = devdocs AND lastModified >= '2025-10-01'"

        with pytest.raises(ValueError) as exc_info:
            await client.cql_search(cql=cql)

        assert "Invalid space key format" in str(exc_info.value)
        assert "uppercase" in str(exc_info.value).lower()
        mock_confluence_api.return_value.cql.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_validates_space_key(self, client, mock_confluence_api):
        """Verify get_space_pages_ids() calls validate_space_key() for valid space keys."""
        # Mock successful API response
        mock_confluence_api.return_value.get_all_pages_from_space = MagicMock(
            return_value=[{"id": "123"}, {"id": "456"}]
        )

        # Valid space key
        page_ids = await client.get_space_pages_ids(space_key="DEVDOCS")

        assert isinstance(page_ids, list)
        assert len(page_ids) == 2
        mock_confluence_api.return_value.get_all_pages_from_space.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_rejects_invalid_space_key(self, client, mock_confluence_api):
        """Verify get_space_pages_ids() rejects invalid space keys."""
        mock_confluence_api.return_value.get_all_pages_from_space = MagicMock()

        # Malicious space key
        malicious_space_key = "SPACE'; DROP TABLE--"

        with pytest.raises(ValueError) as exc_info:
            await client.get_space_pages_ids(space_key=malicious_space_key)

        assert "Invalid space key format" in str(exc_info.value)
        # Verify API was NOT called (validation blocked it)
        mock_confluence_api.return_value.get_all_pages_from_space.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_space_pages_ids_rejects_empty_space_key(self, client, mock_confluence_api):
        """Verify get_space_pages_ids() rejects empty space keys."""
        mock_confluence_api.return_value.get_all_pages_from_space = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            await client.get_space_pages_ids(space_key="")

        assert "cannot be empty" in str(exc_info.value).lower()
        mock_confluence_api.return_value.get_all_pages_from_space.assert_not_called()

    @pytest.mark.asyncio
    async def test_cql_search_handles_space_key_with_different_casing_in_query(self, client, mock_confluence_api):
        """Verify cql_search() handles 'SPACE', 'space', 'Space' in CQL query."""
        mock_confluence_api.return_value.cql = MagicMock(return_value={"results": []})

        # Lowercase 'space' keyword but uppercase space key value
        cql_variants = [
            "space = DEVDOCS",
            "SPACE = DEVDOCS",
            "Space = DEVDOCS",
            "space=DEVDOCS",  # No spaces
            "space  =  DEVDOCS",  # Extra spaces
        ]

        for cql in cql_variants:
            pages = await client.cql_search(cql=cql)
            assert isinstance(pages, list), f"Failed for CQL: {cql}"

    @pytest.mark.asyncio
    async def test_validation_error_message_quality(self, client, mock_confluence_api):
        """Verify validation error messages are clear and actionable."""
        invalid_space_key = "dev-docs"

        with pytest.raises(ValueError) as exc_info:
            await client.get_space_pages_ids(space_key=invalid_space_key)

        error_msg = str(exc_info.value)

        # Error should mention the invalid input
        assert "dev-docs" in error_msg

        # Error should provide guidance
        assert "uppercase" in error_msg.lower() or "alphanumeric" in error_msg.lower()

        # Error should provide examples
        assert "DEVDOCS" in error_msg or "IT123" in error_msg


class TestValidationIntegrationWithRealScenarios:
    """Test validation with realistic Confluence usage scenarios."""

    @pytest.fixture
    def mock_confluence_api(self):
        with patch("src.server.services.confluence.confluence_client.Confluence") as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_confluence_api):
        return ConfluenceClient(
            base_url="https://test.atlassian.net/wiki", api_token="test-token", email="test@example.com"
        )

    @pytest.mark.asyncio
    async def test_incremental_sync_cql_with_valid_space(self, client, mock_confluence_api):
        """Test realistic incremental sync CQL query with valid space key."""
        mock_confluence_api.return_value.cql = MagicMock(
            return_value={"results": [{"id": "123", "title": "Test Page"}]}
        )

        # Realistic incremental sync CQL
        cql = 'space = DEVDOCS AND lastModified >= "2025-10-01 10:00"'

        pages = await client.cql_search(cql=cql, expand="body.storage,version")
        assert len(pages) == 1
        assert pages[0]["id"] == "123"

    @pytest.mark.asyncio
    async def test_deletion_detection_with_valid_space(self, client, mock_confluence_api):
        """Test realistic deletion detection flow with valid space key."""
        mock_confluence_api.return_value.get_all_pages_from_space = MagicMock(
            return_value=[{"id": "123"}, {"id": "456"}, {"id": "789"}]
        )

        # Realistic deletion detection
        page_ids = await client.get_space_pages_ids(space_key="ENGINEERING")
        assert len(page_ids) == 3
        assert "123" in page_ids

    @pytest.mark.asyncio
    async def test_multi_space_keys_all_validated(self, client, mock_confluence_api):
        """Verify validation runs for multiple space keys in sequence."""
        mock_confluence_api.return_value.get_all_pages_from_space = MagicMock(
            return_value=[{"id": "123"}]
        )

        valid_space_keys = ["DEVDOCS", "IT", "ENGINEERING123", "PROJ"]

        for space_key in valid_space_keys:
            page_ids = await client.get_space_pages_ids(space_key=space_key)
            assert isinstance(page_ids, list), f"Failed for space: {space_key}"

    @pytest.mark.asyncio
    async def test_attack_vectors_all_blocked(self, client, mock_confluence_api):
        """Verify common attack vectors are blocked by validation."""
        mock_confluence_api.return_value.get_all_pages_from_space = MagicMock()

        attack_vectors = [
            "SPACE'; DROP TABLE confluence_pages--",
            "SPACE' OR '1'='1",
            "SPACE'; DELETE FROM documents--",
            "'; UNION SELECT * FROM users--",
            "admin'--",
            "1' OR '1' = '1",
        ]

        for attack in attack_vectors:
            with pytest.raises(ValueError):
                await client.get_space_pages_ids(space_key=attack)

            # Verify API was NEVER called
            mock_confluence_api.return_value.get_all_pages_from_space.assert_not_called()
