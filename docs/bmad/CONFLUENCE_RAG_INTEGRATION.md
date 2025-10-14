# Confluence RAG Integration Guide

## Executive Summary

This guide outlines the implementation approach for integrating 4000+ Confluence Cloud pages into Archon's RAG system for code implementation assistance and documentation generation.

**Selected Approach**: Direct Confluence API integration with **Hybrid database schema** (Option 3 from CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md) - dedicated metadata table + unified chunks for optimal code reuse and unified search.

### Why Hybrid Schema?

After analyzing three database schema options (see CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md), the Hybrid approach was selected for the following reasons:

**Code Reuse (90%)**:
- Reuses existing `document_storage_service.add_documents_to_supabase()` for chunking/embeddings
- Reuses existing `hybrid_search_strategy.py` for search
- Only ~800 lines of new Confluence sync logic vs 2000+ lines for separate tables

**Unified Search**:
- ONE query searches web crawls, Confluence, document uploads, and future sources
- No complex UNION queries needed
- Existing MCP tools work without modification

**Clean Separation**:
- Confluence metadata in dedicated `confluence_pages` table (~15 KB per page)
- Chunks in shared `archon_crawled_pages` table (minimal metadata)
- Natural SQL for incremental sync and version tracking

**Future-Proof**:
- Pattern: `{source}_metadata` table + shared `archon_crawled_pages`
- Easy to add Google Drive, SharePoint, Notion, etc. using same pattern
- Scales to N sources without exponential complexity

**Development Efficiency**:
- **1.5-2 weeks implementation** vs 3-4 weeks for separate tables
- Leverages battle-tested code for embeddings, chunking, search
- Focus effort on Confluence-specific sync logic only

## Implementation Approach

### RAG Integration with Hybrid Schema

We will implement a RAG solution using the **Hybrid approach** that:
- Fetches content directly from Confluence Cloud API
- Stores Confluence metadata in dedicated `confluence_pages` table
- **Reuses existing `archon_crawled_pages` table for chunks** (90% code reuse)
- Uses `archon_sources` for Confluence Space metadata
- Maintains unified search across all sources (web, Confluence, future Drive)
- Supports incremental synchronization with version tracking

### Why Hybrid Approach?

**Code Reuse (90%)**:
- Reuse `document_storage_service.add_documents_to_supabase()` for chunking and embeddings
- Reuse `hybrid_search_strategy.py` for search infrastructure
- Only need Confluence-specific sync logic (~800 lines vs 2000+ lines for separate tables)

**Unified Search**:
- ONE query searches across web crawls, Confluence, and future sources
- No complex UNION queries needed
- Existing MCP tools work without modification

**Future-Proof**:
- Pattern: `{source}_metadata` table + shared `archon_crawled_pages`
- Google Drive: Add `drive_files` table, reuse chunks
- SharePoint: Add `sharepoint_files` table, reuse chunks

### Why RAG

For 4000+ pages used for code implementation and documentation generation, RAG provides:
- **Hybrid Search**: Vector + keyword + graph capabilities
- **Performance**: <100ms local pgvector queries
- **Offline Support**: Works without internet after initial sync
- **Code Extraction**: Pre-indexed code blocks with language detection
- **No Rate Limits**: Once synced, unlimited queries
- **Optimized Context**: Intelligently chunked content for better retrieval

## Database Schema Architecture

### Hybrid Schema: Dedicated Metadata + Unified Chunks

We use the **Hybrid approach** combining dedicated metadata storage with unified chunk storage:

```sql
-- Confluence pages (metadata table - NEW)
CREATE TABLE confluence_pages (
  page_id TEXT PRIMARY KEY,  -- Confluence native page ID
  source_id TEXT NOT NULL REFERENCES archon_sources(source_id) ON DELETE CASCADE,

  -- Core fields
  space_key TEXT NOT NULL,
  title TEXT NOT NULL,
  version INTEGER NOT NULL,
  last_modified TIMESTAMPTZ NOT NULL,
  is_deleted BOOLEAN DEFAULT FALSE,

  -- Materialized path for hierarchy queries (e.g., "/parent_id/child_id/grandchild_id")
  path TEXT,

  -- Rich metadata stored ONCE per page (~15 KB)
  metadata JSONB NOT NULL,  -- Contains:
  -- {
  --   "ancestors": [{id, title, url}, ...],
  --   "children": [{id, title, url}, ...],
  --   "created_by": {account_id, display_name, email, profile_url},
  --   "jira_issue_links": [{issue_key, issue_url}, ...],
  --   "user_mentions": [{account_id, display_name, profile_url}, ...],
  --   "internal_links": [{page_id, page_title, page_url}, ...],
  --   "external_links": [{title, url}, ...],
  --   "asset_links": [{id, title, type, download_url}, ...],
  --   "word_count": 7351,
  --   "content_length": 75919
  -- }

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- archon_crawled_pages (EXISTING table - REUSED for chunks!)
-- Chunks linked to confluence_pages via metadata->>'page_id'
-- Example INSERT:
-- INSERT INTO archon_crawled_pages (url, content, metadata, source_id, embedding)
-- VALUES (
--   'confluence://NANOVEST/1100808193/chunk/1',
--   'chunk content...',
--   '{"page_id": "1100808193", "section_title": "Pre-deployment"}'::jsonb,
--   'conf_space_NANOVEST',
--   embedding_vector
-- );

-- Indexes for Confluence pages
CREATE INDEX idx_confluence_pages_source ON confluence_pages(source_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_confluence_pages_space ON confluence_pages(space_key) WHERE is_deleted = FALSE;
CREATE INDEX idx_confluence_pages_version ON confluence_pages(page_id, version);

-- Materialized path for efficient hierarchy queries (find descendants, siblings, breadcrumbs)
CREATE INDEX idx_confluence_pages_path ON confluence_pages USING btree(path text_pattern_ops);

-- JSONB indexes for metadata queries (optimized with jsonb_path_ops for exact matches)
CREATE INDEX idx_confluence_pages_jira_exact ON confluence_pages
  USING gin((metadata->'jira_issue_links') jsonb_path_ops);

CREATE INDEX idx_confluence_pages_jira_text ON confluence_pages
  USING gin(to_tsvector('english', metadata->'jira_issue_links'));

CREATE INDEX idx_confluence_pages_mentions ON confluence_pages
  USING gin((metadata->'user_mentions') jsonb_path_ops);

-- Index to link chunks back to pages
CREATE INDEX idx_crawled_pages_confluence_page_id
  ON archon_crawled_pages ((metadata->>'page_id'))
  WHERE metadata ? 'page_id';
```

