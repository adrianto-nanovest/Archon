"""Unit tests for Link Handler."""

import pytest
from bs4 import BeautifulSoup
from unittest.mock import AsyncMock, MagicMock

from src.server.services.confluence.element_handlers.link_handler import LinkHandler


@pytest.mark.asyncio
async def test_bulk_api_call_with_multiple_titles():
    """Test that bulk API call is made once for multiple page titles."""
    # Create mock confluence client
    mock_client = MagicMock()
    mock_client.find_pages_by_titles = AsyncMock(
        return_value={
            "User Guide": {
                "page_id": "123",
                "url": "https://example.atlassian.net/wiki/spaces/DEV/pages/123",
            },
            "API Reference": {
                "page_id": "456",
                "url": "https://example.atlassian.net/wiki/spaces/DEV/pages/456",
            },
        }
    )

    # Create handler with trackers
    internal_links_tracker = []
    handler = LinkHandler(
        confluence_client=mock_client, internal_links_tracker=internal_links_tracker
    )

    # Create HTML with multiple page links
    html = """
    <ac:link>
        <ri:page ri:content-title="User Guide"/>
        <ac:plain-text-link-body>User Guide</ac:plain-text-link-body>
    </ac:link>
    <ac:link>
        <ri:page ri:content-title="API Reference"/>
        <ac:plain-text-link-body>API Reference</ac:plain-text-link-body>
    </ac:link>
    <ac:link>
        <ri:page ri:content-title="User Guide"/>
        <ac:plain-text-link-body>User Guide Again</ac:plain-text-link-body>
    </ac:link>
    """
    soup = BeautifulSoup(html, "html.parser")

    # Process links
    await handler.process(soup, space_id="DEV")

    # Verify bulk API called ONCE with unique titles
    mock_client.find_pages_by_titles.assert_called_once()
    call_args = mock_client.find_pages_by_titles.call_args
    assert call_args[0][0] == "DEV"  # space_id
    assert set(call_args[0][1]) == {"User Guide", "API Reference"}  # unique titles

    # Verify metadata populated
    assert len(internal_links_tracker) == 3  # 3 links total
    assert internal_links_tracker[0]["title"] == "User Guide"
    assert internal_links_tracker[0]["page_id"] == "123"


@pytest.mark.asyncio
async def test_internal_link_resolution():
    """Test internal link resolution with valid page titles."""
    mock_client = MagicMock()
    mock_client.find_pages_by_titles = AsyncMock(
        return_value={
            "Test Page": {
                "page_id": "789",
                "url": "https://example.atlassian.net/wiki/spaces/DEV/pages/789",
            }
        }
    )

    internal_links_tracker = []
    handler = LinkHandler(
        confluence_client=mock_client, internal_links_tracker=internal_links_tracker
    )

    html = """
    <ac:link>
        <ri:page ri:content-title="Test Page"/>
        <ac:plain-text-link-body>Click Here</ac:plain-text-link-body>
    </ac:link>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id="DEV")

    # Verify markdown link created
    result = str(soup)
    assert "[Click Here](https://example.atlassian.net/wiki/spaces/DEV/pages/789)" in result

    # Verify metadata
    assert len(internal_links_tracker) == 1
    assert internal_links_tracker[0]["page_id"] == "789"


@pytest.mark.asyncio
async def test_internal_link_missing_page():
    """Test internal link with missing page (placeholder)."""
    mock_client = MagicMock()
    mock_client.find_pages_by_titles = AsyncMock(
        return_value={"Missing Page": {"page_id": None, "url": None}}
    )

    internal_links_tracker = []
    handler = LinkHandler(
        confluence_client=mock_client, internal_links_tracker=internal_links_tracker
    )

    html = """
    <ac:link>
        <ri:page ri:content-title="Missing Page"/>
        <ac:plain-text-link-body>Broken Link</ac:plain-text-link-body>
    </ac:link>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id="DEV")

    # Verify placeholder used
    result = str(soup)
    assert "[Broken Link](PLACEHOLDER_Missing_Page)" in result

    # Verify metadata with None values
    assert internal_links_tracker[0]["page_id"] is None
    assert internal_links_tracker[0]["url"] is None


