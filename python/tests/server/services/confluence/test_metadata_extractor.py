"""Unit tests for Metadata Extractor."""

import pytest

from src.server.services.confluence.metadata_extractor import MetadataExtractor
from src.server.services.confluence.utils.deduplication import (
    deduplicate_asset_links,
    deduplicate_by_key,
)


@pytest.fixture
def extractor():
    """Create MetadataExtractor instance."""
    return MetadataExtractor()


def test_jira_link_deduplication(extractor):
    """Test JIRA link deduplication by issue key."""
    jira_links = [
        {"issue_key": "PROJ-123", "url": "https://jira.../browse/PROJ-123"},
        {"issue_key": "PROJ-456", "url": "https://jira.../browse/PROJ-456"},
        {"issue_key": "PROJ-123", "url": "https://jira.../browse/PROJ-123"},  # Duplicate
    ]

    result = deduplicate_by_key(jira_links, "issue_key")

    # Should have 2 unique issue keys
    assert len(result) == 2
    issue_keys = [link["issue_key"] for link in result]
    assert "PROJ-123" in issue_keys
    assert "PROJ-456" in issue_keys


def test_jira_three_tier_aggregation(extractor):
    """Test 3-tier JIRA extraction with deduplication."""
    # Tier 1 + Tier 2 (from trackers)
    jira_tracker = [
        {"issue_key": "PROJ-123", "url": "https://jira.../browse/PROJ-123"},  # Tier 1
        {"issue_key": "PROJ-456", "url": "https://jira.../browse/PROJ-456"},  # Tier 2
    ]

    # Tier 3 (plain text)
    markdown = "See PROJ-123 and PROJ-789 for details."

    metadata = extractor.extract_metadata(
        jira_links_tracker=jira_tracker,
        user_mentions_tracker=[],
        internal_links_tracker=[],
        external_links_tracker=[],
        asset_links_tracker=[],
        markdown_content=markdown,
    )

    jira_links = metadata["jira_issue_links"]

    # Should have 3 unique issue keys (PROJ-123 deduplicated)
    assert len(jira_links) == 3
    issue_keys = [link["issue_key"] for link in jira_links]
    assert "PROJ-123" in issue_keys  # From Tier 1 (deduplicated with Tier 3)
    assert "PROJ-456" in issue_keys  # From Tier 2
    assert "PROJ-789" in issue_keys  # From Tier 3


def test_jira_plain_text_extraction(extractor):
    """Test Tier 3 JIRA extraction from plain text."""
    markdown = """
    This document references PROJ-123, DEVOPS-456, and INFRA-789.
    See also TEAM-42 for more details.
    """

    jira_links = extractor._extract_jira_from_plain_text(markdown)

    # Should extract all 4 issue keys
    assert len(jira_links) == 4
    issue_keys = [link["issue_key"] for link in jira_links]
    assert "PROJ-123" in issue_keys
    assert "DEVOPS-456" in issue_keys
    assert "INFRA-789" in issue_keys
    assert "TEAM-42" in issue_keys


def test_jira_plain_text_word_boundaries(extractor):
    """Test Tier 3 JIRA extraction respects word boundaries."""
    markdown = """
    Valid: PROJ-123
    Invalid: NOTJIRA-123ABC (letters after number)
    Invalid: PREFIX-PROJ-456 (no word boundary before)
    """

    jira_links = extractor._extract_jira_from_plain_text(markdown)

    # Should only extract PROJ-123 (valid pattern)
    issue_keys = [link["issue_key"] for link in jira_links]
    assert "PROJ-123" in issue_keys
    # Invalid patterns should not be extracted
    assert len([k for k in issue_keys if "NOTJIRA" in k]) == 0


