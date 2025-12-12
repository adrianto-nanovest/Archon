"""
Confluence Sync Service - CQL-Based Incremental Sync

This module provides the ConfluenceSyncService class that orchestrates incremental
synchronization of Confluence spaces using CQL (Confluence Query Language) to fetch
only changed pages since the last sync.

Key Features:
- CQL-based incremental sync (fetches only modified pages)
- Version comparison for create/update/delete detection
- Integration with ConfluenceProcessor for HTML→Markdown conversion
- Automatic chunking and embedding via document_storage_service
- Sync metrics tracking (pages added/updated/deleted, duration, API calls)
- Progress tracking for real-time status updates
- Configurable deletion detection strategies (weekly, every_sync, on_demand)

Example usage:
    ```python
    from server.services.confluence.confluence_client import ConfluenceClient
    from server.services.confluence.confluence_processor import ConfluenceProcessor
    from server.utils.progress.progress_tracker import ProgressTracker
    from server.utils import get_supabase_client

    # Initialize dependencies
    confluence_client = ConfluenceClient(base_url, email, token)
    confluence_processor = ConfluenceProcessor(confluence_client=confluence_client)
    supabase_client = get_supabase_client()

    # Create sync service
    sync_service = ConfluenceSyncService(
        confluence_client=confluence_client,
        confluence_processor=confluence_processor,
        supabase_client=supabase_client
    )

    # Execute sync
    progress_tracker = ProgressTracker(progress_id="sync_123", operation_type="confluence_sync")
    metrics = await sync_service.sync_space(
        source_id="src_abc123",
        space_key="DEVDOCS",
        progress_tracker=progress_tracker
    )

    print(f"Sync completed: {metrics['pages_added']} added, {metrics['pages_updated']} updated")
    ```
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypedDict

from ...utils import get_supabase_client
from ...utils.progress.progress_tracker import ProgressTracker
from ..storage.document_storage_service import add_documents_to_supabase
from ..storage.storage_services import DocumentStorageService
from .confluence_client import ConfluenceClient
from .confluence_processor import ConfluenceProcessor

logger = logging.getLogger(__name__)


class DeletionStrategy(str, Enum):
    """Configurable deletion detection strategies for Confluence sync.

    Each strategy balances API efficiency vs. data freshness:
    - WEEKLY_RECONCILIATION: Minimizes API calls (1 per week), deleted pages remain up to 7 days
    - EVERY_SYNC: Immediate detection (1 extra API call per sync), best for critical spaces
    - ON_DEMAND: Zero API overhead during sync, user triggers deletion detection manually
    """

    WEEKLY_RECONCILIATION = "weekly_reconciliation"  # Check once per week (default)
    EVERY_SYNC = "every_sync"  # Check every sync cycle
    ON_DEMAND = "on_demand"  # Never auto-check, manual trigger only


@dataclass
class DeletionEvent:
    """Records a page deletion event for logging and auditing.

    Attributes:
        page_id: Confluence page ID that was deleted
        title: Page title at time of deletion
        deletion_timestamp: ISO 8601 timestamp when deletion was detected
        source_id: archon_sources.source_id for this Confluence space
        space_key: Confluence space key (e.g., "DEVDOCS")
    """

    page_id: str
    title: str
    deletion_timestamp: str
    source_id: str
    space_key: str


class SyncMetrics(TypedDict):
    """Type definition for sync metrics returned by sync_space."""

    pages_added: int
    pages_updated: int
    pages_deleted: int
    duration_seconds: float
    api_calls_made: int
    last_sync_timestamp: str
    status: str
    # Atomic update metrics
    chunks_marked_pending: int
    chunks_deleted: int
    chunks_rolled_back: int
    atomic_update_failures: int
    # Deletion detection metrics (Story 3.3)
    deletion_strategy: str  # Strategy used for this sync
    deletion_check_performed: bool  # Whether deletion check ran
    last_deletion_check: str | None  # ISO timestamp of last check


class ConfluenceSyncService:
    """
    Orchestrates CQL-based incremental synchronization of Confluence spaces.

    This service coordinates the full sync workflow:
    1. Fetch last_sync_timestamp from archon_sources.metadata
    2. Execute CQL query to find changed pages
    3. Process each page with ConfluenceProcessor
    4. Store metadata in confluence_pages table
    5. Chunk and embed content via document_storage_service
    6. Track sync metrics and update archon_sources.metadata

    Attributes:
        confluence_client: Client for Confluence API operations
        confluence_processor: Processor for HTML→Markdown conversion
        supabase_client: Supabase client for database operations
    """

    def __init__(
        self,
        confluence_client: ConfluenceClient,
        confluence_processor: ConfluenceProcessor,
        supabase_client: Any | None = None,
    ):
        """
        Initialize ConfluenceSyncService with required dependencies.

        Args:
            confluence_client: ConfluenceClient instance for API calls
            confluence_processor: ConfluenceProcessor for HTML→Markdown conversion
            supabase_client: Optional Supabase client (uses get_supabase_client() if None)
        """
        self.confluence_client = confluence_client
        self.confluence_processor = confluence_processor
        self.supabase_client = supabase_client or get_supabase_client()
        self.document_storage = DocumentStorageService(self.supabase_client)
        self.logger = logging.getLogger("ConfluenceSyncService")

    async def _get_deletion_strategy(self, source_id: str) -> DeletionStrategy:
        """
        Retrieve the deletion detection strategy for a source.

        Queries archon_sources.metadata->>'deletion_strategy' and returns the
        configured strategy. Defaults to WEEKLY_RECONCILIATION if not set.

        Args:
            source_id: Source ID from archon_sources table

        Returns:
            DeletionStrategy enum value

        Example:
            >>> strategy = await sync_service._get_deletion_strategy("src_123")
            >>> if strategy == DeletionStrategy.EVERY_SYNC:
            ...     # Run deletion detection
        """
        try:
            response = (
                self.supabase_client.from_("archon_sources")
                .select("metadata")
                .eq("source_id", source_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                metadata = response.data[0].get("metadata", {})
                if isinstance(metadata, dict):
                    strategy_value = metadata.get("deletion_strategy")
                    if strategy_value:
                        try:
                            strategy = DeletionStrategy(strategy_value)
                            self.logger.debug(
                                f"Deletion strategy for source {source_id}: {strategy.value}"
                            )
                            return strategy
                        except ValueError:
                            self.logger.warning(
                                f"Invalid deletion_strategy '{strategy_value}' for source {source_id}, "
                                f"using default: weekly_reconciliation"
                            )

            # Default to weekly reconciliation
            self.logger.debug(
                f"No deletion_strategy configured for source {source_id}, "
                f"using default: weekly_reconciliation"
            )
            return DeletionStrategy.WEEKLY_RECONCILIATION

        except Exception as e:
            self.logger.error(
                f"Failed to get deletion strategy for source {source_id}: {e}",
                exc_info=True
            )
            # Default to weekly reconciliation on error
            return DeletionStrategy.WEEKLY_RECONCILIATION

    async def _check_weekly_reconciliation(self, source_id: str, space_key: str) -> bool:
        """
        Check if deletion detection should run for weekly_reconciliation strategy.

        Retrieves last_deletion_check from archon_sources.metadata and determines
        if 7+ days have passed since the last check.

        Args:
            source_id: Source ID from archon_sources table
            space_key: Confluence space key (for logging)

        Returns:
            True if deletion check should run (NULL or >= 7 days), False otherwise

        Example:
            >>> should_check = await sync_service._check_weekly_reconciliation("src_123", "DEVDOCS")
            >>> if should_check:
            ...     deleted_ids = await sync_service._detect_deleted_pages_every_sync(...)
        """
        try:
            response = (
                self.supabase_client.from_("archon_sources")
                .select("metadata")
                .eq("source_id", source_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                metadata = response.data[0].get("metadata", {})
                if isinstance(metadata, dict):
                    last_check_str = metadata.get("last_deletion_check")
                    if last_check_str:
                        try:
                            last_check = datetime.fromisoformat(last_check_str.replace("Z", "+00:00"))
                            days_since_check = (datetime.now(UTC) - last_check).days

                            if days_since_check < 7:
                                self.logger.info(
                                    f"Skipping deletion check for space {space_key}: "
                                    f"last check {days_since_check} days ago (< 7)"
                                )
                                return False

                            self.logger.info(
                                f"Running deletion check for space {space_key}: "
                                f"last check {days_since_check} days ago (>= 7)"
                            )
                            return True

                        except ValueError as e:
                            self.logger.warning(
                                f"Invalid last_deletion_check timestamp '{last_check_str}': {e}, "
                                f"forcing deletion check"
                            )
                            return True

            # First-time sync or no last_deletion_check - force check
            self.logger.info(
                f"No last_deletion_check for space {space_key}, running first deletion check"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to check weekly reconciliation for source {source_id}: {e}",
                exc_info=True
            )
            # On error, skip deletion check to avoid disruption
            return False

    async def _update_last_deletion_check(self, source_id: str) -> None:
        """
        Update last_deletion_check timestamp after successful deletion detection.

        Updates archon_sources.metadata->>'last_deletion_check' with current timestamp.
        Preserves existing metadata fields.

        Args:
            source_id: Source ID from archon_sources table

        Raises:
            Exception: If database update fails
        """
        try:
            # First get existing metadata to preserve other fields
            response = (
                self.supabase_client.from_("archon_sources")
                .select("metadata")
                .eq("source_id", source_id)
                .execute()
            )

            existing_metadata: dict[str, Any] = {}
            if response.data and len(response.data) > 0:
                existing_metadata = response.data[0].get("metadata", {}) or {}

            # Update with new timestamp
            updated_metadata = {
                **existing_metadata,
                "last_deletion_check": datetime.now(UTC).isoformat(),
            }

            self.supabase_client.from_("archon_sources").update({
                "metadata": updated_metadata
            }).eq("source_id", source_id).execute()

            self.logger.debug(f"Updated last_deletion_check for source {source_id}")

        except Exception as e:
            self.logger.error(
                f"Failed to update last_deletion_check for source {source_id}: {e}",
                exc_info=True
            )
            raise

    async def _detect_deleted_pages_every_sync(
        self,
        source_id: str,
        space_key: str,
    ) -> list[str]:
        """
        Detect deleted pages by comparing Confluence API with database state.

        Calls get_space_pages_ids() to get current page IDs from Confluence,
        then compares with confluence_pages table to find deletions.

        Args:
            source_id: Source ID from archon_sources table
            space_key: Confluence space key

        Returns:
            List of page_ids that exist in DB but not in Confluence (deleted)

        Example:
            >>> deleted_ids = await sync_service._detect_deleted_pages_every_sync(
            ...     source_id="src_123",
            ...     space_key="DEVDOCS"
            ... )
            >>> print(f"Found {len(deleted_ids)} deleted pages")
        """
        try:
            # Get current page IDs from Confluence API
            api_page_ids = await self.confluence_client.get_space_pages_ids(space_key)
            api_page_ids_set = {str(pid) for pid in api_page_ids}

            self.logger.debug(
                f"Confluence API returned {len(api_page_ids_set)} pages for space {space_key}"
            )

            # Get page IDs from database (non-deleted pages only)
            db_response = (
                self.supabase_client.from_("confluence_pages")
                .select("page_id")
                .eq("source_id", source_id)
                .eq("is_deleted", False)
                .execute()
            )

            db_page_ids_set = {
                row["page_id"] for row in (db_response.data or [])
            }

            self.logger.debug(
                f"Database has {len(db_page_ids_set)} non-deleted pages for source {source_id}"
            )

            # Find pages that exist in DB but not in Confluence (deleted)
            deleted_page_ids = list(db_page_ids_set - api_page_ids_set)

            if deleted_page_ids:
                self.logger.info(
                    f"Deletion detection: {len(deleted_page_ids)} pages no longer in Confluence"
                )
            else:
                self.logger.debug("Deletion detection: no deleted pages found")

            return deleted_page_ids

        except Exception as e:
            self.logger.error(
                f"Failed to detect deleted pages for source {source_id}: {e}",
                exc_info=True
            )
            raise

    async def _mark_pages_deleted(
        self,
        page_ids: list[str],
        source_id: str,
        space_key: str,
    ) -> int:
        """
        Mark pages as deleted and remove their chunks from RAG system.

        For each page:
        1. Set is_deleted = TRUE in confluence_pages table
        2. Delete chunks from archon_crawled_pages via metadata->>'page_id' filter
        3. Log deletion event with structured metadata

        Args:
            page_ids: List of Confluence page IDs to mark as deleted
            source_id: Source ID from archon_sources table
            space_key: Confluence space key (for logging)

        Returns:
            Number of pages successfully marked as deleted

        Note:
            Continues processing other pages if one fails (no batch rollback).
            Individual failures are logged but do not stop the deletion process.
        """
        deleted_count = 0
        deletion_timestamp = datetime.now(UTC).isoformat()

        for page_id in page_ids:
            try:
                # Get page title for logging before marking deleted
                page_response = (
                    self.supabase_client.from_("confluence_pages")
                    .select("title")
                    .eq("page_id", page_id)
                    .execute()
                )
                page_title = "Unknown"
                if page_response.data and len(page_response.data) > 0:
                    page_title = page_response.data[0].get("title", "Unknown")

                # Mark page as deleted in confluence_pages
                self.supabase_client.from_("confluence_pages").update({
                    "is_deleted": True,
                    "updated_at": deletion_timestamp,
                }).eq("page_id", page_id).execute()

                # Delete chunks from archon_crawled_pages
                self.supabase_client.from_("archon_crawled_pages").delete().eq(
                    "source_id", source_id
                ).filter("metadata->>page_id", "eq", page_id).execute()

                deleted_count += 1

                # Log deletion event with structured data (Task 6)
                deletion_event = DeletionEvent(
                    page_id=page_id,
                    title=page_title,
                    deletion_timestamp=deletion_timestamp,
                    source_id=source_id,
                    space_key=space_key,
                )
                self._log_deletion_event(deletion_event)

            except Exception as e:
                self.logger.error(
                    f"Failed to delete page {page_id}: {e}",
                    exc_info=True
                )
                # Continue with other pages (don't fail entire batch)
                continue

        self.logger.info(
            f"Marked {deleted_count}/{len(page_ids)} pages as deleted for source {source_id}"
        )
        return deleted_count

    def _log_deletion_event(self, event: DeletionEvent) -> None:
        """
        Log a deletion event with structured metadata.

        Emits an INFO-level log with extra fields for structured logging systems.

        Args:
            event: DeletionEvent with page details
        """
        self.logger.info(
            f"Confluence page deleted: {event.title} ({event.page_id})",
            extra={
                "page_id": event.page_id,
                "title": event.title,
                "deletion_timestamp": event.deletion_timestamp,
                "source_id": event.source_id,
                "space_key": event.space_key,
            }
        )

    async def check_deletions_on_demand(
        self,
        source_id: str,
        space_key: str,
    ) -> dict[str, Any]:
        """
        Manually trigger deletion detection (public API method).

        This method runs deletion detection regardless of the configured strategy
        or last_deletion_check timestamp. Use for manual cleanup or API-triggered
        deletion detection.

        Args:
            source_id: Source ID from archon_sources table
            space_key: Confluence space key

        Returns:
            Dict with deletion metrics:
            - pages_deleted: int - Number of pages marked as deleted
            - page_ids: list[str] - IDs of pages marked as deleted

        Example:
            >>> result = await sync_service.check_deletions_on_demand(
            ...     source_id="src_123",
            ...     space_key="DEVDOCS"
            ... )
            >>> print(f"Deleted {result['pages_deleted']} pages: {result['page_ids']}")
        """
        self.logger.info(f"On-demand deletion detection triggered for space {space_key}")

        try:
            # Always run deletion detection regardless of strategy/timestamps
            deleted_page_ids = await self._detect_deleted_pages_every_sync(
                source_id=source_id,
                space_key=space_key,
            )

            if deleted_page_ids:
                # Mark pages as deleted and remove chunks
                deleted_count = await self._mark_pages_deleted(
                    page_ids=deleted_page_ids,
                    source_id=source_id,
                    space_key=space_key,
                )
            else:
                deleted_count = 0

            # Update last_deletion_check timestamp
            await self._update_last_deletion_check(source_id)

            result = {
                "pages_deleted": deleted_count,
                "page_ids": deleted_page_ids,
            }

            self.logger.info(
                f"On-demand deletion detection completed for space {space_key}: "
                f"{deleted_count} pages deleted"
            )

            return result

        except Exception as e:
            self.logger.error(
                f"On-demand deletion detection failed for space {space_key}: {e}",
                exc_info=True
            )
            raise

    async def sync_space(
        self,
        source_id: str,
        space_key: str,
        progress_tracker: ProgressTracker | None = None,
    ) -> SyncMetrics:
        """
        Orchestrate CQL-based incremental sync for a Confluence space.

        This method implements the full sync workflow:
        1. Retrieve last_sync_timestamp from archon_sources.metadata
        2. Construct CQL query: space = {space_key} AND lastModified >= "{timestamp}"
        3. Execute CQL search via ConfluenceClient
        4. For each changed page:
           - Process HTML→Markdown with ConfluenceProcessor
           - Store/update metadata in confluence_pages table
           - Delete old chunks for updated pages
           - Chunk and embed content via document_storage_service
        5. Detect page creates, updates, deletes via version comparison
        6. Track metrics: pages_added, pages_updated, pages_deleted, duration, api_calls
        7. Store metrics in archon_sources.metadata->>'sync_metrics'

        Args:
            source_id: Source ID from archon_sources table
            space_key: Confluence space key (e.g., "DEVDOCS")
            progress_tracker: Optional progress tracker for sync status updates

        Returns:
            Sync metrics dict with keys:
            - pages_added: int - Number of new pages created
            - pages_updated: int - Number of existing pages updated
            - pages_deleted: int - Number of pages marked as deleted
            - duration_seconds: float - Total sync duration
            - api_calls_made: int - Total Confluence API calls executed

        Raises:
            ConfluenceAuthError: If authentication fails
            ConfluenceNotFoundError: If space not found
            Exception: For other sync errors (database, network, etc.)

        Example:
            >>> metrics = await sync_service.sync_space(
            ...     source_id="src_abc123",
            ...     space_key="DEVDOCS"
            ... )
            >>> print(f"Added: {metrics['pages_added']}, Updated: {metrics['pages_updated']}")
            Added: 5, Updated: 3
        """
        # Implementation will be added in subsequent tasks
        start_time = time.time()

        # Initialize metrics
        metrics: SyncMetrics = {
            "pages_added": 0,
            "pages_updated": 0,
            "pages_deleted": 0,
            "duration_seconds": 0.0,
            "api_calls_made": 0,
            "last_sync_timestamp": datetime.now(UTC).isoformat(),
            "status": "in_progress",
            # Atomic update metrics
            "chunks_marked_pending": 0,
            "chunks_deleted": 0,
            "chunks_rolled_back": 0,
            "atomic_update_failures": 0,
            # Deletion detection metrics
            "deletion_strategy": DeletionStrategy.WEEKLY_RECONCILIATION.value,
            "deletion_check_performed": False,
            "last_deletion_check": None,
        }

        try:
            # Task 2: Retrieve last_sync_timestamp from archon_sources.metadata
            self.logger.info(f"Starting sync for space {space_key}, source {source_id}")

            # Query archon_sources for last_sync_timestamp
            source_response = (
                self.supabase_client.from_("archon_sources")
                .select("metadata")
                .eq("source_id", source_id)
                .execute()
            )

            last_sync_timestamp = "1970-01-01T00:00:00Z"  # Default for first sync
            if source_response.data and len(source_response.data) > 0:
                metadata = source_response.data[0].get("metadata", {})
                if isinstance(metadata, dict) and "last_sync_timestamp" in metadata:
                    last_sync_timestamp = metadata["last_sync_timestamp"]
                    self.logger.info(f"Incremental sync from {last_sync_timestamp}")
                else:
                    self.logger.info("First sync - fetching all pages since epoch")

            # Task 2: Construct CQL query for changed pages
            cql_query = f'space = {space_key} AND lastModified >= "{last_sync_timestamp}"'
            self.logger.debug(f"CQL query: {cql_query}")

            # Task 2: Execute CQL search with required expansions
            changed_pages = await self.confluence_client.cql_search(
                cql=cql_query,
                expand="body.storage,version,ancestors",
                limit=10000,  # High limit for large spaces
            )
            metrics["api_calls_made"] += 1  # Track CQL search API call
            self.logger.info(f"CQL search returned {len(changed_pages)} changed pages")

            # Task 7: Initialize progress tracking
            if progress_tracker:
                await progress_tracker.update(
                    status="confluence_sync",
                    progress=5,
                    log=f"Found {len(changed_pages)} changed pages to process"
                )

            # Task 3: Process each changed page
            for page_idx, page in enumerate(changed_pages):
                page_id = str(page.get("id", ""))
                page_title = page.get("title", "Untitled")
                page_version = page.get("version", {}).get("number", 1)
                page_last_modified = page.get("history", {}).get("lastUpdated", {}).get("when", datetime.now(UTC).isoformat())

                self.logger.debug(f"Processing page {page_id}: {page_title} (v{page_version})")

                # Task 5: Check if page exists and compare versions
                existing_page_response = (
                    self.supabase_client.from_("confluence_pages")
                    .select("version")
                    .eq("page_id", page_id)
                    .execute()
                )

                is_new_page = not existing_page_response.data or len(existing_page_response.data) == 0
                if is_new_page:
                    self.logger.info(f"New page detected: {page_id}")
                    metrics["pages_added"] += 1
                else:
                    stored_version = existing_page_response.data[0].get("version", 0)
                    if page_version <= stored_version:
                        self.logger.debug(f"Page {page_id} unchanged (v{stored_version}), skipping")
                        continue  # Skip unchanged pages
                    self.logger.info(f"Page {page_id} updated: v{stored_version} → v{page_version}")
                    metrics["pages_updated"] += 1

                # Task 7: Update progress
                progress_percent = 10 + int((page_idx / len(changed_pages)) * 80)
                if progress_tracker:
                    await progress_tracker.update(
                        status="confluence_sync",
                        progress=progress_percent,
                        log=f"Processing page {page_idx + 1}/{len(changed_pages)}: {page_title}"
                    )

                # Task 3: Extract HTML content from body.storage
                html_content = page.get("body", {}).get("storage", {}).get("value", "")
                if not html_content:
                    self.logger.warning(f"Page {page_id} has no HTML content, skipping")
                    continue

                # Task 3: Process HTML → Markdown with ConfluenceProcessor
                markdown_content, page_metadata = await self.confluence_processor.html_to_markdown(
                    html=html_content,
                    page_id=page_id,
                    space_id=space_key
                )

                # Task 3: Compute materialized path from ancestors
                ancestors = page.get("ancestors", [])
                materialized_path = "/" + "/".join(str(a.get("id", "")) for a in ancestors) + f"/{page_id}"

                # Task 3: Store/update metadata in confluence_pages table
                confluence_page_data = {
                    "page_id": page_id,
                    "source_id": source_id,
                    "space_key": space_key,
                    "title": page_title,
                    "version": page_version,
                    "last_modified": page_last_modified,
                    "is_deleted": False,
                    "path": materialized_path,
                    "metadata": page_metadata,
                    "updated_at": datetime.now(UTC).isoformat(),
                }

                self.supabase_client.from_("confluence_pages").upsert(
                    confluence_page_data,
                    on_conflict="page_id"
                ).execute()

                self.logger.debug(f"Stored metadata for page {page_id}")

                # Atomic chunk update with zero-downtime strategy
                page_url = f"{self.confluence_client._client.url}/pages/viewpage.action?pageId={page_id}"

                try:
                    update_metrics = await self._update_page_chunks_atomic(
                        page_id=page_id,
                        markdown=markdown_content,
                        page_url=page_url,
                        source_id=source_id,
                        page_title=page_title,
                        space_key=space_key,
                        progress_tracker=progress_tracker,
                    )

                    # Track atomic update metrics
                    metrics["chunks_marked_pending"] += update_metrics["chunks_marked"]
                    metrics["chunks_deleted"] += update_metrics["chunks_deleted"]

                    self.logger.debug(
                        f"Atomic update completed for page {page_id}: "
                        f"{update_metrics['chunks_created']} chunks created"
                    )

                except Exception as atomic_error:
                    # Track failure and rollback metrics
                    metrics["atomic_update_failures"] += 1
                    if "chunks_rolled_back" in locals() and update_metrics:
                        metrics["chunks_rolled_back"] += update_metrics.get("chunks_rolled_back", 0)

                    self.logger.error(
                        f"Atomic update failed for page {page_id}: {atomic_error}",
                        exc_info=True
                    )
                    # Continue processing other pages despite this failure
                    continue

            # Story 3.3: Run deletion detection based on configured strategy
            strategy = await self._get_deletion_strategy(source_id)
            metrics["deletion_strategy"] = strategy.value

            if strategy == DeletionStrategy.EVERY_SYNC:
                # Always run deletion detection
                deleted_page_ids = await self._detect_deleted_pages_every_sync(source_id, space_key)
                metrics["api_calls_made"] += 1  # Track get_space_pages_ids() API call
                if deleted_page_ids:
                    deleted_count = await self._mark_pages_deleted(deleted_page_ids, source_id, space_key)
                    metrics["pages_deleted"] = deleted_count
                metrics["deletion_check_performed"] = True
                await self._update_last_deletion_check(source_id)

            elif strategy == DeletionStrategy.WEEKLY_RECONCILIATION:
                # Only run deletion detection if 7+ days since last check
                if await self._check_weekly_reconciliation(source_id, space_key):
                    deleted_page_ids = await self._detect_deleted_pages_every_sync(source_id, space_key)
                    metrics["api_calls_made"] += 1  # Track get_space_pages_ids() API call
                    if deleted_page_ids:
                        deleted_count = await self._mark_pages_deleted(deleted_page_ids, source_id, space_key)
                        metrics["pages_deleted"] = deleted_count
                    metrics["deletion_check_performed"] = True
                    await self._update_last_deletion_check(source_id)
                else:
                    self.logger.debug("Skipping deletion detection (weekly strategy, checked recently)")
                    metrics["deletion_check_performed"] = False

            elif strategy == DeletionStrategy.ON_DEMAND:
                # Never auto-check, only via manual API call
                self.logger.debug("Skipping deletion detection (on_demand strategy)")
                metrics["deletion_check_performed"] = False

            # Fetch last_deletion_check for metrics
            source_meta_response = (
                self.supabase_client.from_("archon_sources")
                .select("metadata")
                .eq("source_id", source_id)
                .execute()
            )
            if source_meta_response.data and len(source_meta_response.data) > 0:
                src_metadata = source_meta_response.data[0].get("metadata", {})
                metrics["last_deletion_check"] = src_metadata.get("last_deletion_check")

            # Task 6 & Task 2: Store sync metrics and last_sync_timestamp
            new_timestamp = datetime.now(UTC).isoformat()
            metrics["last_sync_timestamp"] = new_timestamp
            metrics["duration_seconds"] = time.time() - start_time
            metrics["status"] = "completed"

            # Task 6: Store metrics in archon_sources.metadata
            self.supabase_client.from_("archon_sources").update({
                "metadata": {
                    "last_sync_timestamp": new_timestamp,
                    "sync_metrics": metrics
                }
            }).eq("source_id", source_id).execute()

            self.logger.info(
                f"Sync completed for space {space_key}: "
                f"{metrics['pages_added']} added, "
                f"{metrics['pages_updated']} updated, "
                f"{metrics['pages_deleted']} deleted, "
                f"{metrics['duration_seconds']:.1f}s"
            )

            # Task 7: Complete progress tracking
            if progress_tracker:
                await progress_tracker.complete({
                    "status": "completed",
                    "space_key": space_key,
                    "pages_added": metrics["pages_added"],
                    "pages_updated": metrics["pages_updated"],
                    "pages_deleted": metrics["pages_deleted"],
                    "duration_seconds": metrics["duration_seconds"],
                })

            return metrics

        except Exception as e:
            metrics["duration_seconds"] = time.time() - start_time
            metrics["status"] = "failed"

            # Task 7: Report error to progress tracker
            if progress_tracker:
                await progress_tracker.error(
                    error_message=str(e),
                    error_details={"space_key": space_key, "source_id": source_id}
                )

            self.logger.error(
                f"Sync failed for space {space_key}: {e}",
                exc_info=True,
            )
            raise

    async def _mark_chunks_pending_deletion(self, page_id: str, source_id: str) -> int:
        """
        Mark old chunks for deletion by setting _pending_deletion flag.

        This is Phase 1 of the atomic update - chunks remain searchable.

        Args:
            page_id: Confluence page ID
            source_id: Source ID from archon_sources

        Returns:
            Number of chunks marked for deletion
        """
        try:
            # Query existing chunks to get their metadata
            existing_chunks_response = (
                self.supabase_client.from_("archon_crawled_pages")
                .select("id, metadata")
                .eq("source_id", source_id)
                .filter("metadata->>page_id", "eq", page_id)
                .execute()
            )

            if not existing_chunks_response.data:
                self.logger.debug(f"No existing chunks found for page {page_id}")
                return 0

            # Update each chunk's metadata to add _pending_deletion flag
            marked_count = 0
            for chunk in existing_chunks_response.data:
                chunk_id = chunk["id"]
                existing_metadata = chunk.get("metadata", {})

                # Add _pending_deletion flag while preserving existing metadata
                updated_metadata = {**existing_metadata, "_pending_deletion": "true"}

                self.supabase_client.from_("archon_crawled_pages").update({
                    "metadata": updated_metadata
                }).eq("id", chunk_id).execute()

                marked_count += 1

            self.logger.info(f"Marked {marked_count} chunks pending deletion for page {page_id}")
            return marked_count

        except Exception as e:
            self.logger.error(f"Failed to mark chunks pending deletion for page {page_id}: {e}", exc_info=True)
            raise

    async def _delete_pending_chunks(self, page_id: str, source_id: str) -> int:
        """
        Delete chunks marked with _pending_deletion flag.

        This is Phase 3 of the atomic update - only called after new chunks committed.

        Args:
            page_id: Confluence page ID
            source_id: Source ID from archon_sources

        Returns:
            Number of chunks deleted
        """
        try:
            result = (
                self.supabase_client.from_("archon_crawled_pages")
                .delete()
                .eq("source_id", source_id)
                .filter("metadata->>page_id", "eq", page_id)
                .filter("metadata->>_pending_deletion", "eq", "true")
                .execute()
            )

            deleted_count = len(result.data) if result.data else 0
            self.logger.info(f"Deleted {deleted_count} pending chunks for page {page_id}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to delete pending chunks for page {page_id}: {e}", exc_info=True)
            raise

    async def _rollback_pending_deletion(self, page_id: str, source_id: str) -> int:
        """
        Rollback pending deletion by removing _pending_deletion flag.

        Restores old chunks to searchable state on failure.

        Args:
            page_id: Confluence page ID
            source_id: Source ID from archon_sources

        Returns:
            Number of chunks restored
        """
        try:
            # Query chunks with pending deletion flag
            pending_chunks_response = (
                self.supabase_client.from_("archon_crawled_pages")
                .select("id, metadata")
                .eq("source_id", source_id)
                .filter("metadata->>page_id", "eq", page_id)
                .filter("metadata->>_pending_deletion", "eq", "true")
                .execute()
            )

            if not pending_chunks_response.data:
                self.logger.debug(f"No pending chunks to rollback for page {page_id}")
                return 0

            # Remove _pending_deletion flag from each chunk
            restored_count = 0
            for chunk in pending_chunks_response.data:
                chunk_id = chunk["id"]
                existing_metadata = chunk.get("metadata", {})

                # Remove _pending_deletion flag
                updated_metadata = {k: v for k, v in existing_metadata.items() if k != "_pending_deletion"}

                self.supabase_client.from_("archon_crawled_pages").update({
                    "metadata": updated_metadata
                }).eq("id", chunk_id).execute()

                restored_count += 1

            self.logger.info(f"Rolled back {restored_count} chunks for page {page_id}")
            return restored_count

        except Exception as e:
            self.logger.error(f"Failed to rollback pending deletion for page {page_id}: {e}", exc_info=True)
            raise

    async def _update_page_chunks_atomic(
        self,
        page_id: str,
        markdown: str,
        page_url: str,
        source_id: str,
        page_title: str,
        space_key: str,
        progress_tracker: ProgressTracker | None = None,
    ) -> dict[str, int]:
        """
        Update page chunks with atomic transaction.

        Ensures zero-downtime: Old chunks remain searchable until new ones committed.
        Rollback on failure preserves old chunks.

        Args:
            page_id: Confluence page ID
            markdown: Markdown content to chunk and store
            page_url: Page URL for chunk metadata
            source_id: Source ID from archon_sources
            page_title: Page title for metadata
            space_key: Confluence space key
            progress_tracker: Optional progress tracker

        Returns:
            Metrics dict with:
            - chunks_marked: Number of chunks marked for deletion
            - chunks_created: Number of new chunks created
            - chunks_deleted: Number of old chunks deleted
            - chunks_rolled_back: Number of chunks restored on failure (0 on success)
            - failed: 1 if update failed, 0 if successful

        Raises:
            Exception: If any step fails (rollback is attempted automatically)
        """
        update_metrics = {
            "chunks_marked": 0,
            "chunks_created": 0,
            "chunks_deleted": 0,
            "chunks_rolled_back": 0,
            "failed": 0,
        }

        try:
            # STEP 1: Mark old chunks pending deletion (still searchable)
            update_metrics["chunks_marked"] = await self._mark_chunks_pending_deletion(page_id, source_id)
            self.logger.debug(f"Atomic update step 1: Marked {update_metrics['chunks_marked']} chunks pending deletion")

            # STEP 2: Insert new chunks via document_storage_service
            chunks = await self.document_storage.smart_chunk_text_async(
                markdown,
                chunk_size=5000
            )

            all_urls = []
            all_chunk_numbers = []
            all_contents = []
            all_metadatas = []
            url_to_full_document = {page_url: markdown}

            for chunk_idx, chunk in enumerate(chunks):
                all_urls.append(page_url)
                all_chunk_numbers.append(chunk_idx)
                all_contents.append(chunk)

                chunk_metadata = {
                    "page_id": page_id,
                    "section_title": page_title,
                    "space_key": space_key,
                    "source_id": source_id,
                    "url": page_url,
                    "chunk_index": chunk_idx,
                    "word_count": len(chunk.split()),
                    "char_count": len(chunk),
                }
                all_metadatas.append(chunk_metadata)

            if all_contents:
                await add_documents_to_supabase(
                    client=self.supabase_client,
                    urls=all_urls,
                    chunk_numbers=all_chunk_numbers,
                    contents=all_contents,
                    metadatas=all_metadatas,
                    url_to_full_document=url_to_full_document,
                    batch_size=25,
                    progress_callback=None,
                    enable_parallel_batches=True,
                    provider=None,
                    cancellation_check=None,
                    url_to_page_id={page_url: page_id},
                )
                update_metrics["chunks_created"] = len(chunks)
                self.logger.debug(f"Atomic update step 2: Created {update_metrics['chunks_created']} new chunks")

            # STEP 3: Delete old chunks (only after new chunks committed)
            update_metrics["chunks_deleted"] = await self._delete_pending_chunks(page_id, source_id)
            self.logger.debug(f"Atomic update step 3: Deleted {update_metrics['chunks_deleted']} old chunks")

            self.logger.info(
                f"Atomic chunk update completed for page {page_id}: "
                f"{update_metrics['chunks_marked']} marked, {update_metrics['chunks_created']} created, "
                f"{update_metrics['chunks_deleted']} deleted"
            )

            return update_metrics

        except Exception:
            # ROLLBACK: Remove pending deletion flag, restore old chunks
            update_metrics["failed"] = 1
            self.logger.error(
                f"Atomic chunk update failed for page {page_id}, attempting rollback",
                exc_info=True
            )

            try:
                update_metrics["chunks_rolled_back"] = await self._rollback_pending_deletion(page_id, source_id)
                self.logger.info(f"Rollback successful: restored {update_metrics['chunks_rolled_back']} chunks for page {page_id}")
            except Exception as rollback_error:
                self.logger.error(
                    f"CRITICAL: Rollback failed for page {page_id}: {rollback_error}",
                    exc_info=True
                )

            raise
