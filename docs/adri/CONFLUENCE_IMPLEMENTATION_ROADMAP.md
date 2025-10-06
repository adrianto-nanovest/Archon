# Confluence Integration Implementation Roadmap

## Overview

This roadmap provides a detailed, actionable plan for implementing Confluence RAG integration into Archon, broken down by phase with specific tasks, file locations, and acceptance criteria.

## Prerequisites

### Dependencies to Install

```bash
# Add to python/pyproject.toml
[project.dependencies]
atlassian-python-api = "^3.41.0"
markdownify = "^0.11.6"

# Install
cd python
uv add atlassian-python-api markdownify
```

### API Credentials Required

- Confluence Cloud URL (e.g., `https://yourcompany.atlassian.net`)
- Confluence API Token (create at https://id.atlassian.com/manage-profile/security/api-tokens)
- User email associated with token

### Database Backup

```bash
# Backup before starting
docker compose exec postgres pg_dump -U postgres archon > backup_before_confluence_$(date +%Y%m%d).sql
```

---

## Phase 1: Foundation & Basic Crawler (Week 1-2)

### Goal
Implement basic Confluence API integration and initial crawling capability.

### Tasks

#### 1.1 Database Schema Extensions

**File**: Create `python/alembic/versions/XXX_add_confluence_support.py`

```python
"""Add Confluence support columns

Revision ID: XXX
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Extend archon_sources
    op.add_column('archon_sources',
        sa.Column('last_sync_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column('archon_sources',
        sa.Column('sync_status', sa.String(50), server_default='active', nullable=False)
    )
    op.add_column('archon_sources',
        sa.Column('sync_error', sa.Text, nullable=True)
    )

    # Extend archon_crawled_pages
    op.add_column('archon_crawled_pages',
        sa.Column('confluence_page_id', sa.String(255), nullable=True)
    )
    op.add_column('archon_crawled_pages',
        sa.Column('confluence_version', sa.Integer, nullable=True)
    )
    op.add_column('archon_crawled_pages',
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False)
    )
    op.add_column('archon_crawled_pages',
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True)
    )

    # Create index for efficient lookups
    op.create_index(
        'idx_confluence_page_id',
        'archon_crawled_pages',
        ['confluence_page_id'],
        postgresql_where=sa.text("confluence_page_id IS NOT NULL")
    )

def downgrade():
    op.drop_index('idx_confluence_page_id', table_name='archon_crawled_pages')
    op.drop_column('archon_crawled_pages', 'deleted_at')
    op.drop_column('archon_crawled_pages', 'is_deleted')
    op.drop_column('archon_crawled_pages', 'confluence_version')
    op.drop_column('archon_crawled_pages', 'confluence_page_id')
    op.drop_column('archon_sources', 'sync_error')
    op.drop_column('archon_sources', 'sync_status')
    op.drop_column('archon_sources', 'last_sync_at')
```

**Commands**:
```bash
cd python
uv run alembic upgrade head
```

#### 1.2 Confluence API Client Service

**File**: Create `python/src/server/services/confluence_client.py`

```python
"""
Confluence API Client Service

Handles all interactions with Confluence Cloud API.
"""

import asyncio
from typing import Any, Optional
from atlassian import Confluence

from ..config.logfire_config import get_logger, safe_logfire_info, safe_logfire_error
from .credential_service import credential_service

logger = get_logger(__name__)


class ConfluenceClient:
    """Async wrapper around Confluence API client"""

    def __init__(
        self,
        confluence_url: str,
        api_token: str,
        user_email: str,
        timeout: int = 30
    ):
        """
        Initialize Confluence client.

        Args:
            confluence_url: Base URL (e.g., https://company.atlassian.net)
            api_token: API token from Atlassian
            user_email: Email associated with token
            timeout: Request timeout in seconds
        """
        self.confluence_url = confluence_url
        self.client = Confluence(
            url=confluence_url,
            username=user_email,
            password=api_token,
            timeout=timeout,
            cloud=True
        )

    async def get_space(self, space_key: str) -> dict[str, Any]:
        """Get space metadata"""
        safe_logfire_info(f"Fetching space metadata | space={space_key}")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.get_space(space_key, expand='description,homepage')
        )

    async def get_all_pages_from_space(
        self,
        space_key: str,
        start: int = 0,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get all pages from a space with pagination.

        Args:
            space_key: Confluence space key
            start: Pagination start
            limit: Results per page (max 100)

        Returns:
            List of page objects
        """
        safe_logfire_info(
            f"Fetching pages | space={space_key} | start={start} | limit={limit}"
        )
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.get_all_pages_from_space(
                space_key,
                start=start,
                limit=limit,
                expand='body.storage,version,metadata.labels,ancestors'
            )
        )

    async def get_page_by_id(
        self,
        page_id: str,
        expand: str = 'body.storage,version,metadata.labels,ancestors'
    ) -> dict[str, Any]:
        """Get page by ID with expanded content"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.get_page_by_id(page_id, expand=expand)
        )

    async def search_content_cql(
        self,
        cql: str,
        start: int = 0,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        Search using CQL (Confluence Query Language).

        Example CQL:
            "lastModified >= '2025-10-01' AND space = 'DEVDOCS'"

        Args:
            cql: CQL query string
            start: Pagination start
            limit: Results per page

        Returns:
            Search results with pagination
        """
        safe_logfire_info(f"CQL search | query={cql}")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.cql(cql, start=start, limit=limit, expand='version')
        )

    async def get_attachments(self, page_id: str) -> dict[str, Any]:
        """Get attachments for a page"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.get_attachments_from_content(page_id)
        )

    async def download_attachment(
        self,
        attachment_id: str
    ) -> bytes:
        """Download attachment content"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.download_attachment(attachment_id)
        )

    @classmethod
    async def from_source_id(cls, source_id: str) -> Optional["ConfluenceClient"]:
        """
        Create client from stored credentials.

        Args:
            source_id: Source ID to load credentials for

        Returns:
            Configured client or None if credentials missing
        """
        try:
            credentials = await credential_service.get_credentials_by_category(
                f"confluence_{source_id}"
            )

            confluence_url = credentials.get('CONFLUENCE_URL')
            api_token = credentials.get('CONFLUENCE_TOKEN')
            user_email = credentials.get('CONFLUENCE_EMAIL')

            if not all([confluence_url, api_token, user_email]):
                safe_logfire_error(
                    f"Missing Confluence credentials | source_id={source_id}"
                )
                return None

            return cls(confluence_url, api_token, user_email)

        except Exception as e:
            safe_logfire_error(
                f"Failed to create Confluence client | error={str(e)}",
                exc_info=True
            )
            return None
```

**Acceptance Criteria**:
- [ ] Can connect to Confluence Cloud
- [ ] Can retrieve space metadata
- [ ] Can paginate through pages
- [ ] Can search using CQL
- [ ] Handles API errors gracefully

#### 1.3 Content Processing Utilities

**File**: Create `python/src/server/services/confluence_content_processor.py`

```python
"""
Confluence Content Processor

Handles conversion of Confluence HTML to markdown and extraction of structured data.
"""

import re
from typing import Any
from markdownify import markdownify as md

from ..config.logfire_config import get_logger

logger = get_logger(__name__)


class ConfluenceContentProcessor:
    """Process Confluence page content for RAG indexing"""

    @staticmethod
    def html_to_markdown(html: str) -> str:
        """
        Convert Confluence HTML to markdown.

        Args:
            html: Confluence storage format HTML

        Returns:
            Cleaned markdown text
        """
        # Convert to markdown
        markdown = md(html, heading_style="ATX")

        # Clean up Confluence-specific artifacts
        markdown = ConfluenceContentProcessor._clean_markdown(markdown)

        return markdown

    @staticmethod
    def _clean_markdown(markdown: str) -> str:
        """Clean up markdown artifacts"""
        # Remove excessive newlines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)

        # Remove Confluence macro remnants
        markdown = re.sub(r'<ac:.*?>', '', markdown)

        # Trim whitespace
        markdown = markdown.strip()

        return markdown

    @staticmethod
    def extract_code_blocks(markdown: str) -> list[dict[str, Any]]:
        """
        Extract code blocks from markdown.

        Args:
            markdown: Markdown text

        Returns:
            List of code block dictionaries
        """
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, markdown, re.DOTALL)

        code_blocks = []
        for lang, code in matches:
            if code.strip():
                code_blocks.append({
                    'language': lang.lower() if lang else 'text',
                    'content': code.strip(),
                    'lines': len(code.strip().split('\n'))
                })

        return code_blocks

    @staticmethod
    def extract_metadata(page: dict[str, Any]) -> dict[str, Any]:
        """
        Extract metadata from Confluence page object.

        Args:
            page: Confluence page object

        Returns:
            Metadata dictionary
        """
        metadata = {
            'source_type': 'confluence',
            'confluence_page_id': page['id'],
            'confluence_version': page['version']['number'],
            'confluence_space': page['space']['key'] if 'space' in page else None,
            'confluence_title': page['title'],
            'confluence_type': page['type'],  # 'page' or 'blogpost'
        }

        # Extract labels if present
        if 'metadata' in page and 'labels' in page['metadata']:
            labels = page['metadata']['labels'].get('results', [])
            metadata['confluence_labels'] = [label['name'] for label in labels]

        # Extract parent page ID if present
        if 'ancestors' in page and page['ancestors']:
            parent = page['ancestors'][-1]
            metadata['confluence_parent_id'] = parent['id']

        # Extract author
        if 'history' in page and 'createdBy' in page['history']:
            metadata['confluence_author'] = page['history']['createdBy']['displayName']

        # Extract dates
        if 'version' in page:
            metadata['confluence_created_at'] = page['version'].get('when')

        return metadata

    @staticmethod
    def should_skip_page(page: dict[str, Any]) -> bool:
        """
        Determine if page should be skipped during crawl.

        Args:
            page: Confluence page object

        Returns:
            True if page should be skipped
        """
        # Skip archived pages
        if page.get('status') == 'archived':
            return True

        # Skip pages with minimal content
        if 'body' in page and 'storage' in page['body']:
            content = page['body']['storage'].get('value', '')
            if len(content.strip()) < 100:
                logger.debug(f"Skipping page {page['id']}: minimal content")
                return True

        return False
```

**Acceptance Criteria**:
- [ ] Converts Confluence HTML to clean markdown
- [ ] Extracts code blocks with language detection
- [ ] Extracts all relevant metadata
- [ ] Handles malformed HTML gracefully

#### 1.4 Confluence Crawl Strategy

**File**: Create `python/src/server/services/crawling/strategies/confluence.py`

```python
"""
Confluence Crawl Strategy

Implements crawling for Confluence spaces using the Confluence API.
"""

import asyncio
from typing import Any, Callable, Awaitable

from ....config.logfire_config import get_logger, safe_logfire_info, safe_logfire_error
from ...confluence_client import ConfluenceClient
from ...confluence_content_processor import ConfluenceContentProcessor

logger = get_logger(__name__)


class ConfluenceCrawlStrategy:
    """Strategy for crawling Confluence spaces"""

    def __init__(self, client: ConfluenceClient):
        """
        Initialize strategy.

        Args:
            client: Configured Confluence client
        """
        self.client = client
        self.processor = ConfluenceContentProcessor()

    async def crawl_space(
        self,
        space_key: str,
        progress_callback: Callable[[str, int, str], Awaitable[None]] = None,
        max_pages: int = None
    ) -> list[dict[str, Any]]:
        """
        Crawl all pages from a Confluence space.

        Args:
            space_key: Confluence space key
            progress_callback: Optional callback for progress updates
            max_pages: Optional limit on pages to crawl (for testing)

        Returns:
            List of processed documents
        """
        safe_logfire_info(f"Starting Confluence space crawl | space={space_key}")

        try:
            # Get space metadata first
            space = await self.client.get_space(space_key)
            space_name = space.get('name', space_key)

            # Fetch all pages with pagination
            all_pages = []
            start = 0
            limit = 100
            page_count = 0

            while True:
                batch = await self.client.get_all_pages_from_space(
                    space_key, start=start, limit=limit
                )

                if not batch:
                    break

                all_pages.extend(batch)
                start += limit
                page_count += len(batch)

                if progress_callback:
                    await progress_callback(
                        'fetching',
                        min(100, int((page_count / (max_pages or 1000)) * 30)),
                        f"Fetched {page_count} pages from {space_name}",
                        total_pages=page_count,
                        processed_pages=page_count
                    )

                # Stop if we hit the limit (useful for testing)
                if max_pages and page_count >= max_pages:
                    safe_logfire_info(f"Hit max_pages limit: {max_pages}")
                    break

                # Stop if we got fewer than requested (last page)
                if len(batch) < limit:
                    break

            safe_logfire_info(
                f"Fetched all pages | space={space_key} | total={len(all_pages)}"
            )

            # Process pages in parallel (batches of 10)
            documents = []
            batch_size = 10

            for i in range(0, len(all_pages), batch_size):
                batch = all_pages[i:i+batch_size]

                # Process batch
                batch_docs = await asyncio.gather(*[
                    self._process_page(page) for page in batch
                ], return_exceptions=True)

                # Filter out exceptions and None results
                for doc in batch_docs:
                    if isinstance(doc, Exception):
                        safe_logfire_error(f"Page processing failed: {doc}")
                    elif doc is not None:
                        documents.append(doc)

                # Update progress
                progress_pct = int((len(documents) / len(all_pages)) * 70) + 30
                if progress_callback:
                    await progress_callback(
                        'processing',
                        progress_pct,
                        f"Processed {len(documents)}/{len(all_pages)} pages",
                        total_pages=len(all_pages),
                        processed_pages=len(documents)
                    )

            safe_logfire_info(
                f"Confluence crawl complete | space={space_key} | "
                f"pages={len(all_pages)} | documents={len(documents)}"
            )

            return documents

        except Exception as e:
            safe_logfire_error(
                f"Confluence crawl failed | space={space_key} | error={str(e)}",
                exc_info=True
            )
            raise

    async def _process_page(self, page: dict[str, Any]) -> dict[str, Any] | None:
        """
        Process a single Confluence page.

        Args:
            page: Confluence page object

        Returns:
            Processed document or None if skipped
        """
        try:
            # Check if we should skip this page
            if self.processor.should_skip_page(page):
                return None

            # Extract HTML content
            if 'body' not in page or 'storage' not in page['body']:
                logger.warning(f"Page {page['id']} has no body content")
                return None

            html_content = page['body']['storage']['value']

            # Convert to markdown
            markdown = self.processor.html_to_markdown(html_content)

            # Extract code blocks
            code_blocks = self.processor.extract_code_blocks(markdown)

            # Extract metadata
            metadata = self.processor.extract_metadata(page)

            # Build document structure
            document = {
                'url': f"{self.client.confluence_url}/wiki/spaces/{page['space']['key']}/pages/{page['id']}",
                'title': page['title'],
                'content': markdown,
                'markdown': markdown,
                'metadata': metadata,
                'code_blocks': code_blocks,
                'word_count': len(markdown.split()),
                'source_type': 'confluence'
            }

            return document

        except Exception as e:
            safe_logfire_error(
                f"Failed to process page | page_id={page.get('id')} | error={str(e)}"
            )
            return None
```

**Acceptance Criteria**:
- [ ] Can crawl entire space with pagination
- [ ] Processes pages in parallel batches
- [ ] Handles errors gracefully (continues crawl)
- [ ] Reports progress accurately
- [ ] Skips archived/minimal pages

#### 1.5 Integration into Crawling Service

**File**: Modify `python/src/server/services/crawling/crawling_service.py`

Add to imports:
```python
from .strategies.confluence import ConfluenceCrawlStrategy
from ..confluence_client import ConfluenceClient
```

Add to `__init__`:
```python
self.confluence_strategy = None  # Initialized per-request with credentials
```

Add new method:
```python
async def crawl_confluence_space(
    self,
    space_key: str,
    source_id: str,
    request: dict[str, Any]
) -> dict[str, Any]:
    """
    Crawl a Confluence space.

    Args:
        space_key: Confluence space key
        source_id: Source ID for storage
        request: Original crawl request with credentials

    Returns:
        Crawl results
    """
    self._check_cancellation()

    try:
        # Create Confluence client from credentials
        client = await ConfluenceClient.from_source_id(source_id)
        if not client:
            raise ValueError(f"Failed to create Confluence client for {source_id}")

        # Initialize strategy
        strategy = ConfluenceCrawlStrategy(client)

        # Create progress callback
        progress_callback = await self._create_crawl_progress_callback('crawling')

        # Crawl the space
        documents = await strategy.crawl_space(
            space_key=space_key,
            progress_callback=progress_callback,
            max_pages=request.get('max_pages')  # Optional limit for testing
        )

        # Store documents
        if documents:
            await self.doc_storage_ops.store_crawled_documents(
                documents,
                source_id,
                request
            )

        return {
            'success': True,
            'pages_crawled': len(documents),
            'source_id': source_id
        }

    except asyncio.CancelledError:
        safe_logfire_info(f"Confluence crawl cancelled | space={space_key}")
        raise
    except Exception as e:
        safe_logfire_error(
            f"Confluence crawl failed | space={space_key} | error={str(e)}",
            exc_info=True
        )
        raise
```

**Acceptance Criteria**:
- [ ] Integrates with existing progress tracking
- [ ] Uses existing document storage operations
- [ ] Handles cancellation properly
- [ ] Reports errors correctly

---

## Phase 2: API Endpoints & UI Integration (Week 3)

### Goal
Expose Confluence crawling via API and integrate into Knowledge Base UI.

### Tasks

#### 2.1 Confluence API Routes

**File**: Create `python/src/server/api_routes/confluence_api.py`

```python
"""
Confluence API Routes

Endpoints for managing Confluence sources and crawling.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ..config.logfire_config import safe_logfire_info, safe_logfire_error
from ..services.confluence_client import ConfluenceClient
from ..services.crawling.crawling_service import CrawlingService, register_orchestration
from ..services.credential_service import credential_service
from ..utils import get_supabase_client
from ..utils.progress.progress_tracker import ProgressTracker

router = APIRouter(prefix="/api/confluence", tags=["confluence"])


class CreateConfluenceSourceRequest(BaseModel):
    """Request to create a new Confluence source"""
    confluence_url: str = Field(..., description="Confluence base URL")
    user_email: str = Field(..., description="User email for API")
    api_token: str = Field(..., description="Confluence API token")
    space_key: str = Field(..., description="Space key to crawl")
    knowledge_type: str = Field(default="technical", description="Knowledge type")
    tags: list[str] = Field(default_factory=list, description="Tags")
    max_pages: int | None = Field(default=None, description="Max pages (testing)")


class CreateConfluenceSourceResponse(BaseModel):
    """Response after creating Confluence source"""
    source_id: str
    progress_id: str
    status: str


@router.post("/sources", response_model=CreateConfluenceSourceResponse)
async def create_confluence_source(
    request: CreateConfluenceSourceRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new Confluence source and start crawling.

    This will:
    1. Validate credentials
    2. Store credentials securely
    3. Start background crawl
    4. Return progress ID for tracking
    """
    try:
        safe_logfire_info(
            f"Creating Confluence source | space={request.space_key}"
        )

        # Validate credentials by testing connection
        client = ConfluenceClient(
            request.confluence_url,
            request.api_token,
            request.user_email
        )
        space = await client.get_space(request.space_key)
        space_name = space.get('name', request.space_key)

        # Generate source ID
        source_id = f"{request.confluence_url.replace('https://', '').replace('http://', '')}_{request.space_key}"

        # Store credentials securely
        await credential_service.set_credential(
            key=f"confluence_{source_id}_CONFLUENCE_URL",
            value=request.confluence_url,
            category=f"confluence_{source_id}",
            is_encrypted=False
        )
        await credential_service.set_credential(
            key=f"confluence_{source_id}_CONFLUENCE_TOKEN",
            value=request.api_token,
            category=f"confluence_{source_id}",
            is_encrypted=True
        )
        await credential_service.set_credential(
            key=f"confluence_{source_id}_CONFLUENCE_EMAIL",
            value=request.user_email,
            category=f"confluence_{source_id}",
            is_encrypted=False
        )

        # Create progress tracker
        progress_id = f"confluence_{source_id}_{int(time.time())}"
        progress = ProgressTracker(progress_id, operation_type="crawl")

        # Start background crawl
        background_tasks.add_task(
            _background_confluence_crawl,
            space_key=request.space_key,
            source_id=source_id,
            progress_id=progress_id,
            knowledge_type=request.knowledge_type,
            tags=request.tags,
            max_pages=request.max_pages
        )

        return CreateConfluenceSourceResponse(
            source_id=source_id,
            progress_id=progress_id,
            status="started"
        )

    except Exception as e:
        safe_logfire_error(
            f"Failed to create Confluence source | error={str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


async def _background_confluence_crawl(
    space_key: str,
    source_id: str,
    progress_id: str,
    knowledge_type: str,
    tags: list[str],
    max_pages: int | None
):
    """Background task for Confluence crawling"""
    try:
        safe_logfire_info(
            f"Starting background Confluence crawl | space={space_key} | progress_id={progress_id}"
        )

        # Initialize crawling service
        supabase_client = get_supabase_client()
        service = CrawlingService(
            supabase_client=supabase_client,
            progress_id=progress_id
        )
        register_orchestration(progress_id, service)

        # Build request
        crawl_request = {
            'url': f"confluence://{source_id}",
            'space_key': space_key,
            'knowledge_type': knowledge_type,
            'tags': tags,
            'max_pages': max_pages,
            'source_type': 'confluence'
        }

        # Execute crawl
        result = await service.crawl_confluence_space(
            space_key=space_key,
            source_id=source_id,
            request=crawl_request
        )

        # Update progress to completed
        if service.progress_tracker:
            await service.progress_tracker.complete(
                result=result,
                log=f"Crawled {result['pages_crawled']} pages from {space_key}"
            )

        safe_logfire_info(
            f"Confluence crawl completed | space={space_key} | pages={result['pages_crawled']}"
        )

    except Exception as e:
        safe_logfire_error(
            f"Background Confluence crawl failed | error={str(e)}",
            exc_info=True
        )
        if service.progress_tracker:
            await service.progress_tracker.fail(error=str(e))


@router.get("/sources")
async def list_confluence_sources():
    """List all Confluence sources"""
    try:
        supabase_client = get_supabase_client()
        response = supabase_client.table("archon_sources") \
            .select("*") \
            .contains("metadata", {"source_type": "confluence"}) \
            .execute()

        sources = []
        for row in response.data:
            metadata = row.get("metadata", {})
            sources.append({
                "source_id": row["source_id"],
                "title": row.get("title", ""),
                "summary": row.get("summary", ""),
                "confluence_space": metadata.get("confluence_space"),
                "last_sync_at": row.get("last_sync_at"),
                "sync_status": row.get("sync_status", "active"),
                "total_pages": metadata.get("total_pages", 0),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at")
            })

        return {"sources": sources, "count": len(sources)}

    except Exception as e:
        safe_logfire_error(f"Failed to list Confluence sources | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sources/{source_id}")
async def delete_confluence_source(source_id: str):
    """Delete a Confluence source and all its data"""
    try:
        safe_logfire_info(f"Deleting Confluence source | source_id={source_id}")

        # Delete credentials
        await credential_service.delete_credentials_by_category(f"confluence_{source_id}")

        # Delete source and pages (existing deletion logic)
        from ..services.source_management_service import SourceManagementService
        service = SourceManagementService()
        success, result = service.delete_source(source_id)

        if not success:
            raise HTTPException(status_code=404, detail=result.get("error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        safe_logfire_error(f"Failed to delete Confluence source | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Register router** in `python/src/server/main.py`:
```python
from .api_routes.confluence_api import router as confluence_router
app.include_router(confluence_router)
```

**Acceptance Criteria**:
- [ ] POST /api/confluence/sources creates source and starts crawl
- [ ] GET /api/confluence/sources lists all Confluence sources
- [ ] DELETE /api/confluence/sources/{id} removes source and credentials
- [ ] Returns progress ID for tracking
- [ ] Validates credentials before starting

#### 2.2 Frontend Service Layer

**File**: Create `archon-ui-main/src/features/knowledge/services/confluenceService.ts`

```typescript
import { apiClient } from "@/features/shared/api/apiClient";

export interface CreateConfluenceSourceRequest {
  confluence_url: string;
  user_email: string;
  api_token: string;
  space_key: string;
  knowledge_type?: string;
  tags?: string[];
  max_pages?: number;
}

export interface ConfluenceSource {
  source_id: string;
  title: string;
  summary: string;
  confluence_space: string;
  last_sync_at: string | null;
  sync_status: string;
  total_pages: number;
  created_at: string;
  updated_at: string;
}

export const confluenceService = {
  async createSource(data: CreateConfluenceSourceRequest) {
    const response = await apiClient.post<{
      source_id: string;
      progress_id: string;
      status: string;
    }>("/api/confluence/sources", data);
    return response;
  },

  async listSources() {
    const response = await apiClient.get<{
      sources: ConfluenceSource[];
      count: number;
    }>("/api/confluence/sources");
    return response;
  },

  async deleteSource(sourceId: string) {
    await apiClient.delete(`/api/confluence/sources/${sourceId}`);
  },
};
```

#### 2.3 Frontend UI Component

**File**: Create `archon-ui-main/src/features/knowledge/components/AddConfluenceSourceModal.tsx`

```typescript
import { useState } from "react";
import { Button } from "@/features/ui/primitives/button";
import { Input } from "@/features/ui/primitives/input";
import { Label } from "@/features/ui/primitives/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/features/ui/primitives/dialog";
import { confluenceService } from "../services/confluenceService";
import { useToast } from "@/features/ui/hooks/useToast";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (progressId: string) => void;
}

