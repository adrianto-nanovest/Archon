-- Migration: 900_add_source_type_column.sql
-- Description: Add source_type column to archon_sources table to differentiate between web crawl and Confluence sources
-- Version: 0.1.0
-- Author: Archon Team
-- Date: 2025-12-12

-- ============================================================================
-- SOURCE TYPE COLUMN
-- ============================================================================
-- Adds source_type column to archon_sources to distinguish between:
-- - 'web' (default): Web crawl and document upload sources
-- - 'confluence': Confluence Cloud integration sources
-- ============================================================================

-- Add source_type column with default 'web' for existing sources
ALTER TABLE archon_sources
ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'web';

-- Add constraint to validate source_type values
ALTER TABLE archon_sources
DROP CONSTRAINT IF EXISTS archon_sources_source_type_check;

ALTER TABLE archon_sources
ADD CONSTRAINT archon_sources_source_type_check
CHECK (source_type IN ('web', 'confluence'));

-- Create index for efficient filtering by source_type
CREATE INDEX IF NOT EXISTS idx_archon_sources_source_type
ON archon_sources(source_type);

-- Add column comment
COMMENT ON COLUMN archon_sources.source_type IS 'Type of source: web (crawl/upload) or confluence (Confluence Cloud integration)';

-- ============================================================================
-- SELF-RECORDING MIGRATION TRACKING
-- ============================================================================
-- Records this migration in archon_migrations table for tracking
-- Uses ON CONFLICT DO NOTHING for idempotency
-- ============================================================================

INSERT INTO archon_migrations (version, migration_name)
VALUES ('0.1.0', '900_add_source_type_column')
ON CONFLICT (version, migration_name) DO NOTHING;
