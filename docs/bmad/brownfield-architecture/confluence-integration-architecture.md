# Confluence Integration Architecture

## Overview: Hybrid Schema Approach

**Source:** `docs/bmad/CONFLUENCE_RAG_INTEGRATION.md` (1,333 lines of detailed planning)

The Confluence integration uses a **Hybrid database schema** that combines:
1. Dedicated `confluence_pages` table for rich metadata (~15 KB per page)
2. **REUSE** of existing `archon_crawled_pages` table for chunks (unified storage)
3. Link via `metadata->>'page_id'` with indexed lookup

**Why Hybrid?**
- **90% code reuse**: Leverage existing `document_storage_service.py` and `hybrid_search_strategy.py`
- **Unified search**: ONE table for all chunks (web, Confluence, future sources) - no UNION queries!
- **Clean separation**: Metadata in dedicated table, chunks in shared table
- **Future-proof**: Pattern scales to Google Drive, SharePoint, Notion, etc.
- **Fast implementation**: 1.5-2 weeks vs 3-4 weeks for separate tables

## Data Pipeline Flow (90% Code Reuse!)

```
┌─────────────────┐
│ Confluence API  │
│   (REST v2)     │
└────────┬────────┘
         │
         │ 1. Fetch pages (CQL queries)
         │    CQL: space = DEVDOCS AND lastModified >= "2025-10-01 10:00"
         │    Only changed pages - no full space scans!
         │
         ▼
┌──────────────────────────────────────────┐
│ Confluence Sync Service (NEW - ~400 lines) │
│                                            │
│ - CQL-based incremental sync              │
│ - Atomic chunk update strategy            │
│ - Deletion detection & reconciliation     │
│ - Sync observability (metrics tracking)   │
└────────┬───────────────────────────────────┘
         │
         │ 2. For each page: Process HTML → Markdown
         │
         ▼
┌──────────────────────────────────────────────────┐
│ Confluence Processor (NEW - ~200 lines orchestrator) │
│                                                  │
│ Five-Pass Processing Pipeline:                  │
│ Pass 1: Process Confluence Macros               │
│   ├─ Code blocks (CDATA unwrap, whitespace)     │
│   ├─ Panels (Info/Note/Warning/Tip)             │
│   ├─ JIRA macros (3-tier extraction ★)          │
│   ├─ Attachments (file type mapping)            │
│   ├─ Embeds (YouTube/Maps URL conversion)       │
│   └─ Unknown macros (graceful fallback)         │
│                                                  │
│ Pass 2: Process Special HTML Elements           │
│   ├─ User mentions (bulk API resolution)        │
│   ├─ Page links (bulk API lookups)              │
│   ├─ Images (attachment tracking)               │
│   └─ Simple elements (emoticons, time)          │
│                                                  │
│ Pass 3: Process Tables                          │
│   └─ Hierarchical markdown (NOT std tables!)    │
│      - Colspan/rowspan duplication              │
│      - Metadata enrichment                      │
│                                                  │
│ Pass 4: Convert to Markdown                     │
│   └─ markdownify with ATX headings              │
│                                                  │
│ Pass 5: Extract Metadata                        │
│   ├─ 3-tier JIRA extraction (95%+ coverage)     │
│   ├─ User mentions deduplication                │
│   ├─ Link deduplication                         │
│   └─ Asset aggregation                          │
└────────┬─────────────────────────────────────────┘
         │
         │ 3. Store metadata
         │
         ▼
┌─────────────────┐
│confluence_pages │ ◄─── archon_sources (space metadata)
│  (metadata)     │      {confluence_space_key, last_sync_timestamp,
│                 │       total_pages, sync_metrics}
│ Rich JSONB:     │
│ - ancestors     │      ★ Metadata enriched via Confluence API
│ - jira_links    │        + HTML processing extraction
│ - user_mentions │
│ - internal_links│
│ - asset_links   │
└────────┬────────┘
         │
         │ 4. Delete old chunks & Call existing service
         │    DELETE WHERE metadata->>'page_id' = $1
         │    CALL document_storage_service.add_documents_to_supabase()
         │    **REUSE existing chunking/embedding logic!**
         │
         ▼
┌─────────────────────────┐
│ archon_crawled_pages    │ ◄─── EXISTING table (REUSED!)
│ (unified chunks)        │      - Web crawls
│                         │      - Document uploads
│ metadata: {             │      - Confluence pages ✓
│   "page_id": "...",     │      - Future: Drive, SharePoint
│   "section_title": "..."│
│ }                       │
└────────┬────────────────┘
         │
         │ 5. Unified Search (NO VIEW NEEDED!)
         │    Query archon_crawled_pages directly
         │    LEFT JOIN confluence_pages for metadata enrichment
         │
         ▼
┌─────────────────┐
│ Hybrid Search   │ ◄─── EXISTING service (REUSED!)
│  (One table)    │      hybrid_search_strategy.py
└─────────────────┘      **No changes needed for basic search!**
```