### Schema Benefits

**Storage Efficiency**:
- Page metadata stored ONCE in `confluence_pages` (~15 KB)
- Chunks use minimal metadata (~150 bytes each)
- Total for 1000-page space: ~18 MB (same as separate tables)

**Code Reuse**:
- Chunks use existing `archon_crawled_pages` table
- Reuse `document_storage_service.add_documents_to_supabase()`
- Reuse `hybrid_search_strategy.py`
- No duplicate embedding/chunking code

**Unified Search**:
- ONE table for all chunks (web, Confluence, future sources)
- No UNION queries needed
- Existing MCP tools work without changes

### Integration with archon_sources

Confluence Spaces are registered as sources in the existing `archon_sources` table:

```sql
-- Existing archon_sources table usage
INSERT INTO archon_sources (source_id, source_type, metadata)
VALUES (
  'confluence_DEVDOCS',
  'confluence',
  '{
    "confluence_space_key": "DEVDOCS",
    "confluence_base_url": "https://company.atlassian.net",
    "last_sync_timestamp": "2025-10-01T10:00:00Z",
    "total_pages": 4127,
    "sync_frequency_hours": 24,
    "deletion_check_strategy": "weekly_reconciliation",
    "last_full_reconciliation": "2025-10-01T00:00:00Z",
    "sync_metrics": {
      "pages_created": 0,
      "pages_updated": 45,
      "pages_deleted": 2,
      "chunks_created": 890,
      "last_sync_duration_seconds": 120,
      "api_calls": 15
    }
  }'::jsonb
);
```


## Data Pipeline Architecture

### Hybrid Schema Flow with Code Reuse

```
┌─────────────────┐
│ Confluence API  │
│   (REST v2)     │
└────────┬────────┘
         │
         │ 1. Fetch pages (CQL queries)
         │    - Full sync or incremental
         │    - Metadata + content
         │
         ▼
┌─────────────────┐
│ Confluence      │
│ Sync Service    │ (NEW - ~800 lines)
└────────┬────────┘
         │
         │ 2. Process & Store Metadata
         │    - HTML → Markdown
         │    - Extract rich metadata
         │    - Store in confluence_pages
         │
         ▼
┌─────────────────┐
│confluence_pages │ ◄─── archon_sources (space metadata)
│  (metadata)     │
└────────┬────────┘
         │
         │ 3. Delete old chunks & Call existing service
         │    - DELETE WHERE metadata->>'page_id' = $1
         │    - Call document_storage_service.add_documents_to_supabase()
         │    - REUSE existing chunking/embedding logic!
         │
         ▼
┌─────────────────────────┐
│ archon_crawled_pages    │ ◄─── EXISTING table (REUSED!)
│ (unified chunks)        │      - Web crawls
│                         │      - Document uploads
│                         │      - Confluence pages
│                         │      - Future: Drive, SharePoint
└────────┬────────────────┘
         │
         │ 4. Unified Search (NO VIEW NEEDED!)
         │    - Query archon_crawled_pages directly
         │    - JOIN confluence_pages for metadata enrichment
         │
         ▼
┌─────────────────┐
│ Hybrid Search   │ ◄─── EXISTING service (REUSED!)
│  (One table)    │      hybrid_search_strategy.py
└─────────────────┘
```

**Benefits:**
- **90% code reuse**: Only sync service is new
- **Unified search**: One table, one query
- **Clean metadata separation**: confluence_pages vs chunks
- **Efficient incremental sync**: Version tracking in confluence_pages
- **Future-proof**: Pattern works for Drive, SharePoint, etc.
- **1.5-2 week implementation** vs 3-4 weeks for separate tables

## Metadata Strategy

### Rich Metadata Preservation

Based on the sample Confluence pages (`155254944_metadata-2.json` and `1100808193_metadata.json`), we preserve comprehensive metadata for each page:

**Why Rich Metadata?**
- **Better Search Context**: Links, mentions, and JIRA issues provide relationship context
- **Navigation**: Hierarchy (ancestors/children) enables tree navigation in UI
- **Filtering**: Space, author, labels enable targeted search
- **Traceability**: Creation/update timestamps and authors for auditing
- **Cross-references**: External links, internal links, and JIRA links for knowledge graph

**Metadata Fields Stored in `confluence_pages.metadata` JSONB:**

| Field | Purpose | Example from Samples |
|-------|---------|---------------------|
| `ancestors` | Page hierarchy | `[{id, title, url}, ...]` |
| `children` | Child pages | `[{id, title, url}, ...]` |
| `created_by` | Author info | `{account_id, display_name, email, profile_url}` |
| `external_links` | External URLs | Google Drive links, etc. |
| `internal_links` | Links to other pages | `[{page_id, page_title, page_url}, ...]` |
| `jira_issue_links` | Linked JIRA tickets | `[{issue_key: "IC-548", issue_url}, ...]` |
| `user_mentions` | @-mentions | `[{account_id, display_name, profile_url}, ...]` |
| `asset_links` | Attachments | `[{id, title, size, mimetype, download_url, drive_url}, ...]` |
| `content_length` | Character count | 75919 |
| `word_count` | Word count | 7351 |

**Core Fields as Native Columns:**
- `page_id`: Confluence native page ID (PRIMARY KEY)
- `space_key`: For efficient filtering (indexed)
- `title`: Page title
- `version`: For incremental sync
- `last_modified`: Timestamp for change detection
- `is_deleted`: Soft delete tracking

