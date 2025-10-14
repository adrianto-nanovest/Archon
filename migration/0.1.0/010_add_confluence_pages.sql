-- Migration: 010_add_confluence_pages.sql
-- Description: Create confluence_pages table with metadata storage and performance indexes for Confluence Cloud integration
-- Version: 0.1.0
-- Author: Archon Team
-- Date: 2025-10-10

-- ============================================================================
-- CONFLUENCE PAGES TABLE
-- ============================================================================
-- Stores Confluence page metadata using Hybrid Schema approach:
-- - Rich metadata (~15KB) stored in this dedicated table
-- - Chunks stored in existing archon_crawled_pages table (unified storage)
-- - Linked via metadata->>'page_id' for 90% code reuse
-- ============================================================================

CREATE TABLE IF NOT EXISTS confluence_pages (
  -- Primary identifier (Confluence native page ID)
  page_id TEXT PRIMARY KEY,

  -- Foreign key to archon_sources with CASCADE DELETE
  source_id TEXT NOT NULL REFERENCES archon_sources(source_id) ON DELETE CASCADE,

  -- Core fields for filtering and display
  space_key TEXT NOT NULL,
  title TEXT NOT NULL,
  version INTEGER NOT NULL,
  last_modified TIMESTAMPTZ NOT NULL,

  -- Soft delete tracking (preserves metadata for audit trail)
  is_deleted BOOLEAN DEFAULT FALSE,

  -- Materialized path for efficient hierarchy queries
  -- Pattern: "/parent_id/child_id/grandchild_id"
  -- Enables: descendants (LIKE '/parent/%'), siblings (~ '^/parent/[^/]+$'), breadcrumbs
  path TEXT,

  -- Rich metadata stored ONCE per page (~15 KB per page)
  -- Structure: {
  --   "ancestors": [{id, title, url}, ...],
  --   "children": [{id, title, url}, ...],
  --   "created_by": {account_id, display_name, email, profile_url},
  --   "jira_issue_links": [{issue_key, issue_url}, ...],
  --   "user_mentions": [{account_id, display_name, profile_url}, ...],
  --   "internal_links": [{page_id, page_title, page_url}, ...],
  --   "external_links": [{title, url}, ...],
  --   "asset_links": [{id, title, type, download_url}, ...],
  --   "word_count": 7351,
  --   "content_length": 75919
  -- }
  metadata JSONB NOT NULL,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add table-level comments
COMMENT ON TABLE confluence_pages IS 'Stores Confluence page metadata using Hybrid Schema approach - chunks stored in archon_crawled_pages for unified search';
COMMENT ON COLUMN confluence_pages.page_id IS 'Confluence native page ID (primary key)';
COMMENT ON COLUMN confluence_pages.source_id IS 'Foreign key to archon_sources with CASCADE DELETE for complete cleanup';
COMMENT ON COLUMN confluence_pages.space_key IS 'Confluence space key for filtering (indexed)';
COMMENT ON COLUMN confluence_pages.title IS 'Page title for display and search';
COMMENT ON COLUMN confluence_pages.version IS 'Confluence page version number for incremental sync tracking';
COMMENT ON COLUMN confluence_pages.last_modified IS 'Last modified timestamp from Confluence for CQL-based sync';
COMMENT ON COLUMN confluence_pages.is_deleted IS 'Soft delete flag - preserves metadata for audit trail while removing chunks';
COMMENT ON COLUMN confluence_pages.path IS 'Materialized path for hierarchy queries (pattern: /parent_id/child_id/...)';
COMMENT ON COLUMN confluence_pages.metadata IS 'Rich JSONB metadata (~15KB): ancestors, children, JIRA links, mentions, links, assets, word count';

-- ============================================================================
-- PERFORMANCE INDEXES ON CONFLUENCE_PAGES
-- ============================================================================

-- Index 1: Source ID (partial - excludes soft-deleted pages)
CREATE INDEX IF NOT EXISTS idx_confluence_pages_source
  ON confluence_pages(source_id)
  WHERE is_deleted = FALSE;
COMMENT ON INDEX idx_confluence_pages_source IS 'Partial index for filtering by source, excludes soft-deleted pages';

-- Index 2: Space Key (partial - excludes soft-deleted pages)
CREATE INDEX IF NOT EXISTS idx_confluence_pages_space
  ON confluence_pages(space_key)
  WHERE is_deleted = FALSE;
COMMENT ON INDEX idx_confluence_pages_space IS 'Partial index for filtering by Confluence space, excludes soft-deleted pages';

-- Index 3: Version tracking (composite for incremental sync)
CREATE INDEX IF NOT EXISTS idx_confluence_pages_version
  ON confluence_pages(page_id, version);
COMMENT ON INDEX idx_confluence_pages_version IS 'Composite index for version tracking during incremental sync';

-- Index 4: Materialized path (btree with text_pattern_ops for LIKE queries)
CREATE INDEX IF NOT EXISTS idx_confluence_pages_path
  ON confluence_pages USING btree(path text_pattern_ops);
COMMENT ON INDEX idx_confluence_pages_path IS 'Btree index with text_pattern_ops for efficient hierarchy queries (LIKE /parent_id/%)';

-- Index 5: JIRA issue links (GIN with jsonb_path_ops for exact matches)
CREATE INDEX IF NOT EXISTS idx_confluence_pages_jira
  ON confluence_pages
  USING gin((metadata->'jira_issue_links') jsonb_path_ops);
COMMENT ON INDEX idx_confluence_pages_jira IS 'GIN index for fast JIRA issue link queries using @> containment operator';

-- Index 6: User mentions (GIN with jsonb_path_ops for exact matches)
CREATE INDEX IF NOT EXISTS idx_confluence_pages_mentions
  ON confluence_pages
  USING gin((metadata->'user_mentions') jsonb_path_ops);
COMMENT ON INDEX idx_confluence_pages_mentions IS 'GIN index for fast user mention queries using @> containment operator';

-- ============================================================================
-- CHUNK LINKAGE INDEX ON EXISTING ARCHON_CRAWLED_PAGES
-- ============================================================================
-- Links Confluence chunks back to their parent pages via metadata->>'page_id'
-- Partial index: only indexes chunks that have page_id metadata (Confluence chunks)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_crawled_pages_confluence_page_id
  ON archon_crawled_pages ((metadata->>'page_id'))
  WHERE metadata ? 'page_id';
COMMENT ON INDEX idx_crawled_pages_confluence_page_id IS 'Links Confluence chunks back to confluence_pages via metadata->>page_id (partial index for Confluence chunks only)';

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================
-- Following pattern from migration 008_add_migration_tracking.sql
-- ============================================================================

-- Enable Row Level Security
ALTER TABLE confluence_pages ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (makes this migration idempotent)
DROP POLICY IF EXISTS "Allow service role full access to confluence_pages" ON confluence_pages;
DROP POLICY IF EXISTS "Allow authenticated users to read confluence_pages" ON confluence_pages;

-- Service role has full access (backend operations)
CREATE POLICY "Allow service role full access to confluence_pages" ON confluence_pages
    FOR ALL USING (auth.role() = 'service_role');

-- Authenticated users can only read Confluence pages (no modification)
CREATE POLICY "Allow authenticated users to read confluence_pages" ON confluence_pages
    FOR SELECT TO authenticated
    USING (true);

-- ============================================================================
-- SELF-RECORDING MIGRATION TRACKING
-- ============================================================================
-- Records this migration in archon_migrations table for tracking
-- Uses ON CONFLICT DO NOTHING for idempotency
-- ============================================================================

INSERT INTO archon_migrations (version, migration_name)
VALUES ('0.1.0', '010_add_confluence_pages')
ON CONFLICT (version, migration_name) DO NOTHING;
