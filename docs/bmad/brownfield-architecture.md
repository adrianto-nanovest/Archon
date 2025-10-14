# Archon Brownfield Architecture Document v3.0

## Introduction

This document captures the **CURRENT STATE** of the Archon codebase as of October 2025, including technical realities, architectural patterns, and integration points. It serves as a definitive reference for AI agents and developers working on the Confluence Knowledge Base integration and other enhancements.

### Document Scope

**Primary Focus:** Confluence Knowledge Base Integration using Direct API + Hybrid Database Schema

**Enhancement Context:**
- Integrating 4000+ Confluence Cloud pages into Archon's RAG system
- Direct Confluence API approach (NOT Google Drive intermediary)
- Hybrid schema: Dedicated `confluence_pages` metadata table + unified `archon_crawled_pages` chunks
- 90% code reuse leveraging existing document storage and search infrastructure
- Expected implementation: 1.5-2 weeks

**Secondary Coverage:** Current system architecture, recent changes (Aug-Oct 2025), and technical constraints

### Change Log

| Date       | Version | Description                                    | Author              |
| ---------- | ------- | ---------------------------------------------- | ------------------- |
| 2025-08-21 | 1.0     | Initial brownfield analysis                    | Winston (Architect) |
| 2025-10-06 | 2.0     | Updated with multi-LLM, migrations, versioning | AI Agent            |
| 2025-10-06 | 3.0     | **Comprehensive rewrite focusing on Confluence integration with Hybrid Schema** | **Winston (Architect)** |

---

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System

#### Backend Core
- **Main Entry**: `python/src/server/main.py` - FastAPI application with lifespan management
- **Configuration**: `.env.example`, `python/src/server/config/`
- **Core Business Logic**: `python/src/server/services/`
- **API Definitions**: `python/src/server/api_routes/`

#### Knowledge Base & RAG
- **Knowledge Management**: `python/src/server/services/knowledge/knowledge_item_service.py`
- **Document Storage**: `python/src/server/services/storage/document_storage_service.py`
- **Hybrid Search**: `python/src/server/services/search/hybrid_search_strategy.py`
- **LLM Providers**: `python/src/server/services/llm_provider_service.py`
- **Embeddings**: `python/src/server/services/embeddings/embedding_service.py`

#### Database & Migrations
- **Schema**: `migration/complete_setup.sql` - Complete database schema (no ORM models!)
- **Migration Tracking**: `python/src/server/services/migration_service.py`
- **Migration Files**: `migration/0.1.0/` (001-009 migrations)

#### Frontend Architecture
- **Features Directory**: `archon-ui-main/src/features/` - Vertical slice architecture
- **Query Client**: `archon-ui-main/src/features/shared/config/queryClient.ts`
- **API Client**: `archon-ui-main/src/features/shared/api/apiClient.ts`

### Files Relevant to Confluence Integration

#### Existing Infrastructure (90% Code Reuse!)
- **Document Storage Service**: `python/src/server/services/storage/document_storage_service.py`
  - `add_documents_to_supabase()` - **REUSE THIS** for chunking and embeddings
  - Handles chunking, code detection, embedding generation, progress tracking

- **Hybrid Search Strategy**: `python/src/server/services/search/hybrid_search_strategy.py`
  - **ALREADY searches `archon_crawled_pages`** - works with Confluence chunks out of the box!

- **Progress Tracking**: `python/src/server/services/progress_tracker.py`
  - **REUSE THIS** for sync status updates

#### Files to CREATE for Confluence (New ~800 lines)
- `python/src/server/services/confluence/confluence_client.py` - Atlassian API client
- `python/src/server/services/confluence/confluence_sync_service.py` - CQL-based sync logic
- `python/src/server/services/confluence/confluence_processor.py` - HTML → Markdown conversion
- `python/src/server/api_routes/confluence_api.py` - REST endpoints
- `migration/0.1.0/010_add_confluence_pages.sql` - Database migration

#### Files to MODIFY (Minimal Changes)
- `python/src/server/services/knowledge/knowledge_item_service.py` - Add 'confluence' source type
- Optional: `python/src/server/services/search/hybrid_search_strategy.py` - Add Confluence metadata JOIN

---

## High Level Architecture

### Technical Summary

Archon is a **microservices-based RAG system** designed to provide knowledge base management and task tracking for AI coding assistants. It uses a monolithic repository with Docker orchestration for three distinct services: server (port 8181), MCP server (port 8051), and agents service (port 8052).

**Current Version:** 0.1.0
**Database:** Supabase (PostgreSQL 15+ with pgvector extension)
**Architecture Pattern:** Vertical slice (frontend) + Service layer (backend)

### Actual Tech Stack

| Category          | Technology           | Version | Notes                                      |
| ----------------- | -------------------- | ------- | ------------------------------------------ |
| **Backend**       |                      |         |                                            |
| Runtime           | Python               | 3.12    | Required for latest typing features        |
| Framework         | FastAPI              | 0.104+  | Async-first with lifespan events           |
| Package Manager   | uv                   | latest  | Faster than pip, lockfile support          |
| Web Crawler       | crawl4ai             | 0.6.2   | Advanced async crawling with JS rendering  |
| **Database**      |                      |         |                                            |
| Primary DB        | PostgreSQL           | 15+     | via Supabase cloud or local                |
| Vector Store      | pgvector             | 0.5+    | Extension for embeddings (1536 dimensions) |
| DB Client         | asyncpg + Supabase SDK | 0.29+ / 2.15.1 | Direct SQL + Supabase helpers    |
| **AI/ML**         |                      |         |                                            |
| LLM SDK           | openai               | 1.71.0  | Universal client (works with compatible APIs) |
| Document Processing | pypdf2, pdfplumber, python-docx | 3.0+ | Basic extraction (no Docling yet) |
| **Frontend**      |                      |         |                                            |
| Framework         | React                | 18      | via Vite dev server                        |
| State Management  | TanStack Query       | v5      | Query-centric architecture (no Redux!)     |
| Styling           | Tailwind CSS         | 3.4.17  | Tron-inspired glassmorphism                |
| UI Primitives     | Radix UI             | various | Headless accessible components             |
| **Infrastructure**|                      |         |                                            |
| Orchestration     | Docker Compose       | latest  | Multi-service development environment      |
| Build Tool        | Makefile             | -       | Common workflow shortcuts                  |

