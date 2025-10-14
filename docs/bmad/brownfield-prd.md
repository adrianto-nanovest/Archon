# Archon Brownfield Enhancement PRD

## Intro Project Analysis and Context

### Existing Project Overview

#### Analysis Source
**IDE-based fresh analysis** - Using the comprehensive brownfield architecture document at `docs/bmad/brownfield-architecture.md`

#### Current Project State

**Archon** is a microservices-based RAG (Retrieval Augmented Generation) system designed for knowledge base management and task tracking for AI coding assistants.

**Current Version**: 0.1.0
**Architecture**: Monolithic repository with Docker orchestration for three distinct services:
- **Server** (port 8181): Main backend with FastAPI, handles knowledge base, projects, tasks, settings
- **MCP Server** (port 8051): Model Context Protocol server for IDE integration
- **Agents Service** (port 8052): AI agents service using PydanticAI

**Core Capabilities**:
- Multi-LLM provider orchestration (OpenAI, Google, Ollama, Anthropic, Grok, OpenRouter)
- Document ingestion pipeline with chunking and embeddings
- Hybrid search with vector similarity + keyword + reranking
- Web crawling with domain filtering
- Project and task management (optional feature)
- Migration tracking and version checking system

### Available Documentation Analysis

✅ **Document-project analysis available** - Using existing technical documentation from `brownfield-architecture.md`

**Key Documents Available**:
- ✅ **Tech Stack Documentation** - Comprehensive tech stack table in architecture doc
- ✅ **Source Tree/Architecture** - Complete project structure and module organization
- ✅ **API Documentation** - All API endpoints documented with examples
- ✅ **External API Documentation** - LLM providers, Supabase, GitHub API integration details
- ✅ **Technical Debt Documentation** - Known issues, incomplete features, architecture constraints
- ✅ **Coding Standards** - References to CLAUDE.md, PRPs/ai_docs pattern guides
- ✅ **Database Schema** - Complete SQL schema with migration tracking

### Enhancement Scope Definition

#### Enhancement Type
✅ **Integration with New Systems** - Confluence Cloud integration for RAG system

#### Enhancement Description
Integrate 4000+ Confluence Cloud pages into Archon's RAG system using Direct Confluence API approach (not Google Drive intermediary). Implementation uses Hybrid Database Schema with dedicated `confluence_pages` metadata table + unified `archon_crawled_pages` chunks, leveraging 90% code reuse from existing infrastructure.

#### Impact Assessment
✅ **Moderate Impact (some existing code changes)**
- New Confluence-specific services (~800 lines)
- Minimal modifications to existing knowledge service
- Database migration for new tables
- 90% code reuse of existing document storage and search infrastructure

### Goals and Background Context

#### Goals
- Enable RAG-powered search across 4000+ Confluence Cloud documentation pages
- Provide code implementation assistance using internal documentation
- Support automated documentation generation from Confluence knowledge base
- Maintain sub-second search response times with efficient incremental sync
- Preserve existing web crawl and document upload functionality

#### Background Context

The Archon system currently supports web crawling and document uploads for knowledge base ingestion. However, the primary internal documentation lives in Confluence Cloud (4000+ pages), which is not efficiently accessible to the RAG system. Manual exports or Google Drive intermediary approaches were considered but rejected in favor of direct Confluence API integration.

The enhancement leverages extensive planning (1,333 lines in `CONFLUENCE_RAG_INTEGRATION.md`) and architectural analysis that identified a Hybrid Schema approach, enabling 90% code reuse and 1.5-2 week implementation timeline versus 3-4 weeks for alternative approaches.

### Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial PRD Draft | 2025-10-07 | 1.0 | Created brownfield PRD for Confluence integration based on architecture v3.0 | John (PM) |

---

## Requirements

### Functional Requirements

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

### Non-Functional Requirements

**NFR1**: Confluence sync operations shall complete for 4000+ pages within 15 minutes maximum, with progress updates every 50 pages processed

**NFR2**: Search response times shall remain under 500ms for sub-second user experience, maintaining existing performance characteristics

**NFR3**: The system shall support multi-provider embeddings (OpenAI text-embedding-3-small/large, Google gemini-embedding-001, Ollama local models) for Confluence chunks identical to existing document sources

**NFR4**: Memory usage during Confluence sync shall not exceed 20% increase over baseline system memory consumption