**Metadata in `archon_crawled_pages` chunks (Minimal):**
- `metadata->>'page_id'`: Link back to confluence_pages (indexed)
- `metadata->>'section_title'`: Heading context for the chunk

**Search Use Cases Enabled:**

1. **Find pages mentioning user**: Query `metadata->'user_mentions'` JSONB field
   ```sql
   SELECT * FROM confluence_pages
   WHERE metadata->'user_mentions' @> '[{"account_id": "61ad6c68c75da8007239a6db"}]'::jsonb;
   ```

2. **Find pages with JIRA ticket**: Query `metadata->'jira_issue_links'` for specific issue key
   ```sql
   -- Exact match using jsonb_path_ops index (FAST)
   SELECT * FROM confluence_pages
   WHERE metadata->'jira_issue_links' @> '[{"issue_key": "IC-548"}]'::jsonb;

   -- Full-text search in JIRA metadata (for searching in descriptions)
   SELECT * FROM confluence_pages
   WHERE to_tsvector('english', metadata->'jira_issue_links') @@ to_tsquery('deployment');
   ```

3. **Find pages with attachments**: Filter where `metadata->'asset_links'` is not empty
   ```sql
   SELECT * FROM confluence_pages
   WHERE metadata->'asset_links' IS NOT NULL
     AND jsonb_array_length(metadata->'asset_links') > 0;
   ```

4. **Find child pages**: Use materialized path for efficient hierarchy queries
   ```sql
   -- Find direct children (fast with btree index)
   SELECT * FROM confluence_pages
   WHERE path ~ '^/parent_id/[^/]+$';

   -- Find all descendants (any depth)
   SELECT * FROM confluence_pages
   WHERE path LIKE '/parent_id/%';

   -- Build breadcrumbs (path shows full hierarchy)
   SELECT title, path FROM confluence_pages WHERE page_id = '155254944';
   ```

5. **Find related pages via internal links**: Query `metadata->'internal_links'`
   ```sql
   SELECT * FROM confluence_pages
   WHERE metadata->'internal_links' @> '[{"page_id": "166199304"}]'::jsonb;
   ```

6. **Find pages by author**: Query `metadata->'created_by'` JSONB field
   ```sql
   SELECT * FROM confluence_pages
   WHERE metadata->'created_by'->>'email' = 'adrianto@nanovest.io';
   ```

7. **Unified search across all sources**: Query chunks and JOIN for metadata enrichment
   ```sql
   -- Search ALL sources (web, Confluence, uploads) with ONE query
   SELECT
     c.content,
     c.metadata->>'page_id' as page_id,
     p.title as page_title,
     p.space_key,
     p.metadata->'jira_issue_links' as jira_links,
     1 - (c.embedding <=> $1::vector) as similarity
   FROM archon_crawled_pages c
   LEFT JOIN confluence_pages p ON c.metadata->>'page_id' = p.page_id
   WHERE c.embedding <=> $1::vector < 0.3
   ORDER BY similarity DESC
   LIMIT 10;
   ```

## CQL-Based Incremental Sync Strategy

### Overview

Archon uses **CQL (Confluence Query Language)** for efficient incremental synchronization:
- **Only fetches changed pages** using `lastModified >= timestamp`
- **No full space scans** - Confluence indexes handle change detection
- **Configurable deletion detection** - Choose between immediate, weekly, or on-demand strategies

### Change Detection with CQL

```python
async def sync_confluence_space_incremental(self, space_key: str, source_id: str):
    """
    Incremental sync using CQL - only fetches pages modified since last sync.
    Handles creates, updates, and deletions efficiently.
    """

    # Get last sync timestamp from archon_sources metadata
    source = await self.db.fetchrow("""
        SELECT source_id,
               metadata->>'last_sync_timestamp' as last_sync,
               metadata->>'deletion_check_strategy' as deletion_strategy
        FROM archon_sources
        WHERE source_id = $1
    """, source_id)

    last_sync = source['last_sync'] or '1970-01-01T00:00:00Z'
    deletion_strategy = source['deletion_strategy'] or 'weekly_reconciliation'

    # Build CQL query for pages modified since last sync
    # CQL date format: "yyyy-MM-dd HH:mm"
    last_sync_cql = datetime.fromisoformat(last_sync).strftime('%Y-%m-%d %H:%M')
    cql = f'space = {space_key} AND lastModified >= "{last_sync_cql}" ORDER BY lastModified ASC'

    # Fetch only changed pages from Confluence
    changed_pages = await self.confluence_client.cql_search(
        cql=cql,
        expand='body.storage,version,ancestors,metadata.labels',
        limit=1000  # Confluence max per request
    )

    logger.info(f"CQL found {len(changed_pages)} changed pages since {last_sync}")

    # Get stored pages with their current versions
    stored_pages = await self.db.fetch("""
        SELECT page_id, version
        FROM confluence_pages
        WHERE source_id = $1 AND is_deleted = FALSE
    """, source_id)
    stored_page_map = {p['page_id']: p['version'] for p in stored_pages}

    # Separate creates vs updates based on version comparison
    creates = []
    updates = []

    for page in changed_pages:
        page_id = page['id']
        page_version = page['version']['number']

        if page_id not in stored_page_map:
            creates.append(page)  # New page
        elif page_version > stored_page_map[page_id]:
            updates.append(page)  # Existing page with version bump

    # Process creates and updates
    for page in creates:
        await self.process_page_create(page, source_id)

    for page in updates:
        await self.process_page_update(page, source_id)

    # Handle deletions based on configured strategy
    deleted_count = await self._handle_deletions(space_key, source_id, deletion_strategy)

    # Update sync metadata with metrics
    await self._update_sync_metrics(source_id, {
        'last_sync_timestamp': datetime.utcnow().isoformat(),
        'pages_created': len(creates),
        'pages_updated': len(updates),
        'pages_deleted': deleted_count,
        'last_sync_duration_seconds': sync_duration
    })

    return {
        'created': len(creates),
        'updated': len(updates),
        'deleted': deleted_count
    }
```

### Deletion Detection Strategies

