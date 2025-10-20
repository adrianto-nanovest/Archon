"""
Utility modules for Confluence HTML processing.

This package contains shared utility functions for HTML parsing, URL conversion,
link deduplication, and other common operations used by macro and element handlers.

Utilities are designed to be stateless and reusable across different handler implementations.
"""

# HTML utilities
# Deduplication utilities
from .deduplication import (
    deduplicate_asset_links,
    deduplicate_by_key,
    deduplicate_external_links,
    deduplicate_internal_links,
    deduplicate_jira_links,
    deduplicate_user_mentions,
    is_jira_already_processed,
    is_jira_url_already_processed,
)
from .html_utils import (
    clean_heading_text,
    clean_table_cell_text,
    ensure_utf8_safe,
    extract_text_content,
    normalize_whitespace,
)

# URL converter
from .url_converter import convert_embed_url

__all__ = [
    # HTML utilities
    "normalize_whitespace",
    "clean_heading_text",
    "clean_table_cell_text",
    "ensure_utf8_safe",
    "extract_text_content",
    # URL converter
    "convert_embed_url",
    # Deduplication utilities
    "deduplicate_by_key",
    "is_jira_already_processed",
    "is_jira_url_already_processed",
    "deduplicate_asset_links",
    "deduplicate_jira_links",
    "deduplicate_user_mentions",
    "deduplicate_internal_links",
    "deduplicate_external_links",
]