def test_user_mention_deduplication(extractor):
    """Test user mention deduplication by account_id."""
    user_mentions = [
        {
            "account_id": "557058:abc",
            "display_name": "John Doe",
            "profile_url": "https://...",
        },
        {
            "account_id": "557058:def",
            "display_name": "Jane Smith",
            "profile_url": "https://...",
        },
        {
            "account_id": "557058:abc",
            "display_name": "John Doe",
            "profile_url": "https://...",
        },  # Duplicate
    ]

    result = deduplicate_by_key(user_mentions, "account_id")

    # Should have 2 unique account IDs
    assert len(result) == 2
    account_ids = [mention["account_id"] for mention in result]
    assert "557058:abc" in account_ids
    assert "557058:def" in account_ids


def test_internal_link_deduplication(extractor):
    """Test internal link deduplication by page_id."""
    internal_links = [
        {"page_id": "12345", "title": "User Guide", "url": "https://..."},
        {"page_id": "67890", "title": "API Docs", "url": "https://..."},
        {"page_id": "12345", "title": "User Guide", "url": "https://..."},  # Duplicate
    ]

    result = deduplicate_by_key(internal_links, "page_id")

    # Should have 2 unique page IDs
    assert len(result) == 2
    page_ids = [link["page_id"] for link in result]
    assert "12345" in page_ids
    assert "67890" in page_ids


def test_external_link_deduplication(extractor):
    """Test external link deduplication by URL."""
    external_links = [
        {"title": "GitHub", "url": "https://github.com/example"},
        {"title": "Documentation", "url": "https://docs.example.com"},
        {"title": "GitHub", "url": "https://github.com/example"},  # Duplicate
    ]

    result = deduplicate_by_key(external_links, "url")

    # Should have 2 unique URLs
    assert len(result) == 2
    urls = [link["url"] for link in result]
    assert "https://github.com/example" in urls
    assert "https://docs.example.com" in urls


def test_asset_link_deduplication_priority(extractor):
    """Test asset link deduplication with priority (processed > unprocessed)."""
    asset_links = [
        {
            "filename": "document.pdf",
            "source": "attachment",
            "type": "document",
            "processed": False,
        },
        {
            "filename": "document.pdf",
            "source": "attachment",
            "type": "document",
            "processed": True,
            "processor": "docling",
            "metadata": {"page_count": 10},
        },
        {
            "filename": "image.png",
            "source": "attachment",
            "type": "image",
            "processed": True,
        },
    ]

    result = deduplicate_asset_links(asset_links)

    # Should have 2 unique filenames
    assert len(result) == 2

    # document.pdf should keep processed=True version
    doc_asset = next((a for a in result if a["filename"] == "document.pdf"), None)
    assert doc_asset is not None
    assert doc_asset["processed"] is True
    assert doc_asset["processor"] == "docling"


def test_asset_link_deduplication_metadata_merge(extractor):
    """Test asset link deduplication merges metadata from duplicates."""
    asset_links = [
        {
            "filename": "document.pdf",
            "source": "attachment",
            "type": "document",
            "processed": True,
            "processor": "docling",
        },
        {
            "filename": "document.pdf",
            "source": "attachment",
            "type": "document",
            "processed": False,
            "extra_field": "value",
        },
    ]

    result = deduplicate_asset_links(asset_links)

    # Should merge processed=True from first entry
    assert len(result) == 1
    assert result[0]["processed"] is True
    assert result[0]["processor"] == "docling"


def test_content_metrics_calculation(extractor):
    """Test content metrics calculation."""
    markdown = "This is a test document with some content. It has multiple sentences."

    metrics = extractor._calculate_content_metrics(markdown)

    assert metrics["word_count"] == len(markdown.split())
    assert metrics["content_length"] == len(markdown)
    assert metrics["word_count"] > 0
    assert metrics["content_length"] > 0


