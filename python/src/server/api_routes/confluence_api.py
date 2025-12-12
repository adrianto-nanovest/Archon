"""Confluence API endpoints for source management and sync.

This module provides REST API endpoints for:
- Creating and managing Confluence sources
- Triggering manual syncs
- Monitoring sync progress
- Listing pages in synced spaces

All endpoints follow the /api/confluence/* pattern.
"""

import re
import uuid
from datetime import UTC, datetime
from email.utils import formatdate
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Response
from fastapi import status as http_status
from pydantic import BaseModel, Field

from ..config.logfire_config import get_logger
from ..services.confluence.confluence_client import ConfluenceClient
from ..services.confluence.confluence_processor import ConfluenceProcessor
from ..services.confluence.confluence_sync_service import ConfluenceSyncService
from ..services.credential_service import credential_service
from ..utils import get_supabase_client
from ..utils.etag_utils import check_etag, generate_etag
from ..utils.progress import ProgressTracker

logger = get_logger(__name__)

router = APIRouter(prefix="/api/confluence", tags=["confluence"])


# ============================================================================
# Pydantic Models
# ============================================================================


class CreateConfluenceSourceRequest(BaseModel):
    """Request body for creating a Confluence source."""

    base_url: str = Field(
        ...,
        description="Confluence Cloud base URL (e.g., https://company.atlassian.net/wiki)",
    )
    api_token: str = Field(
        ...,
        description="Confluence API token (will be encrypted)",
    )
    email: str = Field(
        ...,
        description="Atlassian account email for authentication",
    )
    space_key: str = Field(
        ...,
        description="Confluence space key (e.g., DEVDOCS)",
    )
    deletion_strategy: str = Field(
        default="weekly_reconciliation",
        description="Deletion detection strategy: weekly_reconciliation, every_sync, or on_demand",
    )


class ConfluenceSourceResponse(BaseModel):
    """Response for Confluence source details."""

    source_id: str
    source_type: str = "confluence"
    space_key: str
    base_url: str
    status: str | None
    last_sync: str | None
    total_pages: int
    created_at: str
    updated_at: str


class SyncTriggerResponse(BaseModel):
    """Response when triggering a sync operation."""

    operation_id: str
    message: str
    source_id: str


class ConfluencePageSummary(BaseModel):
    """Summary of a Confluence page for listing."""

    page_id: str
    title: str
    space_key: str
    version: int
    last_modified: str
    is_deleted: bool
    path: str | None


class ConfluenceSourceListResponse(BaseModel):
    """Response for listing Confluence sources."""

    sources: list[ConfluenceSourceResponse]
    count: int


class ConfluenceStatusResponse(BaseModel):
    """Response for sync status."""

    status: str
    last_sync: str | None = None
    sync_metrics: dict[str, Any] = {}
    total_pages: int = 0
    active_operation: dict[str, Any] | None = None


class ConfluencePagesListResponse(BaseModel):
    """Response for paginated pages listing."""

    pages: list[ConfluencePageSummary]
    page: int
    page_size: int
    total: int
    has_more: bool


class DeleteSourceResponse(BaseModel):
    """Response for source deletion."""

    deleted: bool
    source_id: str


# ============================================================================
# Helper Functions
# ============================================================================


def _validate_base_url(base_url: str) -> str:
    """Validate Confluence base URL format.

    Args:
        base_url: URL to validate

    Returns:
        Cleaned URL (no trailing slash)

    Raises:
        HTTPException: If URL is invalid
    """
    # Must be HTTPS
    if not base_url.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid URL", "message": "Confluence URL must use HTTPS"},
        )

    # Remove trailing slash
    return base_url.rstrip("/")


def _validate_space_key(space_key: str) -> str:
    """Validate Confluence space key format.

    Args:
        space_key: Space key to validate

    Returns:
        Validated space key

    Raises:
        HTTPException: If space key is invalid
    """
    # Must be alphanumeric (uppercase preferred, but lowercase allowed)
    if not re.match(r"^[A-Za-z0-9]+$", space_key):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid space key",
                "message": "Space key must be alphanumeric (e.g., DEVDOCS)",
            },
        )
    return space_key


