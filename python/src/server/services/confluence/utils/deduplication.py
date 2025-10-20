"""
Deduplication Utilities for Confluence Metadata.

Provides generic and specialized deduplication functions for JIRA links,
user mentions, internal/external links, and asset links.

Story 2.5: Utility Modules & Integration Testing
"""

import logging

logger = logging.getLogger(__name__)


def deduplicate_by_key(items: list[dict], key_field: str) -> list[dict]:
    """
    Generic deduplication by any field.

    Uses set-based deduplication (O(n) complexity) to efficiently remove
    duplicates while preserving first occurrence.

    Args:
        items: List of dicts to deduplicate
        key_field: Field name to use as unique key (e.g., "issue_key", "account_id")

    Returns:
        Deduplicated list (first occurrence preserved)

    Examples:
        >>> items = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}, {"id": "1", "name": "C"}]
        >>> deduplicate_by_key(items, "id")
        [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
    """
    seen: set[str] = set()
    deduplicated: list[dict] = []

    for item in items:
        key_value = item.get(key_field)
        if key_value and key_value not in seen:
            seen.add(key_value)
            deduplicated.append(item)

    return deduplicated


def is_jira_already_processed(issue_key: str, tracker: list[dict]) -> bool:
    """
    Check if JIRA issue key already exists in tracker.

    Case-insensitive comparison (PROJ-123 == proj-123).

    Args:
        issue_key: JIRA issue key to check (e.g., "PROJ-123")
        tracker: List of JIRA link dicts with issue_key field

    Returns:
        True if found, False otherwise

    Examples:
        >>> tracker = [{"issue_key": "PROJ-123", "url": "..."}]
        >>> is_jira_already_processed("PROJ-123", tracker)
        True
        >>> is_jira_already_processed("proj-123", tracker)
        True
        >>> is_jira_already_processed("PROJ-456", tracker)
        False
    """
    normalized_key = issue_key.upper()
    return any(
        link.get("issue_key", "").upper() == normalized_key for link in tracker
    )


def is_jira_url_already_processed(url: str, tracker: list[dict]) -> bool:
    """
    Check if JIRA URL already exists in tracker (normalized).

    Normalizes URL by stripping query params and trailing slash before comparison.

    Args:
        url: JIRA URL to check
        tracker: List of JIRA link dicts with url field

    Returns:
        True if found, False otherwise

    Examples:
        >>> tracker = [{"issue_key": "PROJ-123", "url": "https://jira.com/browse/PROJ-123"}]
        >>> is_jira_url_already_processed("https://jira.com/browse/PROJ-123", tracker)
        True
        >>> is_jira_url_already_processed("https://jira.com/browse/PROJ-123?param=1", tracker)
        True
        >>> is_jira_url_already_processed("https://jira.com/browse/PROJ-456", tracker)
        False
    """
    normalized_url = _normalize_url(url)
    return any(
        _normalize_url(link.get("url", "")) == normalized_url for link in tracker
    )


def _normalize_url(url: str) -> str:
    """
    Normalize URL for comparison.

    Strips query parameters and trailing slash.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL

    Examples:
        >>> _normalize_url("https://example.com/page?param=value")
        "https://example.com/page"
        >>> _normalize_url("https://example.com/page/")
        "https://example.com/page"
    """
    # Strip query parameters
    base_url = url.split("?")[0] if url else ""
    # Strip trailing slash
    return base_url.rstrip("/")