**NFR5**: The implementation shall achieve 90% code reuse from existing services (`document_storage_service.py`, `hybrid_search_strategy.py`, `progress_tracker.py`)

**NFR6**: New Confluence-specific code shall total approximately 800 lines distributed across: `confluence_client.py` (~200), `confluence_sync_service.py` (~400), `confluence_processor.py` (~100), `confluence_api.py` (~100)

**NFR7**: Database queries shall utilize optimized indexes on `confluence_pages` (source, space, path with `text_pattern_ops`, GIN JSONB for jira_issue_links and user_mentions) and `archon_crawled_pages` (ivfflat vector, GIN full-text, page_id lookup) to support metadata-driven search filtering

**NFR8**: The system shall handle API rate limits gracefully with exponential backoff retry logic (max 3 retries, 1s/2s/4s delays)

### Compatibility Requirements

**CR1 - Existing API Compatibility**: All existing knowledge base APIs (`/api/knowledge/*`) shall remain unchanged and fully functional; Confluence integration adds new `/api/confluence/*` endpoints without modifying existing routes

**CR2 - Database Schema Compatibility**: Existing `archon_crawled_pages`, `archon_sources`, `archon_code_examples` tables shall remain unchanged; migration 010 adds new `confluence_pages` table only, preserving existing web crawl and document upload functionality

**CR3 - UI/UX Consistency**: Confluence source management UI shall follow existing vertical slice architecture in `archon-ui-main/src/features/confluence/` matching patterns from `features/knowledge/`, using identical TanStack Query hooks, Radix UI primitives, and Tron-inspired glassmorphism styling

**CR4 - Integration Compatibility (Phased)**:
- **Phase 1**: MCP server tools (`archon:rag_search_knowledge_base`, `archon:rag_search_code_examples`) shall support basic Confluence search via unified `archon_crawled_pages` storage
- **Phase 2**: Enhanced search with metadata filters (space, JIRA, mentions) via `confluence_pages` JOIN

---

## User Interface Enhancement Goals

### Integration with Existing UI

The Confluence feature UI will follow Archon's **vertical slice architecture** pattern established in `archon-ui-main/src/features/`. All components will be housed in a new `src/features/confluence/` directory, maintaining complete feature independence while adhering to established design patterns.

**Consistency Requirements:**
- **TanStack Query v5**: All data fetching via query hooks (`useConfluenceQueries.ts`) with standardized stale times from `shared/config/queryPatterns.ts`
- **Radix UI Primitives**: Reuse existing primitives from `features/ui/primitives/` (Dialog, Select, Button, Progress, Badge)
- **Tron-Inspired Glassmorphism**: Match existing styling with cyan/blue accent colors, backdrop blur effects, and subtle animations
- **Smart Polling**: Sync status updates using `useSmartPolling` hook for visibility-aware refresh intervals
- **Optimistic Updates**: Source creation/deletion using `createOptimisticEntity` and `replaceOptimisticEntity` patterns from `shared/utils/optimistic.ts`

### Modified/New Screens and Views

**New: Confluence Source Management Panel** (`/knowledge` page extension)
- Add "Confluence" tab alongside existing "Web Crawl" and "Document Upload" tabs
- Source configuration form with fields: Confluence URL, API Token (encrypted), Space Key
- Source card display showing space metadata, last sync timestamp, page count
- Sync status indicator with progress bar (leveraging existing ProgressTracker visualization)

**Modified: Knowledge Base Search Results** (`/knowledge` page)
- Enhance result cards with Confluence-specific metadata badges:
  - Space key tag (e.g., "DEVDOCS")
  - JIRA issue links (clickable chips)
  - Page hierarchy breadcrumbs using materialized path
- Filter sidebar additions:
  - "Source Type" filter: Web, Upload, **Confluence** (new)
  - "Confluence Space" multi-select dropdown
  - "Contains JIRA Links" boolean toggle

**New: Confluence Sync History Modal**
- Accessible from source card "View Sync History" action
- Table displaying: Sync timestamp, Pages added/updated/deleted, Duration, Status
- Error logs for failed syncs with retry button

**Modified: Settings Page** (`/settings`)
- Add "Confluence Integration" section in "Knowledge Base" settings category
- Deletion detection strategy selector: Weekly reconciliation, Every sync, On-demand
- Sync schedule configuration (future: automated periodic sync)

### UI Consistency Requirements

