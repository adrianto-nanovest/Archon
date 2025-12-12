"""
Tests for Confluence-specific search filters (Story 4.2).

Tests the ConfluenceSearchFilters dataclass and the _apply_confluence_filters()
method in HybridSearchStrategy.
"""

import pytest
from unittest.mock import MagicMock

from src.server.services.search.hybrid_search_strategy import (
    ConfluenceSearchFilters,
    HybridSearchStrategy,
)


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Create a mock Supabase client."""
    return MagicMock()


@pytest.fixture
def strategy(mock_supabase_client: MagicMock) -> HybridSearchStrategy:
    """Create a HybridSearchStrategy instance with mock client."""
    return HybridSearchStrategy(mock_supabase_client, None)


class TestConfluenceSearchFilters:
    """Tests for the ConfluenceSearchFilters dataclass."""

    def test_has_any_filter_with_no_filters(self) -> None:
        """Test has_any_filter returns False when no filters are set."""
        filters = ConfluenceSearchFilters()
        assert filters.has_any_filter() is False

    def test_has_any_filter_with_space_key(self) -> None:
        """Test has_any_filter returns True when space_key is set."""
        filters = ConfluenceSearchFilters(space_key="DEVDOCS")
        assert filters.has_any_filter() is True

    def test_has_any_filter_with_jira_issue(self) -> None:
        """Test has_any_filter returns True when jira_issue is set."""
        filters = ConfluenceSearchFilters(jira_issue="PROJ-123")
        assert filters.has_any_filter() is True

    def test_has_any_filter_with_hierarchy_path(self) -> None:
        """Test has_any_filter returns True when hierarchy_path is set."""
        filters = ConfluenceSearchFilters(hierarchy_path="/parent123/")
        assert filters.has_any_filter() is True

    def test_has_any_filter_with_mentioned_user(self) -> None:
        """Test has_any_filter returns True when mentioned_user is set."""
        filters = ConfluenceSearchFilters(mentioned_user="user123")
        assert filters.has_any_filter() is True

    def test_has_any_filter_with_multiple_filters(self) -> None:
        """Test has_any_filter returns True when multiple filters are set."""
        filters = ConfluenceSearchFilters(
            space_key="DEVDOCS",
            jira_issue="PROJ-123",
        )
        assert filters.has_any_filter() is True


class TestApplyConfluenceFilters:
    """Tests for the _apply_confluence_filters method."""

    def test_no_filters_returns_all_results(self, strategy: HybridSearchStrategy) -> None:
        """Test that no filters returns all results unchanged."""
        mock_results = [
            {"confluence_metadata": {"space_key": "DEVDOCS", "title": "Page 1"}},
            {"confluence_metadata": {"space_key": "INTERNAL", "title": "Page 2"}},
            {"confluence_metadata": None},  # Web crawl chunk
        ]

        filters = ConfluenceSearchFilters()
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 3

    def test_none_filters_returns_all_results(self, strategy: HybridSearchStrategy) -> None:
        """Test that None filters returns all results unchanged."""
        mock_results = [
            {"confluence_metadata": {"space_key": "DEVDOCS", "title": "Page 1"}},
            {"confluence_metadata": None},
        ]

        filtered = strategy._apply_confluence_filters(mock_results, None)  # type: ignore[arg-type]

        assert len(filtered) == 2

    def test_space_key_filter(self, strategy: HybridSearchStrategy) -> None:
        """Test that space_key filter returns only matching space results (IV1)."""
        mock_results = [
            {"confluence_metadata": {"space_key": "DEVDOCS", "title": "Page 1"}},
            {"confluence_metadata": {"space_key": "INTERNAL", "title": "Page 2"}},
            {"confluence_metadata": {"space_key": "DEVDOCS", "title": "Page 3"}},
        ]

        filters = ConfluenceSearchFilters(space_key="DEVDOCS")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 2
        assert all(r["confluence_metadata"]["space_key"] == "DEVDOCS" for r in filtered)

    def test_jira_issue_filter(self, strategy: HybridSearchStrategy) -> None:
        """Test that jira_issue filter finds pages with specific JIRA links (IV2)."""
        mock_results = [
            {"confluence_metadata": {"jira_issue_links": [{"issue_key": "PROJ-123"}]}},
            {"confluence_metadata": {"jira_issue_links": [{"issue_key": "PROJ-456"}]}},
            {
                "confluence_metadata": {
                    "jira_issue_links": [
                        {"issue_key": "PROJ-123"},
                        {"issue_key": "PROJ-789"},
                    ]
                }
            },
        ]

        filters = ConfluenceSearchFilters(jira_issue="PROJ-123")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 2
        for r in filtered:
            assert any(
                link["issue_key"] == "PROJ-123"
                for link in r["confluence_metadata"]["jira_issue_links"]
            )

    def test_hierarchy_path_filter(self, strategy: HybridSearchStrategy) -> None:
        """Test that hierarchy_path filter returns descendants of parent page (IV3)."""
        mock_results = [
            {"confluence_metadata": {"path": "/parent123/child1", "title": "Child 1"}},
            {"confluence_metadata": {"path": "/parent456/child2", "title": "Child 2"}},
            {
                "confluence_metadata": {
                    "path": "/parent123/child1/grandchild",
                    "title": "Grandchild",
                }
            },
        ]

        filters = ConfluenceSearchFilters(hierarchy_path="/parent123/")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 2
        assert all(
            r["confluence_metadata"]["path"].startswith("/parent123/") for r in filtered
        )

    def test_mentioned_user_filter(self, strategy: HybridSearchStrategy) -> None:
        """Test that mentioned_user filter finds pages mentioning specific user."""
        mock_results = [
            {"confluence_metadata": {"user_mentions": [{"account_id": "user123"}]}},
            {"confluence_metadata": {"user_mentions": [{"account_id": "user456"}]}},
            {"confluence_metadata": {"user_mentions": []}},
        ]

        filters = ConfluenceSearchFilters(mentioned_user="user123")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1
        assert filtered[0]["confluence_metadata"]["user_mentions"][0]["account_id"] == "user123"

    def test_combined_filters_and_logic(self, strategy: HybridSearchStrategy) -> None:
        """Test that multiple filters are combined with AND logic (AC: 6)."""
        mock_results = [
            {
                "confluence_metadata": {
                    "space_key": "DEVDOCS",
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                }
            },
            {
                "confluence_metadata": {
                    "space_key": "DEVDOCS",
                    "jira_issue_links": [{"issue_key": "PROJ-456"}],
                }
            },
            {
                "confluence_metadata": {
                    "space_key": "INTERNAL",
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                }
            },
        ]

        filters = ConfluenceSearchFilters(space_key="DEVDOCS", jira_issue="PROJ-123")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1
        assert filtered[0]["confluence_metadata"]["space_key"] == "DEVDOCS"
        assert filtered[0]["confluence_metadata"]["jira_issue_links"][0]["issue_key"] == "PROJ-123"

    def test_non_confluence_excluded_with_filters(self, strategy: HybridSearchStrategy) -> None:
        """Test that non-Confluence chunks are excluded when Confluence filters are active."""
        mock_results = [
            {"confluence_metadata": {"space_key": "DEVDOCS"}},
            {"confluence_metadata": None},  # Web crawl chunk
        ]

        filters = ConfluenceSearchFilters(space_key="DEVDOCS")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1
        assert filtered[0]["confluence_metadata"] is not None

    def test_empty_jira_links_excluded(self, strategy: HybridSearchStrategy) -> None:
        """Test that pages with empty jira_issue_links are excluded when filtering by JIRA."""
        mock_results = [
            {"confluence_metadata": {"jira_issue_links": [{"issue_key": "PROJ-123"}]}},
            {"confluence_metadata": {"jira_issue_links": []}},
            {"confluence_metadata": {}},  # No jira_issue_links key
        ]

        filters = ConfluenceSearchFilters(jira_issue="PROJ-123")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1

    def test_empty_user_mentions_excluded(self, strategy: HybridSearchStrategy) -> None:
        """Test that pages with empty user_mentions are excluded when filtering by user."""
        mock_results = [
            {"confluence_metadata": {"user_mentions": [{"account_id": "user123"}]}},
            {"confluence_metadata": {"user_mentions": []}},
            {"confluence_metadata": {}},  # No user_mentions key
        ]

        filters = ConfluenceSearchFilters(mentioned_user="user123")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1

    def test_empty_path_excluded(self, strategy: HybridSearchStrategy) -> None:
        """Test that pages with empty path are excluded when filtering by hierarchy."""
        mock_results = [
            {"confluence_metadata": {"path": "/parent123/child1"}},
            {"confluence_metadata": {"path": ""}},
            {"confluence_metadata": {}},  # No path key
        ]

        filters = ConfluenceSearchFilters(hierarchy_path="/parent123/")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1

    def test_triple_filter_combination(self, strategy: HybridSearchStrategy) -> None:
        """Test combining space, JIRA, and hierarchy filters."""
        mock_results = [
            {
                "confluence_metadata": {
                    "space_key": "DEVDOCS",
                    "path": "/parent123/child1",
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                }
            },
            {
                "confluence_metadata": {
                    "space_key": "DEVDOCS",
                    "path": "/parent456/child1",  # Wrong path
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                }
            },
            {
                "confluence_metadata": {
                    "space_key": "INTERNAL",  # Wrong space
                    "path": "/parent123/child1",
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                }
            },
        ]

        filters = ConfluenceSearchFilters(
            space_key="DEVDOCS",
            hierarchy_path="/parent123/",
            jira_issue="PROJ-123",
        )
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1
        assert filtered[0]["confluence_metadata"]["space_key"] == "DEVDOCS"
        assert filtered[0]["confluence_metadata"]["path"].startswith("/parent123/")

    def test_all_four_filters_combination(self, strategy: HybridSearchStrategy) -> None:
        """Test combining all four filters (space, JIRA, hierarchy, user)."""
        mock_results = [
            {
                "confluence_metadata": {
                    "space_key": "DEVDOCS",
                    "path": "/parent123/child1",
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                    "user_mentions": [{"account_id": "user123"}],
                }
            },
            {
                "confluence_metadata": {
                    "space_key": "DEVDOCS",
                    "path": "/parent123/child1",
                    "jira_issue_links": [{"issue_key": "PROJ-123"}],
                    "user_mentions": [{"account_id": "user456"}],  # Wrong user
                }
            },
        ]

        filters = ConfluenceSearchFilters(
            space_key="DEVDOCS",
            hierarchy_path="/parent123/",
            jira_issue="PROJ-123",
            mentioned_user="user123",
        )
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1
        assert filtered[0]["confluence_metadata"]["user_mentions"][0]["account_id"] == "user123"

    def test_preserves_other_fields(self, strategy: HybridSearchStrategy) -> None:
        """Test that filter preserves all fields in matching results."""
        mock_results = [
            {
                "id": "chunk-123",
                "content": "Some content",
                "similarity": 0.95,
                "confluence_metadata": {"space_key": "DEVDOCS", "title": "Test Page"},
            }
        ]

        filters = ConfluenceSearchFilters(space_key="DEVDOCS")
        filtered = strategy._apply_confluence_filters(mock_results, filters)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "chunk-123"
        assert filtered[0]["content"] == "Some content"
        assert filtered[0]["similarity"] == 0.95
        assert filtered[0]["confluence_metadata"]["title"] == "Test Page"