Since CQL cannot detect deleted pages (they don't exist in Confluence anymore), we offer three strategies:

#### Strategy 1: Weekly Reconciliation (RECOMMENDED - Default)

```python
async def _handle_deletions(self, space_key: str, source_id: str, strategy: str) -> int:
    """Handle page deletions based on configured strategy"""

    if strategy == "weekly_reconciliation":
        source = await self.db.fetchrow("""
            SELECT metadata->>'last_full_reconciliation' as last_check
            FROM archon_sources WHERE source_id = $1
        """, source_id)

        last_check = source['last_check']
        if not last_check or (datetime.utcnow() - datetime.fromisoformat(last_check)).days >= 7:
            return await self._detect_deletions_full(space_key, source_id)
        return 0

    elif strategy == "every_sync":
        return await self._detect_deletions_lightweight(space_key, source_id)

    else:  # "on_demand"
        return 0  # Don't check during sync

async def _detect_deletions_lightweight(self, space_key: str, source_id: str) -> int:
    """Fast deletion check - only fetches page IDs (1 API call per 1000 pages)"""

    # Get DB page IDs
    db_page_ids = await self.db.fetch("""
        SELECT confluence_page_id
        FROM confluence_pages
        WHERE space_key = $1 AND source_id = $2 AND is_deleted = false
    """, space_key, source_id)
    db_ids = {row['confluence_page_id'] for row in db_page_ids}

    # Get live page IDs from Confluence (API: GET /wiki/rest/api/content?spaceKey=X)
    live_ids = await self.confluence_client.get_page_ids_in_space(space_key)

    # Find deleted pages
    deleted_ids = db_ids - set(live_ids)

    if deleted_ids:
        await self.db.execute("""
            UPDATE confluence_pages
            SET is_deleted = true, deleted_at = NOW()
            WHERE confluence_page_id = ANY($1::text[])
        """, list(deleted_ids))

        # Delete chunks atomically
        await self.db.execute("""
            DELETE FROM archon_crawled_pages
            WHERE metadata->>'page_id' = ANY($1::text[])
        """, list(deleted_ids))

    return len(deleted_ids)

async def _detect_deletions_full(self, space_key: str, source_id: str) -> int:
    """Full reconciliation - used weekly (updates last_full_reconciliation timestamp)"""

    deleted_count = await self._detect_deletions_lightweight(space_key, source_id)

    # Update reconciliation timestamp
    await self.db.execute("""
        UPDATE archon_sources
        SET metadata = metadata || jsonb_build_object(
            'last_full_reconciliation', $2
        )
        WHERE source_id = $1
    """, source_id, datetime.utcnow().isoformat())

    return deleted_count
```

#### Deletion Strategy Comparison

| Strategy | API Calls/Sync | Deletion Lag | Best For |
|----------|----------------|--------------|----------|
| `weekly_reconciliation` | 0 (except weekly) | Up to 7 days | Large spaces (>1000 pages) - **DEFAULT** |
| `every_sync` | ~1 per 1000 pages | Immediate | Small spaces (<1000 pages) |
| `on_demand` | 0 during sync | User notices 404s | Beta/testing phase |

### Sync Frequency

| Sync Type | Frequency | Duration (est.) | Use Case |
|-----------|-----------|-----------------|----------|
| **Incremental (CQL)** | Hourly/Daily | 30s - 2 min | Normal updates - **RECOMMENDED** |
| **On-Demand** | Manual | Varies | Immediate needs |

**Note**: Full space re-sync is **not supported**. All syncs are incremental using CQL change detection.

## Implementation Phases

### Phase 1: Database Schema & Basic Sync (Week 1)

**Database Migration:**
- Create `confluence_pages` table (metadata only)
- Create indexes for performance
- Create index on `archon_crawled_pages` for `metadata->>'page_id'`
- **No separate chunks table** - reuse existing `archon_crawled_pages`!

**Backend Files to Create:**
- `python/src/server/services/confluence/confluence_client.py` - API client
- `python/src/server/services/confluence/confluence_sync_service.py` - Sync logic
- `python/src/server/services/confluence/confluence_processor.py` - Content processing

**Tasks:**
1. Implement Confluence API client using `atlassian-python-api`
2. Create CQL-based incremental sync logic (fetch only changed pages)
3. Implement HTML to Markdown conversion
4. Store page metadata in `confluence_pages` table with materialized path
5. **Call existing `document_storage_service.add_documents_to_supabase()`** for chunks
6. Register space in `archon_sources`
7. Implement atomic chunk update strategy (zero-downtime updates)
8. Add sync observability (metrics tracking in metadata)

**API Integration Example:**
```python
from atlassian import Confluence

class ConfluenceClient:
    def __init__(self, base_url: str, api_token: str):
        self.client = Confluence(url=base_url, token=api_token)

    async def cql_search(self, cql: str, expand: str = None, limit: int = 1000):
        """
        Search using CQL for incremental sync.
        Only fetches pages matching the CQL query (e.g., lastModified >= timestamp).
        """
        return self.client.cql(cql, expand=expand, limit=limit)

    async def get_page_ids_in_space(self, space_key: str) -> list[str]:
        """
        Lightweight deletion detection - only fetch page IDs (no content).
        Used for comparing DB pages vs live Confluence pages.
        """
        pages = self.client.get_all_pages_from_space(
            space=space_key,
            start=0,
            limit=1000,
            expand=None  # Don't fetch content, just IDs
        )
        return [p['id'] for p in pages]
```

### Phase 2: Chunking & Embeddings (Week 2) - REUSE EXISTING CODE!

**Backend Changes:**
- **NO new chunking logic needed** - reuse `document_storage_service.py`!
- **NO new embedding logic needed** - reuse `llm_provider_service.py`!
- Only need to prepare data for existing service

**Tasks:**
1. Convert Markdown to plain text chunks (use existing logic)
2. Call `document_storage_service.add_documents_to_supabase()`
3. Pass minimal metadata: `{"page_id": "1100808193", "section_title": "Pre-deployment"}`
4. Existing service handles: chunking, embeddings, storage, progress tracking

**Integration Pattern (Reuse 90% of code):**
```python
from src.server.services.storage.document_storage_service import add_documents_to_supabase

async def process_page_create(self, page: dict, source_id: str):
    """Process a newly created Confluence page"""
    # 1. Extract and convert content
    content_markdown = await self.convert_to_markdown(page['body']['storage']['value'])

    # 2. Store page metadata in confluence_pages
    await self.db.execute("""
        INSERT INTO confluence_pages (page_id, source_id, space_key, title, version, last_modified, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (page_id) DO UPDATE SET
            version = EXCLUDED.version,
            last_modified = EXCLUDED.last_modified,
            metadata = EXCLUDED.metadata
    """, page['id'], source_id, page['space']['key'], page['title'], page['version']['number'],
        page['version']['when'], metadata_jsonb)

    # 3. REUSE existing service for chunking and embedding!
    await add_documents_to_supabase(
        urls=[f"confluence://{page['space']['key']}/{page['id']}"],
        contents=[content_markdown],
        metadatas=[{"page_id": page['id']}],
        source_id=source_id
    )
    # That's it! Existing service handles:
    # - Section-aware chunking
    # - Code block detection
    # - Embedding generation (multi-provider support)
    # - Progress tracking
    # - Parallel batch processing
```

**Code Savings:**
- Chunking logic: Already implemented in `document_storage_service.py`
- Embedding generation: Already supports OpenAI, Google, Ollama
- Storage with vector: Already handles `archon_crawled_pages`
- **Estimated lines saved: ~800 lines of duplicate code**

### Phase 3: Incremental Sync & API (Week 3-4)

**Backend Files to Create:**
- `python/src/server/api_routes/confluence_api.py` - API endpoints

**API Endpoints:**
```python
POST   /api/confluence/sources          # Create Confluence source (registers in archon_sources)
GET    /api/confluence/sources          # List Confluence sources
POST   /api/confluence/{id}/sync        # Trigger manual sync
GET    /api/confluence/{id}/status      # Get sync status
DELETE /api/confluence/{id}             # Delete source (CASCADE deletes pages & chunks)
GET    /api/confluence/{id}/pages       # List pages in a space
```

**Tasks:**
1. Implement incremental sync using CQL (only changed pages)
2. Handle page updates with atomic chunk updates (zero-downtime)
3. Handle page deletions with configurable strategies (weekly/every_sync/on_demand)
4. Add API endpoints for source management
5. Use existing `ProgressTracker` for sync status
6. Build materialized path for page hierarchy queries
7. Track sync metrics in archon_sources.metadata

**Incremental Sync Flow with Observability:**
```python
class ConfluenceSyncMetrics:
    """Track sync performance and health for observability"""

    def __init__(self):
        self.pages_created = 0
        self.pages_updated = 0
        self.pages_deleted = 0
        self.pages_failed = 0
        self.chunks_created = 0
        self.api_calls = 0
        self.api_errors = []
        self.sync_start = datetime.utcnow()
        self.sync_duration = 0

    def to_jsonb(self) -> dict:
        """Convert metrics to JSONB for storage in archon_sources.metadata"""
        return {
            "pages_created": self.pages_created,
            "pages_updated": self.pages_updated,
            "pages_deleted": self.pages_deleted,
            "pages_failed": self.pages_failed,
            "chunks_created": self.chunks_created,
            "api_calls": self.api_calls,
            "api_errors": self.api_errors[:10],  # Last 10 errors only
            "last_sync_duration_seconds": self.sync_duration,
            "last_sync_timestamp": datetime.utcnow().isoformat()
        }

async def sync_incremental(self, source_id: str, space_key: str):
    """
    CQL-based incremental sync - only fetches changed pages.
    Tracks detailed metrics for observability and debugging.
    """

    progress = ProgressTracker(operation_id, operation_type="confluence_sync")
    metrics = ConfluenceSyncMetrics()

    try:
        # Get sync configuration
        source = await self.db.fetchrow("""
            SELECT metadata->>'last_sync_timestamp' as last_sync,
                   metadata->>'deletion_check_strategy' as deletion_strategy
            FROM archon_sources WHERE source_id = $1
        """, source_id)

        last_sync = source['last_sync'] or '1970-01-01T00:00:00Z'
        deletion_strategy = source['deletion_strategy'] or 'weekly_reconciliation'

        # CQL query for changed pages only
        last_sync_cql = datetime.fromisoformat(last_sync).strftime('%Y-%m-%d %H:%M')
        cql = f'space = {space_key} AND lastModified >= "{last_sync_cql}"'

        changed_pages = await self.confluence_client.cql_search(cql, expand='body.storage,version,ancestors')
        metrics.api_calls += 1

        # Separate creates vs updates
        creates, updates = await self._classify_changes(changed_pages, source_id)

        total = len(creates) + len(updates)
        await progress.update(
            status="syncing",
            progress=0,
            log=f"CQL found {len(creates)} new, {len(updates)} updates"
        )

        processed = 0

        # Process creates
        for page in creates:
            try:
                chunk_count = await self.process_page_create(page, source_id)
                metrics.pages_created += 1
                metrics.chunks_created += chunk_count
            except Exception as e:
                metrics.pages_failed += 1
                metrics.api_errors.append({"page_id": page['id'], "error": str(e)})
                safe_logfire_error(f"Failed to create page {page['id']}: {e}")

            processed += 1
            await progress.update(
                progress=int(processed / total * 100) if total > 0 else 100,
                log=f"Created: {page['title']}"
            )

        # Process updates with atomic chunk replacement
        for page in updates:
            try:
                chunk_count = await self.process_page_update(page, source_id)
                metrics.pages_updated += 1
                metrics.chunks_created += chunk_count
            except Exception as e:
                metrics.pages_failed += 1
                metrics.api_errors.append({"page_id": page['id'], "error": str(e)})
                safe_logfire_error(f"Failed to update page {page['id']}: {e}")

            processed += 1
            await progress.update(
                progress=int(processed / total * 100) if total > 0 else 100,
                log=f"Updated: {page['title']}"
            )

        # Handle deletions based on strategy
        deleted_count = await self._handle_deletions(space_key, source_id, deletion_strategy)
        metrics.pages_deleted = deleted_count

        # Store metrics in archon_sources.metadata for observability
        metrics.sync_duration = (datetime.utcnow() - metrics.sync_start).total_seconds()
        await self.db.execute("""
            UPDATE archon_sources
            SET metadata = metadata || $2::jsonb
            WHERE source_id = $1
        """, source_id, metrics.to_jsonb())

        await progress.complete(
            log=f"Sync completed: {metrics.pages_created} created, {metrics.pages_updated} updated, "
                f"{metrics.pages_deleted} deleted, {metrics.pages_failed} failed"
        )

    except Exception as e:
        await progress.fail(log=f"Sync failed: {str(e)}")
        safe_logfire_error(f"Confluence sync failed | source_id={source_id}", exc_info=True)
        raise


async def build_materialized_path(self, page: dict) -> str:
    """
    Build materialized path for efficient hierarchy queries.
    Example: "/parent_id/child_id/grandchild_id"
    Enables fast queries like:
    - Find all descendants: WHERE path LIKE '/parent_id/%'
    - Find siblings: WHERE path ~ '^/parent_id/[^/]+$'
    """
    ancestors = page.get('ancestors', [])
    if not ancestors:
        return f"/{page['id']}"

    # Build path from root to current page
    path_parts = [ancestor['id'] for ancestor in ancestors]
    path_parts.append(page['id'])
    return "/" + "/".join(path_parts)

async def process_page_create(self, page: dict, source_id: str) -> int:
    """
    Process a newly created Confluence page - HYBRID APPROACH.
    Returns: Number of chunks created
    """
    # 1. Extract and convert content
    content_markdown = await self.convert_to_markdown(page['body']['storage']['value'])

    # 2. Build metadata JSONB
    metadata_jsonb = {
        "ancestors": page.get('ancestors', []),
        "children": page.get('children', []),
        "created_by": page['history']['createdBy'],
        "jira_issue_links": await self.extract_jira_links(content_markdown),
        "user_mentions": page.get('metadata', {}).get('mentions', []),
        "internal_links": page.get('metadata', {}).get('internalLinks', []),
        "external_links": await self.extract_external_links(content_markdown),
        "asset_links": page.get('metadata', {}).get('attachments', []),
        "word_count": len(content_markdown.split()),
        "content_length": len(content_markdown)
    }

    # 3. Store page metadata in confluence_pages with materialized path
    materialized_path = await self.build_materialized_path(page)

    await self.db.execute("""
        INSERT INTO confluence_pages (page_id, source_id, space_key, title, version, last_modified, path, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (page_id) DO UPDATE SET
            version = EXCLUDED.version,
            last_modified = EXCLUDED.last_modified,
            path = EXCLUDED.path,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
    """, page['id'], source_id, page['space']['key'], page['title'],
        page['version']['number'], page['version']['when'], materialized_path, metadata_jsonb)

    # 4. REUSE existing service for chunking and embedding!
    result = await add_documents_to_supabase(
        urls=[f"confluence://{page['space']['key']}/{page['id']}"],
        contents=[content_markdown],
        metadatas=[{"page_id": page['id']}],
        source_id=source_id
    )
    # Existing service handles: chunking, code detection, embedding, storage

    return result.get('chunks_created', 0)


async def process_page_update(self, page: dict, source_id: str):
    """
    Process an updated Confluence page with atomic chunk updates.
    Uses zero-downtime strategy: mark old chunks as pending deletion,
    insert new chunks, then delete old chunks only after success.
    """
    page_id = page['id']
    content_markdown = await self.convert_to_markdown(page['body']['storage']['value'])
    metadata_jsonb = await self.build_metadata(page)

    async with self.db.transaction():
        # 1. Update page metadata in confluence_pages
        await self.db.execute("""
            UPDATE confluence_pages
            SET version = $1,
                title = $2,
                last_modified = $3,
                metadata = $4,
                path = $5,
                updated_at = NOW()
            WHERE page_id = $6 AND source_id = $7
        """, page['version']['number'], page['title'], page['version']['when'],
            metadata_jsonb, await self.build_materialized_path(page), page_id, source_id)

        # 2. ATOMIC CHUNK UPDATE: Mark old chunks as pending deletion (don't delete yet!)
        await self.db.execute("""
            UPDATE archon_crawled_pages
            SET metadata = metadata || '{"_pending_deletion": true}'::jsonb
            WHERE metadata->>'page_id' = $1
        """, page_id)

        # 3. Insert new chunks using existing service
        # Old chunks still available during this operation (zero downtime)
        await add_documents_to_supabase(
            urls=[f"confluence://{page['space']['key']}/{page_id}"],
            contents=[content_markdown],
            metadatas=[{"page_id": page_id}],
            source_id=source_id
        )

        # 4. Delete old chunks only after new chunks successfully inserted
        await self.db.execute("""
            DELETE FROM archon_crawled_pages
            WHERE metadata->>'page_id' = $1
            AND metadata->>'_pending_deletion' = 'true'
        """, page_id)

        # Transaction commits here - atomic success or rollback


async def soft_delete_page(self, page_id: str, source_id: str):
    """Soft delete a page that was removed from Confluence"""
    # 1. Mark page as deleted
    await self.db.execute("""
        UPDATE confluence_pages
        SET is_deleted = TRUE, updated_at = NOW()
        WHERE page_id = $1 AND source_id = $2
    """, page_id, source_id)

    # 2. Delete chunks (no CASCADE needed, just delete by metadata)
    await self.db.execute("""
        DELETE FROM archon_crawled_pages
        WHERE metadata->>'page_id' = $1
    """, page_id)
    # Chunks are removed immediately; page metadata preserved for audit trail
```

### Phase 4: Search Integration (Week 3) - MINIMAL CHANGES!

**Backend Files to Modify:**
- **NONE!** Existing `hybrid_search_strategy.py` already searches `archon_crawled_pages`
- Only need to add optional JOIN for Confluence metadata enrichment

**Tasks:**
1. **No changes to core search** - already unified!
2. Add optional JOIN to `confluence_pages` for metadata enrichment
3. Add Confluence-specific filters (space, JIRA links) if needed
4. Existing search infrastructure works out of the box

**Search Integration (REUSE existing code!):**
```python
# EXISTING search already works!
# hybrid_search_strategy.py queries archon_crawled_pages
# No changes needed for basic search

# Optional: Add metadata enrichment for Confluence results
async def hybrid_search(
    query: str,
    filters: dict = None,
    limit: int = 10
) -> list:
    """
    Hybrid search across all sources - EXISTING CODE!
    Just add optional Confluence metadata JOIN
    """

    # Vector search (EXISTING)
    query_embedding = await self.llm_service.get_embedding(query)

    sql = """
    SELECT
        c.id,
        c.source_id,
        c.content as chunk_text,
        c.metadata,
        p.title as confluence_page_title,
        p.space_key as confluence_space,
        p.metadata->'jira_issue_links' as jira_links,
        1 - (c.embedding <=> $1::vector) as similarity
    FROM archon_crawled_pages c
    LEFT JOIN confluence_pages p ON c.metadata->>'page_id' = p.page_id
    WHERE 1=1
    """

    params = [query_embedding]

    # Apply filters (NEW: Confluence-specific)
    if filters:
        if filters.get('confluence_space'):
            sql += f" AND p.space_key = ${len(params) + 1}"
            params.append(filters['confluence_space'])

        if filters.get('has_jira_links'):
            sql += f" AND p.metadata->'jira_issue_links' IS NOT NULL"

    sql += f" ORDER BY similarity DESC LIMIT ${len(params) + 1}"
    params.append(limit)

    results = await self.db.fetch(sql, *params)
    return results
```

**Code Savings:**
- **No duplicate search logic needed**
- **No UNION queries needed**
- **No view maintenance needed**
- Existing MCP tools work without changes!

### Phase 5: Frontend & Testing (Week 5-6)

**Frontend Files to Create:**
- `archon-ui-main/src/features/confluence/` - Feature directory
- `archon-ui-main/src/features/confluence/services/confluenceService.ts`
- `archon-ui-main/src/features/confluence/components/ConfluenceSourceForm.tsx`
- `archon-ui-main/src/features/confluence/components/ConfluenceSourceCard.tsx`
- `archon-ui-main/src/features/confluence/hooks/useConfluenceQueries.ts`

**Tasks:**
1. Create Confluence source creation form
2. Display sync status and progress
3. Add manual sync trigger button
4. Show Confluence-specific metadata in search results
5. Add filters for Confluence search (space, labels)
6. Write unit and integration tests
7. Load test with 4000+ pages

## Configuration

### Environment Variables

```bash
# .env
CONFLUENCE_API_TIMEOUT=30
CONFLUENCE_MAX_PAGES_PER_REQUEST=100
CONFLUENCE_MAX_CONCURRENT_REQUESTS=5
CONFLUENCE_RETRY_ATTEMPTS=3
CONFLUENCE_SYNC_BATCH_SIZE=50
```

### Credential Storage

Use existing Archon credential service:
```python
from src.server.services.credential_service import credential_service

await credential_service.set_credential(
    key=f"confluence_token_{source_id}",
    value=api_token,
    category="confluence",
    is_encrypted=True
)
```

## Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `401 Unauthorized` | Invalid/expired token | Update API token via Settings |
| `403 Forbidden` | Insufficient permissions | Grant read access to space in Confluence |
| `404 Not Found` | Space/page deleted | Soft delete in database |
| `429 Rate Limited` | Too many requests | Exponential backoff retry |
| `500 Server Error` | Confluence downtime | Retry with backoff, alert user |

### Logging

```python
from src.server.config.logfire_config import safe_logfire_info, safe_logfire_error

safe_logfire_info(
    f"Confluence sync started | source_id={source_id} | space={space_key}"
)

safe_logfire_error(
    f"Confluence sync failed | source_id={source_id} | error={str(e)}",
    exc_info=True
)
```

## Performance Optimization

### Indexes

```sql
-- Vector search performance
CREATE INDEX idx_conf_chunks_embedding
ON conf_chunks USING ivfflat(embedding vector_cosine_ops)
WITH (lists = 100);

-- Metadata filtering
CREATE INDEX idx_conf_pages_space ON conf_pages(space_key) WHERE is_deleted = FALSE;
CREATE INDEX idx_conf_chunks_source ON conf_chunks(source_id);

-- Full-text search (if needed)
CREATE INDEX idx_conf_chunks_fts ON conf_chunks USING gin(to_tsvector('english', chunk_text));
```

### Batch Processing

```python
async def sync_pages_batch(self, pages: list, source_id: str):
    """Process pages in batches for efficiency"""
    batch_size = 50

    for i in range(0, len(pages), batch_size):
        batch = pages[i:i+batch_size]

        # Parallel processing within batch
        await asyncio.gather(*[
            self.process_and_store_page(page, source_id)
            for page in batch
        ])
```

## Testing Strategy

### Unit Tests

```python
# tests/test_confluence_sync.py
async def test_detect_changes():
    service = ConfluenceSyncService()
    changes = await service.detect_changes('test_source')
    assert 'updated' in changes
    assert 'deleted' in changes

async def test_chunk_confluence_page():
    content = load_fixture('sample_confluence_page.md')
    chunks = chunk_confluence_page(content, {})
    assert len(chunks) > 0
    assert all('chunk_text' in c for c in chunks)
    assert all('heading_context' in c for c in chunks)
```

### Integration Tests

```python
async def test_full_sync_flow():
    # Create Confluence source
    source_id = await confluence_service.create_source(
        base_url='https://test.atlassian.net',
        space_key='TEST',
        api_token='token'
    )

    # Trigger sync
    await confluence_service.sync_full(source_id)

    # Verify pages stored
    pages = await db.fetch("SELECT * FROM conf_pages WHERE source_id = $1", source_id)
    assert len(pages) > 0

    # Verify chunks created
    chunks = await db.fetch("SELECT * FROM conf_chunks WHERE source_id = $1", source_id)
    assert len(chunks) > 0

    # Test search
    results = await search_service.hybrid_search(
        query="authentication",
        filters={'confluence_space': 'TEST'}
    )
    assert len(results) > 0
```

### Load Testing

```python
async def test_large_space_sync():
    """Test with 4000+ pages"""
    import time

    start = time.time()
    await confluence_service.sync_full('large_space_source_id')
    duration = time.time() - start

    assert duration < 1800  # Should complete in < 30 minutes

    # Verify all pages synced
    page_count = await db.fetch_val(
        "SELECT COUNT(*) FROM conf_pages WHERE source_id = $1",
        'large_space_source_id'
    )
    assert page_count >= 4000
```

## Migration Path

### Step-by-Step Deployment

1. **Backup Database**
   ```bash
   pg_dump archon > archon_backup_$(date +%Y%m%d).sql
   ```

2. **Run Migrations**
   ```bash
   cd python
   uv run alembic revision -m "Add Confluence tables and views"
   uv run alembic upgrade head
   ```

3. **Deploy Backend**
   ```bash
   docker compose down
   docker compose up --build -d
   ```

4. **Create Confluence Source**
   - Navigate to Knowledge Base → Add Source
   - Select "Confluence Space"
   - Enter Confluence URL, Space Key, API Token
   - Start initial sync

5. **Monitor Progress**
   - Check Progress tab for sync status
   - Review logs: `docker compose logs -f archon-server`

6. **Verify Search**
   - Test search with Confluence content
   - Verify metadata filters work
   - Check code block extraction

## Expected Outcomes

After full implementation:

- ✅ **4000+ Confluence pages indexed** with full metadata
- ✅ **Hybrid schema** for optimal code reuse (`confluence_pages` + `archon_crawled_pages`)
- ✅ **90% code reuse** - only ~800 lines of new sync logic
- ✅ **Unified search** - one table, no UNION queries, no views needed
- ✅ **CQL-based incremental sync** - only fetches changed pages, no full scans
- ✅ **Atomic chunk updates** - zero-downtime during page updates
- ✅ **Configurable deletion detection** - weekly/immediate/on-demand strategies
- ✅ **Materialized path hierarchy** - fast descendant/sibling/breadcrumb queries
- ✅ **Sync observability** - detailed metrics tracking in metadata
- ✅ **Sub-100ms search performance** with pgvector indexes
- ✅ **Offline capability** after initial sync
- ✅ **Rich metadata filtering** (space, JIRA links, user mentions, code)
- ✅ **Soft delete tracking** for page lifecycle management
- ✅ **Future-proof pattern** for Google Drive, SharePoint, etc.
- ✅ **1.5-2 week implementation** vs 3-4 weeks for separate tables

## Dependencies

Add to `python/pyproject.toml`:
```toml
atlassian-python-api = "^3.41.0"
markdownify = "^0.11.6"
```

## Resources

### Atlassian API Documentation
- [Confluence REST API v2](https://developer.atlassian.com/cloud/confluence/rest/v2/intro/)
- [Confluence CQL](https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/)
- [atlassian-python-api](https://atlassian-python-api.readthedocs.io/)

### Archon Architecture References
- Architecture: `PRPs/ai_docs/ARCHITECTURE.md`
- Current Implementation: `docs/bmad/brownfield-architecture.md`
- Schema Analysis: `docs/bmad/CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md`
- RAG Service: `python/src/server/services/search/rag_service.py`
- Hybrid Search: `python/src/server/services/search/hybrid_search_strategy.py`
- Document Storage: `python/src/server/services/storage/document_storage_service.py`

### Example Confluence Metadata
- `docs/bmad/conf_metadata_example_1.json`
- `docs/bmad/conf_metadata_example_2.json`

---

## Summary: Key Architectural Decisions

### Hybrid Schema (Option 3)

After comprehensive analysis of three database schema options, the **Hybrid approach** was selected as the optimal solution:

**Database Design**:
- `confluence_pages` table: Stores rich metadata (~15 KB per page) + materialized path
- `archon_crawled_pages` table: **REUSED** for chunks (unified storage)
- Link via `metadata->>'page_id'` with indexed lookup

**CQL-Based Incremental Sync**:
- **No full space scans**: Only fetch pages with `lastModified >= last_sync_timestamp`
- **Configurable deletion detection**: Choose weekly reconciliation (default), every sync, or on-demand
- **Atomic chunk updates**: Zero-downtime updates with pending deletion markers
- **Sync observability**: Track metrics (created/updated/deleted/failed/duration) in metadata

**Implementation Impact**:
- **90% code reuse**: Leverage existing chunking, embedding, search services
- **~800 lines of new code**: Only Confluence sync logic
- **1.5-2 weeks timeline**: vs 3-4 weeks for separate tables
- **Unified search**: One table, no UNION queries, no views
- **Future-proof**: Pattern scales to Drive, SharePoint, Notion, etc.

**Key Files to Create**:
1. `python/src/server/services/confluence/confluence_client.py` - API client
2. `python/src/server/services/confluence/confluence_sync_service.py` - Sync orchestration
3. `python/src/server/services/confluence/confluence_processor.py` - HTML→Markdown
4. `python/src/server/api_routes/confluence_api.py` - API endpoints
5. `migration/0.1.0/010_add_confluence_pages.sql` - Database migration

**Key Files to Modify**:
- None! Existing search, storage, and embedding services work as-is

**Pattern for Future Sources**:
```sql
-- Pattern: {source}_metadata table + shared archon_crawled_pages
CREATE TABLE {source}_files (
  file_id TEXT PRIMARY KEY,
  source_id TEXT REFERENCES archon_sources ON DELETE CASCADE,
  metadata JSONB NOT NULL
);

-- Chunks use existing archon_crawled_pages with metadata->>'file_id' link
```

This approach maximizes code reuse, maintains unified search, and provides a clear path for future source integrations.