**Visual Design:**
- Match existing knowledge source card layout (thumbnail area, metadata section, action buttons)
- Use consistent color coding: Cyan for Confluence (distinct from blue for web, green for uploads)
- Maintain 16px padding, 8px gap spacing, 4px border radius standards

**Interaction Patterns:**
- Source creation follows existing modal workflow (Create → Configure → Sync trigger)
- Deletion requires confirmation dialog matching existing "Delete Source" pattern
- Sync progress displays in existing global progress notification area (top-right)

**Accessibility:**
- All new components use Radix UI primitives ensuring ARIA compliance
- Keyboard navigation support for Confluence-specific filters
- Screen reader announcements for sync status changes

**Error Handling:**
- API errors display using existing toast notification system (`features/ui/hooks/useToast.ts`)
- Network failures show retry mechanism with exponential backoff feedback
- Validation errors inline on form fields (Confluence URL format, API token)

---

## Technical Constraints and Integration Requirements

### Existing Technology Stack

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

### Integration Approach

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

### Code Organization and Standards

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

### Deployment and Operations

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

### Risk Assessment and Mitigation

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

## Epic and Story Structure

### Epic Approach

**Epic Structure Decision**: **5 Smaller Focused Epics**

**Rationale**: Breaking the Confluence integration into multiple smaller epics enables:
- **Incremental delivery**: Each epic delivers tangible value independently
- **Parallel development**: Different team members/agents can work on separate epics
- **Risk mitigation**: Issues in one epic don't block others
- **Clear milestones**: Easier progress tracking and stakeholder updates
- **Brownfield safety**: Smaller changes reduce risk to existing system integrity

**Epic Sequencing Strategy**:
1. **Foundation First**: Database and API client (minimal risk, enables all others)
2. **Core Sync Logic**: Content processing and storage (highest complexity)
3. **Search Enhancement**: Metadata-enriched queries (builds on foundation)
4. **User Interface**: Frontend experience (independent of backend epics)
5. **Quality & Optimization**: Testing and performance tuning (validates all prior work)

**Dependency Management**:
- Epic 1 → Epic 2 (hard dependency: sync needs database schema)
- Epic 2 → Epic 3 (soft dependency: search works without metadata, enhanced with it)
- Epic 1/2 → Epic 4 (hard dependency: UI needs backend APIs)
- All → Epic 5 (validates complete integration)

### Epic Breakdown Overview

**Epic 1: Database Foundation & Confluence API Client** (Week 1, Days 1-2.5)
- **Goal**: Establish database schema, Confluence API connectivity, and security validation
- **Deliverable**: Migration 010 applied, `ConfluenceClient` functional, security audit passed
- **Value**: Foundation for all Confluence integration work with verified security posture
- **Stories**: 4 (added Story 1.4 for security audit)

**Epic 2: Incremental Sync & Content Processing** (Week 1, Days 3-5)
- **Goal**: CQL-based sync, HTML→Markdown conversion, chunk storage
- **Deliverable**: Manual sync creates searchable Confluence chunks
- **Value**: Core functionality - Confluence content in RAG system

**Epic 3: Metadata-Enhanced Search Integration** (Week 2, Days 1-2)
- **Goal**: Metadata enrichment in search results with filters
- **Deliverable**: Search with space/JIRA/hierarchy filters
- **Value**: Advanced discovery using Confluence-specific metadata

**Epic 4: Frontend UI & User Experience** (Week 2, Days 3-4)
- **Goal**: Confluence source management and sync monitoring
- **Deliverable**: Complete UI for source CRUD and sync status
- **Value**: User-facing interface for Confluence integration

**Epic 5: Testing, Performance & Documentation** (Week 2, Days 5-6)
- **Goal**: Load testing, optimization, documentation updates, user communication
- **Deliverable**: Production-ready with performance validation, user onboarding materials
- **Value**: Quality assurance, operational readiness, user adoption enablement
- **Stories**: 5 (added Story 5.5 for user communication and training)

---

## Epic 1: Database Foundation & Confluence API Client

**Epic Goal**: Establish database schema for Confluence metadata storage and implement authenticated API client for Confluence Cloud REST API v2

**Integration Requirements**:
- Migration 010 must be compatible with existing migration tracking system
- API client must handle authentication, rate limiting, and error handling
- No modifications to existing `archon_crawled_pages` or `archon_sources` tables

### Story 1.1: Create Confluence Pages Database Schema

