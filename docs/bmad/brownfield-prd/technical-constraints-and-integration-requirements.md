# Technical Constraints and Integration Requirements

## Existing Technology Stack

**Languages**: Python 3.12 (backend), TypeScript 5 (frontend)

**Frameworks**:
- Backend: FastAPI 0.104+, crawl4ai 0.6.2 (web crawler)
- Frontend: React 18, Vite (build tool), TanStack Query v5 (state management)

**Database**:
- PostgreSQL 15+ via Supabase (cloud or local)
- pgvector 0.5+ extension (1536-dimensional embeddings)
- asyncpg 0.29+ and Supabase SDK 2.15.1 for database access

**Infrastructure**:
- Docker Compose for service orchestration
- uv package manager (Python), npm (frontend)
- Makefile for developer workflow shortcuts

**External Dependencies**:
- **LLM Providers**: OpenAI SDK 1.71.0 (universal client for OpenAI, Google, Ollama, Anthropic, Grok, OpenRouter)
- **Document Processing**: PyPDF2, pdfplumber, python-docx (basic extraction, no Docling)
- **New for Confluence**: `atlassian-python-api` 3.41.0, `markdownify` 0.11.6

## Integration Approach

**Database Integration Strategy**:
- Migration 010 creates `confluence_pages` table with foreign key to `archon_sources(source_id)` CASCADE DELETE
- Reuse existing `archon_crawled_pages` table for chunk storage (no schema changes)
- Link chunks to pages via indexed `metadata->>'page_id'` JSONB path expression
- JSONB metadata column stores rich Confluence metadata (~15KB per page) with GIN indexes for JIRA links and user mentions

**API Integration Strategy**:
- New API router: `python/src/server/api_routes/confluence_api.py` registered in `main.py`
- RESTful endpoints follow existing pattern: `/api/confluence/sources`, `/api/confluence/{id}/sync`
- Reuse existing `ProgressTracker` for sync status (no new progress infrastructure)
- Leverage FastAPI dependency injection for Supabase client and configuration

**Frontend Integration Strategy**:
- Vertical slice: `archon-ui-main/src/features/confluence/` (components, hooks, services, types)
- Service client: `confluenceService.ts` uses shared `apiClient.ts` with ETag support
- Query hooks: `useConfluenceQueries.ts` follows standardized query key factory pattern
- UI components: Reuse Radix UI primitives from `features/ui/primitives/`
- State management: TanStack Query only (no Redux, no Zustand)

**Testing Integration Strategy**:
- Backend: Pytest tests in `python/tests/server/services/confluence/`
- Frontend: Vitest + React Testing Library in `archon-ui-main/src/features/confluence/tests/`
- Integration tests: End-to-end sync with mock Confluence API responses
- Load testing: Validate 4000+ page sync performance

## Code Organization and Standards

**File Structure Approach**:
```
python/src/server/
├── services/confluence/          # NEW directory
│   ├── __init__.py
│   ├── confluence_client.py      # Atlassian API wrapper
│   ├── confluence_sync_service.py # Sync orchestration
│   └── confluence_processor.py   # HTML→Markdown conversion
├── api_routes/
│   └── confluence_api.py         # NEW router
└── services/knowledge/
    └── knowledge_item_service.py # MODIFY: add 'confluence' type

migration/0.1.0/
└── 010_add_confluence_pages.sql  # NEW migration

archon-ui-main/src/features/
└── confluence/                   # NEW vertical slice
    ├── components/
    ├── hooks/
    ├── services/
    └── types/
```

**Naming Conventions**:
- Service methods: `async def sync_confluence_space()`, `async def get_page_metadata()`
- API endpoints: `/api/confluence/sources` (plural), `/api/confluence/{source_id}/sync` (action)
- Query keys: `confluenceKeys.all`, `confluenceKeys.lists()`, `confluenceKeys.detail(id)`
- Components: `ConfluenceSourceCard.tsx`, `ConfluenceSyncStatus.tsx`

**Coding Standards**:
- Backend: Python 3.12 with type hints, 120 char line length, Ruff linting, MyPy type checking
- Frontend: TypeScript strict mode, Biome for features/ (120 char, double quotes), ESLint for legacy
- Direct SQL (no ORM), manual migration scripts with checksum tracking
- Async-first: All I/O operations use async/await patterns

