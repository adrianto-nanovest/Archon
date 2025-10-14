# Technical Debt and Known Issues

## Implemented but Incomplete

1. **Docling Integration (Attempted, Missing Implementation)**
   - Commit bc97f5d mentions Docling for advanced document processing
   - Expected file `python/src/server/utils/docling_processing.py` is **MISSING**
   - Only basic document processing exists (PyPDF2, pdfplumber, python-docx)
   - **Decision needed:** Complete Docling integration or remove from commit history
   - **Impact:** Limited PDF layout preservation, no table extraction

2. **CASCADE DELETE Migration File (Referenced but Missing)**
   - Commit 506ad34 mentions `009_add_cascade_delete_constraints.sql`
   - File **does not exist** in `migration/0.1.0/` directory
   - CASCADE DELETE constraints were added to `complete_setup.sql` instead
   - **Recommendation:** Create migration file for consistency or update documentation

## Planned but Not Implemented

1. **Confluence Integration (Extensively Planned, Zero Implementation)** ← PRIMARY FOCUS
   - Comprehensive documentation exists (1,333+ lines in `CONFLUENCE_RAG_INTEGRATION.md`)
   - Key architectural decisions made:
     - **Hybrid Schema**: Dedicated metadata table + unified chunks ✓
     - **Direct Confluence API**: Not Google Drive intermediary ✓
     - **CQL-based incremental sync**: No full space scans ✓
     - **90% code reuse**: Leverage existing services ✓
   - **No code changes yet** - ready for implementation!
   - **Dependencies NOT added:** `atlassian-python-api`, `markdownify`
   - **Recommendation:** Use existing documentation as roadmap for 1.5-2 week implementation

2. **Google Drive Integration**
   - Original brownfield v1.0 planned Google Drive as Confluence intermediary
   - **ABANDONED** in favor of direct Confluence API approach
   - No implementation in either direction

## Current Technical Debt

1. **Document Processing**
   - Basic PDF extraction (PyPDF2, pdfplumber) - no layout preservation
   - Basic DOCX support (python-docx) - no complex formatting
   - Code block preservation implemented for page boundaries
   - **Missing:** Advanced layout analysis, table extraction, multi-column support

2. **Background Job Management**
   - No formal job queue system (Celery, RQ, etc.)
   - Long-running operations tracked via `archon_progress` table
   - Simple polling-based progress tracking
   - **Recommendation:** Add job queue for Confluence sync (long-running operations)

3. **Migration Versioning Strategy**
   - Current version: 0.1.0
   - Migration files in `migration/0.1.0/` directory
   - **Missing:** Version bump strategy, migration rollback procedures
   - **Recommendation:** Adopt semantic versioning for releases

4. **Test Coverage**
   - Backend tests exist in `python/tests/`
   - Frontend tests use Vitest + React Testing Library
   - **Coverage gaps:** Migration tracking, version checking, newer features
   - **Recommendation:** Comprehensive integration tests, especially for Confluence sync

## Architecture Constraints

1. **No ORM Framework**
   - Direct SQL via asyncpg/Supabase SDK
   - No SQLAlchemy, no Alembic migration tool
   - **Impact:** Manual SQL writing, manual migration tracking
   - **Trade-off:** Performance and simplicity vs ORM features

2. **No WebSockets**
   - HTTP polling with smart intervals (visibility-aware)
   - **Impact:** Not true real-time, but efficient (ETag caching ~70% bandwidth reduction)
   - **Trade-off:** Simplicity vs real-time updates

3. **Vertical Slice Frontend Architecture**
   - Features own their entire stack (UI → API → DB awareness)
   - **Impact:** Some code duplication, but high cohesion
   - **Trade-off:** DRY vs feature independence

---