def deduplicate_asset_links(asset_links: list[dict]) -> list[dict]:
    """
    Deduplicate asset links by filename.

    Priority: processed > unprocessed (keep entry with highest priority).
    Merges metadata from duplicate entries.

    Special case: Preserves richest metadata by prioritizing entries with
    `processed=true` flag (Docling-enriched entries).

    Args:
        asset_links: List of asset link dicts with filename field

    Returns:
        Deduplicated list with merged metadata

    Examples:
        >>> assets = [
        ...     {"filename": "doc.pdf", "processed": False, "url": "..."},
        ...     {"filename": "doc.pdf", "processed": True, "metadata": {...}}
        ... ]
        >>> result = deduplicate_asset_links(assets)
        >>> len(result)
        1
        >>> result[0]["processed"]
        True
    """
    # Group by filename
    filename_map: dict[str, list[dict]] = {}

    for asset in asset_links:
        filename = asset.get("filename")
        if filename:
            if filename not in filename_map:
                filename_map[filename] = []
            filename_map[filename].append(asset)

    # Deduplicate with priority
    deduplicated: list[dict] = []

    for _filename, assets in filename_map.items():
        # Sort by priority: processed=True first
        assets_sorted = sorted(
            assets, key=lambda x: x.get("processed", False), reverse=True
        )

        # Keep first (highest priority)
        best_asset = assets_sorted[0].copy()  # Copy to avoid mutation

        # Merge metadata from other duplicates
        for other_asset in assets_sorted[1:]:
            # Preserve processed=True if any duplicate processed
            if other_asset.get("processed", False):
                best_asset["processed"] = True

            # Merge additional metadata fields
            for key in ["processor", "metadata", "model", "extracted_text"]:
                if key in other_asset and key not in best_asset:
                    best_asset[key] = other_asset[key]

        deduplicated.append(best_asset)

    return deduplicated


def deduplicate_jira_links(jira_links: list[dict]) -> list[dict]:
    """
    Deduplicate JIRA links by issue key (wrapper for deduplicate_by_key).

    Convenience function for JIRA-specific deduplication.

    Args:
        jira_links: List of JIRA link dicts with issue_key field

    Returns:
        Deduplicated list (first occurrence preserved)

    Examples:
        >>> links = [
        ...     {"issue_key": "PROJ-123", "url": "..."},
        ...     {"issue_key": "PROJ-456", "url": "..."},
        ...     {"issue_key": "PROJ-123", "url": "..."}
        ... ]
        >>> result = deduplicate_jira_links(links)
        >>> len(result)
        2
    """
    return deduplicate_by_key(jira_links, "issue_key")


def deduplicate_user_mentions(user_mentions: list[dict]) -> list[dict]:
    """
    Deduplicate user mentions by account_id (wrapper for deduplicate_by_key).

    Convenience function for user mention deduplication.

    Args:
        user_mentions: List of user mention dicts with account_id field

    Returns:
        Deduplicated list (first occurrence preserved)

    Examples:
        >>> mentions = [
        ...     {"account_id": "user1", "display_name": "Alice"},
        ...     {"account_id": "user2", "display_name": "Bob"},
        ...     {"account_id": "user1", "display_name": "Alice Again"}
        ... ]
        >>> result = deduplicate_user_mentions(mentions)
        >>> len(result)
        2
    """
    return deduplicate_by_key(user_mentions, "account_id")


def deduplicate_internal_links(internal_links: list[dict]) -> list[dict]:
    """
    Deduplicate internal links by page_id (wrapper for deduplicate_by_key).

    Convenience function for internal link deduplication.

    Args:
        internal_links: List of internal link dicts with page_id field

    Returns:
        Deduplicated list (first occurrence preserved)

    Examples:
        >>> links = [
        ...     {"page_id": "123", "title": "Page A"},
        ...     {"page_id": "456", "title": "Page B"},
        ...     {"page_id": "123", "title": "Page A Again"}
        ... ]
        >>> result = deduplicate_internal_links(links)
        >>> len(result)
        2
    """
    return deduplicate_by_key(internal_links, "page_id")


def deduplicate_external_links(external_links: list[dict]) -> list[dict]:
    """
    Deduplicate external links by URL (wrapper for deduplicate_by_key).

    Convenience function for external link deduplication.

    Args:
        external_links: List of external link dicts with url field

    Returns:
        Deduplicated list (first occurrence preserved)

    Examples:
        >>> links = [
        ...     {"title": "Google", "url": "https://google.com"},
        ...     {"title": "GitHub", "url": "https://github.com"},
        ...     {"title": "Google Again", "url": "https://google.com"}
        ... ]
        >>> result = deduplicate_external_links(links)
        >>> len(result)
        2
    """
    return deduplicate_by_key(external_links, "url")
