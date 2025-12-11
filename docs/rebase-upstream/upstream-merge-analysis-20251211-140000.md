# Upstream Merge Analysis Report

**Date**: 2025-12-11 14:00:00
**Current Branch**: feature/confluence-rag
**Upstream Branch**: upstream/main
**Analysis By**: Claude Code

## Executive Summary

- **Commits ahead of upstream**: 19
- **Commits behind upstream**: 57
- **Files modified on both sides**: 114
- **Predicted conflicts**: ~15-20 files (HIGH-RISK)
- **Recommended strategy**: Merge (with careful conflict resolution)
- **Estimated complexity**: HIGH

### Key Divergence Points

| Area | Local Changes | Upstream Changes |
|------|---------------|------------------|
| **Feature Focus** | Confluence RAG Integration (Epics 1-3) | Agent Work Orders, OpenRouter Embeddings |
| **Dependencies** | +atlassian-python-api, +markdownify, +docling | +zustand, +sse-starlette, +openrouter embeddings |
| **Docker Config** | Docker socket enabled | Docker socket removed (security fix) |
| **API Routes** | Removed agent_work_orders_proxy | Added agent_work_orders_proxy, openrouter_api |

---

## Repository State

### Current Branch Info
- **Branch**: feature/confluence-rag
- **Last commit**: 5b18119 - Story 3.2: Implement atomic chunk update strategy for zero-downtime sync
- **Uncommitted changes**:
  - M .DS_Store (ignored)
  - M archon-ui-main/package-lock.json
  - ?? package-lock.json

### Remotes Configuration
- **origin**: https://github.com/adrianto-nanovest/Archon.git
- **upstream**: https://github.com/coleam00/archon.git

### Common Ancestor
- **Commit**: 68fb4a8866 (pre-divergence point)

---

## Divergence Analysis

### Commits on Upstream (57 commits not in current branch)

#### Major Features
1. **Agent Work Orders** (~35 commits)
   - New microservice architecture (`python/src/agent_work_orders/`)
   - Zustand state management
   - SSE real-time updates
   - Repository configuration system
   - Supabase persistence

2. **OpenRouter Embeddings Support** (~8 commits)
   - New API route: `openrouter_api.py`
   - OpenRouter discovery service
   - Model validation and caching
   - Credential service updates

3. **Security/Infrastructure** (~5 commits)
   - CVE-2025-9074 fix: Docker socket removed
   - MCP HTTP health endpoint fixes
   - Bug report template updates

4. **Documentation Cleanup** (~3 commits)
   - Docusaurus documentation removed
   - README updates

5. **UI/UX Improvements** (~6 commits)
   - Style guide updates
   - Agent work order UI components
   - Layout changes

### Commits on Current Branch (19 commits not in upstream)

#### Confluence RAG Integration (Primary Feature)
1. **Epic 1**: Database Foundation & API Client
   - Story 1.1: confluence_pages schema migration
   - Story 1.2: ConfluenceClient wrapper
   - Story 1.3: Dependencies (atlassian-python-api, markdownify)
   - Story 1.4: Security audit
   - Story 1.5: Infrastructure validation

2. **Epic 2**: HTML-to-Markdown Processing
   - Story 2.1-2.7: Element handlers, macro handlers, utilities
   - Docling integration for document processing

3. **Epic 3**: Incremental Sync
   - Story 3.1: CQL-based sync service
   - Story 3.2: Atomic chunk update strategy

4. **BMad Framework** (Documentation/Planning)
   - `.bmad-core/` directory structure
   - Story definitions and QA gates
   - Architecture documentation

---

## Modified Files Summary (High-Risk)

### Critical Files Modified on BOTH Sides

