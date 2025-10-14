# Data Models and APIs

## Database Schema (SQL-based, No ORM!)

**Schema Location:** `migration/complete_setup.sql`

The database uses **direct SQL** with no ORM framework. All schemas are defined in SQL migration scripts and accessed via `asyncpg` or Supabase SDK.

### Key Tables

#### Knowledge Base Tables

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

#### Confluence Tables (TO CREATE in migration 010)

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

#### Project Management Tables (Optional Feature)

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

#### Configuration Tables

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

## API Specifications

**API Location:** `python/src/server/api_routes/`

All APIs follow RESTful patterns with JSON request/response. No GraphQL, no gRPC.

### Knowledge Base APIs (`knowledge_api.py`)

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

### Confluence APIs (`confluence_api.py` - TO CREATE)

```
POST   /api/confluence/sources          # Create Confluence source
GET    /api/confluence/sources          # List Confluence sources
POST   /api/confluence/{id}/sync        # Trigger manual sync
GET    /api/confluence/{id}/status      # Get sync status
DELETE /api/confluence/{id}             # Delete source (CASCADE)
GET    /api/confluence/{id}/pages       # List pages in space
```

### Migration APIs (`migration_api.py` - NEW)

```
GET    /api/migrations/status           # Get migration status
GET    /api/migrations/pending          # List pending migrations
```

### Version APIs (`version_api.py` - NEW)

```
GET    /api/version/current             # Current version info
GET    /api/version/check               # Check for updates (1-hour cache)
POST   /api/version/clear-cache         # Force refresh
```

### Projects APIs (`projects_api.py`)

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
