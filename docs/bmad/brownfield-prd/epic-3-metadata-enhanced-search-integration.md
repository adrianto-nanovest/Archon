# Epic 3: Metadata-Enhanced Search Integration

**Epic Goal**: Enhance hybrid search with Confluence metadata enrichment enabling space, JIRA, hierarchy, and mention filters

**Integration Requirements**:
- Modify existing `hybrid_search_strategy.py` with LEFT JOIN to confluence_pages
- Add Confluence-specific filter parameters to search API
- Maintain existing search performance (<500ms response time)

## Story 3.1: Enhance Hybrid Search with Metadata JOIN

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

## Story 3.2: Implement Confluence-Specific Search Filters

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

## Story 3.3: Add Search Performance Optimization

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
