# Enhancement Impact Analysis: Confluence Integration

## Summary

**Goal:** Integrate 4000+ Confluence Cloud pages into Archon's RAG system for code implementation assistance and documentation generation.

**Approach:** Direct Confluence API integration with Hybrid database schema (Option 3 from `CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md`) + modular HTML processing architecture.

**Timeline:** 2 weeks implementation (increased from 1.5-2 weeks due to modular architecture complexity).

**Code Reuse:** 90% of **infrastructure** - Leverage existing `document_storage_service.py` and `hybrid_search_strategy.py`.

**New Code:** ~2,300 lines across 20 focused files (includes Docling integration for asset processing).

**Architecture Approach:**
- **Modular design:** 19 handler/utility files + 1 API route + 1 Docling processor
- **RAG-optimized:** Skip TOC macros, simplify low-value handlers, hierarchical tables
- **3-tier JIRA extraction:** Macros + URLs + Regex for 95%+ coverage
- **Error isolation:** Each handler wrapped in try-except for graceful degradation
- **Bulk API calls:** User mentions and page links use batch operations (N+1 prevention)
- **Hybrid asset processing:**
  - **Documents (Docling):** PDF/Office full-text extraction
  - **Images (Multimodal LLM):** Text extraction + classification via MODEL_CHOICE
  - **Automatic fallback:** Docling OCR when MODEL_CHOICE lacks vision support

## Required Changes

### Backend Files to CREATE (~2,100 lines total)

**Reference:** Complete architectural details in `docs/bmad/confluence-html-processing-analysis.md`

#### Core Services

1. **`python/src/server/services/confluence/confluence_client.py`** (~200 lines)
   - Authenticate with Confluence API using `atlassian-python-api`
   - Implement CQL search for incremental sync
   - Bulk user lookups via `get_users_by_account_ids()` (N+1 prevention)
   - Bulk page lookups via `find_page_by_title()` batch operations
   - Lightweight page ID fetching for deletion detection

2. **`python/src/server/services/confluence/confluence_sync_service.py`** (~400 lines)
   - CQL-based incremental sync (fetch only changed pages)
   - Handle page creates, updates, deletes
   - Atomic chunk update strategy (zero-downtime)
   - Sync observability (metrics tracking in `archon_sources.metadata`)
   - Build materialized path for hierarchy queries
   - Call `document_storage_service.add_documents_to_supabase()` for chunk storage

3. **`python/src/server/services/confluence/confluence_processor.py`** (~200 lines)
   - Main orchestrator for HTML → Markdown conversion
   - Five-pass processing pipeline:
     1. Process Confluence macros (via macro handlers)
     2. Process special HTML elements (via element handlers)
     3. Process tables (hierarchical conversion via table_processor)
     4. Convert to markdown (markdownify)
     5. Extract metadata (via metadata_extractor)
   - Handler registration and dependency injection
   - Error isolation (each handler wrapped in try-except)

#### Macro Handlers (`macro_handlers/` directory)

4. **`code_macro.py`** (~100 lines)
   - Extract language parameter from `<ac:parameter ac:name="language">`
   - Unwrap CDATA from `<ac:plain-text-body>`
   - **Preserve whitespace** (no `strip=True`) - critical for code formatting
   - Format as fenced code blocks with language tags

5. **`panel_macro.py`** (~120 lines)
   - Handle info/note/warning/tip/panel macros
   - Emoji prefix mapping (ℹ️, ⚠️, ❌, ✅)
   - Blockquote formatting with `> ` prefix per line
   - Support nested content via markdownify

6. **`jira_macro.py`** (~150 lines)
   - **3-tier JIRA extraction** for 95%+ coverage:
     - Tier 1: Parse `<ac:parameter ac:name="key">` from JIRA macros (~40% coverage)
     - Tier 2: Extract from `<a href=".../browse/PROJ-123">` URLs (~30% coverage)
     - Tier 3: Regex on plain text `\b([A-Z]+-\d+)\b` (~30% coverage)
   - JQL table handling for embedded JIRA queries
   - Deduplication across all tiers via `_is_jira_url_already_processed()`

7. **`attachment_macro.py`** (~100 lines)
   - Extract filenames from `<ri:attachment ri:filename="...">`
   - File type emoji mapping (📄 PDF, 📝 DOC, 📊 XLS, 📦 ZIP, etc.)
   - Add to `asset_links` metadata
   - Placeholder URL generation for later replacement

8. **`embed_macro.py`** (~120 lines)
   - Extract URL from nested `<ri:url ri:value="...">`
   - Convert embed URLs to original URLs:
     - YouTube: `/embed/ID` → `watch?v=ID`
     - Google Maps: Extract coordinates from `pb` parameter
     - Support 15+ platforms (Vimeo, Twitter, Instagram, etc.)
   - Add to `external_links` metadata

9. **`generic_macro.py`** (~80 lines)
   - Fallback handler for unknown macros
   - Extract macro name and all parameters
   - Try to extract content from `<ac:rich-text-body>`
   - Format as HTML comment with parameters preserved