def test_docling_metadata_extraction_attachments(extractor):
    """Test Docling metadata extraction for processed attachments."""
    asset_links = [
        {
            "filename": "technical-spec.pdf",
            "source": "attachment",
            "type": "document",
            "processed": True,
            "processor": "docling",
            "metadata": {
                "page_count": 15,
                "table_count": 3,
                "code_block_count": 5,
                "has_formulas": True,
                "document_structure": {"sections": 8, "max_heading_level": 4},
            },
        },
        {
            "filename": "unprocessed.pdf",
            "source": "attachment",
            "type": "document",
            "processed": False,
        },
    ]

    docling_metadata = extractor._extract_docling_metadata(asset_links)

    # Should extract processed attachment metadata
    assert len(docling_metadata["processed_attachments"]) == 1
    attachment = docling_metadata["processed_attachments"][0]
    assert attachment["filename"] == "technical-spec.pdf"
    assert attachment["processor"] == "docling"
    assert attachment["page_count"] == 15
    assert attachment["table_count"] == 3
    assert attachment["code_block_count"] == 5
    assert attachment["has_formulas"] is True
    assert "document_structure" in attachment


def test_docling_metadata_extraction_images(extractor):
    """Test Docling metadata extraction for processed images."""
    asset_links = [
        {
            "filename": "screenshot.png",
            "source": "attachment",
            "type": "image",
            "processed": True,
            "processor": "multimodal_llm",
            "model": "gpt-4o",
            "extracted_text": "Login screen with username field",
            "image_type": "screenshot",
        },
        {
            "filename": "diagram.png",
            "source": "attachment",
            "type": "image",
            "processed": True,
            "processor": "docling_ocr",
            "extracted_text": "System architecture diagram",
        },
    ]

    docling_metadata = extractor._extract_docling_metadata(asset_links)

    # Should extract both image processing results
    assert len(docling_metadata["processed_images"]) == 2

    # Check multimodal LLM image
    llm_image = next(
        (
            img
            for img in docling_metadata["processed_images"]
            if img["processor"] == "multimodal_llm"
        ),
        None,
    )
    assert llm_image is not None
    assert llm_image["filename"] == "screenshot.png"
    assert llm_image["model"] == "gpt-4o"
    assert llm_image["extracted_text"] == "Login screen with username field"
    assert llm_image["image_type"] == "screenshot"
    assert llm_image["has_text"] is True

    # Check Docling OCR image
    ocr_image = next(
        (
            img
            for img in docling_metadata["processed_images"]
            if img["processor"] == "docling_ocr"
        ),
        None,
    )
    assert ocr_image is not None
    assert ocr_image["filename"] == "diagram.png"
    assert ocr_image["ocr_text"] == "System architecture diagram"
    assert ocr_image["has_text"] is True


def test_metadata_schema_compliance(extractor):
    """Test metadata schema matches confluence_pages.metadata JSONB structure."""
    # Create sample trackers
    jira_links = [{"issue_key": "PROJ-123", "url": "https://jira.../browse/PROJ-123"}]
    user_mentions = [
        {
            "account_id": "557058:abc",
            "display_name": "John Doe",
            "profile_url": "https://...",
        }
    ]
    internal_links = [
        {"page_id": "12345", "title": "User Guide", "url": "https://..."}
    ]
    external_links = [{"title": "GitHub", "url": "https://github.com/example"}]
    asset_links = [
        {
            "filename": "screenshot.png",
            "source": "attachment",
            "type": "image",
            "processed": True,
        }
    ]
    markdown = "This is a test document with some content."

    metadata = extractor.extract_metadata(
        jira_links_tracker=jira_links,
        user_mentions_tracker=user_mentions,
        internal_links_tracker=internal_links,
        external_links_tracker=external_links,
        asset_links_tracker=asset_links,
        markdown_content=markdown,
    )

    # Verify all required fields present
    assert "jira_issue_links" in metadata
    assert "user_mentions" in metadata
    assert "internal_links" in metadata
    assert "external_links" in metadata
    assert "asset_links" in metadata
    assert "word_count" in metadata
    assert "content_length" in metadata

    # Verify types
    assert isinstance(metadata["jira_issue_links"], list)
    assert isinstance(metadata["user_mentions"], list)
    assert isinstance(metadata["internal_links"], list)
    assert isinstance(metadata["external_links"], list)
    assert isinstance(metadata["asset_links"], list)
    assert isinstance(metadata["word_count"], int)
    assert isinstance(metadata["content_length"], int)