### Repository Structure Reality Check

- **Type:** Monorepo
- **Package Manager:** `uv` (Python), `npm` (Frontend & Docs)
- **Service Split:** Three distinct Python services in `python/src/` directory
- **Build System:** Docker Compose for orchestration, Makefile for developer workflows
- **No ORM:** Direct SQL via asyncpg/Supabase client (no SQLAlchemy, no Alembic!)
- **Migration Strategy:** Manual SQL scripts in `migration/` with checksum tracking

---

## Source Tree and Module Organization

### Project Structure (Actual - October 2025)

```text
archon/
├── python/                          # Backend monolith
│   ├── src/
│   │   ├── server/                  # Core business logic (port 8181)
│   │   │   ├── api_routes/          # FastAPI routers
│   │   │   │   ├── knowledge_api.py         # RAG, crawling, upload
│   │   │   │   ├── projects_api.py          # Project/task CRUD
│   │   │   │   ├── migration_api.py         # NEW: Migration status
│   │   │   │   ├── version_api.py           # NEW: Version checking
│   │   │   │   └── (11 total routers)
│   │   │   ├── services/            # Business logic layer
│   │   │   │   ├── knowledge/               # Knowledge base management
│   │   │   │   │   └── knowledge_item_service.py
│   │   │   │   ├── storage/                 # Document ingestion
│   │   │   │   │   └── document_storage_service.py  # **REUSE FOR CONFLUENCE**
│   │   │   │   ├── search/                  # Hybrid search strategies
│   │   │   │   │   └── hybrid_search_strategy.py    # **ALREADY WORKS WITH CONFLUENCE**
│   │   │   │   ├── embeddings/              # Multi-provider embeddings
│   │   │   │   ├── crawling/                # Web crawling with domain filtering
│   │   │   │   ├── projects/                # Project/task services
│   │   │   │   ├── llm_provider_service.py  # Multi-LLM orchestration
│   │   │   │   ├── migration_service.py     # NEW: Migration tracking
│   │   │   │   ├── version_service.py       # NEW: GitHub release checking
│   │   │   │   └── progress_tracker.py      # **REUSE FOR CONFLUENCE SYNC**
│   │   │   ├── utils/
│   │   │   │   ├── document_processing.py   # PDF/DOCX extraction
│   │   │   │   ├── semantic_version.py      # NEW: Version comparison
│   │   │   │   └── etag_utils.py            # ETag generation
│   │   │   ├── config/                      # Configuration management
│   │   │   ├── middleware/                  # Rate limiting, logging
│   │   │   └── main.py                      # Server entry point
│   │   ├── mcp_server/              # MCP server (port 8051)
│   │   │   ├── features/            # MCP tool implementations
│   │   │   │   ├── knowledge/       # RAG search tools
│   │   │   │   ├── projects/        # Project management tools
│   │   │   │   └── tasks/           # Task management tools
│   │   │   └── main.py
│   │   └── agents/                  # AI agents service (port 8052)
│   │       ├── features/            # Agent capabilities
│   │       └── main.py
│   ├── tests/                       # Pytest suite
│   └── pyproject.toml               # uv dependency config
│
├── archon-ui-main/                  # React frontend (port 3737)
│   ├── src/
│   │   ├── features/                # Vertical slice architecture
│   │   │   ├── knowledge/           # Knowledge base UI
│   │   │   │   ├── components/      # UI components
│   │   │   │   ├── hooks/           # Query hooks & keys
│   │   │   │   ├── services/        # API calls
│   │   │   │   └── types/           # TypeScript types
│   │   │   ├── projects/            # Project management UI
│   │   │   │   ├── tasks/           # Task sub-feature (nested vertical slice)
│   │   │   │   └── documents/       # Document sub-feature
│   │   │   ├── settings/
│   │   │   │   ├── migrations/      # NEW: Migration status UI
│   │   │   │   └── version/         # NEW: Version checking UI
│   │   │   ├── shared/              # Cross-feature utilities
│   │   │   │   ├── api/             # API client with ETag support
│   │   │   │   ├── config/          # QueryClient, patterns
│   │   │   │   ├── hooks/           # Shared hooks (useSmartPolling)
│   │   │   │   └── utils/           # Optimistic updates
│   │   │   └── ui/                  # UI primitives & components
│   │   ├── pages/                   # Route components
│   │   └── components/              # Legacy components (migrating to features/)
│   └── package.json
│
├── migration/                       # SQL database migrations
│   ├── complete_setup.sql           # Full schema for fresh installs
│   └── 0.1.0/                       # Version-specific migrations
│       ├── 001_add_source_url_display_name.sql
│       ├── 002_add_hybrid_search_tsvector.sql
│       ├── 003-007_ollama_*.sql     # Ollama integration
│       ├── 008_add_migration_tracking.sql    # Migration system
│       ├── 009_add_provider_placeholders.sql # LLM providers
│       └── 010_add_confluence_pages.sql      # **TO CREATE: Confluence tables**
│
├── .bmad-core/                      # BMad methodology (100+ files)
│   ├── agents/                      # 10 agent roles
│   ├── tasks/                       # 23 task templates
│   ├── templates/                   # 13 document templates
│   └── workflows/                   # 6 workflow definitions
│
├── PRPs/                            # Project Reference Points
│   └── ai_docs/                     # Architecture & pattern docs
│       ├── ARCHITECTURE.md
│       ├── DATA_FETCHING_ARCHITECTURE.md
│       ├── QUERY_PATTERNS.md
│       ├── ETAG_IMPLEMENTATION.md
│       └── API_NAMING_CONVENTIONS.md
│
├── docs/
│   ├── bmad/                        # Brownfield architecture docs
│   │   ├── brownfield-architecture.md        # **THIS FILE**
│   │   ├── CONFLUENCE_RAG_INTEGRATION.md     # Confluence integration guide
│   │   └── CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md
│   └── claude-notes/                # Development notes
│
├── docker-compose.yml               # Service orchestration
├── Makefile                         # Development workflows
└── .env.example                     # Environment template
```

