# Epic 2: HTML to Markdown Content Processing

**Epic Goal**: Implement modular, RAG-optimized HTML to Markdown processor with specialized handlers for converting Confluence storage format to searchable, embeddable content, **including AI-powered attachment processing via Docling (documents) and multimodal LLM (images) for 10x searchable content increase**

**Architecture Approach**: Based on production reference implementation analysis (2000+ lines), this epic implements:
- **Modular architecture**: 19 focused handler files (~2,200 lines distributed) instead of single monolithic processor
- **RAG optimization**: Hierarchical tables (NOT standard markdown), 3-tier JIRA extraction (NOT regex-only), skip/simplify low-value elements
- **Performance**: Bulk API calls for user/page resolution (prevent N+1 queries)
- **Error isolation**: Each handler wrapped in try-except with graceful degradation
- **AI-Powered Asset Processing**: Docling for PDF/Office docs (structure preservation), multimodal LLM for images (intelligent understanding based on MODEL_CHOICE)

**Integration Requirements**:
- Must integrate with existing `document_storage_service.add_documents_to_supabase()` for chunking (validated in Story 1.5)
- Must return metadata matching `confluence_pages.metadata` JSONB schema
- Must preserve code blocks, handle complex tables, and extract 100% of JIRA references
- **Must process Confluence attachments (PDF, DOCX, PPTX, XLSX) with Docling for full-text searchability**
- **Must support multimodal LLM processing for images based on MODEL_CHOICE (OCR + understanding), with fallback to Docling OCR for non-multimodal models**

---

## Story 2.1: Core Infrastructure & Orchestrator

As a **backend developer**,
I want **to create modular directory structure and main orchestrator for Confluence HTML processing**,
so that **specialized handlers can be registered and coordinated through a clean, testable architecture**.

**Acceptance Criteria**:
1. Create modular directory structure: `confluence/`, `macro_handlers/`, `element_handlers/`, `utils/`
2. Implement `BaseMacroHandler` abstract class with error isolation pattern
3. Implement `BaseElementHandler` abstract class with graceful degradation
4. Create `ConfluenceProcessor` orchestrator (~200 lines) with dependency injection
5. Implement two-pass processing pipeline (macro expansion → HTML conversion)
6. Register handler pattern with try-except wrapper per handler
7. Add comprehensive logging for debugging (page_id, macro name, error context)

**Integration Verification**:
- IV1: Orchestrator successfully loads and registers all handler types
- IV2: Error in one handler doesn't crash entire conversion (graceful degradation)
- IV3: Processing pipeline executes in correct order (macros → elements → tables → markdown)
- IV4: Empty HTML input returns empty markdown + empty metadata (no crash)

**Deliverable**: Working `ConfluenceProcessor` class with handler registration pattern ready for Phase 2 handlers

---

## Story 2.2: High-Value Macro Handlers (Enhanced with Docling)

As a **backend developer**,
I want **to implement 6 RAG-critical macro handlers for Confluence content extraction, including AI-powered attachment processing**,
so that **code blocks, panels, JIRA issues, attachments (with full-text content), and embedded content are preserved in searchable format**.

**Acceptance Criteria**:
1. **Code Macro Handler** (~100 lines): Extract language tags, unwrap CDATA, preserve whitespace (NO strip)
2. **Panel Macro Handler** (~120 lines): Support info/note/warning/tip with emoji prefixes (ℹ️✅⚠️❌), blockquote formatting
3. **JIRA Macro Handler - 3-Tier Extraction** (~150 lines):
   - Tier 1: Macro parameter extraction (~40% coverage)
   - Tier 2: URL pattern matching in `<a>` tags (~30% coverage)
   - Tier 3: Plain text regex on final markdown (~30% coverage)
   - Deduplication across all tiers
   - JQL table handling (if JIRA client provided)
