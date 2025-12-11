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
from datetime import UTC, datetime
from typing import Any, TypedDict

from ...utils import get_supabase_client
from ...utils.progress.progress_tracker import ProgressTracker
from ..storage.document_storage_service import add_documents_to_supabase
from ..storage.storage_services import DocumentStorageService
from .confluence_client import ConfluenceClient
from .confluence_processor import ConfluenceProcessor

logger = logging.getLogger(__name__)


class SyncMetrics(TypedDict):
    """Type definition for sync metrics returned by sync_space."""
    pages_added: int
    pages_updated: int
    pages_deleted: int
    duration_seconds: float
    api_calls_made: int
    last_sync_timestamp: str
    status: str
    chunks_marked_pending: int
    chunks_deleted: int
    chunks_rolled_back: int
    atomic_update_failures: int


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