| File | Risk | Local Intent | Upstream Intent |
|------|------|--------------|-----------------|
| `python/pyproject.toml` | **CRITICAL** | +confluence deps | +agent-work-orders deps, remove docker |
| `python/uv.lock` | **CRITICAL** | Lockfile differences | Different dependency tree |
| `docker-compose.yml` | **HIGH** | Keep docker socket | Remove docker socket (CVE fix) |
| `python/src/server/main.py` | **HIGH** | No agent-work-orders | +agent-work-orders proxy |
| `python/src/server/config/config.py` | **HIGH** | +ConfluenceSettings | -MCPMonitoringConfig, +openrouter |
| `python/src/server/services/credential_service.py` | **MEDIUM** | -openrouter embedding | +openrouter embedding |
| `archon-ui-main/package.json` | **MEDIUM** | TanStack versions | +zustand |
| `CLAUDE.md` | **MEDIUM** | +bmad, +confluence docs | Different structure |

### Files Only Modified Locally (Safe)
- All `python/src/server/services/confluence/**` files (NEW)
- All `docs/bmad/**` files (NEW)
- All `.bmad-core/**` files (NEW)
- All `migration/0.1.0/901_*.sql` files (NEW)
- All Confluence test files (NEW)

### Files Only Modified Upstream (Need to Accept)
- `python/src/agent_work_orders/**` (131 new files)
- `archon-ui-main/src/features/agent-work-orders/**` (48 new files)
- `python/src/server/api_routes/openrouter_api.py` (NEW)
- `python/src/server/services/openrouter_discovery_service.py` (NEW)

---

## Potential Conflicts

### HIGH-RISK Files (Will Require Manual Resolution)

#### 1. `python/pyproject.toml`
**Conflict Type**: Dependency
**Risk Level**: CRITICAL

**Current Branch Changes**:
```toml
# Added to server group:
"atlassian-python-api==4.0.7",
"markdownify==1.2.0",
"docling>=2.18.0",
"docker>=6.1.0",  # Re-enabled

# Added new group:
[project.optional-dependencies]
server-docling = ["docling[easyocr]>=2.18.0"]

# MyPy overrides for bs4, markdownify
```

**Upstream Changes**:
```toml
# Added to dependencies:
agent-work-orders = [
    "fastapi>=0.119.1", "uvicorn>=0.38.0",
    "sse-starlette>=2.3.3", "supabase==2.15.1", ...
]

# Removed docker (commented out for security)
# "docker>=6.1.0",  # REMOVED

# OpenRouter validation function added
```

**Resolution Strategy**:
1. Keep ALL Confluence dependencies from local
2. Accept ALL agent-work-orders dependencies from upstream
3. DECISION REQUIRED: Docker socket dependency
   - Option A: Keep docker (local needs it for container monitoring)
   - Option B: Remove docker (upstream security fix)
   - **Recommendation**: Keep docker, but use HTTP health check mode

---

#### 2. `docker-compose.yml`
**Conflict Type**: Configuration/Security
**Risk Level**: HIGH

**Current Branch**:
- Docker socket mounted: `/var/run/docker.sock:/var/run/docker.sock`

**Upstream**:
- Docker socket REMOVED (CVE-2025-9074 fix)
- New service: `archon-agent-work-orders` (profile-based)

**Resolution Strategy**:
1. Accept agent-work-orders service from upstream
2. DECISION REQUIRED: Docker socket mounting
   - Upstream removed for security
   - If needed, add explicit environment variable toggle
   - **Recommendation**: Accept upstream removal, use HTTP health checks

---

#### 3. `python/src/server/main.py`
**Conflict Type**: Router imports
**Risk Level**: HIGH

**Current Branch Removes**:
```python
# REMOVED these imports:
from .api_routes.agent_work_orders_proxy import router as agent_work_orders_router
from .api_routes.openrouter_api import router as openrouter_router

# REMOVED these router includes:
app.include_router(openrouter_router)
app.include_router(agent_work_orders_router)
```

**Upstream Adds**:
- Same imports/routers that local removed

**Resolution Strategy**:
1. Accept ALL upstream imports
2. Keep local exception handling changes (trivial)
3. Final file should include both agent_work_orders_proxy AND openrouter_api