As a **backend developer**,
I want **to create migration 010 with `confluence_pages` table and indexes**,
so that **Confluence metadata can be stored separately from chunks with optimized query performance**.

**Acceptance Criteria**:
1. Migration file `010_add_confluence_pages.sql` created in `migration/0.1.0/` directory
2. `confluence_pages` table includes: page_id (PK), source_id (FK), space_key, title, version, last_modified, is_deleted, path, metadata JSONB
3. Foreign key constraint: `source_id REFERENCES archon_sources(source_id) ON DELETE CASCADE`
4. Indexes created: source (partial with is_deleted=false), space, path (text_pattern_ops), JSONB (jira_issue_links, user_mentions)
5. Index on `archon_crawled_pages`: `(metadata->>'page_id')` with partial WHERE clause
6. Migration recorded in `archon_migrations` table with checksum

**Integration Verification**:
- IV1: Verify CASCADE DELETE removes confluence_pages and chunks when archon_sources record deleted
- IV2: Confirm existing web crawl and document upload functionality unaffected
- IV3: Validate migration checksum matches expected MD5 hash

### Story 1.2: Implement Confluence API Client Wrapper

As a **backend developer**,
I want **to create `ConfluenceClient` class using `atlassian-python-api` SDK**,
so that **sync services can authenticate and query Confluence Cloud REST API v2**.

**Acceptance Criteria**:
1. File `python/src/server/services/confluence/confluence_client.py` created with ConfluenceClient class
2. Constructor accepts: base_url (str), api_token (str), email (str)
3. Method `async def cql_search(cql: str, expand: str, limit: int)` returns list of pages
4. Method `async def get_page_by_id(page_id: str, expand: str)` returns single page with metadata
5. Method `async def get_space_pages_ids(space_key: str)` returns lightweight page ID list (deletion detection)
6. Exponential backoff retry logic (max 3 retries, 1s/2s/4s delays) on rate limit errors (429)
7. Custom exceptions: `ConfluenceAuthError`, `ConfluenceRateLimitError`, `ConfluenceNotFoundError`

**Integration Verification**:
- IV1: Successfully authenticate with test Confluence Cloud instance using API token
- IV2: CQL query returns expected pages matching `lastModified` filter
- IV3: Rate limit handling gracefully waits and retries without crashing

### Story 1.3: Add Confluence Dependencies and Configuration

As a **backend developer**,
I want **to add required dependencies and environment variables for Confluence integration**,
so that **the system has all necessary libraries and configuration for API connectivity**.

**Acceptance Criteria**:
1. Add to `python/pyproject.toml` dependencies: `atlassian-python-api = "^3.41.0"`, `markdownify = "^0.11.6"`
2. Update `.env.example` with: `CONFLUENCE_BASE_URL`, `CONFLUENCE_API_TOKEN`, `CONFLUENCE_EMAIL`
3. Update `python/src/server/config/settings.py` to load Confluence environment variables
4. Add Confluence API token encryption support in `archon_settings` table (bcrypt-hashed)
5. Document environment variables in `CLAUDE.md` and `brownfield-architecture.md`

**Integration Verification**:
- IV1: `uv sync --group all` successfully installs new dependencies
- IV2: Settings service can retrieve and decrypt Confluence API token
- IV3: Missing environment variables raise clear ConfigurationError at startup

### Story 1.4: Security Audit of Confluence Dependencies

As a **security engineer**,
I want **to conduct comprehensive security audit of new Confluence dependencies and integration points**,
so that **no vulnerabilities are introduced into the existing system**.

**Acceptance Criteria**:
1. Complete security audit checklist: `docs/bmad/confluence-security-audit-checklist.md`
2. Run pip-audit on `atlassian-python-api` and `markdownify` dependencies
3. Verify no CVEs (Common Vulnerabilities and Exposures) for dependency versions
4. Pin exact versions in `pyproject.toml` (not version ranges): `atlassian-python-api = "==3.41.14"`, `markdownify = "==0.11.6"`
5. Test HTML to Markdown conversion with malicious input (XSS attempts, script tags)
6. Verify CQL query parameterization prevents injection attacks
7. Confirm API tokens stored encrypted (bcrypt) and never logged
8. Document security controls in `docs/bmad/confluence-security.md`

