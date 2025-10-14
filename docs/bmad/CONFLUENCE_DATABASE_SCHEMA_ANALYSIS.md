# Confluence Database Schema Analysis

## Executive Summary

This document analyzes database schema options for integrating Confluence into Archon's RAG system, comparing unified vs dedicated table approaches. It provides a detailed comparison of Confluence API data structures vs web crawling patterns.

**Key Decision**: Should we use existing `archon_crawled_pages` table or create Confluence-specific tables (`conf_pages`, `conf_chunks`)?

---

## Understanding the Data Sources

### Web Crawl Structure

**Entry Point**: Single URL (e.g., `https://docs.python.org/3/`)

**Hierarchy**:
```
Main URL (Starting Point)
  └── Recursive Discovery (depth-based)
      ├── Page 1 (/library/index.html)
      │   ├── Chunk 1
      │   ├── Chunk 2
      │   └── Chunk 3
      ├── Page 2 (/tutorial/index.html)
      │   ├── Chunk 1
      │   └── Chunk 2
      └── Page 3 (/reference/index.html)
          └── ...

Depth Levels:
  - Depth 0: Main URL only
  - Depth 1: Main URL + immediate links
  - Depth 2: Main URL + links + their links
  - Depth N: Recursive up to max depth
```

**Data Flow**:
1. User provides: **1 starting URL** + max depth
2. Crawler discovers: **N pages** by following links
3. Each page chunked into: **M chunks**
4. Storage: **1 source → N pages → M chunks**

**Metadata Characteristics**:
- **Minimal**: URL, title, crawl timestamp
- **No version tracking**: Re-crawl replaces all data
- **No native relationships**: Links discovered during crawl
- **No author/creation date**: Web pages don't expose this
- **No structured hierarchy**: Flat URL-based structure

**Current Database Pattern**:
```sql
-- archon_sources: ONE row per crawl source
INSERT INTO archon_sources (source_id, source_url, metadata)
VALUES (
  'hash_of_url',
  'https://docs.python.org/3/',
  '{"knowledge_type": "web_crawl", "max_depth": 2}'::jsonb
);

-- archon_crawled_pages: MANY rows (all chunks from all discovered pages)
INSERT INTO archon_crawled_pages (url, chunk_number, content, source_id)
VALUES
  ('https://docs.python.org/3/library/index.html', 1, 'chunk 1 content', 'hash_of_url'),
  ('https://docs.python.org/3/library/index.html', 2, 'chunk 2 content', 'hash_of_url'),
  ('https://docs.python.org/3/tutorial/index.html', 1, 'chunk 1 content', 'hash_of_url'),
  ...;
```

### Confluence API Structure

**Entry Point**: Confluence Space (e.g., `NANOVEST`)

**Hierarchy**:
```
Space (NANOVEST)                    ← User selects this as "source"
  ├── Space Metadata
  │   ├── Space Key: "NANOVEST"
  │   ├── Space ID: 294913
  │   └── Space Name: "Nanovest"
  │
  ├── Page 1 (1100808193)           ← Explicit page structure
  │   ├── Page Metadata (15 KB)
  │   │   ├── Version: 29
  │   │   ├── Parent: 948273500
  │   │   ├── Ancestors: [...]      (4 levels deep)
  │   │   ├── JIRA Links: [...]     (60+ issues)
  │   │   ├── User Mentions: [...]  (38 users)
  │   │   ├── Internal Links: [...]
  │   │   └── Asset Links: [...]
  │   └── Chunks
  │       ├── Chunk 1 (500 tokens)
  │       ├── Chunk 2 (750 tokens)
  │       └── Chunk N...
  │
  ├── Page 2 (155254944)
  │   ├── Page Metadata (8 KB)
  │   │   ├── Version: 13
  │   │   ├── Parent: 122323582
  │   │   ├── Children: [115540783]
  │   │   └── Asset Links: [4 attachments]
  │   └── Chunks
  │       ├── Chunk 1
  │       └── Chunk 2
  │
  └── Page N... (1000+ pages in a typical space)
```