4. **Attachment Macro Handler with Docling Integration** (~200 lines):
   - Extract filenames, map file type to emoji icons (📄📝📊📦📎)
   - **Download attachments from Confluence API**
   - **Process PDF, DOCX, PPTX, XLSX with DoclingProcessor (Story 2.6 dependency)**
   - **Extract full-text content and embed in page markdown**
   - **Enrich metadata with document structure (page_count, table_count, code_blocks, word_count)**
   - **Graceful fallback to file link if Docling processing fails**
   - **Respect file size limits (skip files > 50MB)**
   - **Background processing mode (don't block page sync)**
5. **Embed Macro Handler** (~120 lines): Convert embed URLs for 15+ platforms (YouTube, Vimeo, Google Maps, etc.)
6. **Generic Macro Handler** (~80 lines): Fallback for unknown macros with parameter extraction

**Integration Verification**:
- IV1: Code blocks preserve whitespace and language tags (no line breaks mid-block)
- IV2: **JIRA 3-tier extraction** achieves ~100% coverage (NOT 40% regex-only)
- IV3: Panel macros render as blockquotes with correct emoji prefixes
- IV4: Attachment macros add filenames to `asset_links` metadata
- **IV5: PDF/Office attachments processed with Docling, full-text content embedded in markdown**
- **IV6: Docling processing failures fall back to file link gracefully**
- **IV7: Large files (>50MB) skipped with warning logged**
- IV8: Unknown macros handled gracefully with comment placeholders

**Deliverable**: 6 macro handlers (~770 lines) with per-handler unit tests

**Estimated Effort**: 2 days (was 1 day, +1 day for Docling integration)

---

## Story 2.3: RAG-Critical Element Handlers (Enhanced with Multimodal LLM)

As a **backend developer**,
I want **to implement 4 element handlers with bulk API call optimization and AI-powered image understanding**,
so that **user mentions, page links, images (with searchable text), and simple elements are processed efficiently without N+1 query anti-pattern**.

**Acceptance Criteria**:
1. **Link Handler** (~120 lines):
   - Internal page links: Bulk API call for all unique page titles (single call)
   - External links: Filter http/https, deduplicate JIRA links, add Google Drive icons
   - Store metadata: `internal_links` (page_id, title, url), `external_links` (title, url)
2. **User Handler** (~100 lines):
   - Extract unique account IDs (deduplication)
   - **Bulk API call**: `get_users_by_account_ids(account_ids)` (single call for all users)
   - Cache user information to avoid duplicate lookups
   - Store metadata: `user_mentions` (account_id, display_name, profile_url)
3. **Image Handler with AI Processing** (~130 lines):
   - Detect `<ac:image>` with two sources: `<ri:attachment>` (local) and `<ri:url>` (external)
   - Determine type by extension: Images (🖼️), Videos (🎬), Other (📎)
   - Add to `asset_links` metadata if attachment
   - **DEFAULT: Multimodal LLM processing** (when `image_processing_mode = "multimodal"`):
     - Use MODEL_CHOICE from RAG Settings > Chat Model to determine LLM
     - Check if selected model supports multimodal (vision) capabilities
     - If multimodal supported: Send image with prompt: "Extract all visible text from this image. Identify the image type (chart, diagram, screenshot, photo). Describe key elements in 1-2 sentences."
     - Extract searchable text from screenshots/diagrams
     - Image classification (chart, diagram, photo, etc.)
     - Embed analysis in markdown comments for searchability
     - **FAST**: API call (~1-2 seconds), no local processing overhead
   - **FALLBACK: Docling OCR** (when model lacks multimodal support OR `image_processing_mode = "docling_ocr"`):
     - Automatically triggered if MODEL_CHOICE doesn't support vision
     - Process images with DoclingProcessor OCR
     - Extract text using EasyOCR/Tesseract
     - Slower (~30-60s per image), useful for non-multimodal models or air-gapped deployments
   - **Graceful fallback if both fail**: Standard image markdown with filename only
4. **Simple Element Handler (Simplified)** (~80 lines):
   - Emoticons: Use `ac:emoji-fallback` attribute only (skip shortname - low RAG value)
   - Inline Comments: Strip `<ac:inline-comment-marker>` entirely (collaborative metadata, not content)
   - Time Elements: Use text content only (skip ISO datetime parsing - minimal RAG value)

**Integration Verification**:
- IV1: User/page resolution uses bulk API calls (verify single call for N items)
- IV2: Link handler correctly deduplicates JIRA links already processed by macro handler
- IV3: Simple elements simplified (60% fewer lines vs. full implementation)
- IV4: All metadata fields populated correctly (internal_links, external_links, user_mentions, asset_links)
- **IV5: Multimodal LLM enabled by default (`image_processing_mode = "multimodal"`) using MODEL_CHOICE**
- **IV6: Multimodal LLM extracts text and classifies images (chart, diagram, photo, screenshot)**
- **IV7: Image analysis results embedded in markdown comments for searchability**
- **IV8: Docling OCR automatically triggered for non-multimodal models OR opt-in via `image_processing_mode = "docling_ocr"`**
- **IV9: Processing failures degrade gracefully to standard image markdown**

**Deliverable**: 4 element handlers (~430 lines) with bulk API call optimization, multimodal LLM support (based on MODEL_CHOICE), automatic Docling OCR fallback, and unit tests

**Estimated Effort**: 1 day (was 1.5 days, -0.5 days due to flexible multimodal LLM integration vs local OCR only)

---

## Story 2.4: Table Processor & Metadata Extractor (Enhanced with Docling Metadata)

As a **backend developer**,
I want **to implement hierarchical table conversion, 3-tier JIRA metadata aggregation, and rich attachment metadata extraction**,
so that **complex Confluence tables are RAG-optimized, JIRA coverage reaches ~100%, and attachment metadata enriches search capabilities**.

**Acceptance Criteria**:
1. **Table Processor** (~350 lines):
   - **CRITICAL**: Use hierarchical markdown format (NOT standard markdown tables)
   - Convert to `## Row` → `### Column` structure
   - Wrap with `<!-- TABLE_START -->` and `<!-- TABLE_END -->` markers
   - Add table summary comment: `<!-- Table Summary: {cols} columns, {rows} rows, ... -->`
   - Handle colspan/rowspan with content duplication (fill all spanned cells)
   - Build multi-level header matrix (rowspan + colspan in headers)
   - Calculate context-aware heading levels (detect surrounding section level)
   - Add metadata enrichment: table complexity score, purpose inference, span locations
2. **Metadata Extractor with Docling Enrichment** (~200 lines):
   - Aggregate JIRA links from all 3 tiers (macros + URLs + regex)
   - Deduplicate user mentions by account ID
   - Deduplicate internal/external links by URL
   - Deduplicate asset links by filename
   - Calculate content metrics: word_count, content_length
   - **Extract rich attachment metadata from Docling-processed documents:**
     - **page_count** (PDF/DOCX documents)
     - **table_count** (tables found in attachments)
     - **code_block_count** (code snippets in attachments)
     - **image_count** (images in attachments)
     - **has_formulas** (mathematical content detection)
     - **document_structure** (sections, headings, TOC presence)
   - **Store attachment metadata in `asset_links` array with `processed=true` flag**
   - Build metadata dict matching `confluence_pages.metadata` JSONB schema

**Integration Verification**:
- IV1: Table conversion uses hierarchical format (verify `<!-- TABLE_START -->`, `## Row`, `### Column`)
- IV2: Colspan/rowspan handling duplicates content across all spanned cells
- IV3: 3-tier JIRA aggregation deduplicates across all sources (no duplicate issue keys)
- IV4: Metadata schema matches `confluence_pages.metadata` JSONB structure (6+ required fields)
- IV5: Hierarchical tables maintain context across chunk boundaries (RAG-optimized)
- **IV6: Attachment metadata extracted from Docling-processed documents**
- **IV7: asset_links array contains rich metadata (page_count, table_count, code_block_count, etc.)**
- **IV8: Unprocessed attachments have `processed=false` flag in asset_links**

**Deliverable**: Table processor (~350 lines) + metadata extractor (~200 lines) with comprehensive tests

**Estimated Effort**: 1.5 days (was 1 day, +0.5 days for Docling metadata extraction)

---

## Story 2.5: Utility Modules & Integration Testing

As a **backend developer**,
I want **to implement utility modules and comprehensive integration tests**,
so that **HTML processing is robust, tested, and verified against all integration requirements**.

**Acceptance Criteria**:
1. **HTML Utilities** (~100 lines):
   - BeautifulSoup helper functions
   - Whitespace normalization (code block preservation, header cleaning, table cell cleaning)
   - UTF-8 encoding safety for emoji
2. **URL Converter** (~100 lines):
   - Iframe embed URL conversion (15+ platforms)
   - YouTube, Vimeo, Google Maps coordinate extraction
   - Generic fallback: convert `/embed/` to `/`
3. **Deduplication Utilities** (~100 lines):
   - `_is_jira_already_processed(issue_key)` - check by key
   - `_is_jira_url_already_processed(url)` - check by URL
   - Set-based deduplication for asset links
4. **Comprehensive Integration Tests**:
   - Test full page conversion (all handlers)
   - Verify 3-tier JIRA extraction (all tiers extract unique issues)
   - Verify hierarchical table format
   - Verify metadata schema compliance
   - Test malformed HTML handling (graceful degradation)
   - Test error isolation (one handler failure doesn't break conversion)
5. **Integration Verification from Epic Requirements**:
   - IV1: Code blocks remain intact (no line breaks mid-block)
   - IV2: JIRA 3-tier coverage ~100% (macros + URLs + regex)
   - IV3: Metadata JSONB structure matches schema
   - IV4: Hierarchical tables (NOT standard markdown)
   - IV5: Modular handlers testable independently

**Integration Verification**:
- IV1-IV5: All integration verification items from Epic 2 requirements pass
- Test coverage: 90%+ per handler, 95%+ integration
- Error rate: <1% of macros/elements fail gracefully
- Performance: Bulk API calls prevent N+1 queries (50x faster)

**Deliverable**: 3 utility modules (~300 lines) + comprehensive integration tests + IV verification complete

---

## Story 2.6: Docling Service & Configuration (NEW)

As a **backend developer**,
I want **to create a reusable Docling service layer with configuration and error handling**,
so that **attachment handlers can process PDF/Office documents efficiently, and image handlers have OCR fallback option**.

**Acceptance Criteria**:
1. **DoclingProcessor Service** (~120 lines):
   - Initialize DocumentConverter with optimized pipeline options
   - **PRIMARY USE: PDF/Office document processing** (DOCX, PPTX, XLSX)
   - **SECONDARY USE: Image OCR fallback** (opt-in when Gemini unavailable)
   - Implement `async process_attachment(file_path: Path) -> dict` method
   - Implement `async process_image_ocr(file_path: Path) -> dict` method (fallback only)
   - Extract metadata helper: `_extract_metadata(doc: DoclingDocument) -> dict`
   - Return structured response: `{success: bool, markdown: str, plain_text: str, metadata: dict, error: str}`
2. **Configuration Settings** (add to `ConfluenceSettings`):
   - `docling_enabled: bool = True` - Master feature flag for PDF/Office processing
   - `image_processing_mode: str = "multimodal"` - Options: "multimodal" (default, uses MODEL_CHOICE), "docling_ocr" (force OCR), "none"
   - `docling_max_file_size_mb: int = 50` - Skip files larger than this
   - `docling_timeout_seconds: int = 60` - Processing timeout per file
   - `docling_max_concurrent: int = 2` - Limit parallel Docling processes (memory management)
3. **Format Detection & Fallback**:
   - **Documents** (always Docling): `.pdf`, `.docx`, `.pptx`, `.xlsx`
   - **Images** (multimodal LLM if supported, else Docling OCR): `.png`, `.jpg`, `.jpeg`, `.tiff`, `.webp`
   - Check MODEL_CHOICE capabilities at runtime to determine fallback path
   - Unsupported formats: graceful fallback to file link
   - Clear logging for unsupported formats and multimodal capability checks
4. **Async Attachment Download**:
   - Download attachment from Confluence API to temp directory
   - Return `Path` object for processing
   - Cleanup temp files after processing
5. **Comprehensive Error Handling**:
   - Try-except wrapper around all Docling calls
   - Timeout handling (prevent infinite processing)
   - Memory exhaustion detection (file too large)
   - Graceful degradation on any error
   - Detailed error logging with context (filename, page_id, error type)
6. **Metadata Extraction Helpers**:
   - Extract page_count, table_count, code_block_count, image_count
   - Extract has_code, has_formulas flags
   - Extract document_structure (sections, headings, TOC)
   - Return dict matching asset_links metadata schema

**Integration Verification**:
- IV1: DoclingProcessor correctly identifies supported formats (9 extensions)
- IV2: File size limits enforced (skip files > 50MB with warning)
- IV3: Image processing defaults to multimodal LLM (`image_processing_mode = "multimodal"`) using MODEL_CHOICE
- IV4: Multimodal capability check performed at runtime against MODEL_CHOICE
- IV5: Docling OCR automatically triggered when MODEL_CHOICE lacks multimodal support
- IV6: Docling OCR available as manual override via `image_processing_mode = "docling_ocr"`
- IV7: Graceful fallback to file link on processing failure (no crashes)
- IV8: Timeout enforced (prevent infinite processing)
- IV9: Temp files cleaned up after processing (no disk leaks)
- IV10: Metadata extraction returns correct schema (6+ fields)
- IV11: Concurrent processing limited by semaphore (prevent memory exhaustion)

**Deliverable**: `docling_processor.py` (~120 lines) + configuration settings + unit tests

**Estimated Effort**: 0.75 days (was 1 day, -0.25 days due to simpler config without OCR by default)

**Dependencies**: Story 2.6 must be completed before Story 2.2 (Attachment Handler uses DoclingProcessor)

---

## Success Metrics

### Code Quality
- No file > 350 lines (table_processor.py max)
- Test coverage: 90%+ per handler, 95%+ integration
- Error rate: <1% of macros/elements fail gracefully
- Modular architecture: **19 focused files (~2,200 lines distributed)** - includes docling_processor.py

### RAG Performance
- JIRA coverage: 95%+ of JIRA references extracted (3-tier)
- Table searchability: 10x better retrieval vs. standard markdown tables
- Metadata completeness: 100% of user mentions, page links, assets tracked
- Chunk quality: Hierarchical tables maintain context across chunk boundaries
- **Searchable content increase: 10x improvement via full-text attachment processing**
- **Attachment coverage: 100% of PDF/Office docs processed with Docling**
- **Image understanding: Multimodal LLM based on MODEL_CHOICE (>90% accuracy for text extraction + classification)**
- **OCR fallback: Docling OCR automatically triggered for non-multimodal models (>85% accuracy, slower)**

### Maintainability
- New macro addition: <100 lines of code, single file
- Debug time: Isolate issues to specific handler in <5 minutes
- Test time: Run all handler unit tests in <30 seconds
- Team velocity: Multiple developers work on different handlers simultaneously

---

## Critical Implementation Notes

### 3-Tier JIRA Extraction (CRITICAL)
**Current Plan (Regex-Only)**: 40% coverage → **UNACCEPTABLE**

**Required Implementation (3-Tier)**:
- **Tier 1: Confluence JIRA Macros** (~40% coverage)
  - Source: `<ac:parameter ac:name="key">PROJ-123</ac:parameter>`
  - Accuracy: 100% (explicit Confluence embedding)
- **Tier 2: JIRA URLs in Hyperlinks** (~30% coverage)
  - Source: `<a href="https://jira.../browse/PROJ-123">`
  - Pattern: `https?://[^/]+/browse/([A-Z]+-\d+)`
- **Tier 3: Plain Text Regex Fallback** (~30% coverage)
  - Source: "See PROJ-123 for details" in text content
  - Pattern: `\b([A-Z]+-\d+)\b` (word boundaries prevent false positives)
  - Run AFTER markdown conversion

**Deduplication Strategy**: Check each tier against previous tiers (prevent duplicates)

**Impact**: 100% JIRA coverage vs. 40% regex-only → **CRITICAL for JIRA-integrated Confluence spaces**

### Hierarchical Tables (NOT Standard Markdown Tables)
**Rationale**: Standard markdown tables have critical limitations for Confluence content
- **No colspan/rowspan**: 35% of Confluence tables have spans
- **No nested content**: 60% have code blocks, lists, formatting inside cells
- **No multi-level headers**: 20% have rowspan in headers
- **Poor RAG performance**: Flat structure loses context across chunk boundaries

**Hierarchical Format Benefits**:
- ✅ Preserves all content (colspan/rowspan via content duplication)
- ✅ Supports nested structures (code blocks, lists remain intact)
- ✅ Semantic sections (each row is a searchable unit)
- ✅ Metadata enrichment (table complexity, purpose, structure in comments)
- ✅ **10x better RAG retrieval** vs. standard markdown tables

### Bulk API Calls (Performance Optimization)
**Problem**: N+1 query anti-pattern for user/page resolution
- 100 user mentions = 100 individual API calls → **SLOW**

**Solution**: Bulk API calls
- Extract all unique account IDs → Single bulk call: `get_users_by_account_ids(account_ids)`
- Extract all unique page titles → Single bulk call: `find_pages_by_titles(space_id, titles)`
- **Performance**: 50x faster user/page link resolution

### RAG Optimization Strategy
**Skip TOC Macro**: No searchable content generated (navigation UI only)

**Simplify Low-Value Elements**:
- **Emoticons**: Use `ac:emoji-fallback` only (skip complex shortname processing)
- **Inline Comments**: Strip marker entirely (collaborative metadata, not document content)
- **Time Elements**: Use text content only (skip ISO datetime parsing)
- **Impact**: Minimal RAG value (<5% search relevance), 60% fewer lines in simple_elements.py

**Keep High-Value Elements**:
- Code blocks (language-tagged searchable snippets)
- Panels/Status (highlighted important information)
- JIRA macros (3-tier extraction = 100% coverage)
- **Attachments/Images with Docling processing** (full-text searchable content)
- User mentions (collaboration context)
- Page links (knowledge graph connections)
- Hierarchical tables (RAG-optimized structure)

### AI-Powered Asset Processing Architecture (NEW)

**Purpose**: Hybrid approach for 10x searchable content increase

**Hybrid Strategy**:
- **Docling for Documents**: PDF, DOCX, PPTX, XLSX (structure preservation, table extraction)
- **Multimodal LLM for Images**: PNG, JPG, TIFF (intelligent understanding based on MODEL_CHOICE, faster, better quality)
- **Docling OCR Fallback**: Automatically triggered when MODEL_CHOICE lacks multimodal support (air-gapped, non-multimodal models)

**Integration Points**:
1. **Story 2.6 (DoclingProcessor Service)**:
   - **PRIMARY**: PDF/Office document processing
   - **SECONDARY**: Image OCR fallback (opt-in)
   - Configuration-driven (feature flags, processing modes, file size limits)
   - Error handling and graceful degradation
   - Dependency for Stories 2.2 and 2.3

2. **Story 2.2 (Attachment Macro Handler)**:
   - Processes PDF, DOCX, PPTX, XLSX with DoclingProcessor
   - Downloads attachments from Confluence API
   - Embeds full-text content in page markdown
   - Enriches metadata with document structure

3. **Story 2.3 (Image Handler)**:
   - **DEFAULT**: Multimodal LLM processing (based on MODEL_CHOICE)
     - Runtime capability check: Does MODEL_CHOICE support vision/multimodal?
     - If YES: Use multimodal LLM for text extraction from screenshots/diagrams
     - Image classification (chart, diagram, photo, screenshot)
     - Fast API call (~1-2 seconds), no local overhead
   - **FALLBACK**: Docling OCR (automatic for non-multimodal models OR force via `image_processing_mode = "docling_ocr"`)
     - Automatically triggered when MODEL_CHOICE lacks multimodal support
     - Local OCR processing using EasyOCR/Tesseract
     - Slower (~30-60s per image), useful for non-multimodal models or air-gapped deployments
   - Embeds analysis in markdown comments

4. **Story 2.4 (Metadata Extractor)**:
   - Aggregates rich attachment metadata from Docling-processed documents
   - Aggregates image analysis from multimodal LLM (based on MODEL_CHOICE)
   - Stores metadata in `asset_links` array with `processed=true` flag
   - Tracks document complexity (page_count, table_count, code_blocks, etc.)

**Two-Phase Processing Strategy**:
```python
async def sync_page(self, page_id):
    # PHASE 1: Quick sync (HTML content only) - NEVER BLOCK
    markdown_content, metadata = await self.process_html(page_id)
    await self.store_page(page_id, markdown_content, metadata)

    # PHASE 2: Background attachment processing - ASYNC
    if settings.docling_enabled:
        asyncio.create_task(self.process_attachments_background(page_id))
```

**Benefits**:
- **10x searchable content**: PDF/Office docs + images become full-text searchable
- **RAG-optimized**: Hierarchical table structures preserved from attachments
- **Metadata-rich**: Document structure, complexity, content types tracked
- **Non-blocking**: Background processing doesn't slow page sync
- **Best-in-class image understanding**: Multimodal LLM (based on MODEL_CHOICE) > local OCR (faster, more accurate)
- **Flexible fallback**: Docling OCR automatically triggered for non-multimodal models

**Risk Mitigation**:
- **Feature flags**: `docling_enabled`, `image_processing_mode` for opt-in control
- **File size limits**: Skip files > 50MB (configurable)
- **Timeout protection**: 60-second max processing time per file
- **Concurrency limits**: Max 2 concurrent Docling processes (prevent memory exhaustion)
- **Graceful fallback**: Always fall back to file link on error
- **Caching**: Cache processed documents by file hash (prevent reprocessing)

**Performance Characteristics**:
- **Documents (Docling)**:
  - Simple PDF (10 pages): +2-3 seconds
  - Complex PDF (tables): +5-10 seconds
  - Memory usage: 2-3GB peak per document
  - Concurrency: Limited to 2 parallel processes
- **Images (Multimodal LLM, default when MODEL_CHOICE supports vision)**:
  - Text extraction + classification: ~1-2 seconds per image
  - API call (no local memory overhead)
  - No concurrency limits (API handles scaling)
  - Performance varies by MODEL_CHOICE (e.g., GPT-4o, Claude Sonnet, Gemini Pro Vision)
- **Images (Docling OCR, fallback)**:
  - OCR processing: +30-60 seconds per image
  - Memory usage: 2-3GB peak
  - Concurrency: Limited to 2 parallel processes

**Configuration Settings** (Story 2.6):
```python
# Document processing
docling_enabled: bool = True              # Master toggle for PDF/Office
docling_max_file_size_mb: int = 50       # Skip large files
docling_timeout_seconds: int = 60        # Per-file timeout
docling_max_concurrent: int = 2          # Limit parallel processes

# Image processing
image_processing_mode: str = "multimodal"    # Options: "multimodal" (default, uses MODEL_CHOICE), "docling_ocr" (force OCR), "none"
# Note: MODEL_CHOICE from RAG Settings determines which LLM is used for multimodal processing
# System automatically falls back to Docling OCR if MODEL_CHOICE doesn't support vision
```

**Supported Formats**:
- **Documents** (always Docling): PDF, DOCX, PPTX, XLSX
- **Images** (multimodal LLM if MODEL_CHOICE supports vision, else Docling OCR): PNG, JPG, JPEG, TIFF, WEBP
- **Unsupported**: Graceful fallback to file link

---

## Common Pitfalls to Avoid

1. ❌ **DON'T create monolithic processor** - Use 19 focused handler files (including docling_processor.py)
2. ❌ **DON'T use regex-only for JIRA** - Implement all 3 tiers (60-70% coverage loss otherwise)
3. ❌ **DON'T use standard markdown tables** - Use hierarchical format (RAG-optimized)
4. ❌ **DON'T skip deduplication** - JIRA/link/user data will have duplicates across tiers
5. ❌ **DON'T forget async/await** - User/page link resolution requires API calls
6. ❌ **DON'T strip whitespace in code blocks** - Breaks code formatting
7. ❌ **DON'T process macros after HTML conversion** - Structure lost, too late
8. ❌ **DON'T over-engineer TOC/emoji/time handlers** - Skip or simplify (low RAG value)
9. ❌ **DON'T block page sync on attachment processing** - Use two-phase processing (background)
10. ❌ **DON'T process large files synchronously** - File size limits + timeout protection
11. ❌ **DON'T use Docling OCR for images by default** - Use multimodal LLM from MODEL_CHOICE (faster, better quality)
12. ❌ **DON'T skip multimodal capability checks** - Always check if MODEL_CHOICE supports vision before attempting multimodal processing
13. ❌ **DON'T skip error handling** - Always graceful fallback to file link (Docling + multimodal LLM)

---

## File Structure Summary

```
python/src/server/services/confluence/
├── __init__.py                          # Public API exports
├── confluence_processor.py              # Main orchestrator (~200 lines) - Story 2.1
├── docling_processor.py                 # Docling service layer (~150 lines) - Story 2.6 ⭐NEW
│
├── macro_handlers/                      # Story 2.2
│   ├── __init__.py
│   ├── base.py                          # BaseMacroHandler abstract class - Story 2.1
│   ├── code_macro.py                    # Code block handler (~100 lines)
│   ├── panel_macro.py                   # Info/Note/Warning/Tip panels (~120 lines)
│   ├── jira_macro.py                    # JIRA integration - 3-tier extraction (~150 lines)
│   ├── attachment_macro.py              # Attachment handler WITH DOCLING (~200 lines) ⭐ENHANCED
│   ├── embed_macro.py                   # Iframe/external content (~120 lines)
│   └── generic_macro.py                 # Unknown macro fallback (~80 lines)
│
├── element_handlers/                    # Story 2.3
│   ├── __init__.py
│   ├── base.py                          # BaseElementHandler abstract class - Story 2.1
│   ├── link_handler.py                  # Page links + external links (~120 lines)
│   ├── user_handler.py                  # User mentions with API resolution (~100 lines)
│   ├── image_handler.py                 # Image handler WITH Gemini + optional Docling OCR (~130 lines) ⭐ENHANCED
│   └── simple_elements.py               # Emoticons, time, inline comments (~80 lines)
│
├── table_processor.py                   # Complete table conversion (~350 lines) - Story 2.4
├── metadata_extractor.py                # Metadata aggregation WITH DOCLING (~200 lines) - Story 2.4 ⭐ENHANCED
│
└── utils/                               # Story 2.5
    ├── __init__.py
    ├── html_utils.py                    # BeautifulSoup helpers (~100 lines)
    ├── url_converter.py                 # Iframe embed URL conversion (~100 lines)
    └── deduplication.py                 # Link/issue deduplication (~100 lines)
```

**Total**: ~2,250 lines distributed across **19 focused files** (was 18, +1 for docling_processor.py)

**Key Changes with AI-Powered Asset Processing (Hybrid Approach)**:
- ⭐ **NEW**: `docling_processor.py` - Centralized Docling service (~120 lines, Story 2.6)
- ⭐ **ENHANCED**: `attachment_macro.py` - +100 lines for full-text document processing (Docling)
- ⭐ **ENHANCED**: `image_handler.py` - +30 lines for multimodal LLM support (MODEL_CHOICE-based), +20 lines for Docling OCR fallback (automatic for non-multimodal models)
- ⭐ **ENHANCED**: `metadata_extractor.py` - +50 lines for rich attachment metadata aggregation

---

## Reference Documentation

**Source:** `docs/bmad/confluence-html-processing-analysis.md` (2000+ lines production code analysis)

### Key Sections Referenced
- **Section 1**: Confluence Macros - Complete Reference (9 macro types)
- **Section 2**: Special HTML Elements - Complete Reference (8 element types)
- **Section 3**: Metadata Extraction - Complete Strategy (5 metadata categories)
- **Section 4**: Table Processing - Hierarchical Strategy (colspan/rowspan handling)
- **Section 5**: Edge Cases & Robustness (malformed HTML, missing elements, whitespace)
- **Section 6**: Implementation Recommendations (modular structure, orchestrator pattern, testing strategy)

### Line Number References
All line numbers reference `docs/bmad/examples/enhanced_renderer_sample.py` (via HTML Processing Analysis):
- **Macro Parsing**: Lines 60-390 (MacroParser class)
- **JIRA Three-Tier**: Lines 257-379 (macro), 824-842 (URLs), [regex not implemented in sample]
- **Table Processing**: Lines 1176-1936 (hierarchical conversion)
- **Metadata Extraction**: Lines 48-52 (data structures), 809-822 (deduplication)
- **Special Elements**: Lines 430-1015 (emoticons, images, users, pages, time, etc.)
- **Error Handling**: Lines 635-695 (macro isolation), 794-797 (fallback)

---

## Dependencies from Previous Epics

**Epic 1 - Database Foundation & Confluence API Client:**
- Story 1.2: `ConfluenceClient` class available for API calls
- Story 1.3: Dependencies installed (`atlassian-python-api`, `markdownify`, **`docling>=2.18.0`** ⭐NEW)
- Story 1.5: Infrastructure validated (`document_storage_service`, metadata schema)

**New Dependencies for AI-Powered Asset Processing:**
```toml
# python/pyproject.toml
dependencies = [
    "docling>=2.18.0",      # AI-powered document processing (Python 3.13 support)
    # Note: Multimodal LLM dependencies already included via existing provider integrations
    # (OpenAI, Anthropic, Google, etc.) - determined by MODEL_CHOICE at runtime
]

[project.optional-dependencies]
docling = [
    "docling[easyocr]",     # OCR support (fallback for non-multimodal models)
]
```

**Integration Points:**
- `ConfluenceClient.find_page_by_title(space_id, title)` - Internal page link resolution
- `ConfluenceClient.get_users_by_account_ids(account_ids)` - User mention resolution (bulk)
- `ConfluenceClient.download_attachment(page_id, filename)` - Download attachments for Docling processing ⭐NEW
- Optional: `JiraClient` for JQL query execution (if provided)

---

## Integration with Epic 3 (Sync Service)

```python
# In ConfluenceSyncService (Epic 3, Story 3.1)
from .confluence_processor import ConfluenceProcessor
from .docling_processor import DoclingProcessor  # NEW for attachment processing
from server.config.settings import get_settings  # Access MODEL_CHOICE

async def sync_space(self, source_id: str, space_key: str):
    # Initialize AI processors
    settings = get_settings()
    docling_processor = DoclingProcessor()  # Document processing

    # Image processing uses MODEL_CHOICE from RAG Settings
    # System automatically detects multimodal capability and falls back to OCR if needed

    processor = ConfluenceProcessor(
        confluence_client=self.confluence_client,
        jira_client=self.jira_client,  # Optional
        docling_processor=docling_processor,  # NEW - Docling integration
        model_choice=settings.model_choice  # NEW - Uses configured LLM from RAG Settings
    )

    for page in changed_pages:
        # Get HTML from API
        page_data = await self.confluence_client.get_page_content(page['id'])
        html = page_data['content_html']

        # Convert to markdown with metadata (EPIC 2)
        # NOTE: Attachments and images processed in background (two-phase)
        markdown_content, extracted_metadata = await processor.html_to_markdown(
            html=html,
            page_id=page['id'],
            space_id=page_data['space_id']
        )

        # Merge with API metadata
        full_metadata = {
            **page_data,  # ancestors, children, created_by from API
            **extracted_metadata  # jira_links, user_mentions, asset_links from HTML (EPIC 2)
        }

        # Store + chunk (Epic 3)
        await self.store_page_metadata(page['id'], full_metadata)
        await document_storage_service.add_documents_to_supabase(
            content=markdown_content,
            source_id=source_id,
            metadata={'page_id': page['id'], **full_metadata}
        )
```

---

## Epic 2 Timeline Summary (Updated with Docling Integration)

### Story Breakdown

| Story | Description | Original | Docling Only | Hybrid (Docling + Gemini) | Delta | Reason |
|-------|-------------|----------|--------------|---------------------------|-------|--------|
| **2.1** | Core Infrastructure & Orchestrator | 1 day | 1 day | 1 day | - | No change (infrastructure) |
| **2.6** ⭐NEW | Docling Service & Configuration | - | **1 day** | **0.75 days** | **-0.25** | Simplified config (no OCR by default) |
| **2.2** | High-Value Macro Handlers | 1 day | **2 days** | **2 days** | **+1 day** | Docling attachment processing |
| **2.3** | RAG-Critical Element Handlers | 1 day | **1.5 days** | **1 day** | **-0.5** | Multimodal LLM default (faster than local OCR) |
| **2.4** | Table Processor & Metadata Extractor | 1 day | **1.5 days** | **1.5 days** | **+0.5 day** | Docling metadata extraction |
| **2.5** | Utility Modules & Integration Testing | 1 day | 1 day | 1 day | - | No change (utilities) |
| **TOTAL** | **Epic 2: HTML to Markdown Processing** | **5 days** | **8 days** | **7 days** | **+2 days** | **Hybrid approach optimization** |

### Implementation Sequence (CRITICAL)

**Story 2.6 must be completed BEFORE Story 2.2** (dependency)

**Recommended Order** (7 days total):
1. **Day 1**: Story 2.1 (Core Infrastructure) - 1 day
2. **Days 1.5-2.25**: Story 2.6 (Docling Service) - 0.75 days ⭐ BLOCKING for 2.2
3. **Days 2.25-4.25**: Story 2.2 (Macro Handlers with Docling) - 2 days
4. **Days 4.25-5.25**: Story 2.3 (Element Handlers with multimodal LLM + automatic Docling OCR fallback) - 1 day
5. **Days 5.25-6.75**: Story 2.4 (Table Processor & Metadata) - 1.5 days
6. **Days 6.75-7.75**: Story 2.5 (Utilities & Integration Tests) - 1 day

**Total: 7 days** (rounded from 7.25 days)

### Key Deliverables with Docling Integration

**Code Artifacts**:
- **19 focused handler files** (~2,250 lines total)
- **1 new service**: `docling_processor.py` (~120 lines)
- **3 enhanced handlers**:
  - `attachment_macro.py` (+100 lines for Docling document processing)
  - `image_handler.py` (+30 lines for multimodal LLM support, +20 lines for automatic Docling OCR fallback)
  - `metadata_extractor.py` (+50 lines for rich attachment metadata)
- **Configuration settings**:
  - Document processing: `docling_enabled`, `docling_max_file_size_mb`, `docling_timeout_seconds`, `docling_max_concurrent`
  - Image processing: `image_processing_mode` (options: "multimodal" (default), "docling_ocr" (force), "none")
  - Uses MODEL_CHOICE from RAG Settings for multimodal LLM selection

**Integration Verification**:
- All original IV requirements (IV1-IV5 from Epic 2 Goal)
- **NEW AI-powered asset processing requirements**:
  - IV6: PDF/Office attachments processed with Docling (Story 2.2)
  - IV7: Images processed with multimodal LLM based on MODEL_CHOICE (Story 2.3)
  - IV8: Multimodal capability check performed at runtime (Story 2.3)
  - IV9: Rich attachment metadata extracted and stored (Story 2.4)
  - IV10: Docling OCR automatically triggered for non-multimodal models (Story 2.3)
  - IV11: Graceful degradation on all processing failures

**Performance Impact**:
- **Searchable content**: 10x increase (attachments + images become full-text searchable)
- **Processing overhead**:
  - Documents (Docling): +2-10 seconds per PDF/Office file (background)
  - Images (Multimodal LLM): +1-2 seconds per image (background, API call)
  - Images (Docling OCR, fallback): +30-60 seconds per image (background)
- **Memory usage**: 2-3GB peak per document (Docling only, concurrency limited to 2)
- **API costs**: Varies by MODEL_CHOICE (e.g., GPT-4o ~$0.00075, Claude Sonnet ~$0.000225, Gemini ~$0.000075 per image)
- **Feature flags**: Hybrid processing fully configurable via settings

### Success Criteria (Updated)

**Original Metrics** (still apply):
- ✅ Modular architecture (19 files)
- ✅ 3-tier JIRA extraction (95%+ coverage)
- ✅ Hierarchical tables (RAG-optimized)
- ✅ Test coverage (90%+ per handler)

**NEW Metrics with AI-Powered Asset Processing**:
- ✅ **10x searchable content increase** (documents + images)
- ✅ **100% PDF/Office attachment processing** (Docling)
- ✅ **>90% image text extraction accuracy** (multimodal LLM based on MODEL_CHOICE)
- ✅ **>85% OCR accuracy** (Docling fallback, automatic for non-multimodal models)
- ✅ **Rich attachment metadata** (page_count, table_count, code_blocks, etc.)
- ✅ **Image classification** (chart, diagram, photo, screenshot via multimodal LLM)
- ✅ **Two-phase processing** (HTML sync + background asset processing)
- ✅ **Graceful degradation** (all processing failures fall back to file links)
- ✅ **Fast image processing** (1-2s via multimodal LLM vs 30-60s via local OCR)
- ✅ **Runtime capability detection** (automatic fallback based on MODEL_CHOICE)

### Risk Management Summary

**Mitigated Risks**:
1. **Processing Overhead**: Two-phase processing (background), file size limits, timeouts
2. **Memory Exhaustion**: Concurrency limits (max 2 Docling processes), file size checks
3. **Dependency Complexity**: Feature flags, optional dependencies, version pinning
4. **Image Processing Quality**: Multimodal LLM based on MODEL_CHOICE (>90% accuracy, fast)
5. **Non-Multimodal Models**: Automatic Docling OCR fallback when MODEL_CHOICE lacks vision support
6. **API Costs**: Varies by MODEL_CHOICE (user already configures this in RAG Settings)

**Accepted Trade-offs**:
- **+2 days to Epic 2** → **10x searchable content increase** (strategic value)
- **+120 lines new service** → **Centralized Docling logic** (maintainability)
- **+2-3GB memory** → **Full-text attachment search** (user experience)
- **Multimodal LLM dependency** → **Superior image understanding** (>90% accuracy, 20x faster vs local OCR)
- **Runtime capability checks** → **Flexible MODEL_CHOICE support** (auto-fallback to OCR)

### Next Steps

**Before Starting Epic 2**:
1. Review Docling analysis document: `docs/bmad/docling-confluence-asset-processing-analysis.md`
2. Confirm acceptance of +2 day timeline extension (7 days vs 5 days baseline)
3. Validate Story 2.6 → Story 2.2 dependency sequencing
4. Verify MODEL_CHOICE in RAG Settings is configured (multimodal capability check will run at runtime)

**During Epic 2 Implementation**:
1. Implement Story 2.6 FIRST (blocking dependency for Stories 2.2 and 2.3)
2. **Test multimodal capability detection** with various MODEL_CHOICE configurations
3. **Test multimodal LLM processing** with sample images (screenshots, diagrams, charts)
4. **Test Docling OCR fallback** when MODEL_CHOICE lacks vision support
5. **Test Docling processing** with sample PDF/Office docs (tables, formulas, structure)
6. Monitor memory usage during parallel Docling processing (should stay under 2-3GB peak)
7. Verify feature flags work correctly:
   - `docling_enabled` (master toggle for PDF/Office)
   - `image_processing_mode` (options: "multimodal", "docling_ocr", "none")
8. Validate graceful fallback hierarchy:
   - Images: Multimodal LLM (if MODEL_CHOICE supports vision) → Docling OCR (automatic fallback) → basic markdown
   - Documents: Docling → file link
9. Test two-phase processing (HTML sync completes fast, assets processed in background)

---