**Integration Verification**:
- IV1: pip-audit reports zero vulnerabilities for new dependencies
- IV2: XSS test cases (malicious HTML) produce safe Markdown output
- IV3: CQL injection tests fail gracefully (invalid space keys rejected)
- IV4: API tokens not exposed in logs, error messages, or browser DevTools

**Security Testing**:
- Test: SQL injection via space key input
- Test: XSS via Confluence page content
- Test: Rate limit bypass attempts
- Test: Authentication bypass on `/api/confluence/*` endpoints
- Test: Oversized page handling (75KB+ HTML)

---

## Epic 2: Incremental Sync & Content Processing

**Epic Goal**: Implement CQL-based incremental sync, HTML to Markdown conversion, and chunk storage reusing existing document processing infrastructure

**Integration Requirements**:
- Must call existing `document_storage_service.add_documents_to_supabase()` for chunking
- Must use existing `ProgressTracker` for sync status updates
- Atomic chunk updates ensure zero-downtime (old chunks searchable during replacement)

### Story 2.1: Implement HTML to Markdown Processor

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

### Story 2.2: Implement CQL-Based Incremental Sync Service

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

### Story 2.3: Implement Atomic Chunk Update Strategy

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

### Story 2.4: Implement Deletion Detection Strategies

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

### Story 2.5: Create Confluence API Endpoints

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

## Epic 3: Metadata-Enhanced Search Integration

**Epic Goal**: Enhance hybrid search with Confluence metadata enrichment enabling space, JIRA, hierarchy, and mention filters

**Integration Requirements**:
- Modify existing `hybrid_search_strategy.py` with LEFT JOIN to confluence_pages
- Add Confluence-specific filter parameters to search API
- Maintain existing search performance (<500ms response time)

### Story 3.1: Enhance Hybrid Search with Metadata JOIN

As a **backend developer**,
I want **to modify `hybrid_search_strategy.py` to JOIN confluence_pages for metadata enrichment**,
so that **search results include Confluence-specific metadata (space, JIRA links, hierarchy)**.

**Acceptance Criteria**:
1. Modify `python/src/server/services/search/hybrid_search_strategy.py` search query
2. Add `LEFT JOIN confluence_pages ON archon_crawled_pages.metadata->>'page_id' = confluence_pages.page_id`
3. Include in SELECT: space_key, title, path (hierarchy), JIRA links, user mentions
4. Return metadata in search response for Confluence chunks only (null for web/upload)
5. Use prepared statement or query builder to avoid SQL injection
6. Add query plan EXPLAIN analysis to verify index usage

**Integration Verification**:
- IV1: Search response time remains <500ms for queries with Confluence results
- IV2: Web crawl and document upload search results unaffected (null metadata)
- IV3: EXPLAIN shows index usage on confluence_pages.page_id (no seq scan)

### Story 3.2: Implement Confluence-Specific Search Filters

As a **backend developer**,
I want **to add filter parameters to search API for space, JIRA, hierarchy, and mentions**,
so that **users can narrow search results using Confluence metadata**.

**Acceptance Criteria**:
1. Modify `POST /api/knowledge/search` request schema to accept filters: space_key, jira_issue, hierarchy_path, mentioned_user
2. Add WHERE clauses: `confluence_pages.space_key = $1` (space filter)
3. JSONB containment: `confluence_pages.metadata->'jira_issue_links' @> '[{"issue_key": "PROJ-123"}]'` (JIRA filter)
4. Path prefix match: `confluence_pages.path LIKE '/parent_id/%'` (hierarchy filter)
5. User mention JSONB: `confluence_pages.metadata->'user_mentions' @> '[{"account_id": "..."}]'`
6. Combine filters with AND logic (all specified filters must match)

**Integration Verification**:
- IV1: Space filter returns only results from specified Confluence space
- IV2: JIRA filter correctly identifies pages linking to specific issues
- IV3: Hierarchy filter shows all descendants of specified parent page

### Story 3.3: Add Search Performance Optimization

As a **backend developer**,
I want **to optimize search queries with composite indexes and query tuning**,
so that **metadata-enriched searches maintain sub-500ms response time**.

**Acceptance Criteria**:
1. Add composite index: `CREATE INDEX idx_confluence_search ON confluence_pages(space_key, page_id) WHERE is_deleted = FALSE`
2. Add partial index on archon_crawled_pages: `WHERE metadata ? 'page_id'` (Confluence chunks only)
3. Benchmark query performance: 100 queries with various filter combinations, average <500ms
4. Add query result caching using existing ETag pattern (30s stale time)
5. Use LIMIT/OFFSET pagination to avoid full result set loading
6. Add slow query logging for searches >1s (investigate and optimize)

