"""
Hybrid Search Strategy

Implements hybrid search combining vector similarity search with full-text search
using PostgreSQL's ts_vector for improved recall and precision in document and
code example retrieval.

Strategy combines:
1. Vector/semantic search for conceptual matches
2. Full-text search using ts_vector for efficient keyword matching
3. Returns union of both result sets for maximum coverage
4. Confluence metadata enrichment for Confluence-sourced chunks

Confluence Integration:
- Chunks from Confluence sources include `metadata.page_id` linking to `confluence_pages`
- Search results are enriched with Confluence metadata (space_key, title, path, JIRA links, etc.)
- Non-Confluence chunks have `confluence_metadata: None` for backward compatibility

Confluence Filtering (Story 4.2):
- Search results can be filtered by Confluence-specific criteria:
  - space_key: Filter by Confluence space
  - jira_issue: Filter by linked JIRA issue key
  - hierarchy_path: Filter by page hierarchy path prefix
  - mentioned_user: Filter by mentioned user account_id
- Filters are combined with AND logic
- Non-Confluence results are excluded when Confluence filters are active

Performance Monitoring (Story 4.3):
- Slow query logging for queries exceeding 1000ms threshold
- Query timing metrics for observability
- Query fingerprinting for pattern analysis
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from supabase import Client

from ...config.logfire_config import get_logger, safe_span
from ..embeddings.embedding_service import create_embedding

# Slow query threshold in milliseconds (Story 4.3)
SLOW_QUERY_THRESHOLD_MS = 1000

logger = get_logger(__name__)


@dataclass
class ConfluenceSearchFilters:
    """
    Filters for Confluence-specific search criteria.

    All filters are combined with AND logic. When any filter is active,
    non-Confluence results are excluded from the response.

    Attributes:
        space_key: Filter by Confluence space key (exact match)
        jira_issue: Filter by linked JIRA issue key (e.g., "PROJ-123")
        hierarchy_path: Filter by page hierarchy path prefix (e.g., "/parent123/")
        mentioned_user: Filter by mentioned user account_id
    """

    space_key: str | None = None
    jira_issue: str | None = None
    hierarchy_path: str | None = None
    mentioned_user: str | None = None

    def has_any_filter(self) -> bool:
        """Check if any filter is active."""
        return any([self.space_key, self.jira_issue, self.hierarchy_path, self.mentioned_user])


class HybridSearchStrategy:
    """Strategy class implementing hybrid search combining vector and full-text search.

    Supports Confluence metadata enrichment for Confluence-sourced chunks. Search results
    from Confluence pages are enriched with metadata from the `confluence_pages` table,
    including space_key, title, path (hierarchy), JIRA issue links, and user mentions.
    """

    def __init__(self, supabase_client: Client, base_strategy: Any):
        self.supabase_client = supabase_client
        self.base_strategy = base_strategy

    async def _fetch_confluence_metadata(
        self,
        page_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """
        Fetch Confluence metadata for given page IDs.

        Queries the `confluence_pages` table in batch to retrieve rich metadata
        for Confluence-sourced chunks. Uses an IN clause for efficiency (single query).

        Args:
            page_ids: List of Confluence page IDs to fetch metadata for

        Returns:
            Dict mapping page_id to metadata dict containing:
            - space_key: Confluence space key
            - title: Page title
            - path: Materialized hierarchy path
            - jira_issue_links: List of linked JIRA issues
            - user_mentions: List of mentioned users
            - ancestors: Page hierarchy breadcrumbs
            - internal_links: Links to other Confluence pages
        """
        if not page_ids:
            return {}

        with safe_span("confluence_metadata_fetch") as span:
            try:
                # Batch query confluence_pages table
                response = (
                    self.supabase_client.from_("confluence_pages")
                    .select("page_id, space_key, title, path, metadata")
                    .in_("page_id", page_ids)
                    .eq("is_deleted", False)
                    .execute()
                )

                result: dict[str, dict[str, Any]] = {}
                for row in response.data or []:
                    page_metadata = row.get("metadata", {}) or {}
                    result[row["page_id"]] = {
                        "space_key": row.get("space_key"),
                        "title": row.get("title"),
                        "path": row.get("path"),
                        "jira_issue_links": page_metadata.get("jira_issue_links", []),
                        "user_mentions": page_metadata.get("user_mentions", []),
                        "ancestors": page_metadata.get("ancestors", []),
                        "internal_links": page_metadata.get("internal_links", []),
                    }

                span.set_attribute("page_ids_requested", len(page_ids))
                span.set_attribute("metadata_found", len(result))

                logger.debug(f"Fetched Confluence metadata for {len(result)}/{len(page_ids)} pages")
                return result

            except Exception as e:
                logger.error(f"Failed to fetch Confluence metadata: {e}")
                span.set_attribute("error", str(e))
                return {}

    def _apply_confluence_filters(
        self,
        results: list[dict[str, Any]],
        filters: ConfluenceSearchFilters,
    ) -> list[dict[str, Any]]:
        """
        Apply Confluence-specific filters to search results.

        Strategy: Post-filter results after enrichment (simpler than modifying SQL)
        - Space filter: exact match on space_key
        - JIRA filter: check jira_issue_links array contains issue_key
        - Hierarchy filter: path prefix match
        - User mention filter: check user_mentions array contains account_id

        All filters combined with AND logic.

        Args:
            results: Search results with confluence_metadata already enriched
            filters: Confluence-specific filter criteria

        Returns:
            Filtered list of results matching all specified criteria
        """
        if not filters or not filters.has_any_filter():
            return results

        filtered_results = []
        for result in results:
            confluence_meta = result.get("confluence_metadata")

            # Non-Confluence chunks: exclude when any Confluence filter is active
            if confluence_meta is None:
                continue

            # Apply space_key filter (AC: 2)
            if filters.space_key:
                if confluence_meta.get("space_key") != filters.space_key:
                    continue

            # Apply jira_issue filter (AC: 3)
            if filters.jira_issue:
                jira_links = confluence_meta.get("jira_issue_links", [])
                if not any(link.get("issue_key") == filters.jira_issue for link in jira_links):
                    continue

            # Apply hierarchy_path filter (AC: 4)
            if filters.hierarchy_path:
                page_path = confluence_meta.get("path", "")
                if not page_path.startswith(filters.hierarchy_path):
                    continue

            # Apply mentioned_user filter (AC: 5)
            if filters.mentioned_user:
                user_mentions = confluence_meta.get("user_mentions", [])
                if not any(m.get("account_id") == filters.mentioned_user for m in user_mentions):
                    continue

            filtered_results.append(result)

        return filtered_results

    async def search_documents_hybrid(
        self,
        query: str,
        query_embedding: list[float],
        match_count: int,
        filter_metadata: dict | None = None,
        confluence_filters: ConfluenceSearchFilters | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search on archon_crawled_pages table using the PostgreSQL
        hybrid search function that combines vector and full-text search.

        Excludes chunks with _pending_deletion flag to ensure zero-downtime during
        atomic chunk updates. Enriches Confluence-sourced chunks with metadata from
        the `confluence_pages` table.

        Performance Monitoring (Story 4.3):
        - Times the entire search operation
        - Logs warning for queries exceeding 1000ms threshold
        - Records timing metrics in span attributes

        Args:
            query: Original search query text
            query_embedding: Pre-computed query embedding
            match_count: Number of results to return
            filter_metadata: Optional metadata filter dict
            confluence_filters: Optional Confluence-specific filters (space_key, jira_issue,
                hierarchy_path, mentioned_user). When active, non-Confluence results are excluded.

        Returns:
            List of matching documents with structure:
            {
                "id": str,
                "url": str,
                "chunk_number": int,
                "content": str,
                "metadata": dict,
                "source_id": str,
                "similarity": float,
                "match_type": str,
                "confluence_metadata": {  # None for non-Confluence chunks
                    "space_key": str,
                    "title": str,
                    "path": str,  # Hierarchy path
                    "jira_issue_links": list[dict],
                    "user_mentions": list[dict],
                    "ancestors": list[dict],
                    "internal_links": list[dict]
                } | None
            }
        """
        # Start timing for slow query detection (Story 4.3)
        start_time = time.perf_counter()

        with safe_span("hybrid_search_documents") as span:
            try:
                # Prepare filter and source parameters
                filter_json = filter_metadata or {}
                source_filter = filter_json.pop("source", None) if "source" in filter_json else None

                # Call the hybrid search PostgreSQL function
                response = self.supabase_client.rpc(
                    "hybrid_search_archon_crawled_pages",
                    {
                        "query_embedding": query_embedding,
                        "query_text": query,
                        "match_count": match_count,
                        "filter": filter_json,
                        "source_filter": source_filter,
                    },
                ).execute()

                if not response.data:
                    logger.debug("No results from hybrid search")
                    # Still record timing for empty results
                    elapsed_ms = (time.perf_counter() - start_time) * 1000
                    span.set_attribute("search_duration_ms", elapsed_ms)
                    return []

                # Format results and exclude chunks with _pending_deletion flag
                results = []
                for row in response.data:
                    # Exclude chunks marked for deletion (atomic update support)
                    metadata = row.get("metadata", {}) or {}
                    if metadata.get("_pending_deletion") == "true":
                        logger.debug(f"Excluding chunk {row['id']} with _pending_deletion flag")
                        continue

                    result = {
                        "id": row["id"],
                        "url": row["url"],
                        "chunk_number": row["chunk_number"],
                        "content": row["content"],
                        "metadata": metadata,
                        "source_id": row["source_id"],
                        "similarity": row["similarity"],
                        "match_type": row["match_type"],
                    }
                    results.append(result)

                span.set_attribute("results_count", len(results))

                # Confluence metadata enrichment
                with safe_span("confluence_metadata_enrichment"):
                    # Extract page_ids from Confluence chunks
                    page_ids = [
                        r["metadata"].get("page_id")
                        for r in results
                        if r.get("metadata", {}).get("page_id")
                    ]

                    # Fetch Confluence metadata in batch (single query)
                    confluence_metadata = await self._fetch_confluence_metadata(page_ids)

                    # Enrich results with Confluence metadata
                    for result in results:
                        page_id = result.get("metadata", {}).get("page_id")
                        if page_id and page_id in confluence_metadata:
                            result["confluence_metadata"] = confluence_metadata[page_id]
                        else:
                            result["confluence_metadata"] = None

                    # Log enrichment stats
                    enriched_count = sum(1 for r in results if r.get("confluence_metadata"))
                    if enriched_count > 0:
                        logger.debug(f"Enriched {enriched_count}/{len(results)} results with Confluence metadata")

                # Apply Confluence-specific filters after enrichment (Story 4.2)
                if confluence_filters and confluence_filters.has_any_filter():
                    pre_filter_count = len(results)
                    results = self._apply_confluence_filters(results, confluence_filters)
                    logger.debug(f"Applied Confluence filters: {pre_filter_count} -> {len(results)} results")
                    span.set_attribute("confluence_filtered_count", len(results))

                # Log match type distribution for debugging
                match_types: dict[str, int] = {}
                for r in results:
                    mt = r.get("match_type", "unknown")
                    match_types[mt] = match_types.get(mt, 0) + 1

                logger.debug(
                    f"Hybrid search returned {len(results)} results. "
                    f"Match types: {match_types}"
                )

                # Calculate elapsed time and log slow queries (Story 4.3)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Generate query fingerprint for pattern analysis
                filter_str = str(confluence_filters) if confluence_filters else ""
                query_fingerprint = hashlib.md5(f"{query}|{filter_str}".encode()).hexdigest()[:8]

                # Record timing metrics in span
                span.set_attribute("search_duration_ms", elapsed_ms)
                span.set_attribute("is_slow_query", elapsed_ms > SLOW_QUERY_THRESHOLD_MS)
                span.set_attribute("query_fingerprint", query_fingerprint)

                # Log slow queries (>1000ms threshold)
                if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
                    logger.warning(
                        f"Slow search query detected: {elapsed_ms:.2f}ms | "
                        f"query='{query[:50]}...' | "
                        f"match_count={match_count} | "
                        f"confluence_filters={confluence_filters} | "
                        f"results_count={len(results)} | "
                        f"fingerprint={query_fingerprint}"
                    )
                else:
                    logger.debug(f"Search completed in {elapsed_ms:.2f}ms | fingerprint={query_fingerprint}")

                return results

            except Exception as e:
                # Record timing even on error
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                span.set_attribute("search_duration_ms", elapsed_ms)
                span.set_attribute("error", str(e))
                logger.error(f"Hybrid document search failed: {e}")
                return []

    async def search_code_examples_hybrid(
        self,
        query: str,
        match_count: int,
        filter_metadata: dict | None = None,
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search on archon_code_examples table using the PostgreSQL
        hybrid search function that combines vector and full-text search.

        Args:
            query: Search query text
            match_count: Number of results to return
            filter_metadata: Optional metadata filter dict
            source_id: Optional source ID to filter results

        Returns:
            List of matching code examples from both vector and text search
        """
        with safe_span("hybrid_search_code_examples") as span:
            try:
                # Create query embedding
                query_embedding = await create_embedding(query)

                if not query_embedding:
                    logger.error("Failed to create embedding for code example query")
                    return []

                # Prepare filter and source parameters
                filter_json = filter_metadata or {}
                # Use source_id parameter if provided, otherwise check filter_metadata
                final_source_filter = source_id
                if not final_source_filter and "source" in filter_json:
                    final_source_filter = filter_json.pop("source")

                # Call the hybrid search PostgreSQL function
                response = self.supabase_client.rpc(
                    "hybrid_search_archon_code_examples",
                    {
                        "query_embedding": query_embedding,
                        "query_text": query,
                        "match_count": match_count,
                        "filter": filter_json,
                        "source_filter": final_source_filter,
                    },
                ).execute()

                if not response.data:
                    logger.debug("No results from hybrid code search")
                    return []

                # Format results and exclude chunks with _pending_deletion flag
                results = []
                for row in response.data:
                    # Exclude chunks marked for deletion (atomic update support)
                    metadata = row.get("metadata", {})
                    if metadata.get("_pending_deletion") == "true":
                        logger.debug(f"Excluding code example {row['id']} with _pending_deletion flag")
                        continue

                    result = {
                        "id": row["id"],
                        "url": row["url"],
                        "chunk_number": row["chunk_number"],
                        "content": row["content"],
                        "summary": row["summary"],
                        "metadata": metadata,
                        "source_id": row["source_id"],
                        "similarity": row["similarity"],
                        "match_type": row["match_type"],
                    }
                    results.append(result)

                span.set_attribute("results_count", len(results))

                # Log match type distribution for debugging
                match_types: dict[str, int] = {}
                for r in results:
                    mt = r.get("match_type", "unknown")
                    match_types[mt] = match_types.get(mt, 0) + 1

                logger.debug(
                    f"Hybrid code search returned {len(results)} results. "
                    f"Match types: {match_types}"
                )

                return results

            except Exception as e:
                logger.error(f"Hybrid code example search failed: {e}")
                span.set_attribute("error", str(e))
                return []
