"""
Comprehensive End-to-End Integration Tests for Confluence Processing.

Tests full page conversion with all handlers working together.

Story 2.5: Utility Modules & Integration Testing
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.server.services.confluence.confluence_processor import ConfluenceProcessor


@pytest.fixture
def mock_confluence_client():
    """Create mock Confluence client."""
    client = MagicMock()
    client.find_pages_by_titles = AsyncMock(return_value={})
    client.get_users_by_account_ids = AsyncMock(return_value={})
    return client


@pytest.fixture
def mock_docling_processor():
    """Create mock Docling processor."""
    processor = MagicMock()
    processor.process_attachment = AsyncMock(
        return_value={
            "success": True,
            "content": "Processed attachment content",
            "metadata": {"page_count": 5, "table_count": 2},
        }
    )
    processor.process_image = AsyncMock(
        return_value={
            "success": True,
            "text": "Extracted image text",
            "metadata": {"image_type": "chart"},
        }
    )
    return processor


@pytest.fixture
def processor(mock_confluence_client, mock_docling_processor):
    """Create ConfluenceProcessor with mocked dependencies."""
    return ConfluenceProcessor(
        confluence_client=mock_confluence_client,
        docling_processor=mock_docling_processor,
    )


@pytest.mark.asyncio
async def test_full_page_conversion_with_all_handlers(processor):
    """Test full page conversion with mixed content types."""
    html = """
    <h1>API Documentation</h1>
    <p>This page describes our REST API endpoints.</p>

    <ac:structured-macro ac:name="code">
        <ac:parameter ac:name="language">python</ac:parameter>
        <ac:plain-text-body><![CDATA[
def get_user(user_id):
    return api.get(f"/users/{user_id}")
        ]]></ac:plain-text-body>
    </ac:structured-macro>

    <h2>Related Issues</h2>
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">API-123</ac:parameter>
    </ac:structured-macro>

    <p>See also <a href="https://jira.company.com/browse/API-456">API-456</a> and API-789 for details.</p>

    <table>
        <tr><th>Endpoint</th><th>Method</th></tr>
        <tr><td>/users</td><td>GET</td></tr>
        <tr><td>/posts</td><td>POST</td></tr>
    </table>

    <p>Contact <ac:link><ri:user ri:account-id="user1"/></ac:link> for questions.</p>
    """

    markdown, metadata = await processor.html_to_markdown(
        html, page_id="test-page", space_id="TEST"
    )

    # Verify markdown structure
    assert "# API Documentation" in markdown
    assert "```python" in markdown
    assert "def get_user" in markdown
    assert "## Related Issues" in markdown
    assert "API-123" in markdown

    # Verify hierarchical table format
    assert "<!-- TABLE_START -->" in markdown
    assert "## Row" in markdown
    assert "### " in markdown
    assert "<!-- TABLE_END -->" in markdown

    # Verify metadata completeness
    assert "jira_issue_links" in metadata
    assert "user_mentions" in metadata
    assert "internal_links" in metadata
    assert "external_links" in metadata
    assert "asset_links" in metadata
    assert "word_count" in metadata
    assert "content_length" in metadata

    # Verify JIRA 3-tier extraction
    jira_keys = [link["issue_key"] for link in metadata["jira_issue_links"]]
    assert "API-123" in jira_keys  # Tier 1: macro
    assert "API-456" in jira_keys  # Tier 2: URL
    assert "API-789" in jira_keys  # Tier 3: plain text


@pytest.mark.asyncio
async def test_3tier_jira_extraction_all_tiers_contribute(processor):
    """Test JIRA extraction from all 3 tiers with deduplication."""
    html = """
    <h1>JIRA Integration Test</h1>

    <!-- Tier 1: JIRA macro -->
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">PROJ-123</ac:parameter>
    </ac:structured-macro>

    <!-- Tier 2: JIRA URL -->
    <p><a href="https://jira.company.com/browse/PROJ-456">PROJ-456</a></p>

    <!-- Tier 3: Plain text reference -->
    <p>This relates to PROJ-789 and PROJ-123 (duplicate)</p>
    """

    markdown, metadata = await processor.html_to_markdown(
        html, page_id="test-page", space_id="TEST"
    )

    jira_links = metadata["jira_issue_links"]
    jira_keys = [link["issue_key"] for link in jira_links]

    # All 3 tiers should contribute
    assert "PROJ-123" in jira_keys
    assert "PROJ-456" in jira_keys
    assert "PROJ-789" in jira_keys

    # Should be deduplicated (PROJ-123 appears twice)
    assert len(jira_keys) == 3


@pytest.mark.asyncio
async def test_hierarchical_table_format_not_standard_markdown(processor):
    """Test hierarchical table format with markers."""
    html = """
    <h1>Table Test</h1>
    <table>
        <thead>
            <tr><th>Name</th><th>Age</th><th>Role</th></tr>
        </thead>
        <tbody>
            <tr><td>Alice</td><td>30</td><td>Engineer</td></tr>
            <tr><td>Bob</td><td>25</td><td>Designer</td></tr>
        </tbody>
    </table>
    """

    markdown, metadata = await processor.html_to_markdown(
        html, page_id="test-page", space_id="TEST"
    )

    # Verify hierarchical structure
    assert "<!-- TABLE_START -->" in markdown
    assert "<!-- TABLE_END -->" in markdown
    assert "## Row" in markdown
    assert "### " in markdown

    # Verify NO standard markdown table pipes
    table_section = markdown[
        markdown.find("<!-- TABLE_START -->") : markdown.find("<!-- TABLE_END -->")
    ]
    assert "|" not in table_section  # No pipe-delimited tables

    # Verify table summary comment
    assert "<!--" in markdown
    assert "columns" in markdown.lower() or "rows" in markdown.lower()


@pytest.mark.asyncio
async def test_metadata_schema_compliance(processor):
    """Test metadata matches confluence_pages.metadata JSONB schema."""
    html = """
    <h1>Metadata Test</h1>
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">TEST-1</ac:parameter>
    </ac:structured-macro>
    <p><ac:link><ri:user ri:account-id="user1"/></ac:link></p>
    <p><a href="https://external.com">External Link</a></p>
    """

    markdown, metadata = await processor.html_to_markdown(
        html, page_id="test-page", space_id="TEST"
    )

    # Verify required fields
    assert "jira_issue_links" in metadata
    assert isinstance(metadata["jira_issue_links"], list)

    assert "user_mentions" in metadata
    assert isinstance(metadata["user_mentions"], list)

    assert "internal_links" in metadata
    assert isinstance(metadata["internal_links"], list)

    assert "external_links" in metadata
    assert isinstance(metadata["external_links"], list)

    assert "asset_links" in metadata
    assert isinstance(metadata["asset_links"], list)

    assert "word_count" in metadata
    assert isinstance(metadata["word_count"], int)

    assert "content_length" in metadata
    assert isinstance(metadata["content_length"], int)

    # Verify JIRA link structure
    if metadata["jira_issue_links"]:
        jira_link = metadata["jira_issue_links"][0]
        assert "issue_key" in jira_link
        assert "url" in jira_link

    # Verify user mention structure
    if metadata["user_mentions"]:
        user_mention = metadata["user_mentions"][0]
        assert "account_id" in user_mention


@pytest.mark.asyncio
async def test_malformed_html_graceful_degradation(processor):
    """Test processing completes with malformed HTML."""
    html = """
    <h1>Malformed HTML Test
    <p>Unclosed paragraph
    <div>Missing closing div
    <table><tr><td>Incomplete table</table>
    """

    # Should not crash
    markdown, metadata = await processor.html_to_markdown(
        html, page_id="test-page", space_id="TEST"
    )

    # Verify processing completed
    assert isinstance(markdown, str)
    assert isinstance(metadata, dict)
    assert len(markdown) > 0


@pytest.mark.asyncio
async def test_error_isolation_one_handler_failure_doesnt_break_pipeline(
    processor, mock_confluence_client
):
    """Test pipeline continues when one handler fails."""
    # Make user lookup fail
    mock_confluence_client.get_users_by_account_ids = AsyncMock(
        side_effect=Exception("User service down")
    )

    html = """
    <h1>Error Isolation Test</h1>
    <p><ac:link><ri:user ri:account-id="user1"/></ac:link></p>
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">TEST-1</ac:parameter>
    </ac:structured-macro>
    """

    # Should complete despite user handler failure
    markdown, metadata = await processor.html_to_markdown(
        html, page_id="test-page", space_id="TEST"
    )

    # Verify processing continued
    assert isinstance(markdown, str)
    assert isinstance(metadata, dict)

    # JIRA should still be extracted (different handler)
    jira_links = metadata["jira_issue_links"]
    assert len(jira_links) > 0
    assert jira_links[0]["issue_key"] == "TEST-1"
