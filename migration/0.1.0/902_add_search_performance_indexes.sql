-- Migration: 902_add_search_performance_indexes.sql
-- Description: Add composite indexes for optimal Confluence search performance (Story 4.3)
-- Version: 0.1.0
-- Author: Archon Team
-- Date: 2025-12-12
-- Related Story: 4.3 - Add Search Performance Optimization

-- ============================================================================
-- COMPOSITE INDEX FOR CONFLUENCE SEARCH
-- ============================================================================
-- Purpose: Optimize search queries that filter by space_key and lookup by page_id
--
-- Query patterns this index optimizes:
-- 1. Story 4.2 filters: WHERE space_key = 'DEVDOCS' (most common filter)
-- 2. Batch lookups in _fetch_confluence_metadata(): WHERE page_id IN (...)
-- 3. Combined queries: WHERE space_key = 'DEVDOCS' AND page_id IN (...)
--
-- Design rationale:
-- - space_key as first column: Most common filter in Confluence-specific searches
-- - page_id as second column: Covers batch lookups for metadata enrichment
-- - Partial index (WHERE is_deleted = FALSE): Excludes soft-deleted pages, reducing index size
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_confluence_search
  ON confluence_pages(space_key, page_id)
  WHERE is_deleted = FALSE;

COMMENT ON INDEX idx_confluence_search IS 'Composite index for Confluence search: space_key filtering + page_id batch lookups (excludes soft-deleted pages)';

-- Update table statistics for optimal query planning
ANALYZE confluence_pages;

-- ============================================================================
-- PARTIAL INDEX FOR CONFLUENCE CHUNKS IN ARCHON_CRAWLED_PAGES
-- ============================================================================
-- Purpose: Optimize extraction of page_ids during metadata enrichment
--
-- Note: The index idx_crawled_pages_confluence_page_id already exists in
-- migration 901_add_confluence_pages.sql and covers this use case.
-- This index is created for redundancy verification and will silently
-- succeed if the existing index covers the same pattern.
--
-- Query pattern this optimizes:
-- - Extract page_ids from search results: SELECT metadata->>'page_id' FROM archon_crawled_pages
-- - Used in HybridSearchStrategy._fetch_confluence_metadata() for batch lookups
--
-- Design rationale:
-- - Expression index on metadata->>'page_id': Directly indexes the page_id value
-- - Partial index (WHERE metadata ? 'page_id'): Only indexes Confluence chunks
-- ============================================================================

-- This index already exists in 901_add_confluence_pages.sql, but we ensure it exists
-- using IF NOT EXISTS for idempotency
CREATE INDEX IF NOT EXISTS idx_crawled_pages_confluence_only
  ON archon_crawled_pages ((metadata->>'page_id'))
  WHERE metadata ? 'page_id';

COMMENT ON INDEX idx_crawled_pages_confluence_only IS 'Partial index for Confluence chunks only - optimizes page_id extraction for metadata enrichment';

-- Update table statistics for optimal query planning
ANALYZE archon_crawled_pages;

-- ============================================================================
-- SELF-RECORDING MIGRATION TRACKING
-- ============================================================================
-- Records this migration in archon_migrations table for tracking
-- Uses ON CONFLICT DO NOTHING for idempotency
-- ============================================================================

INSERT INTO archon_migrations (version, migration_name)
VALUES ('0.1.0', '902_add_search_performance_indexes')
ON CONFLICT (version, migration_name) DO NOTHING;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- To verify index usage after applying this migration, run:
-- EXPLAIN ANALYZE
-- SELECT page_id, space_key, title, path, metadata
-- FROM confluence_pages
-- WHERE space_key = 'DEVDOCS'
-- AND page_id IN ('page1', 'page2', 'page3')
-- AND is_deleted = FALSE;
-- ============================================================================