@pytest.mark.asyncio
async def test_external_link_processing():
    """Test external link processing (http/https filtering)."""
    external_links_tracker = []
    handler = LinkHandler(external_links_tracker=external_links_tracker)

    html = """
    <a href="https://example.com">HTTPS Link</a>
    <a href="http://example.com">HTTP Link</a>
    <a href="ftp://example.com">FTP Link</a>
    <a href="mailto:test@example.com">Email Link</a>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id=None)

    # Verify only http/https links processed
    assert len(external_links_tracker) == 2
    assert external_links_tracker[0]["url"] == "https://example.com"
    assert external_links_tracker[1]["url"] == "http://example.com"

    # Verify markdown links created for http/https only
    result = str(soup)
    assert "[HTTPS Link](https://example.com)" in result
    assert "[HTTP Link](http://example.com)" in result
    # FTP and mailto should remain unchanged (not processed)
    assert 'href="ftp://example.com"' in result or "ftp://example.com" not in result


@pytest.mark.asyncio
async def test_jira_link_deduplication():
    """Test JIRA link deduplication (Tier 2 with existing Tier 1 data)."""
    # Pre-populate jira_links_tracker with Tier 1 data (from macro handler)
    jira_links_tracker = [
        {"issue_key": "PROJ-123", "url": "https://jira.example.com/browse/PROJ-123"}
    ]
    external_links_tracker = []

    handler = LinkHandler(
        jira_links_tracker=jira_links_tracker,
        external_links_tracker=external_links_tracker,
    )

    html = """
    <a href="https://jira.example.com/browse/PROJ-123">PROJ-123 (duplicate)</a>
    <a href="https://jira.example.com/browse/PROJ-456">PROJ-456 (new)</a>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id=None)

    # Verify only PROJ-456 added (PROJ-123 is duplicate from Tier 1)
    jira_issues = [link["issue_key"] for link in jira_links_tracker]
    assert "PROJ-123" in jira_issues
    assert "PROJ-456" in jira_issues
    assert len(jira_links_tracker) == 2  # 1 from Tier 1 + 1 new from Tier 2


@pytest.mark.asyncio
async def test_google_drive_icon_detection():
    """Test Google Drive icon detection (Docs, Sheets, Slides)."""
    external_links_tracker = []
    handler = LinkHandler(external_links_tracker=external_links_tracker)

    html = """
    <a href="https://docs.google.com/document/d/abc123">Google Doc</a>
    <a href="https://docs.google.com/spreadsheets/d/def456">Google Sheet</a>
    <a href="https://docs.google.com/presentation/d/ghi789">Google Slides</a>
    <a href="https://drive.google.com/file/d/jkl012">Google Drive File</a>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id=None)

    result = str(soup)

    # Verify icons added
    assert "[📝 Google Doc]" in result  # Docs icon
    assert "[📊 Google Sheet]" in result  # Sheets icon
    assert "[📊 Google Slides]" in result  # Slides icon
    assert "[Google Drive File]" in result  # No icon for generic Drive files

    # Verify all links in external tracker
    assert len(external_links_tracker) == 4


@pytest.mark.asyncio
async def test_link_without_client_placeholder_mode():
    """Test link handler without confluence_client (placeholder mode)."""
    internal_links_tracker = []
    handler = LinkHandler(
        confluence_client=None, internal_links_tracker=internal_links_tracker
    )

    html = """
    <ac:link>
        <ri:page ri:content-title="Some Page"/>
        <ac:plain-text-link-body>Link Text</ac:plain-text-link-body>
    </ac:link>
    """
    soup = BeautifulSoup(html, "html.parser")

    await handler.process(soup, space_id="DEV")

    # Verify placeholder used (no API call made)
    result = str(soup)
    assert "[Link Text](PLACEHOLDER_Some_Page)" in result

    # Verify metadata with None values
    assert internal_links_tracker[0]["page_id"] is None
    assert internal_links_tracker[0]["url"] is None