### Key Modules and Their Purpose

#### Core Services (Backend)

1. **`server` (port 8181)**: Main backend service handling all business logic
   - REST API for knowledge base, projects, tasks, settings
   - Document ingestion pipeline with chunking and embeddings
   - Multi-LLM provider orchestration (OpenAI, Google, Ollama, Anthropic, Grok, OpenRouter)
   - Hybrid search with vector similarity + keyword + reranking

2. **`mcp_server` (port 8051)**: Model Context Protocol server for IDE integration
   - Exposes knowledge base as MCP tools for Cursor/Windsurf/Claude Code
   - Project and task management tools
   - Supports dual transport: SSE (web clients) + stdio (IDE clients)

3. **`agents` (port 8052)**: AI agents service (PydanticAI)
   - Document processing agents
   - Code analysis agents
   - Project generation agents

#### Knowledge Base Services (Critical for Confluence)

- **`knowledge_item_service.py`**: Manages knowledge source metadata (`archon_sources` table)
  - Web crawls, document uploads, **future: Confluence spaces**
  - Source configuration, status tracking, metadata storage

- **`document_storage_service.py`**: **REUSE THIS FOR CONFLUENCE CHUNKS!**
  - `add_documents_to_supabase()` - Handles chunking, embedding, storage
  - Section-aware chunking with code block detection
  - Multi-provider embedding generation (OpenAI, Google, Ollama)
  - Progress tracking and batch processing
  - **Already stores in `archon_crawled_pages` - perfect for Confluence!**

- **`hybrid_search_strategy.py`**: **ALREADY WORKS WITH CONFLUENCE CHUNKS!**
  - Searches `archon_crawled_pages` table (unified chunks)
  - Vector similarity + keyword + reranking
  - No changes needed for basic Confluence search!

#### LLM & Embedding Services

- **`llm_provider_service.py`**: Multi-provider LLM orchestration
  - Chat providers: OpenAI, Google, Ollama, Anthropic, Grok, OpenRouter
  - Embedding providers: OpenAI, Google, Ollama (UI enforces this subset)
  - Universal client pattern with provider-specific adapters

- **`embedding_service.py`**: Embedding generation with retry logic
  - Supports text-embedding-3-small/large (OpenAI)
  - Supports gemini-embedding-001 (Google)
  - Supports local Ollama models
  - Batch processing for efficiency

#### Migration & Versioning (NEW in v2.0)

- **`migration_service.py`**: Database migration tracking
  - Tracks applied migrations in `archon_migrations` table
  - Self-recording pattern (migration 008 records itself + 001-007)
  - Checksum verification for integrity

- **`version_service.py`**: GitHub release checking
  - Semantic version comparison
  - 1-hour cache to avoid rate limits
  - Update notifications in Settings UI

---

## Data Models and APIs

### Database Schema (SQL-based, No ORM!)

**Schema Location:** `migration/complete_setup.sql`

The database uses **direct SQL** with no ORM framework. All schemas are defined in SQL migration scripts and accessed via `asyncpg` or Supabase SDK.

#### Key Tables

##### Knowledge Base Tables

