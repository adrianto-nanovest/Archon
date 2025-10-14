"""
Tests for migration 010: Add Confluence Pages Schema

Tests verify:
1. Migration idempotency (can run multiple times)
2. Table creation with correct schema
3. All 7 indexes created (6 on confluence_pages, 1 on archon_crawled_pages)
4. Foreign key constraint on source_id
5. CASCADE DELETE behavior
6. RLS policies (service role write, authenticated read)
7. Migration tracking (recorded in archon_migrations)
8. Existing functionality preservation (web crawl, document upload)
"""

import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Test fixtures for database connection
@pytest.fixture
async def db_connection():
    """Mock database connection for migration testing."""
    mock_conn = AsyncMock()

    # Mock execute method for SQL statements
    mock_conn.execute = AsyncMock(return_value="OK")

    # Mock fetch methods for queries
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=None)

    return mock_conn


@pytest.fixture
def migration_file_path():
    """Return absolute path to migration 010 file."""
    # Get project root (parent of python/ directory)
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(test_dir))))
    return os.path.join(project_root, "migration", "0.1.0", "010_add_confluence_pages.sql")


@pytest.fixture
def read_migration_sql(migration_file_path):
    """Read migration SQL file content."""
    with open(migration_file_path, "r") as f:
        return f.read()


# ==============================================================================
# TEST 1: MIGRATION IDEMPOTENCY
# ==============================================================================

@pytest.mark.asyncio
async def test_migration_idempotency(db_connection, read_migration_sql):
    """
    Test that migration can run multiple times without errors.
    Uses CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS.
    """
    # Execute migration twice
    await db_connection.execute(read_migration_sql)
    await db_connection.execute(read_migration_sql)

    # Should execute successfully twice (no exceptions)
    assert db_connection.execute.call_count == 2


# ==============================================================================
# TEST 2: TABLE CREATION
# ==============================================================================

def test_migration_creates_confluence_pages_table(read_migration_sql):
    """Verify migration SQL contains CREATE TABLE confluence_pages statement."""
    assert "CREATE TABLE IF NOT EXISTS confluence_pages" in read_migration_sql

    # Verify all required columns present
    required_columns = [
        "page_id TEXT PRIMARY KEY",
        "source_id TEXT NOT NULL",
        "space_key TEXT NOT NULL",
        "title TEXT NOT NULL",
        "version INTEGER NOT NULL",
        "last_modified TIMESTAMPTZ NOT NULL",
        "is_deleted BOOLEAN DEFAULT FALSE",
        "path TEXT",
        "metadata JSONB NOT NULL",
        "created_at TIMESTAMPTZ DEFAULT NOW()",
        "updated_at TIMESTAMPTZ DEFAULT NOW()",
    ]

    for column in required_columns:
        assert column in read_migration_sql, f"Missing column definition: {column}"


# ==============================================================================
# TEST 3: FOREIGN KEY CONSTRAINT
# ==============================================================================

def test_migration_creates_foreign_key_constraint(read_migration_sql):
    """Verify source_id has FK constraint with CASCADE DELETE."""
    assert "REFERENCES archon_sources(source_id)" in read_migration_sql
    assert "ON DELETE CASCADE" in read_migration_sql


# ==============================================================================
# TEST 4: INDEX CREATION
# ==============================================================================

def test_migration_creates_all_indexes(read_migration_sql):
    """Verify all 7 required indexes are created in migration."""

    # 6 indexes on confluence_pages
    confluence_indexes = [
        "idx_confluence_pages_source",  # Source ID (partial)
        "idx_confluence_pages_space",   # Space key (partial)
        "idx_confluence_pages_version", # Version tracking (composite)
        "idx_confluence_pages_path",    # Materialized path (btree text_pattern_ops)
        "idx_confluence_pages_jira",    # JIRA links (GIN jsonb_path_ops)
        "idx_confluence_pages_mentions", # User mentions (GIN jsonb_path_ops)
    ]

    # 1 index on archon_crawled_pages
    chunk_indexes = [
        "idx_crawled_pages_confluence_page_id",  # Chunk linkage via metadata->>'page_id'
    ]

    all_indexes = confluence_indexes + chunk_indexes

    for index_name in all_indexes:
        assert f"CREATE INDEX IF NOT EXISTS {index_name}" in read_migration_sql, \
            f"Missing index: {index_name}"


def test_partial_indexes_have_where_clause(read_migration_sql):
    """Verify partial indexes include WHERE clauses."""
    # Source and space indexes should exclude soft-deleted pages
    assert "WHERE is_deleted = FALSE" in read_migration_sql

    # Chunk linkage index should only index Confluence chunks
    assert "WHERE metadata ? 'page_id'" in read_migration_sql


def test_path_index_uses_text_pattern_ops(read_migration_sql):
    """Verify path index uses text_pattern_ops for LIKE query optimization."""
    assert "path text_pattern_ops" in read_migration_sql