## CQL-Based Incremental Sync Strategy

**No full space scans!** Confluence syncs use CQL (Confluence Query Language) to fetch only changed pages:

```python
# Example CQL query
cql = f'space = {space_key} AND lastModified >= "{last_sync_timestamp}"'
changed_pages = confluence_client.cql_search(cql, expand='body.storage,version,ancestors')
```

**Deletion Detection Strategies:**
- `weekly_reconciliation` (default): Check for deletions once per week
- `every_sync`: Check every sync (1 API call per 1000 pages)
- `on_demand`: Never check during sync (user notices 404s)

**Atomic Chunk Updates (Zero Downtime):**
1. Mark old chunks as `_pending_deletion` in metadata
2. Insert new chunks (old chunks still searchable!)
3. Delete old chunks only after success
4. Transaction ensures atomicity

## Implementation Phases (1.5-2 Weeks)

### Phase 1: Database & Basic Sync (Week 1)
- Create `confluence_pages` table (migration 010)
- Implement `ConfluenceClient` using `atlassian-python-api`
- CQL-based incremental sync logic
- HTML → Markdown conversion
- Store metadata with materialized path
- **Call existing `document_storage_service.add_documents_to_supabase()`** ✓

### Phase 2: API & Incremental Sync (Week 1)
- Implement `ConfluenceSyncService` with metrics tracking
- Handle page creates, updates, deletes
- Atomic chunk updates
- API endpoints in `confluence_api.py`
- Use existing `ProgressTracker` for sync status ✓

### Phase 3: Search Integration (Week 2)
- **NO CHANGES to core search!** Already works with `archon_crawled_pages` ✓
- Optional: Add `LEFT JOIN confluence_pages` for metadata enrichment
- Add Confluence-specific filters (space, JIRA links)

### Phase 4: Frontend & Testing (Week 2)
- Create `src/features/confluence/` vertical slice
- Source creation form, sync status, progress display
- Unit tests, integration tests, load testing (4000+ pages)

## Files to Create (~2,100 lines total)

### 1. Backend Services - Modular Architecture

**Core Services:**
- `python/src/server/services/confluence/confluence_client.py` (~200 lines)
  - Confluence REST API v2 integration using `atlassian-python-api`
  - CQL search for incremental sync
  - Bulk user/page lookups (N+1 prevention)

- `python/src/server/services/confluence/confluence_sync_service.py` (~400 lines)
  - CQL-based incremental sync orchestration
  - Atomic chunk update strategy (zero-downtime)
  - Sync observability and metrics tracking
  - Deletion detection with configurable strategies

- `python/src/server/services/confluence/confluence_processor.py` (~200 lines)
  - Main orchestrator for HTML → Markdown conversion
  - Five-pass processing pipeline:
    1. Process Confluence macros
    2. Process special HTML elements
    3. Process tables (hierarchical conversion)
    4. Convert to markdown
    5. Extract metadata
  - Handler registration and dependency injection

**Macro Handlers** (`macro_handlers/` - 6 files):
- `code_macro.py` (~100 lines) - Language-tagged code blocks with whitespace preservation
- `panel_macro.py` (~120 lines) - Info/Note/Warning/Tip with emoji prefixes
- `jira_macro.py` (~150 lines) - **3-tier extraction** (macros + URLs + regex) for 95%+ coverage
- `attachment_macro.py` (~100 lines) - File references with type-based emoji mapping
- `embed_macro.py` (~120 lines) - Iframe URL conversion (15+ platforms: YouTube, Vimeo, Maps, etc.)
- `generic_macro.py` (~80 lines) - Unknown macro fallback handler

**Element Handlers** (`element_handlers/` - 4 files):
- `link_handler.py` (~120 lines) - Page links + external links with bulk API lookups
- `user_handler.py` (~100 lines) - User mentions with bulk resolution via `get_users_by_account_ids()`
- `image_handler.py` (~100 lines) - Attachment tracking with extension-based icons
- `simple_elements.py` (~80 lines) - Simplified handlers for emoticons, time, inline comments