async def _get_source_by_id(source_id: str) -> dict[str, Any]:
    """Get Confluence source by ID.

    Args:
        source_id: Source ID to fetch

    Returns:
        Source row from database

    Raises:
        HTTPException: If source not found or not a Confluence source
    """
    supabase_client = get_supabase_client()
    result = (
        supabase_client.from_("archon_sources")
        .select("*")
        .eq("source_id", source_id)
        .execute()
    )

    if not result.data or len(result.data) == 0:
        raise HTTPException(
            status_code=404,
            detail={"error": "Source not found", "source_id": source_id},
        )

    source: dict[str, Any] = result.data[0]

    if source.get("source_type") != "confluence":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid source type",
                "message": f"Source {source_id} is not a Confluence source",
            },
        )

    return source


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/sources", response_model=ConfluenceSourceResponse)
async def create_confluence_source(request: CreateConfluenceSourceRequest):
    """Create a new Confluence source.

    Validates credentials by fetching space info, encrypts API token,
    and stores source configuration.

    Args:
        request: Source creation request with base_url, api_token, email, space_key

    Returns:
        Created source details

    Raises:
        HTTPException: If validation fails or credentials are invalid
    """
    # Validate inputs
    base_url = _validate_base_url(request.base_url)
    space_key = _validate_space_key(request.space_key)

    # Validate credentials by connecting to Confluence
    confluence_client = ConfluenceClient(
        base_url=base_url,
        email=request.email,
        api_token=request.api_token,
    )

    try:
        # Validate by executing a simple CQL query to check credentials and space access
        # Use a simple space query to verify access
        await confluence_client.cql_search(
            cql=f"space = {space_key}",
            expand=None,
            limit=1,
        )
    except Exception as e:
        logger.warning(f"Confluence validation failed | error={e}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid credentials or space not found",
                "message": str(e),
            },
        ) from e

    # Encrypt API token
    encrypted_token = credential_service._encrypt_value(request.api_token)

    # Generate unique source_id
    source_id = f"confluence_{uuid.uuid4().hex[:12]}"

    # Insert into archon_sources
    supabase_client = get_supabase_client()
    now = datetime.now(UTC).isoformat()

    source_data = {
        "source_id": source_id,
        "source_type": "confluence",
        "status": "ready",
        "metadata": {
            "confluence_base_url": base_url,
            "confluence_space_key": space_key,
            "confluence_email": request.email,
            "encrypted_api_token": encrypted_token,
            "deletion_strategy": request.deletion_strategy,
            "total_pages": 0,
            "last_sync_timestamp": None,
        },
        "created_at": now,
        "updated_at": now,
    }

    supabase_client.from_("archon_sources").insert(source_data).execute()

    logger.info(f"Confluence source created | source_id={source_id} | space_key={space_key}")

    return ConfluenceSourceResponse(
        source_id=source_id,
        source_type="confluence",
        space_key=space_key,
        base_url=base_url,
        status="ready",
        last_sync=None,
        total_pages=0,
        created_at=now,
        updated_at=now,
    )


@router.get("/sources", response_model=ConfluenceSourceListResponse)
async def list_confluence_sources(
    response: Response,
    if_none_match: str | None = Header(None),
):
    """List all Confluence sources with sync status.

    Supports ETag caching for efficient polling.

    Returns:
        List of Confluence sources with metadata
    """
    supabase_client = get_supabase_client()

    result = (
        supabase_client.from_("archon_sources")
        .select("*")
        .eq("source_type", "confluence")
        .execute()
    )

    sources = []
    for row in result.data or []:
        metadata = row.get("metadata", {}) or {}
        sources.append(
            ConfluenceSourceResponse(
                source_id=row["source_id"],
                source_type="confluence",
                space_key=metadata.get("confluence_space_key", ""),
                base_url=metadata.get("confluence_base_url", ""),
                status=row.get("status"),
                last_sync=metadata.get("last_sync_timestamp"),
                total_pages=metadata.get("total_pages", 0),
                created_at=row.get("created_at", ""),
                updated_at=row.get("updated_at", ""),
            )
        )

    # Generate ETag
    etag_data = [s.model_dump() for s in sources]
    current_etag = generate_etag(etag_data)

    # Check ETag
    if check_etag(if_none_match, current_etag):
        return Response(
            status_code=http_status.HTTP_304_NOT_MODIFIED,
            headers={"ETag": current_etag, "Cache-Control": "no-cache, must-revalidate"},
        )

    # Set caching headers
    response.headers["ETag"] = current_etag
    response.headers["Last-Modified"] = formatdate(timeval=None, localtime=False, usegmt=True)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"

    return ConfluenceSourceListResponse(sources=sources, count=len(sources))


