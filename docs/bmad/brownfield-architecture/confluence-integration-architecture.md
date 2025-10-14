# Confluence Integration Architecture

## Overview: Hybrid Schema Approach

**Source:** `docs/bmad/CONFLUENCE_RAG_INTEGRATION.md` (1,333 lines of detailed planning)

The Confluence integration uses a **Hybrid database schema** that combines:
1. Dedicated `confluence_pages` table for rich metadata (~15 KB per page)
2. **REUSE** of existing `archon_crawled_pages` table for chunks (unified storage)
3. Link via `metadata->>'page_id'` with indexed lookup

**Why Hybrid?**
- **90% code reuse**: Leverage existing `document_storage_service.py` and `hybrid_search_strategy.py`
- **Unified search**: ONE table for all chunks (web, Confluence, future sources) - no UNION queries!
- **Clean separation**: Metadata in dedicated table, chunks in shared table
- **Future-proof**: Pattern scales to Google Drive, SharePoint, Notion, etc.
- **Fast implementation**: 1.5-2 weeks vs 3-4 weeks for separate tables

## Data Pipeline Flow (90% Code Reuse!)

```
┌─────────────────┐
│ Confluence API  │
│   (REST v2)     │
└────────┬────────┘
         │
         │ 1. Fetch pages (CQL queries)
         │    CQL: space = DEVDOCS AND lastModified >= "2025-10-01 10:00"
         │    Only changed pages - no full space scans!
         │
         ▼
┌─────────────────────────┐
│ Confluence Sync Service │ (NEW - ~800 lines)
│                         │
│ - CQL-based incremental │
│ - HTML → Markdown       │
│ - Extract metadata      │
│ - Atomic chunk updates  │
└────────┬────────────────┘
         │
         │ 2. Store metadata
         │
         ▼
┌─────────────────┐
│confluence_pages │ ◄─── archon_sources (space metadata)
│  (metadata)     │      {confluence_space_key, last_sync_timestamp,
└────────┬────────┘       total_pages, sync_metrics}
         │
         │ 3. Delete old chunks & Call existing service
         │    DELETE WHERE metadata->>'page_id' = $1
         │    CALL document_storage_service.add_documents_to_supabase()
         │    **REUSE existing chunking/embedding logic!**
         │
         ▼
┌─────────────────────────┐
│ archon_crawled_pages    │ ◄─── EXISTING table (REUSED!)
│ (unified chunks)        │      - Web crawls
│                         │      - Document uploads
│ metadata: {             │      - Confluence pages ✓
│   "page_id": "...",     │      - Future: Drive, SharePoint
│   "section_title": "..."│
│ }                       │
└────────┬────────────────┘
         │
         │ 4. Unified Search (NO VIEW NEEDED!)
         │    Query archon_crawled_pages directly
         │    LEFT JOIN confluence_pages for metadata enrichment
         │
         ▼
┌─────────────────┐
│ Hybrid Search   │ ◄─── EXISTING service (REUSED!)
│  (One table)    │      hybrid_search_strategy.py
└─────────────────┘      **No changes needed for basic search!**
```

## CQL-Based Incremental Sync Strategy

**No full space scans!** Confluence syncs use CQL (Confluence Query Language) to fetch only changed pages:

```python
# Example CQL query
cql = f'space = {space_key} AND lastModified >= "{last_sync_timestamp}"'
changed_pages = confluence_client.cql_search(cql, expand='body.storage,version,ancestors')
```

**Deletion Detection Strategies:**
- `weekly_reconciliation` (default): Check for deletions once per week
- `every_sync`: Check every sync (1 API call per 1000 pages)
- `on_demand`: Never check during sync (user notices 404s)

**Atomic Chunk Updates (Zero Downtime):**
1. Mark old chunks as `_pending_deletion` in metadata
2. Insert new chunks (old chunks still searchable!)
3. Delete old chunks only after success
4. Transaction ensures atomicity

## Implementation Phases (1.5-2 Weeks)

### Phase 1: Database & Basic Sync (Week 1)
- Create `confluence_pages` table (migration 010)
- Implement `ConfluenceClient` using `atlassian-python-api`
- CQL-based incremental sync logic
- HTML → Markdown conversion
- Store metadata with materialized path
- **Call existing `document_storage_service.add_documents_to_supabase()`** ✓

### Phase 2: API & Incremental Sync (Week 1)
- Implement `ConfluenceSyncService` with metrics tracking
- Handle page creates, updates, deletes
- Atomic chunk updates
- API endpoints in `confluence_api.py`
- Use existing `ProgressTracker` for sync status ✓

### Phase 3: Search Integration (Week 2)
- **NO CHANGES to core search!** Already works with `archon_crawled_pages` ✓
- Optional: Add `LEFT JOIN confluence_pages` for metadata enrichment
- Add Confluence-specific filters (space, JIRA links)

### Phase 4: Frontend & Testing (Week 2)
- Create `src/features/confluence/` vertical slice
- Source creation form, sync status, progress display
- Unit tests, integration tests, load testing (4000+ pages)

## Files to Create (~800 lines total)

1. **Backend Services:**
   - `python/src/server/services/confluence/confluence_client.py` (~200 lines)
   - `python/src/server/services/confluence/confluence_sync_service.py` (~400 lines)
   - `python/src/server/services/confluence/confluence_processor.py` (~100 lines)

2. **API Routes:**
   - `python/src/server/api_routes/confluence_api.py` (~100 lines)

3. **Database Migration:**
   - `migration/0.1.0/010_add_confluence_pages.sql` (schema + indexes)

4. **Frontend (future):**
   - `archon-ui-main/src/features/confluence/` (vertical slice)

## Dependencies to Add

```toml
# python/pyproject.toml - Add to [dependency-groups.server]
atlassian-python-api = "^3.41.0"  # Confluence REST API client
markdownify = "^0.11.6"           # HTML to Markdown conversion
```

---