**Processing Modules:**
- `table_processor.py` (~350 lines)
  - **Hierarchical markdown conversion** (NOT standard tables!)
  - Colspan/rowspan content duplication for RAG optimization
  - Multi-level header matrix building
  - Metadata enrichment (table complexity, purpose inference)

- `metadata_extractor.py` (~150 lines)
  - 3-tier JIRA extraction (macros → URLs → regex)
  - User mention deduplication
  - Link deduplication (internal/external)
  - Asset aggregation from multiple sources

**Utilities** (`utils/` - 3 files):
- `html_utils.py` (~100 lines) - BeautifulSoup helpers, whitespace normalization
- `url_converter.py` (~100 lines) - Iframe embed URL conversion (YouTube, Maps, etc.)
- `deduplication.py` (~100 lines) - Link/issue deduplication logic

### 2. API Routes
- `python/src/server/api_routes/confluence_api.py` (~100 lines)

### 3. Database Migration
- `migration/0.1.0/010_add_confluence_pages.sql` (schema + indexes)

### 4. Frontend (future)
- `archon-ui-main/src/features/confluence/` (vertical slice)

**Total:** ~2,100 lines (18 focused files vs. 3 monolithic files)

## Docling Asset Processing Integration

**Purpose:** Process Confluence attachments (PDFs, Office docs) and images to enable full-text search and OCR capabilities.

**Reference:** `docs/bmad/docling-confluence-asset-processing-analysis.md` (1,385 lines of analysis)

### Docling Overview

Docling is an open-source document processing library (IBM Research/LF AI & Data Foundation) designed for generative AI applications:
- **41.8k+ GitHub stars**, MIT licensed
- **Advanced capabilities**: Layout analysis, table structure, OCR, metadata extraction
- **RAG-optimized**: DocLayNet & TableFormer state-of-the-art models
- **Multiple formats**: PDF, DOCX, PPTX, XLSX, images (PNG, JPEG, TIFF), HTML
- **Local processing**: Air-gapped execution for sensitive data

### Integration Points in Epic 2

#### 1. Attachment Macro Handler Enhancement (Story 2.2)

**Current:** Emoji icons only (📄📝📊📦📎)
**Enhanced:** Full-text extraction and embedding in page markdown

```python
class AttachmentMacroHandler(BaseMacroHandler):
    def __init__(self):
        self.docling_processor = DoclingProcessor()

    async def handle(self, macro_element, context):
        filename = macro_element.get("ac:parameter", {}).get("filename")
        file_path = await self._download_attachment(filename)

        # Process with Docling if supported format
        if self._is_docling_supported(file_path):
            result = self.docling_processor.process_attachment(file_path)
            markdown_content = result.document.export_to_markdown()

            # Embed in main page content
            return f"\n\n<!-- ATTACHMENT: {filename} -->\n{markdown_content}\n"
        else:
            # Fallback to filename link
            return f"[{filename}]({self._get_download_url(filename)})"
```

**Supported Formats:** PDF, DOCX, PPTX, XLSX, PNG, JPEG, TIFF, BMP, WEBP

#### 2. Image Handler Enhancement (Story 2.3)

**Current:** Asset tracking only
**Enhanced:** AI-powered image understanding with multimodal LLM + OCR fallback

```python
class ImageHandler(BaseElementHandler):
    def __init__(self, model_choice: str, docling_processor: DoclingProcessor):
        self.model_choice = model_choice
        self.docling_processor = docling_processor
        self.image_processing_mode = settings.image_processing_mode  # "multimodal", "docling_ocr", "none"

    async def handle(self, image_element, context):
        image_path = await self._download_image(image_element)

        # DEFAULT: Try multimodal LLM processing first
        if self.image_processing_mode == "multimodal":
            if self._supports_multimodal(self.model_choice):
                # Use MODEL_CHOICE from RAG Settings (e.g., GPT-4o, Claude Sonnet, Gemini Pro Vision)
                result = await self._process_with_multimodal_llm(image_path)
                if result.success:
                    return f"![{alt_text}]({image_path})\n\n<!-- AI Analysis: {result.text}\nType: {result.image_type} -->\n"
            else:
                # Automatic fallback to Docling OCR for non-multimodal models
                logger.info(f"Model {self.model_choice} doesn't support vision, falling back to Docling OCR")
                self.image_processing_mode = "docling_ocr"

        # FALLBACK: Docling OCR (automatic for non-multimodal models OR force via config)
        if self.image_processing_mode == "docling_ocr":
            result = await self.docling_processor.process_image_ocr(image_path)
            if result.success:
                return f"![{alt_text}]({image_path})\n\n<!-- OCR: {result.text} -->\n"

        # Final fallback: Standard image markdown
        return f"![{alt_text}]({image_path})"

    def _supports_multimodal(self, model_choice: str) -> bool:
        """Check if MODEL_CHOICE supports vision/multimodal capabilities."""
        multimodal_models = {
            "gpt-4o", "gpt-4-vision", "claude-3-opus", "claude-3-sonnet",
            "gemini-pro-vision", "gemini-1.5-pro", "gemini-2.0"
        }
        return any(model in model_choice.lower() for model in multimodal_models)
```