**Integration Verification**:
- IV1: 95th percentile search latency <500ms with 4000+ Confluence pages indexed
- IV2: Composite index used in query plan (verify with EXPLAIN ANALYZE)
- IV3: Memory usage during search remains within 20% baseline increase

---

## Epic 4: Frontend UI & User Experience

**Epic Goal**: Implement Confluence source management UI with sync monitoring, following vertical slice architecture and existing design patterns

**Integration Requirements**:
- Follow TanStack Query patterns from existing features
- Reuse Radix UI primitives and Tron-inspired styling
- Integrate with existing Knowledge Base page layout

### Story 4.1: Create Confluence Vertical Slice Foundation

As a **frontend developer**,
I want **to create the `features/confluence/` directory structure with services, hooks, types**,
so that **Confluence UI follows established vertical slice architecture**.

**Acceptance Criteria**:
1. Create directory: `archon-ui-main/src/features/confluence/`
2. Create `services/confluenceService.ts` with API methods: `listSources()`, `createSource()`, `triggerSync()`, `getStatus()`, `deleteSource()`
3. Create `hooks/useConfluenceQueries.ts` with query key factory: `confluenceKeys.all`, `confluenceKeys.lists()`, `confluenceKeys.detail(id)`
4. Create `types/index.ts` with TypeScript types: `ConfluenceSource`, `ConfluenceSyncStatus`, `CreateSourceRequest`
5. Implement query hooks: `useConfluenceSources()`, `useConfluenceDetail(id)`, `useCreateSource()`, `useTriggerSync()`, `useDeleteSource()`
6. Use `STALE_TIMES.normal` (30s) for lists, `STALE_TIMES.frequent` (5s) for sync status

**Integration Verification**:
- IV1: Query keys follow standardized factory pattern from `shared/config/queryPatterns.ts`
- IV2: Service client uses shared `apiClient.ts` with ETag support
- IV3: Types match backend API response schemas exactly

### Story 4.2: Implement Confluence Source Management UI

As a **frontend developer**,
I want **to create Confluence tab in Knowledge page with source cards and creation modal**,
so that **users can create, view, and manage Confluence sources**.

**Acceptance Criteria**:
1. Add "Confluence" tab to `/knowledge` page alongside Web Crawl and Document Upload
2. Create `components/ConfluenceSourceCard.tsx` showing: space key, page count, last sync timestamp, status badge
3. Create `components/NewConfluenceSourceModal.tsx` with form fields: Confluence URL, API Token (password input), Space Key, Deletion Strategy
4. Implement optimistic create using `createOptimisticEntity()` from shared utils
5. Use Radix UI primitives: Dialog (modal), Select (deletion strategy), Button, Badge (status)
6. Apply Tron-inspired styling: cyan accent color, glassmorphism backdrop, subtle animations
7. Add validation: URL format, API token presence, space key pattern (uppercase letters)

**Integration Verification**:
- IV1: Source creation follows same UX flow as web crawl creation (modal → form → create)
- IV2: Optimistic update shows new source immediately, replaced with server data on success
- IV3: Deletion confirmation dialog matches existing pattern from other features

### Story 4.3: Implement Sync Status and Progress Monitoring

As a **frontend developer**,
I want **to create sync status display with real-time progress updates**,
so that **users can monitor Confluence sync operations**.

**Acceptance Criteria**:
1. Create `components/ConfluenceSyncStatus.tsx` showing: sync state, progress percentage, pages processed, estimated time remaining
2. Use `useSmartPolling` hook for sync status updates (5s interval when tab focused, pause when hidden)
3. Display progress bar using Radix Progress primitive with cyan fill
4. Show sync logs in expandable section (last 10 log entries)
5. Add "Sync Now" button on source card (triggers manual sync, disabled during active sync)
6. Display error state with retry button if sync fails
7. Success state shows: pages added/updated/deleted, duration

**Integration Verification**:
- IV1: Progress updates use existing `ProgressTracker` backend service (no new polling infrastructure)
- IV2: Smart polling pauses when browser tab hidden (visibility-aware)
- IV3: Error handling follows existing toast notification pattern

### Story 4.4: Enhance Search UI with Confluence Filters

