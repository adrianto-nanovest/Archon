"""
Metadata Extractor for Confluence Pages.

Aggregates metadata from all handlers (macros, elements, tables) and performs
3-tier JIRA extraction with deduplication.

Story 2.4: Table Processor & Metadata Extractor
"""

import re
from typing import Any

from .utils.deduplication import (
    deduplicate_asset_links,
    deduplicate_by_key,
)


class MetadataExtractor:
    """
    Extracts and aggregates metadata from Confluence page processing.

    Aggregates metadata from:
    - JIRA links (3 tiers: macros, URLs, plain text)
    - User mentions
    - Internal/external links
    - Asset links with Docling enrichment
    - Content metrics
    """

    def __init__(self) -> None:
        """Initialize metadata extractor (no external dependencies)."""
        pass


    def _calculate_content_metrics(self, markdown_content: str) -> dict[str, int]:
        """
        Calculate content metrics from markdown.

        Args:
            markdown_content: Final markdown content

        Returns:
            Dict with word_count and content_length
        """
        word_count = len(markdown_content.split())
        content_length = len(markdown_content)

        return {"word_count": word_count, "content_length": content_length}

    def _extract_docling_metadata(self, asset_links_tracker: list[dict]) -> dict:
        """
        Extract rich attachment metadata from Docling-processed documents.

        Aggregates metadata from Docling processing results for attachments and images.

        Args:
            asset_links_tracker: List of asset link dicts

        Returns:
            Dict with processed_attachments and processed_images arrays
        """
        processed_attachments: list[dict] = []
        processed_images: list[dict] = []

        for asset in asset_links_tracker:
            if not asset.get("processed", False):
                continue

            processor = asset.get("processor", "")
            filename = asset.get("filename", "")
            asset_type = asset.get("type", "")

            # Extract metadata based on processor type
            if processor == "docling" and asset_type in ["document", "pdf", "docx"]:
                # Docling-processed document metadata
                metadata = asset.get("metadata", {})
                attachment_info = {
                    "filename": filename,
                    "processor": "docling",
                    "page_count": metadata.get("page_count", 0),
                    "table_count": metadata.get("table_count", 0),
                    "code_block_count": metadata.get("code_block_count", 0),
                    "has_formulas": metadata.get("has_formulas", False),
                }

                # Add document structure if available
                doc_structure = metadata.get("document_structure", {})
                if doc_structure:
                    attachment_info["document_structure"] = doc_structure

                processed_attachments.append(attachment_info)

            elif processor == "multimodal_llm" and asset_type == "image":
                # Multimodal LLM-processed image metadata
                image_info = {
                    "filename": filename,
                    "processor": "multimodal_llm",
                    "model": asset.get("model", "gpt-4o"),
                    "extracted_text": asset.get("extracted_text", ""),
                    "image_type": asset.get("image_type", "unknown"),
                    "has_text": bool(asset.get("extracted_text")),
                }
                processed_images.append(image_info)

            elif processor == "docling_ocr" and asset_type == "image":
                # Docling OCR-processed image metadata
                image_info = {
                    "filename": filename,
                    "processor": "docling_ocr",
                    "ocr_text": asset.get("extracted_text", ""),
                    "has_text": bool(asset.get("extracted_text")),
                }
                processed_images.append(image_info)

        return {
            "processed_attachments": processed_attachments,
            "processed_images": processed_images,
        }

    def _extract_jira_from_plain_text(self, markdown_content: str) -> list[dict]:
        """
        Extract JIRA issue keys from plain text (Tier 3).

        Uses regex pattern with word boundaries to prevent false positives.

        Args:
            markdown_content: Final markdown content

        Returns:
            List of JIRA link dicts with issue_key and url=None
        """
        # Pattern: word boundary, uppercase letters, hyphen, digits, word boundary
        pattern = r"\b([A-Z]+-\d+)\b"

        matches = re.findall(pattern, markdown_content)

        # Build JIRA links (no URL from plain text)
        jira_links: list[dict] = []
        for issue_key in matches:
            jira_links.append({"issue_key": issue_key, "url": None})

        return jira_links

    def extract_metadata(
        self,
        jira_links_tracker: list[dict],
        user_mentions_tracker: list[dict],
        internal_links_tracker: list[dict],
        external_links_tracker: list[dict],
        asset_links_tracker: list[dict],
        markdown_content: str,
    ) -> dict[str, Any]:
        """
        Extract and aggregate metadata from all trackers.

        Performs 3-tier JIRA extraction, deduplication, content metrics calculation,
        and Docling metadata enrichment.

        Args:
            jira_links_tracker: JIRA links from Tier 1 (macros) and Tier 2 (URLs)
            user_mentions_tracker: User mentions from element handlers
            internal_links_tracker: Internal page links from element handlers
            external_links_tracker: External links from macro and element handlers
            asset_links_tracker: Asset links from macro and element handlers
            markdown_content: Final markdown content

        Returns:
            Metadata dict matching confluence_pages.metadata JSONB schema
        """
        # Step 1: Aggregate JIRA links from all 3 tiers
        # Tier 1 + Tier 2 already in jira_links_tracker
        tier_1_2_jira = jira_links_tracker.copy()

        # Tier 3: Plain text regex
        tier_3_jira = self._extract_jira_from_plain_text(markdown_content)

        # Combine all tiers
        all_jira_links = tier_1_2_jira + tier_3_jira

        # Deduplicate across all tiers using utility function
        final_jira_links = deduplicate_by_key(all_jira_links, "issue_key")

        # Step 2: Deduplicate other metadata using utility functions
        final_user_mentions = deduplicate_by_key(user_mentions_tracker, "account_id")
        final_internal_links = deduplicate_by_key(internal_links_tracker, "page_id")
        final_external_links = deduplicate_by_key(external_links_tracker, "url")
        final_asset_links = deduplicate_asset_links(asset_links_tracker)

        # Step 3: Calculate content metrics
        content_metrics = self._calculate_content_metrics(markdown_content)

        # Step 4: Extract Docling-processed attachment metadata
        docling_metadata = self._extract_docling_metadata(asset_links_tracker)

        # Step 5: Build metadata dict matching confluence_pages.metadata JSONB schema
        metadata: dict[str, Any] = {
            "jira_issue_links": final_jira_links,
            "user_mentions": final_user_mentions,
            "internal_links": final_internal_links,
            "external_links": final_external_links,
            "asset_links": final_asset_links,
            "word_count": content_metrics["word_count"],
            "content_length": content_metrics["content_length"],
        }

        # Add optional asset_processing_metadata if Docling used
        if (
            docling_metadata["processed_attachments"]
            or docling_metadata["processed_images"]
        ):
            metadata["asset_processing_metadata"] = docling_metadata

        return metadata