**Data Flow**:
1. User provides: **1 Space Key** (e.g., "NANOVEST")
2. Confluence API returns: **Exact list of N pages** in space
3. Each page has: **Rich metadata** (15 KB average)
4. Each page chunked into: **M chunks** (minimal metadata per chunk)
5. Storage: **1 space → N pages → M chunks**

**Metadata Characteristics**:
- **Rich**: 15 KB per page (ancestors, JIRA links, mentions, assets)
- **Version tracking**: Native `version` number for incremental sync
- **Explicit relationships**: Parent/child, ancestors, internal links
- **Author metadata**: Created by, created at, last updated
- **Structured hierarchy**: Tree-based with explicit parent/child

**Key Differences from Web Crawl**:

| Aspect | Web Crawl | Confluence API |
|--------|-----------|----------------|
| **Entry Point** | 1 URL | 1 Space Key |
| **Discovery** | Recursive link following (depth-based) | Explicit page list from API |
| **Page Count** | Unknown until crawl completes | Known upfront from API |
| **Hierarchy** | Implicit (URL paths) | Explicit (parent_id, ancestors) |
| **Metadata per Page** | ~200 bytes (URL, title) | ~15 KB (JIRA, mentions, links, etc.) |
| **Version Tracking** | None (re-crawl replaces all) | Native (`version` field) |
| **Change Detection** | Full re-crawl | Incremental via CQL (`lastModified >= timestamp`) |
| **Relationships** | None (just links in content) | Rich (JIRA issues, user mentions, internal links) |
| **Deletion Tracking** | Not possible (page just 404s) | Explicit (API returns active pages only) |
| **Update Frequency** | Full re-crawl (expensive) | Incremental sync (efficient) |

---

## Storage Comparison: Same Page from Different Sources

**Example**: Documentation page about "Deployment Checklist"

### Web Crawl Storage

```sql
-- archon_sources (1 row)
source_id: "hash_abc123"
source_url: "https://nano-vest.atlassian.net/wiki/spaces/NANOVEST"
metadata: {
  "knowledge_type": "web_crawl",
  "max_depth": 2,
  "crawled_at": "2025-10-06T12:00:00Z"
}

-- archon_crawled_pages (20 rows for 1 page with 20 chunks)
url: "https://nano-vest.atlassian.net/.../1100808193"
chunk_number: 1
content: "Deployment Checklist Release 4.9.0..."
metadata: {
  "title": "Deployment Checklist Release 4.9.0",
  "crawled_at": "2025-10-06T12:00:00Z"
}
source_id: "hash_abc123"
embedding_1536: [0.123, -0.456, ...]

-- Metadata per chunk: ~200 bytes
-- Total for 20 chunks: 20 × 200 bytes = 4 KB
```