@router.post("/{source_id}/sync", response_model=SyncTriggerResponse)
async def trigger_confluence_sync(
    source_id: str,
    background_tasks: BackgroundTasks,
):
    """Trigger a manual sync for a Confluence source.

    Launches sync as a background task and returns immediately with operation_id.

    Args:
        source_id: Confluence source ID
        background_tasks: FastAPI background tasks

    Returns:
        Operation ID for tracking sync progress
    """
    # Validate source exists and is Confluence type
    source = await _get_source_by_id(source_id)
    metadata = source.get("metadata", {}) or {}

    # Generate operation_id
    operation_id = f"sync_{uuid.uuid4().hex[:12]}"

    # Get source configuration
    base_url = metadata.get("confluence_base_url", "")
    space_key = metadata.get("confluence_space_key", "")
    email = metadata.get("confluence_email", "")
    encrypted_token = metadata.get("encrypted_api_token", "")

    if not encrypted_token:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing API token", "message": "Source has no encrypted API token"},
        )

    # Decrypt API token
    api_token = credential_service._decrypt_value(encrypted_token)

    # Create ProgressTracker
    progress_tracker = ProgressTracker(
        progress_id=operation_id,
        operation_type="confluence_sync",
    )
    await progress_tracker.start({
        "url": f"{base_url}/spaces/{space_key}",
        "source_id": source_id,
        "space_key": space_key,
    })

    # Initialize services
    supabase_client = get_supabase_client()
    confluence_client = ConfluenceClient(
        base_url=base_url,
        email=email,
        api_token=api_token,
    )
    confluence_processor = ConfluenceProcessor(confluence_client=confluence_client)
    sync_service = ConfluenceSyncService(
        confluence_client=confluence_client,
        confluence_processor=confluence_processor,
        supabase_client=supabase_client,
    )

    async def run_sync():
        """Background task to execute sync."""
        try:
            metrics = await sync_service.sync_space(
                source_id=source_id,
                space_key=space_key,
                progress_tracker=progress_tracker,
            )
            logger.info(
                f"Confluence sync completed | source_id={source_id} | "
                f"added={metrics['pages_added']} | updated={metrics['pages_updated']} | "
                f"deleted={metrics['pages_deleted']}"
            )
        except Exception as e:
            logger.error(f"Confluence sync failed | source_id={source_id} | error={e}", exc_info=True)
            await progress_tracker.error(
                error_message=str(e),
                error_details={"source_id": source_id, "space_key": space_key},
            )

    background_tasks.add_task(run_sync)

    logger.info(f"Confluence sync triggered | source_id={source_id} | operation_id={operation_id}")

    return SyncTriggerResponse(
        operation_id=operation_id,
        message=f"Sync started for space {space_key}",
        source_id=source_id,
    )


@router.get("/{source_id}/status", response_model=ConfluenceStatusResponse)
async def get_confluence_status(
    source_id: str,
    response: Response,
    if_none_match: str | None = Header(None),
):
    """Get sync status for a Confluence source.

    Returns active operation progress or last sync metadata.
    Supports ETag caching.

    Args:
        source_id: Confluence source ID

    Returns:
        Current sync status with metrics
    """
    # Validate source exists
    source = await _get_source_by_id(source_id)
    metadata = source.get("metadata", {}) or {}

    # Check for active sync operations
    active_ops = ProgressTracker.list_active()
    active_operation = None

    for op_id, op in active_ops.items():
        if op.get("source_id") == source_id and op.get("type") == "confluence_sync":
            active_operation = {
                "operation_id": op_id,
                "status": op.get("status"),
                "progress": op.get("progress", 0),
                "log": op.get("log", ""),
            }
            break

    response_data = {
        "status": "syncing" if active_operation else "idle",
        "last_sync": metadata.get("last_sync_timestamp"),
        "sync_metrics": metadata.get("sync_metrics", {}),
        "total_pages": metadata.get("total_pages", 0),
        "active_operation": active_operation,
    }

    # Generate ETag
    current_etag = generate_etag(response_data)

    # Check ETag
    if check_etag(if_none_match, current_etag):
        return Response(
            status_code=http_status.HTTP_304_NOT_MODIFIED,
            headers={"ETag": current_etag, "Cache-Control": "no-cache, must-revalidate"},
        )

    # Set caching headers
    response.headers["ETag"] = current_etag
    response.headers["Last-Modified"] = formatdate(timeval=None, localtime=False, usegmt=True)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"

    # Add polling hint
    if active_operation:
        response.headers["X-Poll-Interval"] = "1000"
    else:
        response.headers["X-Poll-Interval"] = "0"

    return ConfluenceStatusResponse(**response_data)