---

#### 4. `python/src/server/config/config.py`
**Conflict Type**: Configuration dataclasses
**Risk Level**: HIGH

**Current Branch Adds**:
```python
# Added:
@dataclass
class ConfluenceSettings:
    docling_enabled: bool = True
    docling_max_file_size_mb: int = 50
    ...

def validate_confluence_url(url: str) -> bool:
    ...

# Environment config additions:
confluence_base_url: str | None = None
confluence_api_token: str | None = None
confluence_email: str | None = None
```

**Upstream Changes**:
```python
# Removed MCPMonitoringConfig (replaced with simpler check)
# Added OpenRouter validation

def validate_openrouter_api_key(api_key: str) -> bool:
    ...
```

**Resolution Strategy**:
1. Keep ConfluenceSettings (local)
2. Accept openrouter validation (upstream)
3. Determine if MCPMonitoringConfig is needed (likely not)

---

#### 5. `python/src/server/services/credential_service.py`
**Conflict Type**: Provider logic
**Risk Level**: MEDIUM

**Current Branch**:
```python
# Line 446: embedding_capable_providers excludes openrouter
embedding_capable_providers = {"openai", "google", "ollama"}
```

**Upstream**:
```python
# Line 446: embedding_capable_providers INCLUDES openrouter
embedding_capable_providers = {"openai", "google", "openrouter", "ollama"}
```

**Resolution Strategy**:
1. Accept upstream change (add "openrouter" to set)
2. This is a feature addition, no conflict

---

#### 6. `archon-ui-main/package.json`
**Conflict Type**: Dependencies
**Risk Level**: MEDIUM

**Current Branch**:
```json
{
  "@tanstack/react-query": "^5.90.2",
  "@tanstack/react-query-devtools": "^5.90.2",
  // NO zustand
}
```

**Upstream**:
```json
{
  "@tanstack/react-query": "^5.85.8",
  "@tanstack/react-query-devtools": "^5.85.8",
  "zustand": "^5.0.8"  // ADDED
}
```

**Resolution Strategy**:
1. Keep higher TanStack versions from local (^5.90.2)
2. Accept zustand from upstream
3. Regenerate package-lock.json after merge

---

### MEDIUM-RISK Files

| File | Conflict Type | Resolution |
|------|---------------|------------|
| `.gitignore` | Different entries | Merge both additions |
| `.env.example` | Different vars | Merge both additions |
| `CLAUDE.md` | Documentation | Accept local (more comprehensive) |
| `archon-ui-main/src/contexts/SettingsContext.tsx` | Feature flags | Accept upstream agent-work-orders |
| `archon-ui-main/src/components/settings/FeaturesSection.tsx` | UI options | Accept upstream |
| `archon-ui-main/src/App.tsx` | Routes | Accept upstream agent-work-orders routes |

### LOW-RISK Files (Auto-merge likely)
- Most test files
- Service files with whitespace-only changes
- Documentation files

---

## Recommended Merge Strategy

**Strategy**: MERGE (not rebase)

**Rationale**:
1. **19 local commits** - Too many for clean rebase
2. **Already pushed to origin** - Force-push would disrupt
3. **Preserve commit history** - Important for audit trail
4. **Feature branch** - Merge preserves feature boundary

**Pros**:
- Preserves all commit history
- Clear merge commit shows integration point
- Easier to bisect if issues arise
- No force-push required

**Cons**:
- Creates merge commit
- History not linear
- Slightly harder to read

---

## Execution Plan

### Pre-Merge Checklist
- [ ] All local changes committed or stashed
- [ ] Upstream remote configured correctly
- [x] Latest changes fetched from both remotes
- [ ] Backup branch created: `git branch backup/feature-confluence-rag-20251211`
- [ ] Team notified (if applicable)
- [ ] CI/CD passing on current branch (verify tests)

### Step-by-Step Instructions

#### Phase 1: Preparation

