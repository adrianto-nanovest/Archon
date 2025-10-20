"""
Unit tests for JiraMacroHandler.

Tests Tier 1 extraction (macro parameters), JQL handling, and deduplication.
"""

from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from src.server.services.confluence.macro_handlers.jira_macro import JiraMacroHandler


@pytest.fixture
def jira_handler():
    """Create JiraMacroHandler instance without JIRA client."""
    return JiraMacroHandler()


@pytest.fixture
def jira_handler_with_client():
    """Create JiraMacroHandler instance with mocked JIRA client."""
    mock_client = MagicMock()
    return JiraMacroHandler(jira_client=mock_client)


@pytest.mark.asyncio
async def test_tier1_single_issue_key_extraction(jira_handler):
    """Test Tier 1: Extract single issue key from macro parameter."""
    html = """
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">PROJ-123</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await jira_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify markdown link created
    assert "[PROJ-123]" in result
    assert "JIRA_PLACEHOLDER_PROJ-123" in result

    # Verify issue tracked in metadata
    assert len(jira_handler.jira_links_tracker) == 1
    assert jira_handler.jira_links_tracker[0]["issue_key"] == "PROJ-123"
    assert "https://jira.example.com/browse/PROJ-123" in jira_handler.jira_links_tracker[0]["url"]


@pytest.mark.asyncio
async def test_deduplication_same_issue_twice(jira_handler):
    """Test deduplication: Same issue key tracked only once."""
    html1 = """
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">PROJ-456</ac:parameter>
    </ac:structured-macro>
    """
    html2 = """
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">PROJ-456</ac:parameter>
    </ac:structured-macro>
    """

    # Process first occurrence
    soup1 = BeautifulSoup(html1, "html.parser")
    macro_tag1 = soup1.find("ac:structured-macro")
    await jira_handler.process(macro_tag1, page_id="test-page")

    # Process second occurrence (duplicate)
    soup2 = BeautifulSoup(html2, "html.parser")
    macro_tag2 = soup2.find("ac:structured-macro")
    await jira_handler.process(macro_tag2, page_id="test-page")

    # Verify only one entry tracked
    assert len(jira_handler.jira_links_tracker) == 1
    assert jira_handler.jira_links_tracker[0]["issue_key"] == "PROJ-456"


@pytest.mark.asyncio
async def test_jql_query_with_jira_client(jira_handler_with_client):
    """Test JQL query parameter with JIRA client present."""
    html = """
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="jqlQuery">project = DEV AND status = Open</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await jira_handler_with_client.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify JQL placeholder comment with client (HTML-escaped by BeautifulSoup)
    assert "JIRA Table: JQL Query: project = DEV AND status = Open" in result


@pytest.mark.asyncio
async def test_jql_query_without_jira_client(jira_handler):
    """Test JQL query parameter without JIRA client (placeholder only)."""
    html = """
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="jqlQuery">status = Done AND assignee = currentUser()</ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await jira_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify JQL placeholder comment without client (HTML-escaped by BeautifulSoup)
    assert "JIRA Table (JQL): status = Done AND assignee = currentUser()" in result


@pytest.mark.asyncio
async def test_no_parameters_edge_case(jira_handler):
    """Test JIRA macro without key or jqlQuery parameters."""
    html = """
    <ac:structured-macro ac:name="jira">
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await jira_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify placeholder comment for missing parameters (HTML-escaped by BeautifulSoup)
    assert "JIRA Macro (no parameters)" in result

    # Verify nothing tracked
    assert len(jira_handler.jira_links_tracker) == 0


@pytest.mark.asyncio
async def test_multiple_different_issues(jira_handler):
    """Test multiple different issue keys tracked correctly."""
    issues = ["PROJ-100", "PROJ-200", "PROJ-300"]

    for issue_key in issues:
        html = f"""
        <ac:structured-macro ac:name="jira">
            <ac:parameter ac:name="key">{issue_key}</ac:parameter>
        </ac:structured-macro>
        """
        soup = BeautifulSoup(html, "html.parser")
        macro_tag = soup.find("ac:structured-macro")
        await jira_handler.process(macro_tag, page_id="test-page")

    # Verify all 3 tracked
    assert len(jira_handler.jira_links_tracker) == 3
    tracked_keys = [link["issue_key"] for link in jira_handler.jira_links_tracker]
    assert set(tracked_keys) == set(issues)


@pytest.mark.asyncio
async def test_issue_key_with_whitespace(jira_handler):
    """Test issue key with leading/trailing whitespace is trimmed."""
    html = """
    <ac:structured-macro ac:name="jira">
        <ac:parameter ac:name="key">  PROJ-789  </ac:parameter>
    </ac:structured-macro>
    """
    soup = BeautifulSoup(html, "html.parser")
    macro_tag = soup.find("ac:structured-macro")

    await jira_handler.process(macro_tag, page_id="test-page")

    result = str(soup).strip()

    # Verify whitespace trimmed
    assert "[PROJ-789]" in result
    assert len(jira_handler.jira_links_tracker) == 1
    assert jira_handler.jira_links_tracker[0]["issue_key"] == "PROJ-789"