As a **frontend developer**,
I want **to add Confluence-specific filters to search sidebar and metadata to result cards**,
so that **users can leverage Confluence metadata for refined searches**.

**Acceptance Criteria**:
1. Modify `features/knowledge/components/SearchFilters.tsx` to add: Source Type filter (Web/Upload/Confluence), Confluence Space multi-select, "Has JIRA Links" toggle
2. Enhance `features/knowledge/components/SearchResultCard.tsx` for Confluence results: space badge, JIRA issue chips (clickable), hierarchy breadcrumbs (using path)
3. Use Radix Badge component for space tags (cyan background)
4. JIRA chips link to external JIRA instance (configurable base URL)
5. Breadcrumbs truncate at 5 levels with "..." for deeper paths
6. Add filter persistence using URL query params (restore filters on page reload)

**Integration Verification**:
- IV1: Filters apply correctly to search API request (verify network tab)
- IV2: Confluence metadata displays only for Confluence results (null for web/upload)
- IV3: Filter UI matches existing design patterns (same spacing, colors, interactions)

---

## Epic 5: Testing, Performance & Documentation

**Epic Goal**: Validate integration with comprehensive testing, optimize performance for 4000+ pages, and update documentation

**Integration Requirements**:
- Load test sync with 4000+ page mock dataset
- Validate all existing functionality remains intact
- Update brownfield architecture documentation

### Story 5.1: Implement Backend Integration Tests

As a **QA engineer**,
I want **to create comprehensive integration tests for Confluence sync and search**,
so that **all critical paths are validated before production deployment**.

**Acceptance Criteria**:
1. Create `python/tests/server/services/confluence/test_confluence_integration.py`
2. Test: Full sync workflow (create source → sync → verify chunks in database)
3. Test: Incremental sync (modify page → sync → verify only changed page updated)
4. Test: Deletion detection (delete page in Confluence → sync → verify removed from database)
5. Test: Search with metadata filters (space, JIRA, hierarchy)
6. Test: Atomic chunk updates (sync during active search, verify no empty results)
7. Use mock Confluence API responses (no actual API calls in tests)
8. All tests pass with >90% code coverage for new Confluence services

**Integration Verification**:
- IV1: Existing knowledge base tests (web crawl, upload) still pass (no regressions)
- IV2: CASCADE DELETE test verifies complete cleanup of pages and chunks
- IV3: Concurrent sync test validates no race conditions in chunk updates

### Story 5.2: Implement Frontend Component Tests

As a **QA engineer**,
I want **to create Vitest tests for Confluence UI components**,
so that **user interactions and data flows are validated**.

**Acceptance Criteria**:
1. Create `archon-ui-main/src/features/confluence/tests/` directory
2. Test: Source creation flow (form validation, optimistic update, success/error states)
3. Test: Sync status polling (smart polling behavior, visibility awareness)
4. Test: Search filters (filter application, URL param persistence)
5. Test: Query hook behavior (cache updates, invalidation, stale time)
6. Use React Testing Library for component tests, msw for API mocking
7. All tests pass with >85% code coverage for Confluence feature

**Integration Verification**:
- IV1: Mock service methods match actual API contracts (type-safe)
- IV2: Query pattern tests validate correct stale times and key factories
- IV3: Existing feature tests (knowledge, projects) still pass

### Story 5.3: Perform Load Testing and Optimization

As a **performance engineer**,
I want **to load test Confluence sync with 4000+ pages and optimize bottlenecks**,
so that **performance requirements (15min sync, <500ms search) are met**.

**Acceptance Criteria**:
1. Create mock Confluence dataset: 4000 pages, varying sizes (1KB-75KB), 7-level hierarchy
2. Execute full sync, measure: total duration, memory usage, API calls made, database query time
3. Validate: Sync completes <15min, memory increase <20%, progress updates every 50 pages
4. Execute search benchmarks: 100 queries with metadata filters, measure p50/p95/p99 latency
5. Validate: p95 latency <500ms, index usage confirmed in query plans
6. Identify and optimize top 3 bottlenecks (if any exceed thresholds)
7. Document performance characteristics in PRD appendix

**Integration Verification**:
- IV1: Existing web crawl performance unaffected by Confluence additions
- IV2: Database connection pool handles concurrent sync + search load
- IV3: Frontend renders 4000+ source pages list with pagination (no UI lag)

### Story 5.4: Update Documentation and Architecture Docs