#### Element Handlers (`element_handlers/` directory)

10. **`link_handler.py`** (~120 lines)
    - **Page links:** Extract from `<ri:page ri:content-title="...">`
      - Bulk API lookup via `find_page_by_title(space_id, title)`
      - Store internal link metadata (page_id, title, URL)
      - Deduplication via processed links set
    - **External links:** Process `<a href="...">` tags
      - Google Drive icon detection (Docs, Sheets, Slides, Forms)
      - Add to `external_links` metadata

11. **`user_handler.py`** (~100 lines)
    - Extract account IDs from `<ri:user ri:account-id="...">`
    - **Bulk fetch user info** via `get_users_by_account_ids()` (single API call)
    - Cache user information to avoid duplicate lookups
    - Store user mentions metadata (account_id, display_name, profile_url)
    - Deduplication by unique account IDs

12. **`image_handler.py`** (~130 lines)
    - Detect `<ri:attachment>` vs `<ri:url>`
    - **DEFAULT: Multimodal LLM processing** (when `image_processing_mode = "multimodal"`)
      - Use MODEL_CHOICE from RAG Settings to determine LLM
      - Check if selected model supports multimodal (vision) capabilities
      - If multimodal supported: Send image with prompt for text extraction and classification
      - Extract searchable text from screenshots/diagrams
      - Image classification (chart, diagram, photo, screenshot)
      - Embed analysis in markdown comments for searchability
      - **FAST:** API call (~1-2 seconds), no local processing overhead
    - **FALLBACK: Docling OCR** (when model lacks multimodal support OR `image_processing_mode = "docling_ocr"`)
      - Automatically triggered if MODEL_CHOICE doesn't support vision
      - Process images with DoclingProcessor OCR
      - Extract text using EasyOCR/Tesseract
      - Slower (~30-60s per image), useful for non-multimodal models or air-gapped deployments
    - **Graceful fallback:** Standard image markdown with filename only if both fail
    - Extension-based icon selection (🖼️ images, 🎬 videos, 📎 other)
    - Add to `asset_links` metadata

13. **`simple_elements.py`** (~80 lines)
    - **Emoticons:** Use `ac:emoji-fallback` attribute only (simplified)
    - **Inline comments:** Strip `<ac:inline-comment-marker>` entirely
    - **Time elements:** Use text content only (no ISO parsing)
    - **ADF extensions:** Extract text content only

#### Processing Modules

14. **`table_processor.py`** (~350 lines)
    - **Hierarchical markdown conversion** (NOT standard markdown tables!)
    - Why: Better RAG retrieval, preserves nested content, supports colspan/rowspan
    - Colspan/rowspan content duplication for RAG optimization
    - Multi-level header matrix building
    - Metadata enrichment (table summary, complexity score, purpose inference)
    - Context-aware heading levels (adjust based on surrounding document structure)

15. **`metadata_extractor.py`** (~150 lines)
    - Aggregate all metadata from handlers
    - 3-tier JIRA extraction orchestration
    - User mention deduplication
    - Link deduplication (internal/external)
    - Asset aggregation from multiple sources
    - Word count and content length metrics

#### Utilities (`utils/` directory)

16. **`html_utils.py`** (~100 lines)
    - BeautifulSoup helper functions
    - Whitespace normalization (preserve in code blocks, clean elsewhere)
    - Header text cleaning (emoji encoding, newline collapse)
    - UTF-8 encoding safety

17. **`url_converter.py`** (~100 lines)
    - Universal iframe embed URL converter
    - Platform-specific conversions (YouTube, Vimeo, Maps, etc.)
    - Coordinate extraction for Google Maps
    - Generic `/embed/` fallback

18. **`deduplication.py`** (~100 lines)
    - Link deduplication logic
    - JIRA issue deduplication across tiers
    - Set-based deduplication for assets
    - Performance: O(1) lookups with sets

#### Docling Integration Module

19. **`docling_processor.py`** (~120 lines)
    - Docling service wrapper for asset processing
    - **PRIMARY USE:** PDF/Office document processing (DOCX, PPTX, XLSX)
    - **SECONDARY USE:** Image OCR fallback (opt-in when multimodal LLM unavailable)
    - Implement `async process_attachment(file_path: Path) -> dict` method for documents
    - Implement `async process_image_ocr(file_path: Path) -> dict` method (fallback only)
    - Extract metadata helper: `_extract_metadata(doc: DoclingDocument) -> dict`
    - Return structured response: `{success: bool, markdown: str, plain_text: str, metadata: dict, error: str}`
    - File format detection and routing
    - Caching by file hash for performance
    - Error handling and fallback patterns

#### API Routes

20. **`python/src/server/api_routes/confluence_api.py`** (~100 lines)
    - `POST /api/confluence/sources` - Create Confluence source
    - `GET /api/confluence/sources` - List sources
    - `POST /api/confluence/{id}/sync` - Trigger sync
    - `GET /api/confluence/{id}/status` - Get sync status
    - `DELETE /api/confluence/{id}` - Delete source (CASCADE)
    - `GET /api/confluence/{id}/pages` - List pages in space

