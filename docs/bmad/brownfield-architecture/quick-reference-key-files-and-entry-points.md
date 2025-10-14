# Quick Reference - Key Files and Entry Points

## Critical Files for Understanding the System

### Backend Core
- **Main Entry**: `python/src/server/main.py` - FastAPI application with lifespan management
- **Configuration**: `.env.example`, `python/src/server/config/`
- **Core Business Logic**: `python/src/server/services/`
- **API Definitions**: `python/src/server/api_routes/`

### Knowledge Base & RAG
- **Knowledge Management**: `python/src/server/services/knowledge/knowledge_item_service.py`
- **Document Storage**: `python/src/server/services/storage/document_storage_service.py`
- **Hybrid Search**: `python/src/server/services/search/hybrid_search_strategy.py`
- **LLM Providers**: `python/src/server/services/llm_provider_service.py`
- **Embeddings**: `python/src/server/services/embeddings/embedding_service.py`

### Database & Migrations
- **Schema**: `migration/complete_setup.sql` - Complete database schema (no ORM models!)
- **Migration Tracking**: `python/src/server/services/migration_service.py`
- **Migration Files**: `migration/0.1.0/` (001-009 migrations)

### Frontend Architecture
- **Features Directory**: `archon-ui-main/src/features/` - Vertical slice architecture
- **Query Client**: `archon-ui-main/src/features/shared/config/queryClient.ts`
- **API Client**: `archon-ui-main/src/features/shared/api/apiClient.ts`

## Files Relevant to Confluence Integration

### Existing Infrastructure (90% Code Reuse!)
- **Document Storage Service**: `python/src/server/services/storage/document_storage_service.py`
  - `add_documents_to_supabase()` - **REUSE THIS** for chunking and embeddings
  - Handles chunking, code detection, embedding generation, progress tracking

- **Hybrid Search Strategy**: `python/src/server/services/search/hybrid_search_strategy.py`
  - **ALREADY searches `archon_crawled_pages`** - works with Confluence chunks out of the box!

- **Progress Tracking**: `python/src/server/services/progress_tracker.py`
  - **REUSE THIS** for sync status updates

### Files to CREATE for Confluence (New ~800 lines)
- `python/src/server/services/confluence/confluence_client.py` - Atlassian API client
- `python/src/server/services/confluence/confluence_sync_service.py` - CQL-based sync logic
- `python/src/server/services/confluence/confluence_processor.py` - HTML → Markdown conversion
- `python/src/server/api_routes/confluence_api.py` - REST endpoints
- `migration/0.1.0/010_add_confluence_pages.sql` - Database migration

### Files to MODIFY (Minimal Changes)
- `python/src/server/services/knowledge/knowledge_item_service.py` - Add 'confluence' source type
- Optional: `python/src/server/services/search/hybrid_search_strategy.py` - Add Confluence metadata JOIN

---
