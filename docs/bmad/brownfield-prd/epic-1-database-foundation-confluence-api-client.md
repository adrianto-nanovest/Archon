# Epic 1: Database Foundation & Confluence API Client

**Epic Goal**: Establish database schema for Confluence metadata storage and implement authenticated API client for Confluence Cloud REST API v2

**Integration Requirements**:
- Migration 010 must be compatible with existing migration tracking system
- API client must handle authentication, rate limiting, and error handling
- No modifications to existing `archon_crawled_pages` or `archon_sources` tables

## Story 1.1: Create Confluence Pages Database Schema

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

## Story 1.2: Implement Confluence API Client Wrapper

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

## Story 1.3: Add Confluence Dependencies and Configuration

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

## Story 1.4: Security Audit of Confluence Dependencies

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

## Story 1.5: Validate Existing Infrastructure for Epic 2 Integration

As a **backend developer**,
I want **to verify existing document processing infrastructure can handle Confluence content**,
so that **Epic 2 implementation can proceed without infrastructure modifications**.

**Acceptance Criteria**:
1. Verify `document_storage_service.add_documents_to_supabase()` accepts Markdown input and returns chunk IDs
2. Confirm `ProgressTracker` supports custom operation types (e.g., "confluence_sync")
3. Validate `archon_crawled_pages` table schema supports JSONB metadata field with nested structures
4. Test chunk replacement flow with mock Confluence data (create → mark pending deletion → replace → delete)
5. Verify search queries correctly filter chunks by source_id (no cross-source pollution)
6. Confirm CASCADE DELETE works for source deletion (removes all pages and chunks)
7. Test atomic transaction rollback for failed chunk updates (old chunks remain searchable)
8. Validate ETag caching pattern works with Confluence API endpoints

**Integration Verification**:
- IV1: `document_storage_service` successfully chunks 1000+ word Markdown document with code blocks and tables
- IV2: `ProgressTracker` updates visible in `/api/progress/active` endpoint with custom metadata
- IV3: Mock Confluence metadata (JIRA links, mentions, page links) stored in `archon_crawled_pages.metadata` JSONB column
- IV4: Search results correctly isolated by source_id (create 2 sources, verify no cross-contamination)
- IV5: Source deletion removes all dependent records (verify CASCADE to confluence_pages and chunks)
- IV6: Failed chunk update transaction rolls back cleanly (old chunks still searchable, no orphaned data)

---