**Total:** ~2,300 lines across 20 focused files (19 handlers/utils + 1 API route + 1 Docling processor)

### Backend Files to MODIFY (Minimal Changes)

1. **`python/src/server/services/knowledge/knowledge_item_service.py`**
   - Add `'confluence'` to supported source types
   - Register Confluence spaces in `archon_sources` table

2. **`python/src/server/services/search/hybrid_search_strategy.py`** (OPTIONAL)
   - Add `LEFT JOIN confluence_pages` for metadata enrichment
   - Add Confluence-specific filters (space, JIRA links, user mentions)
   - **Core search already works without changes!**

### Database Changes

**Migration File:** `migration/0.1.0/010_add_confluence_pages.sql`

```sql
-- Create confluence_pages table (see Data Models section for full schema)
CREATE TABLE confluence_pages (...);

-- Create performance indexes
CREATE INDEX idx_confluence_pages_source ON confluence_pages(...);
CREATE INDEX idx_confluence_pages_space ON confluence_pages(...);
CREATE INDEX idx_confluence_pages_path ON confluence_pages(...);
CREATE INDEX idx_confluence_pages_jira ON confluence_pages(...);

-- Link chunks to pages
CREATE INDEX idx_crawled_pages_confluence_page_id ON archon_crawled_pages(...);
```

**No changes to `archon_crawled_pages`** - already supports Confluence chunks via `metadata->>'page_id'`!

### Frontend Files to CREATE (Future Phase)

**Vertical Slice:** `archon-ui-main/src/features/confluence/`

1. **`services/confluenceService.ts`** - API client
2. **`hooks/useConfluenceQueries.ts`** - Query hooks & keys
3. **`components/ConfluenceSourceForm.tsx`** - Source creation form
4. **`components/ConfluenceSourceCard.tsx`** - Source display card
5. **`components/ConfluenceSyncStatus.tsx`** - Sync status & progress
6. **`types/index.ts`** - TypeScript types

### Dependencies to Add

```toml
# python/pyproject.toml
[dependency-groups.server]
# Confluence integration
atlassian-python-api = "^3.41.0"  # Confluence REST API client
markdownify = "^0.11.6"           # HTML to Markdown conversion

# Docling asset processing (Phase 1 - Epic 2)
docling = ">=2.18.0"               # Document processing library (PDF/Office docs)
# Note: Multimodal LLM dependencies already included via existing provider integrations
# (OpenAI, Anthropic, Google, etc.) - determined by MODEL_CHOICE at runtime

[project.optional-dependencies]
docling = [
    "docling[easyocr]",            # OCR support (fallback for non-multimodal models)
]
```

## Implementation Workflow

**Week 1: Database & Sync Logic**
1. Create migration 010 (Confluence tables)
2. Implement `ConfluenceClient` (API integration)
3. Implement `ConfluenceSyncService` (CQL-based sync)
4. Implement `ConfluenceProcessor` (HTML → Markdown)
5. **Call existing `document_storage_service.add_documents_to_supabase()`** ✓

**Week 2: API & Frontend**
6. Create `confluence_api.py` (REST endpoints)
7. Create frontend vertical slice in `features/confluence/`
8. Write unit tests, integration tests
9. Load test with 4000+ pages

## Code Reuse Highlights

**Existing Service:** `document_storage_service.add_documents_to_supabase()`
```python
# Confluence sync service calls existing function!
await add_documents_to_supabase(
    urls=[f"confluence://{space_key}/{page_id}"],
    contents=[content_markdown],
    metadatas=[{"page_id": page_id, "section_title": "..."}],
    source_id=source_id
)
# That's it! Existing service handles:
# - Section-aware chunking
# - Code block detection & preservation
# - Embedding generation (multi-provider)
# - Progress tracking
# - Batch processing
# - Storage in archon_crawled_pages
```

**Existing Service:** `hybrid_search_strategy.py`
```python
# Already searches archon_crawled_pages!
# No changes needed for basic Confluence search
# Optional: Add LEFT JOIN confluence_pages for metadata
```

**Existing Service:** `progress_tracker.py`
```python
# Reuse for Confluence sync status
progress = ProgressTracker(operation_id, operation_type="confluence_sync")
await progress.update(status="syncing", progress=50, log="Synced 50 pages")
await progress.complete(log="Sync completed successfully")
```

## Reference Documentation

All comprehensive planning completed - ready for implementation!

- **Main Guide:** `docs/bmad/CONFLUENCE_RAG_INTEGRATION.md` (1,333 lines)
  - Hybrid schema rationale
  - CQL-based incremental sync strategy
  - Deletion detection strategies
  - Atomic chunk update pattern
  - Search integration
  - Performance optimization
  - Testing strategy

- **Schema Analysis:** `docs/bmad/CONFLUENCE_DATABASE_SCHEMA_ANALYSIS.md`
  - Comparison of 3 database schema options
  - Why Hybrid Schema was selected

- **Example Metadata:** `docs/bmad/examples/conf_metadata_example_*.json`
  - Real Confluence page metadata samples

---
