# Enhancement Impact Analysis: Confluence Integration

## Summary

**Goal:** Integrate 4000+ Confluence Cloud pages into Archon's RAG system for code implementation assistance and documentation generation.

**Approach:** Direct Confluence API integration with Hybrid database schema (Option 3 from `CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md`).

**Timeline:** 1.5-2 weeks implementation (vs 3-4 weeks for separate tables approach).

**Code Reuse:** 90% - Leverage existing `document_storage_service.py` and `hybrid_search_strategy.py`.

## Required Changes

### Backend Files to CREATE (~800 lines total)

1. **`python/src/server/services/confluence/confluence_client.py`** (~200 lines)
   - Authenticate with Confluence API using `atlassian-python-api`
   - Implement CQL search for incremental sync
   - Lightweight page ID fetching for deletion detection

2. **`python/src/server/services/confluence/confluence_sync_service.py`** (~400 lines)
   - CQL-based incremental sync (fetch only changed pages)
   - Handle page creates, updates, deletes
   - Atomic chunk update strategy (zero-downtime)
   - Sync observability (metrics tracking in `archon_sources.metadata`)
   - Build materialized path for hierarchy queries

3. **`python/src/server/services/confluence/confluence_processor.py`** (~100 lines)
   - HTML to Markdown conversion using `markdownify`
   - Extract rich metadata (JIRA links, user mentions, internal/external links)
   - Build metadata JSONB structure

4. **`python/src/server/api_routes/confluence_api.py`** (~100 lines)
   - `POST /api/confluence/sources` - Create Confluence source
   - `GET /api/confluence/sources` - List sources
   - `POST /api/confluence/{id}/sync` - Trigger sync
   - `GET /api/confluence/{id}/status` - Get sync status
   - `DELETE /api/confluence/{id}` - Delete source (CASCADE)
   - `GET /api/confluence/{id}/pages` - List pages in space

### Backend Files to MODIFY (Minimal Changes)

1. **`python/src/server/services/knowledge/knowledge_item_service.py`**
   - Add `'confluence'` to supported source types
   - Register Confluence spaces in `archon_sources` table

2. **`python/src/server/services/search/hybrid_search_strategy.py`** (OPTIONAL)
   - Add `LEFT JOIN confluence_pages` for metadata enrichment
   - Add Confluence-specific filters (space, JIRA links, user mentions)
   - **Core search already works without changes!**

### Database Changes

**Migration File:** `migration/0.1.0/010_add_confluence_pages.sql`

```sql
-- Create confluence_pages table (see Data Models section for full schema)
CREATE TABLE confluence_pages (...);

-- Create performance indexes
CREATE INDEX idx_confluence_pages_source ON confluence_pages(...);
CREATE INDEX idx_confluence_pages_space ON confluence_pages(...);
CREATE INDEX idx_confluence_pages_path ON confluence_pages(...);
CREATE INDEX idx_confluence_pages_jira ON confluence_pages(...);

-- Link chunks to pages
CREATE INDEX idx_crawled_pages_confluence_page_id ON archon_crawled_pages(...);
```

**No changes to `archon_crawled_pages`** - already supports Confluence chunks via `metadata->>'page_id'`!

### Frontend Files to CREATE (Future Phase)

**Vertical Slice:** `archon-ui-main/src/features/confluence/`

1. **`services/confluenceService.ts`** - API client
2. **`hooks/useConfluenceQueries.ts`** - Query hooks & keys
3. **`components/ConfluenceSourceForm.tsx`** - Source creation form
4. **`components/ConfluenceSourceCard.tsx`** - Source display card
5. **`components/ConfluenceSyncStatus.tsx`** - Sync status & progress
6. **`types/index.ts`** - TypeScript types

### Dependencies to Add

```toml
# python/pyproject.toml
[dependency-groups.server]
# Add these two lines:
atlassian-python-api = "^3.41.0"  # Confluence REST API client
markdownify = "^0.11.6"           # HTML to Markdown conversion
```

## Implementation Workflow

**Week 1: Database & Sync Logic**
1. Create migration 010 (Confluence tables)
2. Implement `ConfluenceClient` (API integration)
3. Implement `ConfluenceSyncService` (CQL-based sync)
4. Implement `ConfluenceProcessor` (HTML → Markdown)
5. **Call existing `document_storage_service.add_documents_to_supabase()`** ✓

**Week 2: API & Frontend**
6. Create `confluence_api.py` (REST endpoints)
7. Create frontend vertical slice in `features/confluence/`
8. Write unit tests, integration tests
9. Load test with 4000+ pages

## Code Reuse Highlights

**Existing Service:** `document_storage_service.add_documents_to_supabase()`
```python
# Confluence sync service calls existing function!
await add_documents_to_supabase(
    urls=[f"confluence://{space_key}/{page_id}"],
    contents=[content_markdown],
    metadatas=[{"page_id": page_id, "section_title": "..."}],
    source_id=source_id
)
# That's it! Existing service handles:
# - Section-aware chunking
# - Code block detection & preservation
# - Embedding generation (multi-provider)
# - Progress tracking
# - Batch processing
# - Storage in archon_crawled_pages
```

**Existing Service:** `hybrid_search_strategy.py`
```python
# Already searches archon_crawled_pages!
# No changes needed for basic Confluence search
# Optional: Add LEFT JOIN confluence_pages for metadata
```

**Existing Service:** `progress_tracker.py`
```python
# Reuse for Confluence sync status
progress = ProgressTracker(operation_id, operation_type="confluence_sync")
await progress.update(status="syncing", progress=50, log="Synced 50 pages")
await progress.complete(log="Sync completed successfully")
```

## Reference Documentation

All comprehensive planning completed - ready for implementation!

- **Main Guide:** `docs/bmad/CONFLUENCE_RAG_INTEGRATION.md` (1,333 lines)
  - Hybrid schema rationale
  - CQL-based incremental sync strategy
  - Deletion detection strategies
  - Atomic chunk update pattern
  - Search integration
  - Performance optimization
  - Testing strategy

- **Schema Analysis:** `docs/bmad/CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md`
  - Comparison of 3 database schema options
  - Why Hybrid Schema was selected

- **Example Metadata:** `docs/bmad/conf_metadata_example_*.json`
  - Real Confluence page metadata samples

---