def test_empty_trackers_return_empty_lists(extractor):
    """Test empty trackers return empty lists, not None."""
    metadata = extractor.extract_metadata(
        jira_links_tracker=[],
        user_mentions_tracker=[],
        internal_links_tracker=[],
        external_links_tracker=[],
        asset_links_tracker=[],
        markdown_content="",
    )

    # All should be empty lists, not None
    assert metadata["jira_issue_links"] == []
    assert metadata["user_mentions"] == []
    assert metadata["internal_links"] == []
    assert metadata["external_links"] == []
    assert metadata["asset_links"] == []
    assert metadata["word_count"] == 0
    assert metadata["content_length"] == 0


def test_optional_asset_processing_metadata(extractor):
    """Test asset_processing_metadata is optional (only when Docling used)."""
    # Test without Docling
    metadata_no_docling = extractor.extract_metadata(
        jira_links_tracker=[],
        user_mentions_tracker=[],
        internal_links_tracker=[],
        external_links_tracker=[],
        asset_links_tracker=[],
        markdown_content="test",
    )

    # Should NOT have asset_processing_metadata
    assert "asset_processing_metadata" not in metadata_no_docling

    # Test with Docling
    asset_links_with_docling = [
        {
            "filename": "document.pdf",
            "source": "attachment",
            "type": "document",
            "processed": True,
            "processor": "docling",
            "metadata": {"page_count": 10},
        }
    ]

    metadata_with_docling = extractor.extract_metadata(
        jira_links_tracker=[],
        user_mentions_tracker=[],
        internal_links_tracker=[],
        external_links_tracker=[],
        asset_links_tracker=asset_links_with_docling,
        markdown_content="test",
    )

    # Should have asset_processing_metadata
    assert "asset_processing_metadata" in metadata_with_docling
    assert "processed_attachments" in metadata_with_docling["asset_processing_metadata"]


def test_jira_deduplication_across_all_tiers(extractor):
    """Test JIRA deduplication works across Tier 1, Tier 2, and Tier 3."""
    # Same issue key from all 3 tiers
    jira_tracker = [
        {"issue_key": "PROJ-123", "url": "https://jira.../browse/PROJ-123"},  # Tier 1
        {"issue_key": "PROJ-123", "url": "https://jira.../browse/PROJ-123"},  # Tier 2
    ]

    markdown = "See PROJ-123 for details."  # Tier 3

    metadata = extractor.extract_metadata(
        jira_links_tracker=jira_tracker,
        user_mentions_tracker=[],
        internal_links_tracker=[],
        external_links_tracker=[],
        asset_links_tracker=[],
        markdown_content=markdown,
    )

    # Should have only ONE entry for PROJ-123
    assert len(metadata["jira_issue_links"]) == 1
    assert metadata["jira_issue_links"][0]["issue_key"] == "PROJ-123"


def test_asset_links_preserve_rich_metadata(extractor):
    """Test asset link deduplication preserves rich metadata."""
    asset_links = [
        {
            "filename": "screenshot.png",
            "source": "attachment",
            "type": "image",
            "processed": True,
            "processor": "multimodal_llm",
            "model": "gpt-4o",
            "extracted_text": "Login screen",
            "image_type": "screenshot",
        }
    ]

    metadata = extractor.extract_metadata(
        jira_links_tracker=[],
        user_mentions_tracker=[],
        internal_links_tracker=[],
        external_links_tracker=[],
        asset_links_tracker=asset_links,
        markdown_content="test",
    )

    # Rich metadata should be preserved in asset_links
    asset = metadata["asset_links"][0]
    assert asset["filename"] == "screenshot.png"
    assert asset["processed"] is True
    assert asset["processor"] == "multimodal_llm"
    assert asset["model"] == "gpt-4o"
    assert asset["extracted_text"] == "Login screen"
    assert asset["image_type"] == "screenshot"