**`archon_sources`** - Knowledge source metadata
```sql
CREATE TABLE archon_sources (
  source_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,  -- 'web', 'upload', 'confluence' (future)
  status TEXT,
  metadata JSONB,  -- Flexible storage for source-specific data
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**`archon_crawled_pages`** - **UNIFIED CHUNK STORAGE** (used by web crawls, uploads, **CONFLUENCE**)
```sql
CREATE TABLE archon_crawled_pages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  source_id TEXT REFERENCES archon_sources(source_id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB,  -- Minimal: {"page_id": "...", "section_title": "..."}
  embedding vector(1536),  -- pgvector type
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_crawled_pages_source ON archon_crawled_pages(source_id);
CREATE INDEX idx_crawled_pages_embedding ON archon_crawled_pages
  USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_crawled_pages_content_fts ON archon_crawled_pages
  USING gin(to_tsvector('english', content));
```

**`archon_code_examples`** - Extracted code snippets (Agentic RAG feature)
```sql
CREATE TABLE archon_code_examples (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  source_id TEXT REFERENCES archon_sources(source_id) ON DELETE CASCADE,
  language TEXT,
  code_content TEXT NOT NULL,
  summary TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

##### Confluence Tables (TO CREATE in migration 010)

**`confluence_pages`** - Confluence metadata (NEW)
```sql
CREATE TABLE confluence_pages (
  page_id TEXT PRIMARY KEY,  -- Confluence native page ID
  source_id TEXT NOT NULL REFERENCES archon_sources(source_id) ON DELETE CASCADE,

  -- Core fields
  space_key TEXT NOT NULL,
  title TEXT NOT NULL,
  version INTEGER NOT NULL,
  last_modified TIMESTAMPTZ NOT NULL,
  is_deleted BOOLEAN DEFAULT FALSE,

  -- Materialized path for hierarchy ("/parent_id/child_id/grandchild_id")
  path TEXT,

  -- Rich metadata stored ONCE per page (~15 KB)
  metadata JSONB NOT NULL,
  -- {
  --   "ancestors": [{id, title, url}, ...],
  --   "children": [{id, title, url}, ...],
  --   "created_by": {account_id, display_name, email},
  --   "jira_issue_links": [{issue_key, issue_url}, ...],
  --   "user_mentions": [{account_id, display_name}, ...],
  --   "internal_links": [{page_id, page_title, page_url}, ...],
  --   "external_links": [{title, url}, ...],
  --   "asset_links": [{id, title, download_url}, ...],
  --   "word_count": 7351,
  --   "content_length": 75919
  -- }

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_confluence_pages_source ON confluence_pages(source_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_confluence_pages_space ON confluence_pages(space_key) WHERE is_deleted = FALSE;
CREATE INDEX idx_confluence_pages_version ON confluence_pages(page_id, version);
CREATE INDEX idx_confluence_pages_path ON confluence_pages USING btree(path text_pattern_ops);

-- JSONB indexes for metadata queries
CREATE INDEX idx_confluence_pages_jira ON confluence_pages
  USING gin((metadata->'jira_issue_links') jsonb_path_ops);
CREATE INDEX idx_confluence_pages_mentions ON confluence_pages
  USING gin((metadata->'user_mentions') jsonb_path_ops);

-- Link chunks back to pages
CREATE INDEX idx_crawled_pages_confluence_page_id ON archon_crawled_pages
  ((metadata->>'page_id')) WHERE metadata ? 'page_id';
```

**Key Design Decision:** Confluence chunks are stored in **existing `archon_crawled_pages` table** (unified storage), linked via `metadata->>'page_id'`. Rich metadata lives in `confluence_pages` table. This is the **Hybrid Schema** approach from `CONFLUENCE_RAG_INTEGRATION.md`.

##### Project Management Tables (Optional Feature)

**`archon_projects`** - Projects (can be disabled in Settings)
```sql
CREATE TABLE archon_projects (
  project_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  features TEXT[],  -- Array of feature names
  status TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**`archon_tasks`** - Tasks linked to projects
```sql
CREATE TABLE archon_tasks (
  task_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  project_id UUID REFERENCES archon_projects(project_id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT CHECK (status IN ('todo', 'doing', 'review', 'done')),
  assignee TEXT,  -- 'User', 'Archon', 'AI IDE Agent'
  priority INTEGER,
  fractional_index TEXT,  -- Lexorank-style ordering
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

##### Configuration Tables

**`archon_settings`** - Application settings and encrypted credentials
```sql
CREATE TABLE archon_settings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  key VARCHAR(255) UNIQUE NOT NULL,
  value TEXT,                    -- Plain text config
  encrypted_value TEXT,          -- Bcrypt-hashed sensitive data
  is_encrypted BOOLEAN DEFAULT FALSE,
  category VARCHAR(100),         -- 'rag_strategy', 'api_keys', 'monitoring', etc.
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS enabled for security
ALTER TABLE archon_settings ENABLE ROW LEVEL SECURITY;
```

**`archon_migrations`** - Migration tracking (NEW in v2.0)
```sql
CREATE TABLE archon_migrations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  version VARCHAR(20) NOT NULL,
  migration_name VARCHAR(255) NOT NULL,
  applied_at TIMESTAMPTZ DEFAULT NOW(),
  checksum VARCHAR(32),
  UNIQUE(version, migration_name)
);
```

### API Specifications

**API Location:** `python/src/server/api_routes/`

All APIs follow RESTful patterns with JSON request/response. No GraphQL, no gRPC.

#### Knowledge Base APIs (`knowledge_api.py`)

```
GET    /api/knowledge/sources           # List all knowledge sources
POST   /api/knowledge/sources           # Create knowledge source
GET    /api/knowledge/sources/{id}      # Get source details
DELETE /api/knowledge/sources/{id}      # Delete source (CASCADE)

POST   /api/knowledge/crawl             # Start web crawl
POST   /api/knowledge/upload            # Upload document

POST   /api/knowledge/search            # RAG search (hybrid)
POST   /api/knowledge/code-search       # Code-specific search
```

#### Confluence APIs (`confluence_api.py` - TO CREATE)

```
POST   /api/confluence/sources          # Create Confluence source
GET    /api/confluence/sources          # List Confluence sources
POST   /api/confluence/{id}/sync        # Trigger manual sync
GET    /api/confluence/{id}/status      # Get sync status
DELETE /api/confluence/{id}             # Delete source (CASCADE)
GET    /api/confluence/{id}/pages       # List pages in space
```

#### Migration APIs (`migration_api.py` - NEW)

```
GET    /api/migrations/status           # Get migration status
GET    /api/migrations/pending          # List pending migrations
```

#### Version APIs (`version_api.py` - NEW)

```
GET    /api/version/current             # Current version info
GET    /api/version/check               # Check for updates (1-hour cache)
POST   /api/version/clear-cache         # Force refresh
```

#### Projects APIs (`projects_api.py`)

```
GET    /api/projects                    # List all projects
POST   /api/projects                    # Create project
GET    /api/projects/{id}               # Get project details
PUT    /api/projects/{id}               # Update project
DELETE /api/projects/{id}               # Delete project (CASCADE)

GET    /api/projects/{id}/tasks         # Get project tasks
GET    /api/projects/{id}/docs          # Get project documents
GET    /api/projects/{id}/versions      # Get version history
```

---

## Confluence Integration Architecture

### Overview: Hybrid Schema Approach

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

### Data Pipeline Flow (90% Code Reuse!)

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

### CQL-Based Incremental Sync Strategy

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

### Implementation Phases (1.5-2 Weeks)

#### Phase 1: Database & Basic Sync (Week 1)
- Create `confluence_pages` table (migration 010)
- Implement `ConfluenceClient` using `atlassian-python-api`
- CQL-based incremental sync logic
- HTML → Markdown conversion
- Store metadata with materialized path
- **Call existing `document_storage_service.add_documents_to_supabase()`** ✓

#### Phase 2: API & Incremental Sync (Week 1)
- Implement `ConfluenceSyncService` with metrics tracking
- Handle page creates, updates, deletes
- Atomic chunk updates
- API endpoints in `confluence_api.py`
- Use existing `ProgressTracker` for sync status ✓

#### Phase 3: Search Integration (Week 2)
- **NO CHANGES to core search!** Already works with `archon_crawled_pages` ✓
- Optional: Add `LEFT JOIN confluence_pages` for metadata enrichment
- Add Confluence-specific filters (space, JIRA links)

#### Phase 4: Frontend & Testing (Week 2)
- Create `src/features/confluence/` vertical slice
- Source creation form, sync status, progress display
- Unit tests, integration tests, load testing (4000+ pages)

### Files to Create (~800 lines total)

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

### Dependencies to Add

```toml
# python/pyproject.toml - Add to [dependency-groups.server]
atlassian-python-api = "^3.41.0"  # Confluence REST API client
markdownify = "^0.11.6"           # HTML to Markdown conversion
```

---

## Recent Major Changes (August - October 2025)

### 1. Multi-LLM Provider Ecosystem ✅ IMPLEMENTED

**New Providers:**
- OpenRouter - Community model access (chat only)
- Anthropic - Native Claude API support (chat only)
- Grok - xAI models integration (chat only)

**Backend Changes:**
- `llm_provider_service.py` - Extended with provider-specific adapters
- `credential_service.py` - API key management for new providers
- Migration 009 - Added provider API key placeholders in `archon_settings`

**Frontend Changes:**
- `RAGSettings.tsx` - Major rewrite with tabbed interface
  - Chat Provider tab: All providers available
  - Embedding Provider tab: OpenAI, Google, Ollama ONLY (UI enforces this)
- Provider-specific colors for visual distinction
- Smart defaults: Grok uses `grok-3-mini`, Google embeddings use `gemini-embedding-001`

**New Environment Variables:**
```bash
OPENROUTER_API_KEY=  # https://openrouter.ai/keys
ANTHROPIC_API_KEY=   # https://console.anthropic.com/account/keys
GROK_API_KEY=        # https://console.x.ai/
```

### 2. Migration Tracking System ✅ IMPLEMENTED

**Purpose:** Track applied database migrations and detect pending ones.

**Backend:**
- `migration_service.py` - Service for migration tracking
- `migration_api.py` - API endpoints (`/api/migrations/status`, `/api/migrations/pending`)
- Database table: `archon_migrations` (version, name, checksum, applied_at)

**Frontend:**
- `features/settings/migrations/MigrationStatusCard.tsx` - Shows applied/pending status
- `features/settings/migrations/PendingMigrationsModal.tsx` - Alert for pending migrations

**Key Features:**
- Self-recording pattern (migration 008 records itself + retroactively records 001-007)
- Checksum verification for migration integrity (MD5 hash)
- UI banner for pending migrations

### 3. Version Checking System ✅ IMPLEMENTED

**Purpose:** Check GitHub for latest release and notify users of updates.

**Backend:**
- `version_service.py` - Version checking logic with 1-hour cache
- `version_api.py` - API endpoints
- `config/version.py` - `ARCHON_VERSION = "0.1.0"`
- `utils/semantic_version.py` - Semantic versioning comparison

**Frontend:**
- `features/settings/version/VersionStatusCard.tsx` - Shows current version and update status

**Key Features:**
- GitHub API integration (`GET /repos/:owner/:repo/releases/latest`)
- 1-hour cache TTL to avoid rate limits
- Semantic versioning comparison (0.1.0 < 0.2.0 < 1.0.0)

### 4. Web Crawling Enhancements ✅ IMPLEMENTED

**Changes:**
- Advanced domain filtering (whitelist/blacklist) in `crawling_service.py`
- Edit Crawler Configuration dialog with metadata viewer
- Auto-expand advanced configuration options in UI
- Improved robustness and error handling

### 5. BMad Methodology Integration 🆕 INTEGRATED

**Purpose:** Structured agent-based development methodology for brownfield projects.

**Directory Structure:**
- `.bmad-core/` - Complete framework (100+ files)
  - `agents/` - 10 agent roles (analyst, architect, dev, pm, po, qa, etc.)
  - `tasks/` - 23 task templates
  - `templates/` - 13 document templates
  - `workflows/` - 6 workflow definitions
- `.claude/commands/BMad/` - Mirror for Claude Code integration

**Impact:** Provides structured approach for requirements gathering, story creation, quality assurance.

### 6. Frontend Architecture Improvements ✅ IMPLEMENTED

**Shared Utilities Refactor:**
- Moved shared hooks from `features/ui/hooks` to `features/shared/hooks`
- Better separation of concerns between UI primitives and shared utilities

**TanStack Query Architecture:**
- Query-centric state management (no Redux, no Zustand)
- Smart polling with visibility awareness (`useSmartPolling.ts`)
- ETag support for bandwidth optimization (~70% reduction on 304 responses)
- Request deduplication (same query key = one request)
- Standardized stale times and query patterns (`queryPatterns.ts`)

---

## Technical Debt and Known Issues

### Implemented but Incomplete

1. **Docling Integration (Attempted, Missing Implementation)**
   - Commit bc97f5d mentions Docling for advanced document processing
   - Expected file `python/src/server/utils/docling_processing.py` is **MISSING**
   - Only basic document processing exists (PyPDF2, pdfplumber, python-docx)
   - **Decision needed:** Complete Docling integration or remove from commit history
   - **Impact:** Limited PDF layout preservation, no table extraction

2. **CASCADE DELETE Migration File (Referenced but Missing)**
   - Commit 506ad34 mentions `009_add_cascade_delete_constraints.sql`
   - File **does not exist** in `migration/0.1.0/` directory
   - CASCADE DELETE constraints were added to `complete_setup.sql` instead
   - **Recommendation:** Create migration file for consistency or update documentation

### Planned but Not Implemented

1. **Confluence Integration (Extensively Planned, Zero Implementation)** ← PRIMARY FOCUS
   - Comprehensive documentation exists (1,333+ lines in `CONFLUENCE_RAG_INTEGRATION.md`)
   - Key architectural decisions made:
     - **Hybrid Schema**: Dedicated metadata table + unified chunks ✓
     - **Direct Confluence API**: Not Google Drive intermediary ✓
     - **CQL-based incremental sync**: No full space scans ✓
     - **90% code reuse**: Leverage existing services ✓
   - **No code changes yet** - ready for implementation!
   - **Dependencies NOT added:** `atlassian-python-api`, `markdownify`
   - **Recommendation:** Use existing documentation as roadmap for 1.5-2 week implementation

2. **Google Drive Integration**
   - Original brownfield v1.0 planned Google Drive as Confluence intermediary
   - **ABANDONED** in favor of direct Confluence API approach
   - No implementation in either direction

### Current Technical Debt

1. **Document Processing**
   - Basic PDF extraction (PyPDF2, pdfplumber) - no layout preservation
   - Basic DOCX support (python-docx) - no complex formatting
   - Code block preservation implemented for page boundaries
   - **Missing:** Advanced layout analysis, table extraction, multi-column support

2. **Background Job Management**
   - No formal job queue system (Celery, RQ, etc.)
   - Long-running operations tracked via `archon_progress` table
   - Simple polling-based progress tracking
   - **Recommendation:** Add job queue for Confluence sync (long-running operations)

3. **Migration Versioning Strategy**
   - Current version: 0.1.0
   - Migration files in `migration/0.1.0/` directory
   - **Missing:** Version bump strategy, migration rollback procedures
   - **Recommendation:** Adopt semantic versioning for releases

4. **Test Coverage**
   - Backend tests exist in `python/tests/`
   - Frontend tests use Vitest + React Testing Library
   - **Coverage gaps:** Migration tracking, version checking, newer features
   - **Recommendation:** Comprehensive integration tests, especially for Confluence sync

### Architecture Constraints

1. **No ORM Framework**
   - Direct SQL via asyncpg/Supabase SDK
   - No SQLAlchemy, no Alembic migration tool
   - **Impact:** Manual SQL writing, manual migration tracking
   - **Trade-off:** Performance and simplicity vs ORM features

2. **No WebSockets**
   - HTTP polling with smart intervals (visibility-aware)
   - **Impact:** Not true real-time, but efficient (ETag caching ~70% bandwidth reduction)
   - **Trade-off:** Simplicity vs real-time updates

3. **Vertical Slice Frontend Architecture**
   - Features own their entire stack (UI → API → DB awareness)
   - **Impact:** Some code duplication, but high cohesion
   - **Trade-off:** DRY vs feature independence

---

## Integration Points and External Dependencies

### External Services

| Service       | Purpose                        | Integration Type | Key Files                               | Status |
| ------------- | ------------------------------ | ---------------- | --------------------------------------- | ------ |
| **Supabase**  | Database & Vector Store        | SDK              | Throughout `server` service             | ✅ Active |
| **OpenAI**    | LLM for chat & embeddings      | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Google AI** | Gemini models & embeddings     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Ollama**    | Local LLM serving              | HTTP API         | `services/llm_provider_service.py`      | ✅ Active |
| **Anthropic** | Claude API                     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Grok**      | xAI models                     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **OpenRouter**| Community model hub            | API              | `services/llm_provider_service.py`      | ✅ Active |
| **GitHub API**| Version checking               | REST API         | `services/version_service.py`           | ✅ Active |
| **Confluence**| Knowledge base sync (future)   | REST API v2      | TBD: `services/confluence/`             | 📝 Planned |

### LLM Provider Capabilities

**Chat + Embeddings:**
- OpenAI: GPT-4o, GPT-4o-mini + text-embedding-3-small/large
- Google: Gemini 1.5/2.0 models + gemini-embedding-001
- Ollama: Local models (llama3, mistral, etc.) with embedding support

**Chat Only (No Embeddings):**
- Anthropic: Claude 3.5 Sonnet, Claude 3 Opus/Haiku
- Grok: grok-3-mini, grok-3 (xAI models)
- OpenRouter: Community-hosted models (various)

**Embedding Providers (UI Enforces Restriction):**
- ✅ OpenAI, Google, Ollama ONLY
- ❌ Anthropic, Grok, OpenRouter NOT supported for embeddings

### Confluence API Integration (To Implement)

**API Documentation:**
- Confluence REST API v2: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
- Confluence CQL: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/
- Python SDK: `atlassian-python-api` (https://atlassian-python-api.readthedocs.io/)

**Integration Pattern:**
```python
from atlassian import Confluence

class ConfluenceClient:
    def __init__(self, base_url: str, api_token: str):
        self.client = Confluence(url=base_url, token=api_token)

    async def cql_search(self, cql: str, expand: str = None):
        # CQL example: 'space = DEVDOCS AND lastModified >= "2025-10-01 10:00"'
        return self.client.cql(cql, expand=expand, limit=1000)

    async def get_page_ids_in_space(self, space_key: str) -> list[str]:
        # Lightweight deletion detection - IDs only, no content
        pages = self.client.get_all_pages_from_space(
            space=space_key, expand=None
        )
        return [p['id'] for p in pages]
```

---

## Development and Deployment

### Local Development Setup

1. **Environment Configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with required values:
   # - SUPABASE_URL (cloud or local)
   # - SUPABASE_SERVICE_KEY (use legacy key format for cloud)
   # - OPENAI_API_KEY (if using OpenAI provider)
   ```

2. **Backend Setup (Python 3.12):**
   ```bash
   cd python
   uv sync --group all    # Install all dependencies (dev + server + mcp + agents)
   uv run python -m src.server.main  # Run locally on port 8181
   ```

3. **Frontend Setup:**
   ```bash
   cd archon-ui-main
   npm install
   npm run dev            # Runs on port 3737
   ```

4. **Docker Development (Recommended):**
   ```bash
   make dev               # Hybrid mode: backend in Docker, frontend local
   # or
   make dev-docker        # Full Docker mode: all services containerized
   ```

### Build and Deployment Process

**Docker Compose Orchestration:**
```bash
docker compose up --build -d          # Build and start all services
docker compose --profile backend up -d # Backend only (for hybrid dev)
docker compose logs -f archon-server   # View server logs
docker compose logs -f archon-mcp      # View MCP server logs
docker compose restart archon-server   # Restart after code changes
docker compose down -v                 # Stop and remove volumes
```

**Service Ports:**
- Frontend (dev): `http://localhost:3737`
- Backend server: `http://localhost:8181`
- MCP server: `http://localhost:8051`
- Agents service: `http://localhost:8052`

### Testing

**Backend Tests (Pytest):**
```bash
cd python
uv run pytest                          # Run all tests
uv run pytest tests/test_api_essentials.py -v  # Specific test
uv run ruff check                      # Linter
uv run ruff check --fix                # Auto-fix
uv run mypy src/                       # Type check
```

**Frontend Tests (Vitest):**
```bash
cd archon-ui-main
npm run test                           # Watch mode
npm run test:ui                        # Vitest UI
npm run test:coverage:stream           # Coverage with streaming output
npx tsc --noEmit                       # TypeScript check
npm run biome:fix                      # Biome auto-fix (features/ only)
npm run lint:files src/path/to/file.tsx # ESLint (legacy code)
```

**Linting Shortcuts:**
```bash
make lint          # Run both frontend and backend linters
make lint-fe       # Frontend only (ESLint + Biome)
make lint-be       # Backend only (Ruff + MyPy)
```

---

## Enhancement Impact Analysis: Confluence Integration

### Summary

**Goal:** Integrate 4000+ Confluence Cloud pages into Archon's RAG system for code implementation assistance and documentation generation.

**Approach:** Direct Confluence API integration with Hybrid database schema (Option 3 from `CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md`).

**Timeline:** 1.5-2 weeks implementation (vs 3-4 weeks for separate tables approach).

**Code Reuse:** 90% - Leverage existing `document_storage_service.py` and `hybrid_search_strategy.py`.

### Required Changes

#### Backend Files to CREATE (~800 lines total)

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

#### Backend Files to MODIFY (Minimal Changes)

1. **`python/src/server/services/knowledge/knowledge_item_service.py`**
   - Add `'confluence'` to supported source types
   - Register Confluence spaces in `archon_sources` table

2. **`python/src/server/services/search/hybrid_search_strategy.py`** (OPTIONAL)
   - Add `LEFT JOIN confluence_pages` for metadata enrichment
   - Add Confluence-specific filters (space, JIRA links, user mentions)
   - **Core search already works without changes!**

#### Database Changes

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

#### Frontend Files to CREATE (Future Phase)

**Vertical Slice:** `archon-ui-main/src/features/confluence/`

1. **`services/confluenceService.ts`** - API client
2. **`hooks/useConfluenceQueries.ts`** - Query hooks & keys
3. **`components/ConfluenceSourceForm.tsx`** - Source creation form
4. **`components/ConfluenceSourceCard.tsx`** - Source display card
5. **`components/ConfluenceSyncStatus.tsx`** - Sync status & progress
6. **`types/index.ts`** - TypeScript types

#### Dependencies to Add

```toml
# python/pyproject.toml
[dependency-groups.server]
# Add these two lines:
atlassian-python-api = "^3.41.0"  # Confluence REST API client
markdownify = "^0.11.6"           # HTML to Markdown conversion
```

### Implementation Workflow

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

### Code Reuse Highlights

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

### Reference Documentation

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

## Summary of Current State (October 2025)

### What Was Implemented ✅

1. **Multi-LLM Provider Ecosystem** - OpenRouter, Anthropic, Grok integration
2. **Migration Tracking System** - Database migration versioning with UI
3. **Version Checking System** - GitHub release notifications
4. **Web Crawling Enhancements** - Domain filtering, improved robustness
5. **BMad Methodology Integration** - 100+ files for structured development
6. **Frontend Architecture Improvements** - TanStack Query, smart polling, ETag caching
7. **CASCADE DELETE Constraints** - Proper foreign key cleanup

### What Was Planned but Not Implemented ❌

1. **Confluence Integration** - Extensive docs (1,333+ lines), zero code ← **PRIMARY FOCUS**
2. **Google Drive Integration** - Abandoned in favor of direct Confluence API
3. **Docling Document Processing** - Commit mentions it, files missing
4. **Background Job Queue** - Identified as needed for long-running operations

### Current Version

- **Backend:** 0.1.0 (defined in `python/src/server/config/version.py`)
- **Database:** Schema versioned via `archon_migrations` table
- **Migrations:** 009 migrations applied (001-009 in 0.1.0 directory)
- **Next Migration:** 010 (Confluence tables) - ready to create

### Recommended Next Steps

1. **✅ PRIORITY: Implement Confluence Integration** (1.5-2 weeks)
   - Use `CONFLUENCE_RAG_INTEGRATION.md` as implementation roadmap
   - Create migration 010 (Confluence tables)
   - Implement services (~800 lines total)
   - Leverage 90% code reuse from existing infrastructure

2. **Complete Docling Integration** or remove references
   - Add missing `docling_processing.py` file
   - Or update documentation to reflect current state

3. **Add Background Job System** (Celery or RQ)
   - Essential for Confluence sync (long-running operations)
   - Scheduled re-indexing, batch document processing
   - Extends `archon_progress` table for job status

4. **Increase Test Coverage**
   - Integration tests for migration system
   - Integration tests for version checking
   - Load testing for Confluence sync (4000+ pages)

5. **Version 0.2.0 Release Planning**
   - Include Confluence integration
   - Migration tracking and multi-provider support
   - Version checking system

---

## Appendix: Useful Commands and References

### Frequently Used Commands

**Development:**
```bash
make dev               # Hybrid mode (backend Docker, frontend local)
make dev-docker        # Full Docker mode
make lint              # Run all linters
make test              # Run all tests
```

**Backend:**
```bash
cd python
uv sync --group all                    # Install dependencies
uv run python -m src.server.main       # Run server locally (8181)
uv run pytest                          # Run tests
uv run ruff check --fix                # Lint and fix
uv run mypy src/                       # Type check
```

**Frontend:**
```bash
cd archon-ui-main
npm run dev                            # Dev server (3737)
npm run test:ui                        # Vitest UI
npm run biome:fix                      # Auto-fix (features/ only)
npx tsc --noEmit                       # TypeScript check
```

**Docker:**
```bash
docker compose up --build -d           # Start all services
docker compose logs -f archon-server   # View logs
docker compose restart archon-server   # Restart after changes
docker compose down -v                 # Stop and clean
```

### Architecture Reference Documents

**Core Architecture:**
- `PRPs/ai_docs/ARCHITECTURE.md` - System overview
- `PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md` - TanStack Query patterns
- `PRPs/ai_docs/QUERY_PATTERNS.md` - Query hook patterns
- `PRPs/ai_docs/ETAG_IMPLEMENTATION.md` - ETag caching
- `PRPs/ai_docs/API_NAMING_CONVENTIONS.md` - API standards

**Confluence Integration:**
- `docs/bmad/CONFLUENCE_RAG_INTEGRATION.md` - **PRIMARY IMPLEMENTATION GUIDE** (1,333 lines)
- `docs/bmad/CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md` - Schema comparison
- `docs/bmad/brownfield-architecture.md` - **THIS FILE** (current state)

**Development Guides:**
- `CLAUDE.md` - Claude Code instructions (root directory)
- `.bmad-core/working-in-the-brownfield.md` - Brownfield methodology
- `migration/0.1.0/DB_UPGRADE_INSTRUCTIONS.md` - Migration guide

### Key Design Patterns

**Backend:**
- Service layer pattern (API route → Service → Database)
- Direct SQL (no ORM)
- Async-first with FastAPI lifespan events
- Multi-provider adapter pattern for LLMs

**Frontend:**
- Vertical slice architecture (features own their stack)
- Query-centric state (TanStack Query, no Redux)
- Smart polling with visibility awareness
- ETag caching for bandwidth optimization
- Optimistic updates with nanoid

**Database:**
- Hybrid schema for source integrations (metadata table + unified chunks)
- JSONB for flexible metadata storage
- pgvector for semantic search
- Materialized path for hierarchies

---

## Document Maintenance

This brownfield architecture document should be updated when:
- Major architectural changes are implemented
- New integration patterns are established
- Significant technical debt is resolved or introduced
- Version milestones are reached (0.2.0, 1.0.0, etc.)

**Current Maintainer:** Winston (Architect Agent)
**Last Updated:** October 6, 2025
**Next Review:** After Confluence integration completion (est. late October 2025)

---

*This document captures the TRUE state of the Archon codebase, including technical debt, architectural constraints, and integration patterns. It is optimized for AI agents performing feature additions, particularly the Confluence Knowledge Base integration using the Hybrid Schema approach.*