**Documentation Standards**:
- Docstrings: Google style for all public functions
- Inline comments: Explain "why" not "what" for complex logic
- API documentation: FastAPI auto-generates OpenAPI schema
- Architecture docs: Update `brownfield-architecture.md` post-implementation

## Deployment and Operations

**Build Process Integration**:
- Backend: Docker multi-stage build in `docker-compose.yml` (no changes needed)
- Frontend: Vite build process unchanged, proxies to backend during dev
- Migration: Run `010_add_confluence_pages.sql` before deploying new code
- Dependencies: Add `atlassian-python-api` and `markdownify` to `pyproject.toml`

**Deployment Strategy**:
- Development: `make dev` (hybrid mode: backend Docker, frontend local)
- Production: `docker compose up --build -d` (all services containerized)
- Migration execution: Manual SQL via Supabase dashboard or `psql` (no Alembic)
- Rollback: Revert migration 010 by dropping `confluence_pages` table (chunks auto-cleanup via CASCADE)

**Monitoring and Logging**:
- Sync progress: Tracked in `archon_progress` table, exposed via `GET /api/progress/{operation_id}`
- Error logging: Python `logging` module with `exc_info=True` for stack traces
- Performance metrics: Store in `archon_sources.metadata->>'sync_metrics'` JSONB field
- Frontend monitoring: Browser console errors, React error boundaries for UI crashes

**Configuration Management**:
- Environment variables: `CONFLUENCE_API_TOKEN`, `CONFLUENCE_BASE_URL` (optional default per source)
- Settings storage: Encrypted API tokens in `archon_settings` table (bcrypt-hashed)
- Feature flags: Confluence deletion detection strategy stored in source metadata
- Version tracking: Migration 010 recorded in `archon_migrations` table with checksum

## Risk Assessment and Mitigation

**Technical Risks**:
- **Risk**: Confluence API rate limits (standard: 10 req/sec, 100,000 req/day) could throttle 4000+ page syncs
  - **Mitigation**: Implement exponential backoff (1s/2s/4s), batch API calls (1000 pages per CQL query), cache page IDs for deletion detection

- **Risk**: Large page content (75KB+ HTML) could exceed chunking service memory limits
  - **Mitigation**: Stream processing for large pages, configurable chunk size limits, monitor memory usage with alerts

- **Risk**: Materialized path queries on deep hierarchies (7+ levels) could cause slow full-table scans
  - **Mitigation**: Use `text_pattern_ops` index for prefix matching, limit path depth display in UI to 5 levels with "..." truncation

**Integration Risks**:
- **Risk**: Existing `hybrid_search_strategy.py` LEFT JOIN could degrade search performance with 4000+ Confluence pages
  - **Mitigation**: Benchmark query performance pre/post-implementation, add composite indexes if needed, consider view materialization

- **Risk**: Unified `archon_crawled_pages` table mixing web/upload/Confluence chunks could cause query plan issues
  - **Mitigation**: Partial indexes on `source_id` for each type, monitor query execution plans, prepared statements for common queries

- **Risk**: Frontend TanStack Query cache could grow excessively with 4000+ page metadata
  - **Mitigation**: Use pagination for page lists, aggressive garbage collection (10min), stale time tuning per query type

**Deployment Risks**:
- **Risk**: Migration 010 could fail on production database with existing load
  - **Mitigation**: Test migration on production clone, run during low-traffic window, prepare rollback script

- **Risk**: New dependencies (`atlassian-python-api`, `markdownify`) could have security vulnerabilities
  - **Mitigation**: Pin exact versions in `pyproject.toml`, run `uv sync --locked`, security audit with `pip-audit`

**Mitigation Strategies**:
- **Pre-deployment**: Load test with 4000+ page mock dataset, chaos engineering for API failures
- **Deployment**: Blue-green deployment with feature flag (disable Confluence tab until fully validated)
- **Post-deployment**: Monitor sync duration metrics, set alerts for >15min syncs or memory spikes >20%
- **Rollback plan**: Drop `confluence_pages` table, remove Confluence UI tab, revert to previous Docker image

---
