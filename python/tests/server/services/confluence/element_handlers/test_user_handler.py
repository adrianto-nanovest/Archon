"""Unit tests for User Handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.element_handlers.user_handler import UserHandler


@pytest.mark.asyncio
async def test_bulk_api_call_with_multiple_account_ids():
    """Test that bulk API call is made once for multiple account IDs."""
    # Create mock confluence client
    mock_client = MagicMock()
    mock_client.get_users_by_account_ids = AsyncMock(
        return_value={
            "557058:abc123": {
                "display_name": "John Doe",
                "email": "john@example.com",
                "profile_url": "https://example.atlassian.net/people/557058:abc123",
            },
            "557058:def456": {
                "display_name": "Jane Smith",
                "email": "jane@example.com",
                "profile_url": "https://example.atlassian.net/people/557058:def456",
            },
        }
    )

    # Create handler with tracker
    user_mentions_tracker = []
    handler = UserHandler(
        confluence_client=mock_client, user_mentions_tracker=user_mentions_tracker
    )

    # Create HTML with multiple user mentions (including duplicate)
    html = """
    <p>Mentioned users: <ri:user ri:account-id="557058:abc123"/> and <ri:user ri:account-id="557058:def456"/> and <ri:user ri:account-id="557058:abc123"/> again</p>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Process user mentions
    await handler.process(soup, space_id=None)

    # Verify bulk API called ONCE with unique account IDs
    mock_client.get_users_by_account_ids.assert_called_once()
    call_args = mock_client.get_users_by_account_ids.call_args
    assert set(call_args[0][0]) == {"557058:abc123", "557058:def456"}  # unique account IDs

    # Verify metadata populated (only unique users)
    assert len(user_mentions_tracker) == 2
    assert user_mentions_tracker[0]["account_id"] == "557058:abc123"
    assert user_mentions_tracker[0]["display_name"] == "John Doe"
    assert user_mentions_tracker[1]["account_id"] == "557058:def456"
    assert user_mentions_tracker[1]["display_name"] == "Jane Smith"


@pytest.mark.asyncio
async def test_user_mention_processing():
    """Test user mention processing with valid accounts."""
    mock_client = MagicMock()
    mock_client.get_users_by_account_ids = AsyncMock(
        return_value={
            "557058:test789": {
                "display_name": "Test User",
                "email": "test@example.com",
                "profile_url": "https://example.atlassian.net/people/557058:test789",
            }
        }
    )

    user_mentions_tracker = []
    handler = UserHandler(
        confluence_client=mock_client, user_mentions_tracker=user_mentions_tracker
    )

    html = """
    <p>Hello <ri:user ri:account-id="557058:test789"/>!</p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id=None)

    # Verify markdown mention created
    result = str(soup)
    assert "@Test User" in result

    # Verify metadata
    assert len(user_mentions_tracker) == 1
    assert user_mentions_tracker[0]["account_id"] == "557058:test789"
    assert user_mentions_tracker[0]["display_name"] == "Test User"
    assert (
        user_mentions_tracker[0]["profile_url"]
        == "https://example.atlassian.net/people/557058:test789"
    )


@pytest.mark.asyncio
async def test_user_mention_without_client():
    """Test user mention processing without confluence_client (placeholder mode)."""
    user_mentions_tracker = []
    handler = UserHandler(confluence_client=None, user_mentions_tracker=user_mentions_tracker)

    html = """
    <p>User: <ri:user ri:account-id="557058:unknown"/></p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id=None)

    # Verify account ID used as fallback
    result = str(soup)
    assert "@557058:unknown" in result

    # Verify metadata with account ID as display_name
    assert len(user_mentions_tracker) == 1
    assert user_mentions_tracker[0]["account_id"] == "557058:unknown"
    assert user_mentions_tracker[0]["display_name"] == "557058:unknown"
    assert user_mentions_tracker[0]["profile_url"] is None


@pytest.mark.asyncio
async def test_deduplication():
    """Test deduplication (same account ID twice)."""
    mock_client = MagicMock()
    mock_client.get_users_by_account_ids = AsyncMock(
        return_value={
            "557058:dup123": {
                "display_name": "Duplicate User",
                "email": "dup@example.com",
                "profile_url": "https://example.atlassian.net/people/557058:dup123",
            }
        }
    )

    user_mentions_tracker = []
    handler = UserHandler(
        confluence_client=mock_client, user_mentions_tracker=user_mentions_tracker
    )

    html = """
    <p>First mention: <ri:user ri:account-id="557058:dup123"/></p>
    <p>Second mention: <ri:user ri:account-id="557058:dup123"/></p>
    <p>Third mention: <ri:user ri:account-id="557058:dup123"/></p>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id=None)

    # Verify all mentions replaced in markdown
    result = str(soup)
    assert result.count("@Duplicate User") == 3

    # Verify metadata contains only ONE entry (deduplicated)
    assert len(user_mentions_tracker) == 1
    assert user_mentions_tracker[0]["account_id"] == "557058:dup123"


@pytest.mark.asyncio
async def test_user_mentions_tracker_metadata_population():
    """Test user_mentions_tracker metadata population."""
    mock_client = MagicMock()
    mock_client.get_users_by_account_ids = AsyncMock(
        return_value={
            "557058:user1": {
                "display_name": "User One",
                "email": "user1@example.com",
                "profile_url": "https://example.atlassian.net/people/557058:user1",
            },
            "557058:user2": {
                "display_name": "User Two",
                "email": "user2@example.com",
                "profile_url": "https://example.atlassian.net/people/557058:user2",
            },
            "557058:user3": {
                "display_name": None,  # Missing display name
                "email": "user3@example.com",
                "profile_url": None,
            },
        }
    )

    user_mentions_tracker = []
    handler = UserHandler(
        confluence_client=mock_client, user_mentions_tracker=user_mentions_tracker
    )

    html = """
    <ri:user ri:account-id="557058:user1"/>
    <ri:user ri:account-id="557058:user2"/>
    <ri:user ri:account-id="557058:user3"/>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id=None)

    # Verify all users in tracker
    assert len(user_mentions_tracker) == 3

    # Verify complete metadata structure
    user1 = user_mentions_tracker[0]
    assert user1["account_id"] == "557058:user1"
    assert user1["display_name"] == "User One"
    assert user1["profile_url"] == "https://example.atlassian.net/people/557058:user1"

    user2 = user_mentions_tracker[1]
    assert user2["account_id"] == "557058:user2"
    assert user2["display_name"] == "User Two"

    user3 = user_mentions_tracker[2]
    assert user3["account_id"] == "557058:user3"
    assert user3["display_name"] == "557058:user3"  # Fallback to account ID
    assert user3["profile_url"] is None
