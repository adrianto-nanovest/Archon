# Development and Deployment

## Local Development Setup

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

## Build and Deployment Process

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

## Testing

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