As a **technical writer**,
I want **to update brownfield architecture and CLAUDE.md with Confluence integration details**,
so that **future developers have accurate system documentation**.

**Acceptance Criteria**:
1. Update `docs/bmad/brownfield-architecture.md` section "Confluence Integration Architecture" with implementation reality
2. Add Confluence API endpoints to "API Specifications" section
3. Update "Source Tree and Module Organization" with new confluence/ directory
4. Update `CLAUDE.md` with Confluence development commands and file locations
5. Create `docs/confluence-integration-guide.md` with: setup instructions, API token generation, sync configuration
6. Update `migration/0.1.0/DB_UPGRADE_INSTRUCTIONS.md` for migration 010
7. Add Confluence to MCP tools documentation (if applicable)

**Integration Verification**:
- IV1: Architecture doc accurately reflects implemented code (no planned vs actual discrepancies)
- IV2: New developer can follow CLAUDE.md to understand Confluence feature structure
- IV3: Migration instructions tested on fresh database (successful upgrade path)

### Story 5.5: User Communication and Training Materials

As a **product manager**,
I want **to create user-facing documentation, changelog, and training materials for Confluence integration**,
so that **users understand how to use the new feature and are notified of its availability**.

**Acceptance Criteria**:
1. Create comprehensive user guide: `docs/bmad/confluence-user-communication-plan.md` with:
   - Step-by-step setup instructions (API token generation, source creation)
   - Sync monitoring and troubleshooting
   - Advanced search features and filters
   - FAQ and common issues
2. Create changelog entry: `docs/bmad/CHANGELOG-v0.2.0.md` with:
   - Feature highlights (headline: Confluence Cloud Integration)
   - Technical changes (new APIs, dependencies, database schema)
   - Security enhancements
   - Upgrade instructions for users and developers
   - Known issues and workarounds
3. Create in-app changelog modal component: `archon-ui-main/src/features/shared/components/ChangelogModal.tsx`
   - Displays on first login after upgrade to v0.2.0
   - Highlights key features with screenshots
   - "What's New" badge in settings menu
4. Add "Give Feedback" button in Confluence tab UI for user input
5. Create support documentation: Troubleshooting guide, error message explanations, rollback procedures

**User Communication Strategy**:
- Announcement: In-app modal on first v0.2.0 login
- Documentation: Linked from Confluence tab help icon
- Community: Post in Discord/Slack/GitHub Discussions
- Email: Optional announcement to registered users (if applicable)

**Integration Verification**:
- IV1: User guide tested by non-technical team member (successful setup)
- IV2: Changelog modal displays correctly on upgrade (tested with version check)
- IV3: Feedback button functional (logs submitted successfully)

**Deliverables**:
- User setup guide (Markdown)
- Changelog entry (Markdown)
- In-app changelog modal (React component)
- Feedback mechanism (UI + backend logging)
- Support FAQ document

---

## Implementation Summary

**Timeline**: 2 weeks + 1 day (11 working days)
**Total Stories**: 21 stories across 5 epics
**Story Distribution**: Epic 1 (4 stories), Epic 2 (5 stories), Epic 3 (3 stories), Epic 4 (4 stories), Epic 5 (5 stories)

**Dependency Flow**:
```
Epic 1: Database Foundation & API Client (Days 1-2)
  ├─→ Epic 2: Incremental Sync & Processing (Days 3-5)
  │     └─→ Epic 3: Metadata-Enhanced Search (Days 6-7)
  └─→ Epic 4: Frontend UI & UX (Days 8-9)
          ↓
      Epic 5: Testing & Documentation (Day 10)
```

**Risk Mitigation Built Into Stories**:
- Every story includes Integration Verification steps ensuring existing system integrity
- Atomic chunk updates (Story 2.3) guarantee zero-downtime search availability
- Performance validation (Story 5.3) validates NFRs before production
- Comprehensive testing (Stories 5.1-5.2) validates all integration points

**Key Implementation Notes**:
1. **90% Code Reuse**: Stories 2.2, 2.5, 3.1 leverage existing services without modification
2. **Brownfield Safety**: All database changes additive (migration 010), existing tables unchanged
3. **Incremental Value**: Each epic delivers working functionality independently
4. **Metadata-First Search**: Story 3.1-3.2 implement mandatory metadata enrichment per requirements validation

---

*End of Product Requirements Document*