**Problem with Web Crawl**:
- No version tracking (can't detect if page changed)
- No JIRA links (JIRA-548, JIRA-421, etc. are just text)
- No user mentions (38 users mentioned are just text)
- No ancestor hierarchy (no parent page context)
- No incremental sync (must re-crawl entire site)

### Confluence API Storage (Current Proposal in CONFLUENCE_RAG_INTEGRATION.md)

```sql
-- archon_sources (1 row for space)
source_id: "conf_space_NANOVEST"
source_url: "https://nano-vest.atlassian.net/wiki/spaces/NANOVEST"
metadata: {
  "source_type": "confluence",
  "space_key": "NANOVEST",
  "space_id": 294913,
  "last_sync_timestamp": "2025-10-06T12:00:00Z",
  "total_pages": 1000
}

-- conf_pages (1 row per page)
id: uuid_page_1
confluence_page_id: "1100808193"
version: 29
title: "Deployment Checklist Release 4.9.0"
space_key: "NANOVEST"
content_markdown: "full page content..."
metadata: {
  "ancestors": [4 pages with titles and URLs],
  "jira_issue_links": [60 JIRA issues with keys and URLs],
  "user_mentions": [38 users with names and profile URLs],
  "internal_links": [1 related page],
  "asset_links": [1 attachment with drive URL],
  "created_by": {...},
  "created_at": "2025-04-12T04:13:57.470Z",
  "last_updated_at": "2025-06-13T12:24:19.563Z",
  "word_count": 7351
}
source_id: "conf_space_NANOVEST"

-- Metadata per page: ~15 KB (stored ONCE)

-- conf_chunks (20 rows for 20 chunks)
page_id: uuid_page_1
chunk_index: 1
chunk_text: "Deployment Checklist Release 4.9.0..."
heading_context: "Pre-deployment Checklist"
has_code: false
page_title: "Deployment Checklist Release 4.9.0"  -- Denormalized
space_key: "NANOVEST"  -- Denormalized
page_url: "https://..."  -- Denormalized
embedding: [0.123, -0.456, ...]

-- Metadata per chunk: ~150 bytes (minimal)
-- Total: 15 KB (page) + 20 × 150 bytes (chunks) = 15 KB + 3 KB = 18 KB
```

**Benefits of Confluence API**:
- ✅ Version tracking enables incremental sync
- ✅ JIRA links queryable (`WHERE jira_issue_links @> '[{"issue_key": "IC-548"}]'`)
- ✅ User mentions searchable (find all pages mentioning a person)
- ✅ Hierarchy navigation (breadcrumbs, parent/child)
- ✅ Change detection (only fetch pages where `version` changed)

---

## Architectural Options Analysis

### Option 1: Fully Unified Schema (Reuse Existing Tables)

**Approach**: Use `archon_sources` + `archon_crawled_pages` for everything

#### Proposed Structure

```sql
-- archon_sources: THREE-TIER pattern
-- Tier 1: Space-level source
INSERT INTO archon_sources (source_id, source_url, metadata)
VALUES (
  'conf_space_NANOVEST',
  'https://nano-vest.atlassian.net/wiki/spaces/NANOVEST',
  '{
    "source_type": "confluence",
    "space_key": "NANOVEST",
    "space_id": 294913,
    "last_sync_timestamp": "2025-10-06T12:00:00Z",
    "total_pages": 1000
  }'::jsonb
);

-- Tier 2: Page-level source (ONE source per page!)
INSERT INTO archon_sources (source_id, source_url, metadata)
VALUES (
  'conf_page_1100808193',
  'https://nano-vest.atlassian.net/.../1100808193',
  '{
    "source_type": "confluence_page",
    "parent_source_id": "conf_space_NANOVEST",
    "page_id": "1100808193",
    "version": 29,
    "space_key": "NANOVEST",

    -- FULL 15 KB metadata stored ONCE in archon_sources
    "ancestors": [...],
    "jira_issue_links": [...],
    "user_mentions": [...],
    ...
  }'::jsonb
);

-- Tier 3: Chunks (existing table)
INSERT INTO archon_crawled_pages (url, chunk_number, content, metadata, source_id)
VALUES (
  'https://nano-vest.atlassian.net/.../1100808193#chunk-1',
  1,
  'chunk content...',
  '{
    "chunk_type": "text",
    "section_title": "Pre-deployment Checklist"
  }'::jsonb,  -- MINIMAL metadata (150 bytes)
  'conf_page_1100808193'  -- FK to page source
);
```

#### Storage Calculation (1000-page space)

```
Space sources:     1 × 5 KB = 5 KB
Page sources:      1000 × 15 KB = 15 MB
Chunks:            20,000 × 150 bytes = 3 MB
─────────────────────────────────────
Total:             18 MB
```

#### Advantages

✅ **Code Reuse (MAJOR WIN)**
- Zero duplication of complex logic:
  - `document_storage_service.py` (chunking, embeddings, parallel batching)
  - `knowledge_item_service.py` (listing, filtering)
  - `source_management_service.py` (deletion with CASCADE)
- Estimated savings: **2000+ lines of code**

✅ **Unified Search**
```python
# ONE query searches EVERYTHING
results = await rag_search("deployment checklist")
# Returns: web docs, Confluence pages, Google Drive (future) - unified!
```

✅ **Future Extensibility**
- Google Drive: Just add `source_type: "google_drive_file"`
- SharePoint: Just add `source_type: "sharepoint_file"`
- **Same pattern** for all sources

✅ **Operational Simplicity**
- One backup strategy
- One set of indexes
- One deletion path (CASCADE already implemented)

✅ **Existing Deletion Works**
```python
# source_management_service.py:401
# Deletes: archon_crawled_pages → archon_code_examples → archon_sources
# Works for Confluence too!
```

#### Disadvantages

⚠️ **Schema Semantics Unclear**
- `archon_sources` originally designed for **1 source = 1 crawl root**
- Now means: **1 source = 1 space OR 1 page**
- Confusion: "Is this a source or a document?"

⚠️ **URL Column Ambiguity**
- Web crawl: `url = https://docs.python.org/library/index.html` (real URL)
- Confluence: `url = https://.../.../1100808193#chunk-1` (synthetic URL)
- What if page doesn't have a web URL? (draft pages, private pages)

⚠️ **Incremental Sync Complexity**
```python
# Need to find page source by Confluence page_id
page_source = await db.fetchrow("""
    SELECT source_id, metadata->>'version' as current_version
    FROM archon_sources
    WHERE metadata->>'source_type' = 'confluence_page'
      AND metadata->>'page_id' = $1
""", confluence_page_id)

# Complex JSON queries for every operation
```

⚠️ **Many Small Sources**
- 1000-page space = **1000 sources** in `archon_sources`
- Original intent: ~10-50 sources (crawl roots)
- UI showing 1000+ sources could be confusing

⚠️ **Deletion Risk**
- Deleting old chunks: `DELETE FROM archon_crawled_pages WHERE source_id = ?`
- Risk: What if URL patterns overlap with web crawl?
- Example: Web crawled a Confluence page + native sync of same page

#### Implementation Complexity

**Moderate** (1.5-2 weeks)
- Reuse existing services ✅
- Need careful JSON metadata queries ⚠️
- Need synthetic URL generation ⚠️

---

### Option 2: Fully Separate Tables (Dedicated Confluence Schema)

**Approach**: Create `conf_pages` + `conf_chunks` tables (as proposed in CONFLUENCE_RAG_INTEGRATION.md)

#### Structure

```sql
-- archon_sources: Space metadata only
INSERT INTO archon_sources (source_id, source_url, metadata)
VALUES (
  'conf_space_NANOVEST',
  'https://nano-vest.atlassian.net/wiki/spaces/NANOVEST',
  '{"source_type": "confluence", "space_key": "NANOVEST", ...}'::jsonb
);

-- conf_pages: ONE row per page (dedicated table)
CREATE TABLE conf_pages (
  id UUID PRIMARY KEY,
  source_id TEXT REFERENCES archon_sources(source_id) ON DELETE CASCADE,
  confluence_page_id TEXT NOT NULL,
  confluence_version INTEGER NOT NULL,
  space_key TEXT NOT NULL,
  title TEXT NOT NULL,
  content_markdown TEXT NOT NULL,

  -- 15 KB metadata stored ONCE per page
  ancestors JSONB,
  jira_issue_links JSONB,
  user_mentions JSONB,
  internal_links JSONB,
  asset_links JSONB,
  created_by JSONB,
  created_at TIMESTAMPTZ,
  last_updated_at TIMESTAMPTZ,

  -- Sync tracking
  is_deleted BOOLEAN DEFAULT FALSE,
  deleted_at TIMESTAMPTZ,

  UNIQUE(source_id, confluence_page_id)
);

-- conf_chunks: MANY rows per page (dedicated table)
CREATE TABLE conf_chunks (
  id UUID PRIMARY KEY,
  page_id UUID REFERENCES conf_pages(id) ON DELETE CASCADE,
  source_id TEXT REFERENCES archon_sources(source_id) ON DELETE CASCADE,

  chunk_text TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  heading_context TEXT,

  embedding vector(1536),

  -- Denormalized for search performance
  page_title TEXT,
  space_key TEXT,
  page_url TEXT,

  has_code BOOLEAN DEFAULT FALSE,
  code_language TEXT
);
```

#### Storage Calculation (1000-page space)

```
Space source:      1 × 5 KB = 5 KB
Page table:        1000 × 15 KB = 15 MB
Chunk table:       20,000 × 150 bytes = 3 MB
─────────────────────────────────────
Total:             18 MB
```

**Same storage as Option 1!** The difference is WHERE the data lives, not HOW MUCH.

#### Advantages

✅ **Clear Semantic Separation**
```sql
-- Crystal clear intent
SELECT * FROM conf_pages WHERE space_key = 'NANOVEST';
SELECT * FROM archon_crawled_pages WHERE source_id = 'web_crawl_123';
-- No confusion!
```

✅ **Optimal Page Metadata Storage**
- `conf_pages` stores 15 KB **once per page** (native columns, not JSONB)
- `conf_chunks` stores minimal metadata (150 bytes)
- Natural relational design

✅ **Incremental Sync is NATURAL**
```python
# Simple, clean queries
async def sync_page(page_data):
    await db.execute("""
        INSERT INTO conf_pages (page_id, version, metadata, ...)
        VALUES ($1, $2, $3, ...)
        ON CONFLICT (page_id) DO UPDATE SET
            version = EXCLUDED.version,
            metadata = EXCLUDED.metadata,
            last_updated_at = NOW()
    """)

    # Delete old chunks (CASCADE handles this!)
    await db.execute("DELETE FROM conf_chunks WHERE page_id = $1", page_id)

    # Insert new chunks
    await insert_chunks(chunks)
```

✅ **Page-Level Operations Are Clean**
```sql
-- Get all chunks for a page with metadata
SELECT c.*, p.metadata as page_metadata
FROM conf_chunks c
JOIN conf_pages p ON c.page_id = p.page_id
WHERE p.confluence_page_id = '1100808193';

-- Delete page and all chunks (CASCADE!)
DELETE FROM conf_pages WHERE confluence_page_id = '1100808193';

-- Find stale pages (incremental sync)
SELECT * FROM conf_pages
WHERE space_key = 'NANOVEST'
  AND is_deleted = false
  AND confluence_page_id NOT IN (
      SELECT id FROM recent_api_response
  );
```

✅ **No URL Ambiguity**
- `conf_chunks` doesn't need a `url` column - uses `page_id` (native)
- `archon_crawled_pages` only has real web URLs
- Clear separation

#### Disadvantages

❌ **Code Duplication (MAJOR COST)**

Must duplicate:
- **Chunking logic** (~300 lines)
- **Embedding generation** (~500 lines - contextual, batch processing)
- **Storage logic** (~800 lines - parallel batches, cancellation, progress)
- **Search logic** (~400 lines - hybrid search, reranking)
- **Deletion logic** (~200 lines)

**Total**: ~2200 lines of duplicated code

**Estimated effort**: 2-3 weeks

❌ **Search Fragmentation**
```python
# Need TWO searches or complex UNION
async def unified_search(query: str):
    # Search web crawl chunks
    web_results = await db.fetch("""
        SELECT *, embedding <=> $1 as distance
        FROM archon_crawled_pages
        ORDER BY distance
        LIMIT 10
    """, query_embedding)

    # Search Confluence chunks
    conf_results = await db.fetch("""
        SELECT *, embedding <=> $1 as distance
        FROM conf_chunks
        ORDER BY distance
        LIMIT 10
    """, query_embedding)

    # How to merge and rank across sources?
    # Need complex ranking algorithm!
    return merge_and_rank(web_results, conf_results)
```

❌ **Maintenance Burden**
- Two sets of vector indexes to monitor
- Two deletion paths to maintain
- Two backup strategies
- Two sets of migration scripts
- **Every improvement** to web crawl chunking must be manually applied to Confluence chunking

❌ **Google Drive = ANOTHER Table?**
```sql
-- drive_files table?
-- drive_chunks table?
-- Now THREE chunk tables to search!
```

As you add sources:
- Confluence: `conf_chunks`
- Google Drive: `drive_chunks`
- SharePoint: `sharepoint_chunks`
- Notion: `notion_chunks`
- **Search complexity grows exponentially**

❌ **MCP Tools Complexity**
```python
@mcp.tool()
async def search_knowledge_base(query: str, source_type: str = "all"):
    if source_type == "confluence":
        return await search_table("conf_chunks", query)
    elif source_type == "web":
        return await search_table("archon_crawled_pages", query)
    elif source_type == "drive":
        return await search_table("drive_chunks", query)
    else:
        # Complex UNION across 3+ tables
        return await search_all_tables(query)
```

#### Implementation Complexity

**High** (3-4 weeks)
- Create new tables and indexes (1 week)
- Duplicate document storage logic (1-2 weeks)
- Implement unified search (UNION queries) (1 week)
- Testing and debugging (ongoing)

---

### Option 3: HYBRID - Single Page Table + Unified Chunks (RECOMMENDED)

**Approach**: Create `confluence_pages` for metadata, reuse `archon_crawled_pages` for chunks

#### Structure

```sql
-- archon_sources: Space metadata
INSERT INTO archon_sources (source_id, source_url, metadata)
VALUES (
  'conf_space_NANOVEST',
  'https://nano-vest.atlassian.net/wiki/spaces/NANOVEST',
  '{
    "source_type": "confluence",
    "space_key": "NANOVEST",
    "last_sync_timestamp": "2025-10-06T12:00:00Z"
  }'::jsonb
);

-- confluence_pages: NEW TABLE for page metadata
CREATE TABLE confluence_pages (
  page_id TEXT PRIMARY KEY,  -- Confluence native ID
  source_id TEXT REFERENCES archon_sources(source_id) ON DELETE CASCADE,

  space_key TEXT NOT NULL,
  title TEXT NOT NULL,
  version INTEGER NOT NULL,
  last_modified TIMESTAMPTZ NOT NULL,
  is_deleted BOOLEAN DEFAULT false,

  -- FULL 15 KB metadata stored ONCE
  metadata JSONB NOT NULL,  -- ancestors, JIRA, mentions, etc.

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- archon_crawled_pages: EXISTING TABLE (reuse!)
-- Link to confluence_pages via metadata
INSERT INTO archon_crawled_pages (url, chunk_number, content, metadata, source_id)
VALUES (
  'confluence://NANOVEST/1100808193/chunk/1',
  1,
  'chunk content...',
  '{
    "page_id": "1100808193",  -- Link back to confluence_pages
    "chunk_type": "text",
    "section_title": "Pre-deployment"
  }'::jsonb,  -- MINIMAL metadata
  'conf_space_NANOVEST'
);
```

#### Storage Calculation (1000-page space)

```
Space source:      1 × 5 KB = 5 KB
Page table:        1000 × 15 KB = 15 MB
Chunk table:       20,000 × 150 bytes = 3 MB
─────────────────────────────────────
Total:             18 MB
```

#### Advantages

✅ **Reuse 90% of Existing Code**
- Use existing `add_documents_to_supabase()` for chunking and embedding
- Use existing search infrastructure
- Only need Confluence-specific sync logic

✅ **Unified Search (Simple!)**
```python
# Search ALL sources with ONE query
results = await rag_search("deployment")
# Works across web, Confluence, future Drive!
```

✅ **Optimal Page Metadata Storage**
- `confluence_pages` stores 15 KB once per page
- `archon_crawled_pages` stores minimal metadata per chunk

✅ **Natural Incremental Sync**
```python
# Clean page version checking
async def sync_page(page):
    existing = await db.fetchrow(
        "SELECT version FROM confluence_pages WHERE page_id = $1",
        page.id
    )

    if existing and existing['version'] == page.version:
        return  # No changes

    # Update page metadata
    await upsert_confluence_page(page)

    # Delete old chunks (simple!)
    await db.execute("""
        DELETE FROM archon_crawled_pages
        WHERE metadata->>'page_id' = $1
    """, page.id)

    # Use existing storage service!
    await add_documents_to_supabase(
        urls=[f"confluence://.../{page.id}/chunk/{i}" for i in range(len(chunks))],
        contents=chunks,
        metadatas=[{"page_id": page.id} for _ in chunks],
        source_id=space_source_id
    )
```

✅ **Clean CASCADE Deletion**
```sql
-- Delete space → deletes pages → deletes chunks
DELETE FROM archon_sources WHERE source_id = 'conf_space_NANOVEST';
-- CASCADE: confluence_pages deleted (FK to sources)
-- CASCADE: archon_crawled_pages deleted (FK to sources)
```

✅ **Extensible for Future Sources**
- Google Drive: Add `drive_files` table + reuse `archon_crawled_pages`
- SharePoint: Add `sharepoint_files` table + reuse `archon_crawled_pages`
- **Pattern**: `{source}_metadata` table + shared `archon_crawled_pages`

#### Disadvantages

⚠️ **Need to Manage Two Tables**
- `confluence_pages` for metadata
- `archon_crawled_pages` for chunks
- JOIN needed for full context

⚠️ **Metadata Link via JSONB**
```sql
-- Need to query by page_id in metadata
SELECT c.*, p.metadata as page_metadata
FROM archon_crawled_pages c
JOIN confluence_pages p ON c.metadata->>'page_id' = p.page_id
WHERE p.page_id = '1100808193';
```

Requires index:
```sql
CREATE INDEX idx_crawled_pages_confluence_page_id
  ON archon_crawled_pages ((metadata->>'page_id'))
  WHERE metadata ? 'page_id';
```

⚠️ **Synthetic URLs**
- Still need to generate `url` for chunks: `confluence://NANOVEST/1100808193/chunk/1`
- Not a "real" URL, just an identifier

#### Implementation Complexity

**Moderate** (1.5-2 weeks)
- Create `confluence_pages` table (1 day)
- Implement Confluence sync service (5 days)
- Adapt existing storage service calls (2 days)
- Add JOIN queries for search results (2 days)
- Testing (ongoing)

---

## Direct Comparison Matrix

| Criteria | Option 1: Fully Unified | Option 2: Fully Separate | Option 3: Hybrid (RECOMMENDED) |
|----------|------------------------|-------------------------|-------------------------------|
| **Code Reuse** | ✅ 100% (0 duplication) | ❌ 0% (2000+ lines duplicated) | ✅ 90% (only sync logic new) |
| **Search Simplicity** | ✅ 1 table query | ❌ UNION across tables | ✅ 1 table query |
| **Metadata Efficiency** | ✅ 18 MB | ✅ 18 MB | ✅ 18 MB |
| **Incremental Sync** | ⚠️ Complex JSON queries | ✅ Natural SQL | ✅ Natural SQL |
| **Schema Clarity** | ❌ Confusing (sources = pages?) | ✅ Clear separation | ✅ Clear separation |
| **Extensibility** | ✅ Same pattern | ❌ New tables per source | ✅ Same pattern |
| **Maintenance** | ✅ One codebase | ❌ Multiple codebases | ✅ One codebase |
| **Development Time** | 1-2 weeks | 3-4 weeks | **1.5-2 weeks** |
| **Storage** | 18 MB | 18 MB | 18 MB |
| **Search Performance** | Fast (1 table) | Moderate (UNION) | Fast (1 table) |
| **Page Operations** | ⚠️ Complex (JSON queries) | ✅ Simple (native SQL) | ✅ Simple (native SQL) |

---

## Recommendation

### **Use Option 3: Hybrid Approach**

#### Why Hybrid Wins

1. **Best of Both Worlds**
   - Optimal metadata storage (dedicated `confluence_pages`)
   - Unified search (reuse `archon_crawled_pages`)
   - Code reuse (90% of existing services)

2. **Clear Path Forward**
   - Google Drive: Add `drive_files` table
   - SharePoint: Add `sharepoint_files` table
   - **Pattern**: Source-specific metadata table + unified chunks table

3. **Reasonable Trade-offs**
   - Small complexity: Need JOIN for full context
   - Acceptable: One index for `metadata->>'page_id'`
   - Manageable: One new table vs rewriting entire storage layer

4. **Development Efficiency**
   - 1.5-2 weeks vs 3-4 weeks (Option 2)
   - Reuse battle-tested embedding/chunking code
   - Focus effort on Confluence-specific sync logic

#### Implementation Steps

1. **Week 1**: Database and Sync Service
   - Create `confluence_pages` table and indexes
   - Implement Confluence API client
   - Implement full sync logic
   - Store pages in `confluence_pages`

2. **Week 2**: Integration and Testing
   - Call existing `add_documents_to_supabase()` for chunks
   - Implement incremental sync (version checking)
   - Add JOIN queries for search results enrichment
   - Write tests

---

## Future Source Integration Pattern

### Google Drive Example

```sql
-- drive_files: Metadata table
CREATE TABLE drive_files (
  file_id TEXT PRIMARY KEY,
  source_id TEXT REFERENCES archon_sources(source_id) ON DELETE CASCADE,

  file_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  version TEXT NOT NULL,
  last_modified TIMESTAMPTZ NOT NULL,
  is_deleted BOOLEAN DEFAULT false,

  -- Rich Drive metadata
  metadata JSONB NOT NULL,  -- owners, shared_with, comments, etc.

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- archon_crawled_pages: REUSE for chunks!
INSERT INTO archon_crawled_pages (url, chunk_number, content, metadata, source_id)
VALUES (
  'drive://folder_id/file_id/chunk/1',
  1,
  'chunk from PDF page 5...',
  '{
    "file_id": "xyz789",
    "mime_type": "application/pdf",
    "page_number": 5
  }'::jsonb,
  'drive_folder_abc123'
);
```

**Pattern**: `{source}_files` for metadata + `archon_crawled_pages` for chunks

**Benefits**:
- Same chunking/embedding logic
- Same search infrastructure
- Add new sources without touching existing code

---

## Conclusion

**Recommended Architecture**: **Hybrid Approach (Option 3)**

**Key Decision Factors**:
1. Confluence has **explicit Space → Page hierarchy** (not recursive crawl like web)
2. Confluence pages have **rich metadata** (15 KB) that should be stored once
3. Code reuse is **critical** for maintainability
4. Unified search is **non-negotiable** for user experience

**Next Steps**:
1. Update CONFLUENCE_RAG_INTEGRATION.md with hybrid architecture
2. Create migration for `confluence_pages` table
3. Implement Confluence sync service
4. Test incremental sync with version tracking

**Storage Efficiency**: All 3 options use **~18 MB for 1000 pages** - same storage, different organization.

**Development Effort**: Hybrid = **1.5-2 weeks** vs Separate = 3-4 weeks vs Unified = 1-2 weeks

**Long-term Maintenance**: Hybrid wins due to code reuse + clear schema separation.
