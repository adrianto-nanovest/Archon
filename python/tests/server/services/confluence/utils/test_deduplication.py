"""
Unit tests for deduplication utilities module.

Story 2.5: Utility Modules & Integration Testing
"""


from src.server.services.confluence.utils.deduplication import (
    deduplicate_asset_links,
    deduplicate_by_key,
    deduplicate_external_links,
    deduplicate_internal_links,
    deduplicate_jira_links,
    deduplicate_user_mentions,
    is_jira_already_processed,
    is_jira_url_already_processed,
)


class TestDeduplicateByKey:
    """Test generic deduplication by key field."""

    def test_deduplicates_by_single_field(self):
        """Should deduplicate by specified key field."""
        items = [
            {"id": "1", "name": "A"},
            {"id": "2", "name": "B"},
            {"id": "1", "name": "C"},
        ]
        result = deduplicate_by_key(items, "id")
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[0]["name"] == "A"  # First occurrence preserved
        assert result[1]["id"] == "2"

    def test_preserves_first_occurrence(self):
        """Should preserve first occurrence of duplicate keys."""
        items = [
            {"key": "duplicate", "value": "first"},
            {"key": "duplicate", "value": "second"},
        ]
        result = deduplicate_by_key(items, "key")
        assert len(result) == 1
        assert result[0]["value"] == "first"

    def test_handles_empty_list(self):
        """Should handle empty list without error."""
        result = deduplicate_by_key([], "key")
        assert result == []

    def test_handles_missing_key_field(self):
        """Should skip items missing the key field."""
        items = [
            {"id": "1", "name": "A"},
            {"name": "B"},  # Missing id field
            {"id": "2", "name": "C"},
        ]
        result = deduplicate_by_key(items, "id")
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_handles_different_key_fields(self):
        """Should work with any key field name."""
        items = [
            {"account_id": "user1", "name": "Alice"},
            {"account_id": "user2", "name": "Bob"},
            {"account_id": "user1", "name": "Alice Again"},
        ]
        result = deduplicate_by_key(items, "account_id")
        assert len(result) == 2
        assert result[0]["account_id"] == "user1"


class TestIsJiraAlreadyProcessed:
    """Test JIRA key checking function."""

    def test_finds_exact_match(self):
        """Should find exact issue key match."""
        tracker = [{"issue_key": "PROJ-123", "url": "..."}]
        assert is_jira_already_processed("PROJ-123", tracker)

    def test_case_insensitive_comparison(self):
        """Should compare issue keys case-insensitively."""
        tracker = [{"issue_key": "PROJ-123", "url": "..."}]
        assert is_jira_already_processed("proj-123", tracker)
        assert is_jira_already_processed("Proj-123", tracker)
        assert is_jira_already_processed("PROJ-123", tracker)

    def test_returns_false_for_missing_key(self):
        """Should return False for missing issue key."""
        tracker = [{"issue_key": "PROJ-123", "url": "..."}]
        assert not is_jira_already_processed("PROJ-456", tracker)

    def test_handles_empty_tracker(self):
        """Should return False for empty tracker."""
        assert not is_jira_already_processed("PROJ-123", [])

    def test_handles_multiple_entries(self):
        """Should search through multiple entries."""
        tracker = [
            {"issue_key": "PROJ-123", "url": "..."},
            {"issue_key": "PROJ-456", "url": "..."},
            {"issue_key": "PROJ-789", "url": "..."},
        ]
        assert is_jira_already_processed("PROJ-456", tracker)


class TestIsJiraUrlAlreadyProcessed:
    """Test JIRA URL checking function."""

    def test_finds_exact_url_match(self):
        """Should find exact URL match."""
        tracker = [
            {"issue_key": "PROJ-123", "url": "https://jira.com/browse/PROJ-123"}
        ]
        assert is_jira_url_already_processed(
            "https://jira.com/browse/PROJ-123", tracker
        )

    def test_normalizes_query_parameters(self):
        """Should match URLs with query parameters."""
        tracker = [
            {"issue_key": "PROJ-123", "url": "https://jira.com/browse/PROJ-123"}
        ]
        assert is_jira_url_already_processed(
            "https://jira.com/browse/PROJ-123?param=1", tracker
        )

    def test_normalizes_trailing_slash(self):
        """Should match URLs with trailing slash."""
        tracker = [
            {"issue_key": "PROJ-123", "url": "https://jira.com/browse/PROJ-123"}
        ]
        assert is_jira_url_already_processed(
            "https://jira.com/browse/PROJ-123/", tracker
        )

    def test_returns_false_for_different_url(self):
        """Should return False for different URL."""
        tracker = [
            {"issue_key": "PROJ-123", "url": "https://jira.com/browse/PROJ-123"}
        ]
        assert not is_jira_url_already_processed(
            "https://jira.com/browse/PROJ-456", tracker
        )

    def test_handles_empty_tracker(self):
        """Should return False for empty tracker."""
        assert not is_jira_url_already_processed(
            "https://jira.com/browse/PROJ-123", []
        )


