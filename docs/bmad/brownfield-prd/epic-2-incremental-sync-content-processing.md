# Epic 2: Incremental Sync & Content Processing

**Epic Goal**: Implement CQL-based incremental sync, HTML to Markdown conversion, and chunk storage reusing existing document processing infrastructure

**Integration Requirements**:
- Must call existing `document_storage_service.add_documents_to_supabase()` for chunking
- Must use existing `ProgressTracker` for sync status updates
- Atomic chunk updates ensure zero-downtime (old chunks searchable during replacement)

## Story 2.1: Implement HTML to Markdown Processor

As a **backend developer**,
I want **to create `ConfluenceProcessor` for converting Confluence HTML to Markdown**,
so that **Confluence content can be chunked and embedded using existing infrastructure**.

**Acceptance Criteria**:
1. File `python/src/server/services/confluence/confluence_processor.py` created
2. Method `async def html_to_markdown(html: str, page_id: str)` converts storage format HTML to Markdown
3. Preserves code blocks with language tags (```python, ```java, etc.)
4. Preserves tables using Markdown table syntax
5. Extracts metadata: JIRA issue links, user mentions, internal page links, external links, asset attachments
6. Returns tuple: (markdown_content: str, metadata: dict)
7. Handles malformed HTML gracefully with error logging

**Integration Verification**:
- IV1: Code blocks from Confluence remain intact after conversion (no line breaks mid-block)
- IV2: JIRA link extraction matches pattern: `[A-Z]+-\d+` (e.g., PROJ-123)
- IV3: Metadata JSONB structure matches `confluence_pages.metadata` schema

## Story 2.2: Implement CQL-Based Incremental Sync Service

As a **backend developer**,
I want **to create `ConfluenceSyncService` with CQL-based incremental sync logic**,
so that **only modified pages are fetched and processed, minimizing API calls**.

**Acceptance Criteria**:
1. File `python/src/server/services/confluence/confluence_sync_service.py` created
2. Method `async def sync_space(source_id: str, space_key: str)` orchestrates full sync
3. CQL query: `space = {space_key} AND lastModified >= "{last_sync_timestamp}"` fetches changed pages
4. Store last_sync_timestamp in `archon_sources.metadata->>'last_sync_timestamp'`
5. For each changed page: call ConfluenceProcessor, store metadata in confluence_pages, call document_storage_service
6. Handle page creates, updates, deletes using version comparison
7. Track sync metrics: pages_added, pages_updated, pages_deleted, duration, api_calls_made

**Integration Verification**:
- IV1: Subsequent syncs only fetch pages modified since last sync (verify CQL query)
- IV2: Existing `document_storage_service.add_documents_to_supabase()` successfully chunks Confluence markdown
- IV3: Sync metrics stored in `archon_sources.metadata->>'sync_metrics'` JSONB field

## Story 2.3: Implement Atomic Chunk Update Strategy

As a **backend developer**,
I want **to implement zero-downtime chunk replacement with atomic updates**,
so that **Confluence content remains searchable during sync updates without gaps**.

**Acceptance Criteria**:
1. Before inserting new chunks: mark old chunks with `metadata->>'_pending_deletion' = 'true'`
2. Insert new chunks from updated page content (via document_storage_service)
3. Delete old chunks WHERE `metadata->>'_pending_deletion' = 'true'` only after new chunks committed
4. Use database transaction to ensure atomicity (all or nothing)
5. On sync failure: rollback marks old chunks as active again (remove _pending_deletion flag)
6. Search queries exclude chunks with `_pending_deletion = 'true'` if new chunks available

**Integration Verification**:
- IV1: During sync, search returns either old or new chunks (never empty results)
- IV2: Failed sync rollback preserves old chunks (content still searchable)
- IV3: Successful sync removes old chunks completely (no orphaned data)

## Story 2.4: Implement Deletion Detection Strategies

As a **backend developer**,
I want **to support configurable deletion detection strategies (weekly, every sync, on-demand)**,
so that **deleted Confluence pages are removed from RAG system without excessive API calls**.

**Acceptance Criteria**:
1. Strategy stored in `archon_sources.metadata->>'deletion_strategy'`: "weekly_reconciliation", "every_sync", "on_demand"
2. **weekly_reconciliation**: Check for deletions once per week (default), store `last_deletion_check` timestamp
3. **every_sync**: Call `get_space_pages_ids()` after each sync, compare with database page_id list
4. **on_demand**: Never check during sync (user manually triggers or notices 404s)
5. Mark deleted pages with `is_deleted = true` in confluence_pages, CASCADE delete chunks
6. Log deletion events with page_id, title, deletion_timestamp

**Integration Verification**:
- IV1: Weekly strategy only calls deletion check API once per 7 days
- IV2: Every_sync strategy detects deletions immediately (within one sync cycle)
- IV3: Deleted page chunks removed from search results after deletion detection

## Story 2.5: Create Confluence API Endpoints

As a **backend developer**,
I want **to create REST API endpoints for Confluence source management and sync**,
so that **frontend can create sources, trigger syncs, and monitor progress**.

**Acceptance Criteria**:
1. File `python/src/server/api_routes/confluence_api.py` created and registered in main.py
2. `POST /api/confluence/sources` - Create Confluence source (body: base_url, api_token, space_key)
3. `GET /api/confluence/sources` - List all Confluence sources with sync status
4. `POST /api/confluence/{source_id}/sync` - Trigger manual sync, returns operation_id
5. `GET /api/confluence/{source_id}/status` - Get sync status via ProgressTracker
6. `DELETE /api/confluence/{source_id}` - Delete source (CASCADE to pages and chunks)
7. `GET /api/confluence/{source_id}/pages` - List pages in space with metadata

**Integration Verification**:
- IV1: Existing `/api/knowledge/*` endpoints remain unchanged and functional
- IV2: Sync operation tracked in `archon_progress` table with operation_type="confluence_sync"
- IV3: API responses follow existing ETag caching pattern for bandwidth optimization

---