```bash
# 1. Create backup branch
git branch backup/feature-confluence-rag-20251211

# 2. Stash any uncommitted changes
git stash -m "Pre-merge stash"

# 3. Verify clean working directory
git status

# 4. Ensure on correct branch
git checkout feature/confluence-rag
```

#### Phase 2: Execute Merge

```bash
# Start the merge
git merge upstream/main --no-ff -m "Merge upstream/main: Agent Work Orders + OpenRouter Embeddings"
```

**Expected conflicts** (resolve in order):

1. `python/pyproject.toml` - See resolution strategy above
2. `python/uv.lock` - Regenerate with `uv lock` after pyproject.toml
3. `docker-compose.yml` - See resolution strategy above
4. `python/src/server/main.py` - Add back imports removed locally
5. `python/src/server/config/config.py` - Merge both configurations
6. `python/src/server/services/credential_service.py` - Add openrouter
7. `archon-ui-main/package.json` - Merge dependencies

#### Phase 3: Resolve Conflicts

For each conflicted file:

**1. python/pyproject.toml**
```bash
# Open file, merge ALL dependencies from both branches
# Keep:
#   - atlassian-python-api, markdownify, docling (local)
#   - agent-work-orders group (upstream)
#   - openrouter validation (upstream)
# Decision: docker (recommend keep, configure via env var)
git add python/pyproject.toml
```

**2. python/uv.lock**
```bash
# After pyproject.toml is resolved:
uv lock
git add python/uv.lock
```

**3. docker-compose.yml**
```bash
# Accept archon-agent-work-orders service
# Decision on docker socket (recommend remove per CVE)
git add docker-compose.yml
```

**4. python/src/server/main.py**
```bash
# Add back all imports:
from .api_routes.agent_work_orders_proxy import router as agent_work_orders_router
from .api_routes.openrouter_api import router as openrouter_router

# Add back router includes:
app.include_router(openrouter_router)
app.include_router(agent_work_orders_router)

git add python/src/server/main.py
```

**5. python/src/server/config/config.py**
```bash
# Keep ConfluenceSettings class (local)
# Keep validate_confluence_url function (local)
# Add validate_openrouter_api_key function (upstream)
# Add environment config for confluence

git add python/src/server/config/config.py
```

**6. python/src/server/services/credential_service.py**
```bash
# Change line to include openrouter:
embedding_capable_providers = {"openai", "google", "openrouter", "ollama"}

git add python/src/server/services/credential_service.py
```

**7. archon-ui-main/package.json**
```bash
# Keep higher TanStack versions: ^5.90.2
# Add zustand: ^5.0.8

git add archon-ui-main/package.json
```

**8. Regenerate frontend lock**
```bash
cd archon-ui-main
npm install
git add package-lock.json
cd ..
```

#### Phase 4: Verification

```bash
# 1. Run backend linters
cd python
uv run ruff check --fix
uv run mypy src/ --no-error-summary
cd ..

# 2. Run frontend linters
cd archon-ui-main
npm run lint
npm run biome
cd ..

# 3. Run backend tests
cd python
uv run pytest -x
cd ..

# 4. Run frontend tests
cd archon-ui-main
npm run test
cd ..

# 5. Build and verify Docker
docker compose build
docker compose up -d
# Wait 30 seconds
docker compose logs archon-server | tail -50
docker compose logs archon-mcp | tail -50
docker compose down
```

#### Phase 5: Finalize

```bash
# Complete merge
git merge --continue

# Or if conflicts resolved via commit:
git commit -m "Merge upstream/main: Agent Work Orders, OpenRouter Embeddings, Security Fixes

Integrated:
- Agent Work Orders microservice (profile-based)
- OpenRouter embeddings support
- CVE-2025-9074 security fix (docker socket removed)
- MCP HTTP health endpoint improvements

Local features preserved:
- Confluence RAG integration (Epics 1-3)
- BMad framework and documentation
- Docling document processing"

# Push to origin
git push origin feature/confluence-rag
```