@router.delete("/{source_id}", response_model=DeleteSourceResponse)
async def delete_confluence_source(source_id: str):
    """Delete a Confluence source and all associated data.

    CASCADE delete handles:
    - confluence_pages (FK: source_id -> archon_sources.source_id)
    - archon_crawled_pages (FK: source_id -> archon_sources.source_id)

    Args:
        source_id: Confluence source ID

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If source not found or has active sync
    """
    # Validate source exists
    await _get_source_by_id(source_id)

    # Check for active sync operations
    active_ops = ProgressTracker.list_active()
    for op_id, op in active_ops.items():
        if op.get("source_id") == source_id and op.get("type") == "confluence_sync":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Cannot delete source with active sync operation",
                    "operation_id": op_id,
                },
            )

    # Delete from archon_sources (CASCADE handles related tables)
    supabase_client = get_supabase_client()
    supabase_client.from_("archon_sources").delete().eq("source_id", source_id).execute()

    logger.info(f"Confluence source deleted | source_id={source_id}")

    return DeleteSourceResponse(deleted=True, source_id=source_id)


@router.get("/{source_id}/pages", response_model=ConfluencePagesListResponse)
async def list_confluence_pages(
    source_id: str,
    response: Response,
    if_none_match: str | None = Header(None),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page"),
    include_deleted: bool = Query(default=False, description="Include deleted pages"),
):
    """List pages in a Confluence space with pagination.

    Supports ETag caching and optional filtering of deleted pages.

    Args:
        source_id: Confluence source ID
        page: Page number (1-based)
        page_size: Number of items per page
        include_deleted: Whether to include deleted pages

    Returns:
        Paginated list of pages
    """
    # Validate source exists
    await _get_source_by_id(source_id)

    supabase_client = get_supabase_client()

    # Get total count first
    count_query = (
        supabase_client.from_("confluence_pages")
        .select("page_id", count="exact")
        .eq("source_id", source_id)
    )
    if not include_deleted:
        count_query = count_query.eq("is_deleted", False)

    count_result = count_query.execute()
    total = count_result.count or 0

    # Calculate offset
    offset = (page - 1) * page_size

    # Query pages with pagination
    query = (
        supabase_client.from_("confluence_pages")
        .select("page_id, title, space_key, version, last_modified, is_deleted, path")
        .eq("source_id", source_id)
    )
    if not include_deleted:
        query = query.eq("is_deleted", False)

    result = query.order("title").range(offset, offset + page_size - 1).execute()

    pages = [
        ConfluencePageSummary(
            page_id=row["page_id"],
            title=row["title"],
            space_key=row["space_key"],
            version=row["version"],
            last_modified=row["last_modified"],
            is_deleted=row["is_deleted"],
            path=row.get("path"),
        )
        for row in (result.data or [])
    ]

    has_more = len(pages) == page_size and (offset + page_size) < total

    # Generate ETag
    etag_data = {"pages": [p.model_dump() for p in pages], "page": page, "total": total}
    current_etag = generate_etag(etag_data)

    # Check ETag
    if check_etag(if_none_match, current_etag):
        return Response(
            status_code=http_status.HTTP_304_NOT_MODIFIED,
            headers={"ETag": current_etag, "Cache-Control": "no-cache, must-revalidate"},
        )

    # Set caching headers
    response.headers["ETag"] = current_etag
    response.headers["Last-Modified"] = formatdate(timeval=None, localtime=False, usegmt=True)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"

    return ConfluencePagesListResponse(
        pages=pages,
        page=page,
        page_size=page_size,
        total=total,
        has_more=has_more,
    )
