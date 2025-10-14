# Requirements

## Functional Requirements

**FR1**: The system shall support creating Confluence source configurations via `/api/confluence/sources` endpoint, requiring Confluence Cloud URL, API token, and space key

**FR2**: The system shall perform CQL-based incremental syncs fetching only pages modified since last sync timestamp using query pattern: `space = {space_key} AND lastModified >= "{last_sync_timestamp}"`

**FR3**: The system shall convert Confluence HTML storage format to Markdown while preserving code blocks, tables, and formatting using `markdownify` library

**FR4**: The system shall store Confluence page metadata (space key, title, version, hierarchy path, JIRA links, user mentions) in dedicated `confluence_pages` table with materialized path supporting unlimited nesting depth (no max level constraint), accommodating deep hierarchies of 7+ levels

**FR5**: The system shall chunk Confluence Markdown content using existing `document_storage_service.add_documents_to_supabase()` method, reusing 90% of document processing infrastructure

**FR6**: The system shall store Confluence chunks in existing unified `archon_crawled_pages` table with `metadata->>'page_id'` link to `confluence_pages` table

**FR7**: The system shall support searching Confluence content through existing hybrid search strategy with mandatory LEFT JOIN to `confluence_pages` for metadata enrichment, enabling filters on space key, JIRA links, user mentions, and hierarchy path

**FR8**: The system shall track sync progress using existing `ProgressTracker` service with operation type `confluence_sync` and real-time status updates

**FR9**: The system shall detect deleted Confluence pages using configurable strategies: `weekly_reconciliation` (default), `every_sync`, or `on_demand`

**FR10**: The system shall perform atomic chunk updates with zero-downtime pattern: mark old chunks as `_pending_deletion`, insert new chunks, delete old chunks only after success

**FR11**: The system shall extract and index rich metadata including JIRA issue links, user mentions, internal page links, external links, and asset attachments

**FR12**: The system shall support manual sync triggers via `POST /api/confluence/{id}/sync` endpoint and retrieve sync status via `GET /api/confluence/{id}/status`

**FR13**: The system shall implement CASCADE DELETE from `archon_sources` → `confluence_pages` → `archon_crawled_pages` ensuring complete cleanup on source removal

**FR14**: The system shall expose Confluence metadata search capabilities including filtering by space key, JIRA issue links (`metadata->'jira_issue_links'`), user mentions (`metadata->'user_mentions'`), and hierarchical path queries using materialized path pattern matching

## Non-Functional Requirements

**NFR1**: Confluence sync operations shall complete for 4000+ pages within 15 minutes maximum, with progress updates every 50 pages processed

**NFR2**: Search response times shall remain under 500ms for sub-second user experience, maintaining existing performance characteristics

**NFR3**: The system shall support multi-provider embeddings (OpenAI text-embedding-3-small/large, Google gemini-embedding-001, Ollama local models) for Confluence chunks identical to existing document sources

**NFR4**: Memory usage during Confluence sync shall not exceed 20% increase over baseline system memory consumption

**NFR5**: The implementation shall achieve 90% code reuse from existing services (`document_storage_service.py`, `hybrid_search_strategy.py`, `progress_tracker.py`)

**NFR6**: New Confluence-specific code shall total approximately 800 lines distributed across: `confluence_client.py` (~200), `confluence_sync_service.py` (~400), `confluence_processor.py` (~100), `confluence_api.py` (~100)

**NFR7**: Database queries shall utilize optimized indexes on `confluence_pages` (source, space, path with `text_pattern_ops`, GIN JSONB for jira_issue_links and user_mentions) and `archon_crawled_pages` (ivfflat vector, GIN full-text, page_id lookup) to support metadata-driven search filtering

**NFR8**: The system shall handle API rate limits gracefully with exponential backoff retry logic (max 3 retries, 1s/2s/4s delays)

## Compatibility Requirements

**CR1 - Existing API Compatibility**: All existing knowledge base APIs (`/api/knowledge/*`) shall remain unchanged and fully functional; Confluence integration adds new `/api/confluence/*` endpoints without modifying existing routes

**CR2 - Database Schema Compatibility**: Existing `archon_crawled_pages`, `archon_sources`, `archon_code_examples` tables shall remain unchanged; migration 010 adds new `confluence_pages` table only, preserving existing web crawl and document upload functionality

**CR3 - UI/UX Consistency**: Confluence source management UI shall follow existing vertical slice architecture in `archon-ui-main/src/features/confluence/` matching patterns from `features/knowledge/`, using identical TanStack Query hooks, Radix UI primitives, and Tron-inspired glassmorphism styling

**CR4 - Integration Compatibility (Phased)**:
- **Phase 1**: MCP server tools (`archon:rag_search_knowledge_base`, `archon:rag_search_code_examples`) shall support basic Confluence search via unified `archon_crawled_pages` storage
- **Phase 2**: Enhanced search with metadata filters (space, JIRA, mentions) via `confluence_pages` JOIN

---