---

## Rollback Procedures

### During Merge (If Something Goes Wrong)

```bash
# Abort the merge
git merge --abort

# Return to pre-merge state
git checkout feature/confluence-rag
```

### After Merge (If Issues Discovered)

```bash
# Option 1: Reset to backup
git reset --hard backup/feature-confluence-rag-20251211

# Option 2: Revert merge commit
git revert -m 1 <merge-commit-hash>
```

---

## Risk Assessment

### HIGH Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Dependency conflicts in pyproject.toml | Build failure | Careful merge, regenerate lockfile |
| Docker socket security decision | Security vulnerability OR broken MCP monitoring | Document decision, configure via env var |
| Agent Work Orders integration | May need additional config | Follow upstream docs |

### MEDIUM Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| TanStack Query version mismatch | Runtime errors | Use higher version (local) |
| Zustand state conflicts | UI state issues | Test agent work orders feature |
| OpenRouter embedding config | Missing provider option | Verify credential_service merge |

### LOW Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test file conflicts | CI failures | Auto-merge likely |
| Documentation conflicts | Incorrect docs | Review CLAUDE.md |

---

## Dependencies and Breaking Changes

### Upstream Dependency Changes

**Python (pyproject.toml)**:
- ADDED: `sse-starlette>=2.3.3` (agent work orders)
- REMOVED: `docker>=6.1.0` (security)
- ADDED (agent-work-orders group): `fastapi>=0.119.1`, `uvicorn>=0.38.0`, etc.

**JavaScript (package.json)**:
- ADDED: `zustand: ^5.0.8` (state management)
- DOWNGRADED: `@tanstack/react-query` (^5.85.8 vs local ^5.90.2)

### Potential Breaking Changes

1. **Docker socket removal** - MCP monitoring mode changed
2. **Agent Work Orders API** - New endpoints added
3. **OpenRouter embeddings** - New provider option

---

## Testing Requirements

### Pre-Merge Tests
- [ ] `uv run pytest` passes
- [ ] `npm run test` passes
- [ ] Linting passes (ruff, eslint, biome)
- [ ] TypeScript compiles

### Post-Merge Tests
- [ ] Full Docker Compose startup successful
- [ ] MCP health check works (HTTP mode)
- [ ] Knowledge base search functional
- [ ] Confluence sync (if configured) works
- [ ] Agent Work Orders feature works (if enabled)
- [ ] OpenRouter embeddings (if configured) works

### Integration Tests
- [ ] End-to-end crawl → embed → search workflow
- [ ] Project/Task management
- [ ] All API endpoints respond correctly

---

## Additional Notes

### Decision Points Requiring User Input

1. **Docker Socket**: Accept upstream removal OR keep local version?
   - Upstream rationale: CVE-2025-9074 (CVSS 9.3)
   - Local need: May need for container monitoring
   - **Recommendation**: Accept removal, use HTTP health checks

2. **Agent Work Orders**: Enable by default?
   - Currently profile-based (`--profile work-orders`)
   - **Recommendation**: Keep profile-based, opt-in

3. **TanStack Version**: Use local higher version OR upstream?
   - Local: ^5.90.2, Upstream: ^5.85.8
   - **Recommendation**: Keep local (higher is newer)

### Files to Review After Merge

1. `archon-ui-main/src/App.tsx` - Ensure all routes work
2. `archon-ui-main/src/contexts/SettingsContext.tsx` - Feature flags correct
3. `python/src/server/config/service_discovery.py` - Service URLs correct
4. `.env.example` - All variables documented

---

## Next Steps

1. **Review this analysis document** thoroughly
2. **Create backup branch** before starting
3. **Allocate ~2-4 hours** for merge and testing
4. **Have rollback plan ready** (documented above)
5. When ready, execute: `/execute-upstream-merge docs/rebase-upstream/upstream-merge-analysis-20251211-140000.md`

---

*Generated by Claude Code on 2025-12-11 14:00*