#### 3. Metadata Extractor Enhancement (Story 2.4)

**Add rich document metadata:**
```python
{
    "page_count": 15,
    "table_count": 3,
    "code_block_count": 5,
    "has_formulas": True,
    "word_count": 7351,
    "document_structure": {"sections": 8, "max_heading_level": 4}
}
```

### Performance Considerations

**Processing Times (CPU):**
- Simple PDF (10 pages): ~2-3 seconds
- Complex PDF with tables: ~5-10 seconds
- Scanned PDF with OCR: ~30-60 seconds
- Office documents: ~1-2 seconds
- Image with OCR: ~3-5 seconds

**Mitigation Strategies:**
- **Async Processing**: Process attachments in background after page sync
- **File Size Limits**: Skip files > 50MB (configurable)
- **Caching**: Cache processed documents by file hash
- **Selective Processing**: Only process specific file types
- **Feature Flag**: `docling_enabled` configuration option

### Configuration

```python
# python/src/server/config/settings.py
class ConfluenceSettings(BaseSettings):
    # Document processing (PDF/Office)
    docling_enabled: bool = True                      # Master toggle for PDF/Office processing
    docling_max_file_size_mb: int = 50                # Skip large files
    docling_timeout_seconds: int = 60                 # Per-file timeout
    docling_max_concurrent: int = 2                   # Limit parallel processes (memory management)

    # Image processing
    image_processing_mode: str = "multimodal"         # Options: "multimodal" (default, uses MODEL_CHOICE),
                                                       # "docling_ocr" (force OCR), "none"
    # Note: MODEL_CHOICE from RAG Settings determines which LLM is used for multimodal processing
    # System automatically falls back to Docling OCR if MODEL_CHOICE doesn't support vision
```

### Implementation Phases

**Phase 1 (Epic 2):** Hybrid approach (2-3 days)
- **Documents:** Process PDF/Office attachments with Docling
- **Images:** Multimodal LLM processing (based on MODEL_CHOICE from RAG Settings)
  - Runtime capability check (does MODEL_CHOICE support vision?)
  - Automatic fallback to Docling OCR if model lacks multimodal support
  - Manual override via `image_processing_mode = "docling_ocr"`
- Embed extracted content in page markdown
- Extract rich metadata (page counts, tables, code blocks, etc.)

**Phase 2 (Post-Epic 2):** Optimization (1-2 weeks)
- Batch processing optimization
- Result caching by file hash
- GPU acceleration for Docling
- Enhanced multimodal prompts

**Phase 3 (Future):** Advanced features (2-3 weeks)
- Advanced search filters (by document structure, content type, etc.)
- Custom metadata extraction rules
- Multi-file document processing

### Expected Benefits

- **10x increase** in searchable content (attachments + images become full-text searchable)
- **Better RAG quality** through structured document understanding
- **Richer metadata** (document structure, content types, complexity metrics)
- **Code snippet extraction** from technical PDFs
- **Table data** from spreadsheets embedded in markdown
- **Fast image understanding** via multimodal LLM (~1-2s per image vs 30-60s OCR)
- **Automatic fallback** to Docling OCR for non-multimodal models (no manual configuration needed)
- **Flexible MODEL_CHOICE support** - works with any LLM configured in RAG Settings

## Dependencies to Add

```toml
# python/pyproject.toml - Add to [dependency-groups.server]
atlassian-python-api = "^3.41.0"  # Confluence REST API client
markdownify = "^0.11.6"           # HTML to Markdown conversion

# Docling dependencies (Phase 1 - Epic 2)
docling = ">=2.18.0"               # Python 3.13 support (PDF/Office document processing)
# Note: Multimodal LLM dependencies already included via existing provider integrations
# (OpenAI, Anthropic, Google, etc.) - determined by MODEL_CHOICE at runtime

[project.optional-dependencies]
docling = [
    "docling[easyocr]",             # OCR support (fallback for non-multimodal models)
]
```

---