export function AddConfluenceSourceModal({ open, onOpenChange, onSuccess }: Props) {
  const [formData, setFormData] = useState({
    confluence_url: "",
    user_email: "",
    api_token: "",
    space_key: "",
    knowledge_type: "technical",
  });
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const result = await confluenceService.createSource(formData);
      toast({
        title: "Confluence source created",
        description: `Started crawling ${formData.space_key}`,
      });
      onSuccess(result.progress_id);
      onOpenChange(false);
    } catch (error) {
      toast({
        title: "Failed to create source",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Add Confluence Space</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="confluence_url">Confluence URL</Label>
            <Input
              id="confluence_url"
              placeholder="https://yourcompany.atlassian.net"
              value={formData.confluence_url}
              onChange={(e) =>
                setFormData({ ...formData, confluence_url: e.target.value })
              }
              required
            />
          </div>

          <div>
            <Label htmlFor="space_key">Space Key</Label>
            <Input
              id="space_key"
              placeholder="DEVDOCS"
              value={formData.space_key}
              onChange={(e) =>
                setFormData({ ...formData, space_key: e.target.value })
              }
              required
            />
          </div>

          <div>
            <Label htmlFor="user_email">Email</Label>
            <Input
              id="user_email"
              type="email"
              placeholder="you@company.com"
              value={formData.user_email}
              onChange={(e) =>
                setFormData({ ...formData, user_email: e.target.value })
              }
              required
            />
          </div>

          <div>
            <Label htmlFor="api_token">API Token</Label>
            <Input
              id="api_token"
              type="password"
              placeholder="Your Confluence API token"
              value={formData.api_token}
              onChange={(e) =>
                setFormData({ ...formData, api_token: e.target.value })
              }
              required
            />
            <p className="text-sm text-muted-foreground mt-1">
              Create at{" "}
              <a
                href="https://id.atlassian.com/manage-profile/security/api-tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Atlassian API Tokens
              </a>
            </p>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Starting..." : "Start Crawl"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

**Acceptance Criteria**:
- [ ] Modal opens from Knowledge Base page
- [ ] Form validates all required fields
- [ ] Shows loading state during submission
- [ ] Displays success/error toasts
- [ ] Redirects to progress tracking on success

---

## Phase 3: Incremental Sync (Week 4)

### Goal
Implement change detection and incremental sync for Confluence sources.

### Tasks

#### 3.1 Confluence Sync Service

**File**: Create `python/src/server/services/confluence_sync_service.py`

```python
"""
Confluence Sync Service

Handles incremental synchronization of Confluence spaces.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from ..config.logfire_config import get_logger, safe_logfire_info, safe_logfire_error
from ..utils import get_supabase_client
from .confluence_client import ConfluenceClient
from .confluence_content_processor import ConfluenceContentProcessor
from .crawling.document_storage_operations import DocumentStorageOperations

logger = get_logger(__name__)


class ConfluenceSyncService:
    """Service for incremental Confluence synchronization"""

    def __init__(self, supabase_client=None):
        self.supabase_client = supabase_client or get_supabase_client()
        self.processor = ConfluenceContentProcessor()
        self.doc_storage_ops = DocumentStorageOperations(self.supabase_client)

    async def sync_source(self, source_id: str) -> dict[str, Any]:
        """
        Perform incremental sync for a Confluence source.

        Args:
            source_id: Source ID to sync

        Returns:
            Sync results dictionary
        """
        safe_logfire_info(f"Starting incremental sync | source_id={source_id}")

        try:
            # Get source metadata
            source = await self._get_source(source_id)
            if not source:
                raise ValueError(f"Source {source_id} not found")

            metadata = source.get("metadata", {})
            space_key = metadata.get("confluence_space")

            if not space_key:
                raise ValueError(f"Source {source_id} is not a Confluence source")

            # Create client
            client = await ConfluenceClient.from_source_id(source_id)
            if not client:
                raise ValueError(f"Failed to create client for {source_id}")

            # Detect changes
            changes = await self._detect_changes(source_id, space_key, client)

            # Process updates
            updated = await self._process_updates(
                source_id, changes["updated"], client
            )

            # Process deletions
            deleted = await self._process_deletions(source_id, changes["deleted"])

            # Update source metadata
            await self._update_source_sync_timestamp(source_id)

            result = {
                "success": True,
                "source_id": source_id,
                "pages_updated": len(updated),
                "pages_deleted": len(deleted),
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
            }

            safe_logfire_info(
                f"Sync completed | source_id={source_id} | "
                f"updated={len(updated)} | deleted={len(deleted)}"
            )

            return result

        except Exception as e:
            safe_logfire_error(
                f"Sync failed | source_id={source_id} | error={str(e)}",
                exc_info=True
            )
            await self._update_source_sync_error(source_id, str(e))
            raise

    async def _detect_changes(
        self, source_id: str, space_key: str, client: ConfluenceClient
    ) -> dict[str, Any]:
        """Detect changed and deleted pages"""

        # Get last sync timestamp
        last_sync = await self._get_last_sync_timestamp(source_id)

        # Query Confluence for changes using CQL
        if last_sync:
            cql = f"lastModified >= '{last_sync}' AND space = '{space_key}'"
            safe_logfire_info(f"Change detection CQL: {cql}")

            results = await client.search_content_cql(cql)
            updated_pages = results.get("results", [])
        else:
            # First sync - get all pages
            updated_pages = await client.get_all_pages_from_space(space_key)

        # Get stored page IDs
        stored_page_ids = await self._get_stored_page_ids(source_id)

        # Get current Confluence page IDs
        all_pages = await client.get_all_pages_from_space(space_key)
        confluence_page_ids = {p["id"] for p in all_pages}

        # Detect deletions
        deleted_ids = stored_page_ids - confluence_page_ids

        safe_logfire_info(
            f"Change detection | updated={len(updated_pages)} | deleted={len(deleted_ids)}"
        )

        return {"updated": updated_pages, "deleted": deleted_ids}

    async def _process_updates(
        self, source_id: str, pages: list[dict], client: ConfluenceClient
    ) -> list[str]:
        """Process page updates"""
        updated_ids = []

        for page in pages:
            try:
                # Check if version changed
                stored_version = await self._get_stored_version(page["id"])
                current_version = page["version"]["number"]

                if stored_version and stored_version >= current_version:
                    safe_logfire_info(
                        f"Skipping page {page['id']}: version unchanged"
                    )
                    continue

                # Fetch full page content if needed
                if "body" not in page or "storage" not in page["body"]:
                    page = await client.get_page_by_id(page["id"])

                # Process page
                document = await self._process_page_for_update(page, client)

                if document:
                    # Update in database
                    await self._update_page_in_db(source_id, document)
                    updated_ids.append(page["id"])

            except Exception as e:
                safe_logfire_error(f"Failed to update page {page['id']}: {e}")
                continue

        return updated_ids

    async def _process_deletions(
        self, source_id: str, page_ids: set[str]
    ) -> list[str]:
        """Mark pages as deleted (soft delete)"""
        if not page_ids:
            return []

        try:
            # Update pages to mark as deleted
            response = (
                self.supabase_client.table("archon_crawled_pages")
                .update({
                    "is_deleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat()
                })
                .eq("source_id", source_id)
                .in_("confluence_page_id", list(page_ids))
                .execute()
            )

            deleted_count = len(response.data) if response.data else 0
            safe_logfire_info(
                f"Marked {deleted_count} pages as deleted | source_id={source_id}"
            )

            return list(page_ids)

        except Exception as e:
            safe_logfire_error(f"Failed to process deletions: {e}")
            return []

    async def _get_source(self, source_id: str) -> dict[str, Any] | None:
        """Get source record"""
        response = (
            self.supabase_client.table("archon_sources")
            .select("*")
            .eq("source_id", source_id)
            .single()
            .execute()
        )
        return response.data if response.data else None

    async def _get_last_sync_timestamp(self, source_id: str) -> str | None:
        """Get last sync timestamp for source"""
        source = await self._get_source(source_id)
        if source and source.get("last_sync_at"):
            return source["last_sync_at"]
        return None

    async def _get_stored_page_ids(self, source_id: str) -> set[str]:
        """Get all stored page IDs for source"""
        response = (
            self.supabase_client.table("archon_crawled_pages")
            .select("confluence_page_id")
            .eq("source_id", source_id)
            .eq("is_deleted", False)
            .execute()
        )

        return {
            row["confluence_page_id"]
            for row in response.data
            if row.get("confluence_page_id")
        }

    async def _get_stored_version(self, page_id: str) -> int | None:
        """Get stored version number for a page"""
        response = (
            self.supabase_client.table("archon_crawled_pages")
            .select("confluence_version")
            .eq("confluence_page_id", page_id)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0].get("confluence_version")
        return None

    async def _process_page_for_update(
        self, page: dict[str, Any], client: ConfluenceClient
    ) -> dict[str, Any] | None:
        """Process page for database update"""
        # Similar to ConfluenceCrawlStrategy._process_page
        # but adapted for updates

        if self.processor.should_skip_page(page):
            return None

        html_content = page["body"]["storage"]["value"]
        markdown = self.processor.html_to_markdown(html_content)
        code_blocks = self.processor.extract_code_blocks(markdown)
        metadata = self.processor.extract_metadata(page)

        return {
            "url": f"{client.confluence_url}/wiki/spaces/{page['space']['key']}/pages/{page['id']}",
            "title": page["title"],
            "content": markdown,
            "metadata": metadata,
            "code_blocks": code_blocks,
            "word_count": len(markdown.split()),
        }

    async def _update_page_in_db(
        self, source_id: str, document: dict[str, Any]
    ):
        """Update page in database"""
        # Update existing crawled_pages record
        page_id = document["metadata"]["confluence_page_id"]

        response = (
            self.supabase_client.table("archon_crawled_pages")
            .update({
                "content": document["content"],
                "title": document["title"],
                "metadata": document["metadata"],
                "confluence_version": document["metadata"]["confluence_version"],
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("source_id", source_id)
            .eq("confluence_page_id", page_id)
            .execute()
        )

        # Re-extract and update code examples if needed
        if document.get("code_blocks"):
            await self._update_code_examples(source_id, page_id, document["code_blocks"])

    async def _update_code_examples(
        self, source_id: str, page_id: str, code_blocks: list[dict]
    ):
        """Update code examples for a page"""
        # Delete old code examples
        self.supabase_client.table("archon_code_examples") \
            .delete() \
            .eq("source_id", source_id) \
            .contains("metadata", {"confluence_page_id": page_id}) \
            .execute()

        # Insert new code examples
        # (Simplified - use existing code extraction service in production)
        pass

    async def _update_source_sync_timestamp(self, source_id: str):
        """Update last sync timestamp"""
        self.supabase_client.table("archon_sources") \
            .update({
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "sync_status": "active",
                "sync_error": None
            }) \
            .eq("source_id", source_id) \
            .execute()

    async def _update_source_sync_error(self, source_id: str, error: str):
        """Update sync error"""
        self.supabase_client.table("archon_sources") \
            .update({
                "sync_status": "error",
                "sync_error": error
            }) \
            .eq("source_id", source_id) \
            .execute()
```

**Acceptance Criteria**:
- [ ] Detects changed pages using CQL
- [ ] Detects deleted pages by comparing IDs
- [ ] Updates changed pages in database
- [ ] Soft deletes removed pages
- [ ] Updates source sync timestamp
- [ ] Handles errors gracefully

#### 3.2 Sync API Endpoint

Add to `python/src/server/api_routes/confluence_api.py`:

```python
@router.post("/sources/{source_id}/sync")
async def sync_confluence_source(
    source_id: str,
    background_tasks: BackgroundTasks
):
    """Trigger incremental sync for a Confluence source"""
    try:
        safe_logfire_info(f"Triggering sync | source_id={source_id}")

        # Create progress tracker
        progress_id = f"sync_{source_id}_{int(time.time())}"
        progress = ProgressTracker(progress_id, operation_type="sync")

        # Start background sync
        background_tasks.add_task(
            _background_sync,
            source_id=source_id,
            progress_id=progress_id
        )

        return {
            "progress_id": progress_id,
            "status": "started"
        }

    except Exception as e:
        safe_logfire_error(f"Failed to trigger sync | error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _background_sync(source_id: str, progress_id: str):
    """Background task for sync"""
    try:
        from ..services.confluence_sync_service import ConfluenceSyncService

        service = ConfluenceSyncService()
        result = await service.sync_source(source_id)

        safe_logfire_info(f"Sync completed | result={result}")

    except Exception as e:
        safe_logfire_error(f"Background sync failed | error={str(e)}")
```

#### 3.3 Scheduled Sync (Optional)

**File**: Create `python/src/server/services/confluence_scheduler.py`

```python
"""
Confluence Sync Scheduler

Periodically syncs Confluence sources based on configured frequency.
"""

import asyncio
from datetime import datetime, timezone

from ..config.logfire_config import safe_logfire_info
from ..utils import get_supabase_client
from .confluence_sync_service import ConfluenceSyncService


class ConfluenceSyncScheduler:
    """Scheduler for automatic Confluence syncs"""

    def __init__(self, interval_hours: int = 24):
        self.interval_hours = interval_hours
        self.supabase_client = get_supabase_client()
        self.sync_service = ConfluenceSyncService(self.supabase_client)
        self._running = False

    async def start(self):
        """Start the scheduler"""
        self._running = True
        safe_logfire_info(f"Started Confluence scheduler | interval={self.interval_hours}h")

        while self._running:
            try:
                await self._sync_due_sources()
            except Exception as e:
                safe_logfire_error(f"Scheduler error: {e}")

            # Sleep for interval
            await asyncio.sleep(self.interval_hours * 3600)

    def stop(self):
        """Stop the scheduler"""
        self._running = False

    async def _sync_due_sources(self):
        """Sync sources that are due for sync"""
        # Get sources with sync_status = 'active'
        # and last_sync_at > interval_hours ago
        # Implement based on metadata.sync_frequency_hours

        response = self.supabase_client.table("archon_sources") \
            .select("*") \
            .contains("metadata", {"source_type": "confluence"}) \
            .eq("sync_status", "active") \
            .execute()

        for source in response.data:
            try:
                # Check if sync is due
                # (Implement time comparison logic)

                await self.sync_service.sync_source(source["source_id"])

            except Exception as e:
                safe_logfire_error(f"Failed to sync {source['source_id']}: {e}")
```

**Start scheduler** in `python/src/server/main.py`:

```python
from .services.confluence_scheduler import ConfluenceSyncScheduler

# After app initialization
scheduler = ConfluenceSyncScheduler(interval_hours=24)

@app.on_event("startup")
async def startup_scheduler():
    asyncio.create_task(scheduler.start())

@app.on_event("shutdown")
async def shutdown_scheduler():
    scheduler.stop()
```

---

## Phase 4: Testing & Documentation (Week 5)

### Goal
Comprehensive testing and user documentation.

### Tasks

#### 4.1 Unit Tests

**File**: Create `python/tests/test_confluence_integration.py`

```python
"""Tests for Confluence integration"""

import pytest
from src.server.services.confluence_client import ConfluenceClient
from src.server.services.confluence_content_processor import ConfluenceContentProcessor


@pytest.mark.asyncio
async def test_confluence_client_connection():
    """Test Confluence client can connect"""
    # Use test credentials or mock
    pass


@pytest.mark.asyncio
async def test_html_to_markdown_conversion():
    """Test HTML to markdown conversion"""
    processor = ConfluenceContentProcessor()

    html = "<h1>Test</h1><p>Content</p>"
    markdown = processor.html_to_markdown(html)

    assert "# Test" in markdown
    assert "Content" in markdown


def test_code_block_extraction():
    """Test code block extraction"""
    processor = ConfluenceContentProcessor()

    markdown = """
# Title

```python
def hello():
    print("world")
```

Some text

```javascript
console.log("test");
```
"""

    blocks = processor.extract_code_blocks(markdown)

    assert len(blocks) == 2
    assert blocks[0]["language"] == "python"
    assert blocks[1]["language"] == "javascript"


def test_metadata_extraction():
    """Test metadata extraction from Confluence page"""
    processor = ConfluenceContentProcessor()

    page = {
        "id": "123",
        "title": "Test Page",
        "type": "page",
        "version": {"number": 5, "when": "2025-10-01T00:00:00Z"},
        "space": {"key": "TEST"},
        "metadata": {
            "labels": {
                "results": [
                    {"name": "api"},
                    {"name": "documentation"}
                ]
            }
        }
    }

    metadata = processor.extract_metadata(page)

    assert metadata["confluence_page_id"] == "123"
    assert metadata["confluence_version"] == 5
    assert metadata["confluence_space"] == "TEST"
    assert "api" in metadata["confluence_labels"]
```

#### 4.2 Integration Tests

**File**: Create `python/tests/integration/test_confluence_crawl.py`

```python
"""Integration tests for Confluence crawling"""

import pytest
from src.server.services.confluence_client import ConfluenceClient
from src.server.services.crawling.strategies.confluence import ConfluenceCrawlStrategy


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_confluence_crawl(test_confluence_credentials):
    """Test full crawl of a small test space"""
    client = ConfluenceClient(
        confluence_url=test_confluence_credentials["url"],
        api_token=test_confluence_credentials["token"],
        user_email=test_confluence_credentials["email"]
    )

    strategy = ConfluenceCrawlStrategy(client)

    # Crawl test space (limit to 10 pages)
    documents = await strategy.crawl_space(
        space_key="TESTSPACE",
        max_pages=10
    )

    assert len(documents) > 0
    assert all("content" in doc for doc in documents)
    assert all("metadata" in doc for doc in documents)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_incremental_sync(test_confluence_credentials):
    """Test incremental sync detects changes"""
    from src.server.services.confluence_sync_service import ConfluenceSyncService

    # Perform initial crawl
    # ...

    # Wait or manually update a page
    # ...

    # Perform sync
    service = ConfluenceSyncService()
    result = await service.sync_source("test_source_id")

    assert result["success"]
    assert result["pages_updated"] > 0 or result["pages_deleted"] > 0
```

#### 4.3 Load Testing

**File**: Create `python/tests/load/test_confluence_performance.py`

```python
"""Load tests for Confluence integration"""

import pytest
import time


@pytest.mark.load
@pytest.mark.asyncio
async def test_large_space_crawl_performance(test_large_space):
    """Test crawling a large space (1000+ pages)"""
    start = time.time()

    # Crawl large space
    # ...

    duration = time.time() - start

    # Should complete in reasonable time (< 30 minutes for 4000 pages)
    assert duration < 1800, f"Crawl took {duration}s, expected < 1800s"


@pytest.mark.load
@pytest.mark.asyncio
async def test_search_performance_after_crawl():
    """Test search performance with Confluence content"""
    from src.server.services.search.rag_service import RAGService

    service = RAGService()

    start = time.time()
    results = await service.search_documents(
        query="authentication",
        filter_metadata={"source": "confluence_source_id"}
    )
    duration = time.time() - start

    assert duration < 0.1, f"Search took {duration}s, expected < 0.1s"
    assert len(results) > 0
```

#### 4.4 User Documentation

**File**: Update `/Users/macbook/Projects/archon/README.md` with Confluence section

```markdown
## Confluence Integration

Archon supports crawling Confluence Cloud spaces for RAG-powered knowledge base.

### Features

- ✅ Full space crawling with pagination
- ✅ Incremental sync with change detection
- ✅ Code block extraction and indexing
- ✅ Hybrid search (vector + keyword)
- ✅ Metadata preservation (labels, authors, hierarchy)
- ✅ Soft delete tracking

### Setup

1. **Generate Confluence API Token**
   - Visit https://id.atlassian.com/manage-profile/security/api-tokens
   - Create new token
   - Copy token securely

2. **Add Confluence Source in UI**
   - Navigate to Knowledge Base
   - Click "Add Source" → "Confluence Space"
   - Enter:
     - Confluence URL (e.g., `https://yourcompany.atlassian.net`)
     - Space Key (e.g., `DEVDOCS`)
     - Your email
     - API token
   - Click "Start Crawl"

3. **Monitor Progress**
   - View progress in Progress tab
   - Initial crawl time: ~15-30 minutes for 4000 pages
   - Subsequent syncs: ~2-5 minutes (incremental)

### Usage

**Search Confluence Content:**
```
Query: "JWT authentication best practices"
Filter: Select Confluence space
```

**Incremental Sync:**
- Automatic: Daily (configurable)
- Manual: Click "Sync Now" button on source

**Manage Sources:**
- View all sources in Knowledge Base
- Delete source removes all data and credentials

### Troubleshooting

**401 Unauthorized:**
- Token expired → Generate new token in Atlassian
- Update in Settings → Credentials

**403 Forbidden:**
- Insufficient permissions → Grant read access to space

**Rate Limited:**
- Atlassian enforces 10-100 req/min limits
- Archon implements automatic backoff

### API Reference

See `/api/docs` for full API documentation.
```

---

## Testing Checklist

Before deploying to production:

- [ ] Unit tests pass (`uv run pytest tests/test_confluence_*.py`)
- [ ] Integration tests pass with real Confluence space
- [ ] Load test with 1000+ pages completes successfully
- [ ] Search performance < 100ms with Confluence content
- [ ] Error handling tested (invalid credentials, rate limits)
- [ ] UI flows tested (create, view, delete, sync)
- [ ] Documentation reviewed and accurate
- [ ] Database migrations tested (upgrade and downgrade)
- [ ] Backup and restore procedures documented
- [ ] Monitoring and alerting configured

---

## Deployment Steps

1. **Backup Database**
   ```bash
   docker compose exec postgres pg_dump -U postgres archon > backup.sql
   ```

2. **Install Dependencies**
   ```bash
   cd python
   uv add atlassian-python-api markdownify
   ```

3. **Run Migrations**
   ```bash
   uv run alembic upgrade head
   ```

4. **Rebuild Containers**
   ```bash
   docker compose down
   docker compose up --build -d
   ```

5. **Verify Health**
   ```bash
   curl http://localhost:8181/health
   curl http://localhost:8181/api/confluence/sources
   ```

6. **Create Test Source**
   - Use UI to add a small test space
   - Verify crawl completes
   - Test search functionality

7. **Monitor Logs**
   ```bash
   docker compose logs -f archon-server
   ```

---

## Rollback Plan

If issues occur:

1. **Stop Services**
   ```bash
   docker compose down
   ```

2. **Restore Database**
   ```bash
   cat backup.sql | docker compose exec -T postgres psql -U postgres archon
   ```

3. **Revert Migration**
   ```bash
   cd python
   uv run alembic downgrade -1
   ```

4. **Restart Services**
   ```bash
   docker compose up -d
   ```

---

## Future Enhancements

### Phase 5+

- **Advanced Features**
  - Graph relationships (page hierarchy visualization)
  - Attachment indexing (PDFs, images)
  - Page history tracking
  - Multi-space crawling in single operation
  - Smart re-crawl (only changed sections)

- **Performance**
  - Parallel space crawling
  - Incremental embedding (only for changed content)
  - Caching strategies
  - Connection pooling

- **Integration**
  - MCP Confluence write operations
  - Bidirectional sync (Archon → Confluence)
  - Slack notifications for sync events
  - Webhook support for real-time updates

- **Analytics**
  - Usage metrics (popular pages, search terms)
  - Sync health dashboard
  - Cost analysis (API calls, storage)

---

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/your-org/archon/issues
- **Documentation**: `CONFLUENCE_RAG_INTEGRATION.md`
- **Architecture**: `PRPs/ai_docs/ARCHITECTURE.md`
