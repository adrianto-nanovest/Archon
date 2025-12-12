# Source Tree and Module Organization

## Project Structure (Actual - October 2025)

```text
archon/
├── python/                          # Backend monolith
│   ├── src/
│   │   ├── server/                  # Core business logic (port 8181)
│   │   │   ├── api_routes/          # FastAPI routers
│   │   │   │   ├── knowledge_api.py         # RAG, crawling, upload
│   │   │   │   ├── confluence_api.py        # Confluence source management, sync
│   │   │   │   ├── projects_api.py          # Project/task CRUD
│   │   │   │   ├── migration_api.py         # Migration status
│   │   │   │   ├── version_api.py           # Version checking
│   │   │   │   └── (12 total routers)
│   │   │   ├── services/            # Business logic layer
│   │   │   │   ├── knowledge/               # Knowledge base management
│   │   │   │   │   └── knowledge_item_service.py
│   │   │   │   ├── storage/                 # Document ingestion
│   │   │   │   │   └── document_storage_service.py  # **REUSE FOR CONFLUENCE**
│   │   │   │   ├── search/                  # Hybrid search strategies
│   │   │   │   │   └── hybrid_search_strategy.py    # **ALREADY WORKS WITH CONFLUENCE**
│   │   │   │   ├── embeddings/              # Multi-provider embeddings
│   │   │   │   ├── crawling/                # Web crawling with domain filtering
│   │   │   │   ├── confluence/              # Confluence Cloud integration
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── confluence_client.py         # REST API v2 client
│   │   │   │   │   ├── confluence_processor.py      # HTML → Markdown pipeline
│   │   │   │   │   ├── confluence_sync_service.py   # CQL-based incremental sync
│   │   │   │   │   ├── confluence_validator.py      # Input validation
│   │   │   │   │   ├── docling_processor.py         # PDF/Office processing
│   │   │   │   │   ├── metadata_extractor.py        # JIRA, mentions extraction
│   │   │   │   │   ├── table_processor.py           # Hierarchical markdown tables
│   │   │   │   │   ├── macro_handlers/              # Confluence macro processors
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── base.py                  # BaseMacroHandler
│   │   │   │   │   │   ├── attachment_macro.py      # File attachments
│   │   │   │   │   │   ├── code_macro.py            # Code blocks
│   │   │   │   │   │   ├── embed_macro.py           # YouTube/Maps embeds
│   │   │   │   │   │   ├── generic_macro.py         # Unknown macro fallback
│   │   │   │   │   │   ├── jira_macro.py            # 3-tier JIRA extraction
│   │   │   │   │   │   └── panel_macro.py           # Info/Note/Warning panels
│   │   │   │   │   ├── element_handlers/            # HTML element processors
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── base.py                  # BaseElementHandler
│   │   │   │   │   │   ├── image_handler.py         # Attachment tracking
│   │   │   │   │   │   ├── link_handler.py          # Page links with bulk API
│   │   │   │   │   │   ├── simple_elements.py       # Emoticons, time, inline
│   │   │   │   │   │   └── user_handler.py          # User mentions
│   │   │   │   │   └── utils/                       # Shared utilities
│   │   │   │   │       ├── __init__.py
│   │   │   │   │       ├── deduplication.py         # Link/issue deduplication
│   │   │   │   │       ├── html_utils.py            # BeautifulSoup helpers
│   │   │   │   │       └── url_converter.py         # Iframe URL conversion
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
│       ├── 009_add_cascade_delete_constraints.sql
│       ├── 010_add_provider_placeholders.sql # LLM providers
│       ├── 011_add_page_metadata_table.sql
│       ├── 900_add_source_type_column.sql    # Confluence source type
│       ├── 901_add_confluence_pages.sql      # Confluence pages table
│       └── 902_add_search_performance_indexes.sql  # Search optimization
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

## Key Modules and Their Purpose

### Core Services (Backend)

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

### Knowledge Base Services (Critical for Confluence)

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

### LLM & Embedding Services

- **`llm_provider_service.py`**: Multi-provider LLM orchestration
  - Chat providers: OpenAI, Google, Ollama, Anthropic, Grok, OpenRouter
  - Embedding providers: OpenAI, Google, Ollama (UI enforces this subset)
  - Universal client pattern with provider-specific adapters

- **`embedding_service.py`**: Embedding generation with retry logic
  - Supports text-embedding-3-small/large (OpenAI)
  - Supports gemini-embedding-001 (Google)
  - Supports local Ollama models
  - Batch processing for efficiency

### Confluence Integration Services

- **`confluence_client.py`**: Confluence REST API v2 integration
  - CQL search for incremental sync
  - Bulk user/page lookups (N+1 prevention)
  - Rate limit handling with exponential backoff

- **`confluence_sync_service.py`**: CQL-based incremental sync orchestration
  - Atomic chunk update strategy (zero-downtime)
  - Sync observability and metrics tracking
  - Deletion detection with configurable strategies

- **`confluence_processor.py`**: Five-pass HTML → Markdown pipeline
  - Pass 1: Process Confluence macros (code, panels, JIRA, attachments)
  - Pass 2: Process special HTML elements (users, links, images)
  - Pass 3: Process tables (hierarchical markdown conversion)
  - Pass 4: Convert to markdown (markdownify with ATX headings)
  - Pass 5: Extract metadata (JIRA links, mentions, assets)

- **`macro_handlers/`**: Modular Confluence macro processors
  - Code blocks, panels, JIRA macros, attachments, embeds

- **`element_handlers/`**: HTML element processors
  - User mentions, page links, images with bulk API resolution

- **`table_processor.py`**: Hierarchical markdown table conversion
  - Colspan/rowspan content duplication for RAG optimization

### Migration & Versioning

- **`migration_service.py`**: Database migration tracking
  - Tracks applied migrations in `archon_migrations` table
  - Self-recording pattern (migration 008 records itself + 001-007)
  - Checksum verification for integrity

- **`version_service.py`**: GitHub release checking
  - Semantic version comparison
  - 1-hour cache to avoid rate limits
  - Update notifications in Settings UI

---
