"""Integration tests for element handlers (Story 2.3)."""

import pytest
from bs4 import BeautifulSoup
from unittest.mock import AsyncMock, MagicMock

from src.server.services.confluence.confluence_processor import ConfluenceProcessor


@pytest.mark.asyncio
async def test_iv1_bulk_api_calls_single_call_for_n_items():
    """IV1: User/page resolution uses bulk API calls (verify single call for N items)."""
    # Create mock client
    mock_client = MagicMock()
    mock_client.find_pages_by_titles = AsyncMock(
        return_value={
            "Page A": {"page_id": "1", "url": "https://example.com/1"},
            "Page B": {"page_id": "2", "url": "https://example.com/2"},
        }
    )
    mock_client.get_users_by_account_ids = AsyncMock(
        return_value={
            "user1": {"display_name": "User One", "email": None, "profile_url": None},
            "user2": {"display_name": "User Two", "email": None, "profile_url": None},
        }
    )

    processor = ConfluenceProcessor(confluence_client=mock_client)

    html = """
    <ac:link><ri:page ri:content-title="Page A"/></ac:link>
    <ac:link><ri:page ri:content-title="Page B"/></ac:link>
    <ri:user ri:account-id="user1"/>
    <ri:user ri:account-id="user2"/>
    """

    await processor.html_to_markdown(html, "page123", "SPACE")

    # Verify bulk API called ONCE for pages
    assert mock_client.find_pages_by_titles.call_count == 1
    # Verify bulk API called ONCE for users
    assert mock_client.get_users_by_account_ids.call_count == 1


@pytest.mark.asyncio
async def test_iv2_jira_link_deduplication():
    """IV2: Link handler correctly deduplicates JIRA links already processed by macro handler."""
    processor = ConfluenceProcessor()

    # Simulate JIRA macro (Tier 1) adding PROJ-123
    processor.jira_links_tracker.append(
        {"issue_key": "PROJ-123", "url": "https://jira.com/browse/PROJ-123"}
    )

    html = """
    <a href="https://jira.com/browse/PROJ-123">PROJ-123 (duplicate)</a>
    <a href="https://jira.com/browse/PROJ-456">PROJ-456 (new)</a>
    """

    await processor.html_to_markdown(html, "page123")

    # Verify only PROJ-456 added (PROJ-123 is duplicate from Tier 1)
    issue_keys = [link["issue_key"] for link in processor.jira_links_tracker]
    assert issue_keys.count("PROJ-123") == 1  # Only from Tier 1
    assert "PROJ-456" in issue_keys


@pytest.mark.asyncio
async def test_iv4_all_metadata_fields_populated():
    """IV4: All metadata fields populated correctly."""
    mock_client = MagicMock()
    mock_client.find_pages_by_titles = AsyncMock(
        return_value={"Test Page": {"page_id": "1", "url": "https://example.com/1"}}
    )
    mock_client.get_users_by_account_ids = AsyncMock(
        return_value={"user1": {"display_name": "Test User", "email": None, "profile_url": None}}
    )

    processor = ConfluenceProcessor(confluence_client=mock_client)

    html = """
    <ac:link><ri:page ri:content-title="Test Page"/></ac:link>
    <a href="https://external.com">External Link</a>
    <ri:user ri:account-id="user1"/>
    <ac:image><ri:attachment ri:filename="test.png"/></ac:image>
    """

    await processor.html_to_markdown(html, "page123", "SPACE")

    # Verify all metadata fields present
    assert len(processor.internal_links_tracker) > 0
    assert len(processor.external_links_tracker) > 0
    assert len(processor.user_mentions_tracker) > 0
    assert len(processor.asset_links_tracker) > 0


# Tests IV5-IV9 have been covered by individual handler unit tests
# These integration tests verify end-to-end flows