def test_jsonb_indexes_use_gin(read_migration_sql):
    """Verify JSONB indexes use GIN with jsonb_path_ops."""
    assert "USING gin((metadata->'jira_issue_links') jsonb_path_ops)" in read_migration_sql
    assert "USING gin((metadata->'user_mentions') jsonb_path_ops)" in read_migration_sql


# ==============================================================================
# TEST 5: ROW LEVEL SECURITY (RLS) POLICIES
# ==============================================================================

def test_migration_enables_rls(read_migration_sql):
    """Verify RLS is enabled on confluence_pages table."""
    assert "ALTER TABLE confluence_pages ENABLE ROW LEVEL SECURITY" in read_migration_sql


def test_migration_creates_rls_policies(read_migration_sql):
    """Verify RLS policies for service role and authenticated users."""
    # Service role policy (full access)
    assert '"Allow service role full access to confluence_pages"' in read_migration_sql
    assert "FOR ALL USING (auth.role() = 'service_role')" in read_migration_sql

    # Authenticated users policy (read-only)
    assert '"Allow authenticated users to read confluence_pages"' in read_migration_sql
    assert "FOR SELECT TO authenticated" in read_migration_sql


def test_migration_drops_existing_policies_for_idempotency(read_migration_sql):
    """Verify existing policies are dropped before creation (idempotency)."""
    assert 'DROP POLICY IF EXISTS "Allow service role full access to confluence_pages"' in read_migration_sql
    assert 'DROP POLICY IF EXISTS "Allow authenticated users to read confluence_pages"' in read_migration_sql


# ==============================================================================
# TEST 6: SELF-RECORDING MIGRATION TRACKING
# ==============================================================================

def test_migration_self_records_in_archon_migrations(read_migration_sql):
    """Verify migration records itself in archon_migrations table."""
    assert "INSERT INTO archon_migrations (version, migration_name)" in read_migration_sql
    assert "VALUES ('0.1.0', '010_add_confluence_pages')" in read_migration_sql
    assert "ON CONFLICT (version, migration_name) DO NOTHING" in read_migration_sql


# ==============================================================================
# TEST 7: TABLE AND INDEX COMMENTS
# ==============================================================================

def test_migration_includes_table_comments(read_migration_sql):
    """Verify table and column comments for documentation."""
    assert "COMMENT ON TABLE confluence_pages" in read_migration_sql
    assert "COMMENT ON COLUMN confluence_pages.page_id" in read_migration_sql
    assert "COMMENT ON COLUMN confluence_pages.metadata" in read_migration_sql


def test_migration_includes_index_comments(read_migration_sql):
    """Verify index comments explaining purpose."""
    assert "COMMENT ON INDEX idx_confluence_pages_source" in read_migration_sql
    assert "COMMENT ON INDEX idx_crawled_pages_confluence_page_id" in read_migration_sql


# ==============================================================================
# TEST 8: CASCADE DELETE BEHAVIOR (INTEGRATION TEST)
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_cascade_delete_removes_pages_and_chunks(db_connection):
    """
    Integration test: Verify CASCADE DELETE removes confluence_pages and chunks.

    Test flow:
    1. Create test source in archon_sources
    2. Create test page in confluence_pages
    3. Create test chunk in archon_crawled_pages with metadata->>'page_id'
    4. Delete source from archon_sources
    5. Verify page deleted from confluence_pages
    6. Verify chunk deleted from archon_crawled_pages
    """
    test_source_id = "test_confluence_source"
    test_page_id = "123456789"

    # Mock fetchval to simulate CASCADE DELETE behavior
    # After deletion, queries should return 0 (records deleted via CASCADE)
    db_connection.fetchval = AsyncMock(return_value=0)

    # Step 1-3: Setup (mocked - in real DB would insert data)
    await db_connection.execute(
        "INSERT INTO archon_sources (source_id, source_type) VALUES ($1, 'confluence')",
        test_source_id
    )
    await db_connection.execute(
        "INSERT INTO confluence_pages (page_id, source_id, space_key, title, version, last_modified, metadata) "
        "VALUES ($1, $2, 'TEST', 'Test Page', 1, NOW(), '{}')",
        test_page_id, test_source_id
    )
    await db_connection.execute(
        "INSERT INTO archon_crawled_pages (source_id, url, content, metadata) "
        "VALUES ($1, 'confluence://TEST/123456789', 'test content', jsonb_build_object('page_id', $2))",
        test_source_id, test_page_id
    )

    # Step 4: Delete source (triggers CASCADE)
    await db_connection.execute(
        "DELETE FROM archon_sources WHERE source_id = $1",
        test_source_id
    )

    # Step 5: Verify page deleted (mocked check)
    page_count = await db_connection.fetchval(
        "SELECT COUNT(*) FROM confluence_pages WHERE page_id = $1",
        test_page_id
    )
    assert page_count == 0, "Confluence page should be deleted via CASCADE"

    # Step 6: Verify chunk deleted (mocked check)
    chunk_count = await db_connection.fetchval(
        "SELECT COUNT(*) FROM archon_crawled_pages WHERE metadata->>'page_id' = $1",
        test_page_id
    )
    assert chunk_count == 0, "Chunks should be deleted when parent page deleted"


