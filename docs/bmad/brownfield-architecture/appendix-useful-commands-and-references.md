# Appendix: Useful Commands and References

## Frequently Used Commands

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

## Architecture Reference Documents

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

## Key Design Patterns

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
