# Recent Major Changes (August - October 2025)

## 1. Multi-LLM Provider Ecosystem ✅ IMPLEMENTED

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

## 2. Migration Tracking System ✅ IMPLEMENTED

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

## 3. Version Checking System ✅ IMPLEMENTED

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

## 4. Web Crawling Enhancements ✅ IMPLEMENTED

**Changes:**
- Advanced domain filtering (whitelist/blacklist) in `crawling_service.py`
- Edit Crawler Configuration dialog with metadata viewer
- Auto-expand advanced configuration options in UI
- Improved robustness and error handling

## 5. BMad Methodology Integration 🆕 INTEGRATED

**Purpose:** Structured agent-based development methodology for brownfield projects.

**Directory Structure:**
- `.bmad-core/` - Complete framework (100+ files)
  - `agents/` - 10 agent roles (analyst, architect, dev, pm, po, qa, etc.)
  - `tasks/` - 23 task templates
  - `templates/` - 13 document templates
  - `workflows/` - 6 workflow definitions
- `.claude/commands/BMad/` - Mirror for Claude Code integration

**Impact:** Provides structured approach for requirements gathering, story creation, quality assurance.

## 6. Frontend Architecture Improvements ✅ IMPLEMENTED

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