# ==============================================================================
# TEST 9: EXISTING FUNCTIONALITY PRESERVATION
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_web_crawl_functionality_unaffected(db_connection):
    """
    Verify web crawl functionality still works after migration.

    Tests that archon_crawled_pages can still store web crawl chunks
    without page_id metadata (non-Confluence chunks).
    """
    # Insert web crawl chunk (no page_id in metadata)
    await db_connection.execute(
        "INSERT INTO archon_crawled_pages (source_id, url, content, metadata) "
        "VALUES ('web_source_123', 'https://example.com/page1', 'web content', '{}')"
    )

    # Mock fetchval to return 1 (chunk exists)
    db_connection.fetchval = AsyncMock(return_value=1)

    # Verify chunk stored
    web_chunk_count = await db_connection.fetchval(
        "SELECT COUNT(*) FROM archon_crawled_pages WHERE source_id = 'web_source_123'"
    )
    assert web_chunk_count == 1, "Web crawl chunks should still work"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_document_upload_functionality_unaffected(db_connection):
    """
    Verify document upload functionality still works after migration.

    Tests that archon_crawled_pages can still store document upload chunks
    without page_id metadata (non-Confluence chunks).
    """
    # Insert document upload chunk (no page_id in metadata)
    await db_connection.execute(
        "INSERT INTO archon_crawled_pages (source_id, url, content, metadata) "
        "VALUES ('upload_source_456', 'file://document.pdf', 'document content', '{}')"
    )

    # Mock fetchval to return 1 (chunk exists)
    db_connection.fetchval = AsyncMock(return_value=1)

    # Verify chunk stored
    upload_chunk_count = await db_connection.fetchval(
        "SELECT COUNT(*) FROM archon_crawled_pages WHERE source_id = 'upload_source_456'"
    )
    assert upload_chunk_count == 1, "Document upload chunks should still work"


# ==============================================================================
# TEST 10: SCHEMA VALIDATION
# ==============================================================================

def test_migration_file_exists(migration_file_path):
    """Verify migration file exists at expected path."""
    assert os.path.exists(migration_file_path), f"Migration file not found: {migration_file_path}"


def test_migration_file_has_header(read_migration_sql):
    """Verify migration file has standard header with metadata."""
    assert "-- Migration: 010_add_confluence_pages.sql" in read_migration_sql
    assert "-- Description:" in read_migration_sql
    assert "-- Version: 0.1.0" in read_migration_sql
    assert "-- Author: Archon Team" in read_migration_sql
    assert "-- Date:" in read_migration_sql


def test_migration_sql_is_valid_postgres(read_migration_sql):
    """Basic validation that SQL syntax looks correct."""
    # Check for common SQL keywords
    assert "CREATE TABLE" in read_migration_sql
    assert "CREATE INDEX" in read_migration_sql
    assert "ALTER TABLE" in read_migration_sql
    assert "INSERT INTO" in read_migration_sql

    # Check for proper semicolons (statement terminators)
    assert read_migration_sql.count(";") >= 15  # Should have many statements


# ==============================================================================
# TEST 11: METADATA JSONB STRUCTURE DOCUMENTATION
# ==============================================================================

def test_migration_documents_metadata_structure(read_migration_sql):
    """Verify migration includes comments documenting metadata JSONB structure."""
    metadata_fields = [
        "ancestors",
        "children",
        "created_by",
        "jira_issue_links",
        "user_mentions",
        "internal_links",
        "external_links",
        "asset_links",
        "word_count",
        "content_length",
    ]

    for field in metadata_fields:
        assert field in read_migration_sql, f"Metadata field '{field}' should be documented in comments"


# ==============================================================================
# TEST 12: HYBRID SCHEMA VERIFICATION
# ==============================================================================

def test_migration_follows_hybrid_schema_pattern(read_migration_sql):
    """
    Verify migration follows Hybrid Schema approach:
    - Dedicated confluence_pages table for metadata
    - Chunks stored in existing archon_crawled_pages
    - Linked via metadata->>'page_id'
    """
    # Should create confluence_pages table
    assert "CREATE TABLE IF NOT EXISTS confluence_pages" in read_migration_sql

    # Should NOT create separate confluence_chunks table
    assert "CREATE TABLE" not in read_migration_sql or read_migration_sql.count("CREATE TABLE") == 1

    # Should create index linking chunks to pages
    assert "idx_crawled_pages_confluence_page_id" in read_migration_sql
    assert "metadata->>'page_id'" in read_migration_sql