class TestDeduplicateAssetLinks:
    """Test asset link deduplication function."""

    def test_deduplicates_by_filename(self):
        """Should deduplicate by filename field."""
        assets = [
            {"filename": "doc.pdf", "url": "..."},
            {"filename": "image.png", "url": "..."},
            {"filename": "doc.pdf", "url": "..."},
        ]
        result = deduplicate_asset_links(assets)
        assert len(result) == 2

    def test_prioritizes_processed_entries(self):
        """Should prioritize processed=True entries."""
        assets = [
            {"filename": "doc.pdf", "processed": False, "url": "..."},
            {"filename": "doc.pdf", "processed": True, "metadata": {...}},
        ]
        result = deduplicate_asset_links(assets)
        assert len(result) == 1
        assert result[0]["processed"] is True

    def test_merges_metadata_from_duplicates(self):
        """Should merge metadata from duplicate entries."""
        assets = [
            {"filename": "doc.pdf", "url": "url1", "processor": "docling"},
            {"filename": "doc.pdf", "url": "url2", "metadata": {"pages": 5}},
        ]
        result = deduplicate_asset_links(assets)
        assert len(result) == 1
        assert "processor" in result[0]
        assert "metadata" in result[0]

    def test_preserves_richest_metadata(self):
        """Should preserve entry with most metadata fields."""
        assets = [
            {"filename": "doc.pdf", "processed": True, "metadata": {"pages": 5}},
            {
                "filename": "doc.pdf",
                "processed": True,
                "model": "gpt-4o",
                "extracted_text": "...",
            },
        ]
        result = deduplicate_asset_links(assets)
        assert len(result) == 1
        assert "metadata" in result[0]
        assert "model" in result[0]
        assert "extracted_text" in result[0]

    def test_handles_empty_list(self):
        """Should handle empty list without error."""
        result = deduplicate_asset_links([])
        assert result == []

    def test_handles_missing_filename(self):
        """Should skip items missing filename."""
        assets = [
            {"filename": "doc.pdf", "url": "..."},
            {"url": "..."},  # Missing filename
        ]
        result = deduplicate_asset_links(assets)
        assert len(result) == 1


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    def test_deduplicate_jira_links(self):
        """Should deduplicate JIRA links by issue_key."""
        links = [
            {"issue_key": "PROJ-123", "url": "..."},
            {"issue_key": "PROJ-456", "url": "..."},
            {"issue_key": "PROJ-123", "url": "..."},
        ]
        result = deduplicate_jira_links(links)
        assert len(result) == 2
        assert result[0]["issue_key"] == "PROJ-123"
        assert result[1]["issue_key"] == "PROJ-456"

    def test_deduplicate_user_mentions(self):
        """Should deduplicate user mentions by account_id."""
        mentions = [
            {"account_id": "user1", "display_name": "Alice"},
            {"account_id": "user2", "display_name": "Bob"},
            {"account_id": "user1", "display_name": "Alice Again"},
        ]
        result = deduplicate_user_mentions(mentions)
        assert len(result) == 2
        assert result[0]["account_id"] == "user1"
        assert result[0]["display_name"] == "Alice"  # First occurrence

    def test_deduplicate_internal_links(self):
        """Should deduplicate internal links by page_id."""
        links = [
            {"page_id": "123", "title": "Page A"},
            {"page_id": "456", "title": "Page B"},
            {"page_id": "123", "title": "Page A Again"},
        ]
        result = deduplicate_internal_links(links)
        assert len(result) == 2
        assert result[0]["page_id"] == "123"
        assert result[0]["title"] == "Page A"

    def test_deduplicate_external_links(self):
        """Should deduplicate external links by url."""
        links = [
            {"title": "Google", "url": "https://google.com"},
            {"title": "GitHub", "url": "https://github.com"},
            {"title": "Google Again", "url": "https://google.com"},
        ]
        result = deduplicate_external_links(links)
        assert len(result) == 2
        assert result[0]["url"] == "https://google.com"
        assert result[0]["title"] == "Google"
