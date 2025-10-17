# Integration Points and External Dependencies

## External Services

| Service       | Purpose                        | Integration Type | Key Files                               | Status |
| ------------- | ------------------------------ | ---------------- | --------------------------------------- | ------ |
| **Supabase**  | Database & Vector Store        | SDK              | Throughout `server` service             | ✅ Active |
| **OpenAI**    | LLM for chat & embeddings      | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Google AI** | Gemini models & embeddings     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Ollama**    | Local LLM serving              | HTTP API         | `services/llm_provider_service.py`      | ✅ Active |
| **Anthropic** | Claude API                     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Grok**      | xAI models                     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **OpenRouter**| Community model hub            | API              | `services/llm_provider_service.py`      | ✅ Active |
| **GitHub API**| Version checking               | REST API         | `services/version_service.py`           | ✅ Active |
| **Confluence**| Knowledge base sync            | REST API v2      | `services/confluence/`                  | ✅ Active |
| **Docling**   | Document/image processing      | Python Library   | `services/confluence/docling_processor.py` | ✅ Active |

## LLM Provider Capabilities

**Chat + Embeddings:**
- OpenAI: GPT-4o, GPT-4o-mini + text-embedding-3-small/large
- Google: Gemini 1.5/2.0 models + gemini-embedding-001
- Ollama: Local models (llama3, mistral, etc.) with embedding support

**Chat Only (No Embeddings):**
- Anthropic: Claude 3.5 Sonnet, Claude 3 Opus/Haiku
- Grok: grok-3-mini, grok-3 (xAI models)
- OpenRouter: Community-hosted models (various)

**Embedding Providers (UI Enforces Restriction):**
- ✅ OpenAI, Google, Ollama ONLY
- ❌ Anthropic, Grok, OpenRouter NOT supported for embeddings

## Confluence API Integration (Implemented)

**API Documentation:**
- Confluence REST API v2: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
- Confluence CQL: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/
- Python SDK: `atlassian-python-api` v3.41.0+ (https://atlassian-python-api.readthedocs.io/)

**Dependencies (Implemented):**
```toml
# python/pyproject.toml - [dependency-groups.server]
atlassian-python-api = ">=3.41.0"  # Confluence REST API client SDK
markdownify = ">=0.11.0"            # HTML to Markdown conversion
docling = ">=2.18.0"                # Document processing library
docling[easyocr] = ">=2.18.0"       # OCR capabilities
```

**Environment Variables (Optional Configuration):**
```bash
# Can be set via .env file or Settings API (encrypted storage)
CONFLUENCE_BASE_URL=https://your-company.atlassian.net/wiki  # Required: Confluence Cloud URL (HTTPS only)
CONFLUENCE_API_TOKEN=your-api-token-here                      # Required: API token from Atlassian
CONFLUENCE_EMAIL=your-email@company.com                       # Required: Email for API authentication
```

**Configuration Pattern:**
- **Optional at startup**: Archon runs without Confluence configured
- **Required variables**: All three variables needed when creating Confluence source
- **URL validation**: Must use HTTPS (Confluence Cloud requirement)
- **Base URL only**: Don't include space paths (e.g., `/spaces/DEVDOCS`)
- **Encryption**: API tokens stored encrypted (Fernet encryption) in `archon_settings` table
- **Settings API**: Alternative to environment variables via `POST /api/credentials`

**Integration Pattern (Implemented):**
```python
from atlassian import Confluence

class ConfluenceClient:
    def __init__(self, base_url: str, api_token: str, email: str):
        self.client = Confluence(
            url=base_url,
            token=api_token,
            cloud=True  # Confluence Cloud mode
        )
        self.email = email

    async def cql_search(self, cql: str, expand: str = None):
        # CQL example: 'space = DEVDOCS AND lastModified >= "2025-10-01 10:00"'
        return self.client.cql(cql, expand=expand, limit=1000)

    async def get_page_ids_in_space(self, space_key: str) -> list[str]:
        # Lightweight deletion detection - IDs only, no content
        pages = self.client.get_all_pages_from_space(
            space=space_key, expand=None
        )
        return [p['id'] for p in pages]

    async def get_users_by_account_ids(self, account_ids: list[str]) -> dict:
        # Bulk user lookup (N+1 prevention)
        # Single API call instead of individual requests per user
        users = {}
        for account_id in account_ids:
            user_info = self.client.get_user_details_by_accountid(account_id)
            users[account_id] = user_info
        return users

    async def find_page_by_title(self, space_id: str, title: str) -> dict:
        # Bulk page lookup by title (used for internal link resolution)
        return self.client.get_page_by_title(space=space_id, title=title)
```

**HTML Processing Architecture (Modular - ~2,100 lines across 19 files):**

See `docs/bmad/confluence-html-processing-analysis.md` for complete implementation details.

**Key Processing Features:**
- **9 Macro Types**: Code, Panel, Status, Expand, TOC, JIRA, View-File, Iframe, Unknown
- **8 Special Elements**: Emoticons, Inline Comments, ADF Extensions, Images, User Mentions, Page Links, Time, External Links
- **5-Pass Pipeline**: Macros → Elements → Tables → Markdown → Metadata
- **3-Tier JIRA Extraction**: Macros (40%) + URLs (30%) + Regex (30%) = 95%+ coverage
- **Hierarchical Tables**: NOT standard markdown tables (10x better RAG retrieval)
- **RAG Optimization**: Skip TOC, simplify emoticons/time/comments (low search value)
- **Bulk API Calls**: User mentions and page links use batch operations
- **Error Isolation**: Each handler wrapped in try-except for graceful degradation

**Implementation Files:**
- **Configuration**: `python/src/server/config/config.py` (lines 29-35, 145-189, 259-266)
  - `EnvironmentConfig` dataclass with Confluence fields
  - `validate_confluence_url()` function with HTTPS enforcement
  - Optional loading with URL validation
- **Client Service**: `python/src/server/services/confluence/` (planned/TBD)
- **Tests**: `python/tests/server/config/test_config_confluence.py` (18 unit tests)
- **Integration Tests**: `python/tests/server/config/test_confluence_settings_integration.py` (5 tests)

## Docling Document Processing Integration (Implemented)

**Purpose:** Process Confluence PDF/Office attachments for full-text search and structured metadata extraction. Provides OCR fallback for images when multimodal LLM is unavailable.

**Documentation:**
- Official Docs: https://docling-project.github.io/docling/
- GitHub Repository: https://github.com/docling-project/docling (41.8k+ stars)
- Technical Report: arXiv:2408.09869
- Integration Analysis: `docs/bmad/docling-confluence-asset-processing-analysis.md`

**Project Overview:**
- **Maintainer:** LF AI & Data Foundation (IBM Research origin)
- **License:** MIT
- **Python Support:** 3.10, 3.11, 3.12, 3.13
- **Core Capabilities:**
  - Advanced PDF processing (layout analysis, table structure, code blocks)
  - OCR support (EasyOCR, Tesseract, RapidOCR, OnnxTR)
  - Office document conversion (DOCX, PPTX, XLSX)
  - Image processing with vision models
  - Metadata extraction (beta)

**Dependencies:**
```toml
# python/pyproject.toml - [dependency-groups.server]
docling = ">=2.18.0"                # Core document processing (PDF/Office)
# Note: Multimodal LLM dependencies already included via existing provider integrations
# (OpenAI, Anthropic, Google, etc.) - determined by MODEL_CHOICE at runtime

[project.optional-dependencies]
docling = [
    "docling[easyocr]",             # OCR support (fallback for non-multimodal models)
]
```

**Supported File Formats:**
- **Documents:** PDF, DOCX, XLSX, PPTX, HTML, Markdown, AsciiDoc
- **Images:** PNG, JPEG, TIFF, BMP, WEBP
- **Others:** CSV, Audio (WAV, MP3), WebVTT (subtitles)

**Integration Pattern (Phase 1 - Epic 2):**

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions

class DoclingProcessor:
    def __init__(self):
        # Configure for fast processing
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False  # Enable selectively for scanned docs
        pipeline_options.do_table_structure = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    async def process_attachment(self, file_path: Path) -> dict:
        """PRIMARY USE: Process PDF/Office documents and return markdown + metadata."""
        try:
            result = self.converter.convert(str(file_path))

            return {
                "success": True,
                "markdown": result.document.export_to_markdown(),
                "plain_text": result.document.export_to_markdown(strict_text=True),
                "metadata": {
                    "page_count": len(result.document.pages),
                    "table_count": len(result.document.tables),
                    "has_code": any(item.label == 'CODE' for item in result.document.texts),
                    "word_count": len(result.document.export_to_markdown(strict_text=True).split())
                }
            }
        except Exception as e:
            logger.error(f"Docling processing failed: {e}")
            return {"success": False, "error": str(e)}

    async def process_image_ocr(self, file_path: Path) -> dict:
        """SECONDARY USE: OCR fallback for images when multimodal LLM unavailable."""
        try:
            # Configure for image OCR
            ocr_options = PdfPipelineOptions()
            ocr_options.do_ocr = True

            ocr_converter = DocumentConverter(
                format_options={InputFormat.IMAGE: ocr_options}
            )

            result = ocr_converter.convert(str(file_path))
            return {
                "success": True,
                "text": result.document.export_to_markdown(strict_text=True),
                "metadata": {"has_text": bool(result.document.texts)}
            }
        except Exception as e:
            logger.error(f"Docling OCR failed: {e}")
            return {"success": False, "error": str(e)}
```

**Integration with Confluence Handlers:**

1. **Attachment Macro Handler** (`attachment_macro.py`)
   - Downloads PDF/Office attachments from Confluence
   - Processes with Docling for full-text extraction
   - Embeds full markdown content in page
   - Falls back to file link if unsupported

2. **Image Handler** (`image_handler.py`)
   - **DEFAULT:** Multimodal LLM processing (based on MODEL_CHOICE from RAG Settings)
     - Runtime capability check: Does MODEL_CHOICE support vision?
     - If YES: Use multimodal LLM for text extraction + classification (~1-2s)
     - Extract searchable text from screenshots/diagrams
     - Image classification (chart, diagram, photo, screenshot)
   - **FALLBACK:** Docling OCR (automatic for non-multimodal models OR force via config)
     - Automatically triggered when MODEL_CHOICE lacks multimodal support
     - Local OCR processing using EasyOCR/Tesseract (~30-60s)
   - Embeds analysis/OCR text as HTML comment for searchability

3. **Metadata Extractor** (`metadata_extractor.py`)
   - Aggregates document structure metadata from Docling
   - Aggregates image analysis from multimodal LLM
   - Tracks page counts, table counts, code blocks, image types
   - Enriches confluence_pages metadata field

**Configuration:**
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

**Performance Characteristics:**
- **Documents (Docling):**
  - Simple PDF (10 pages): ~2-3 seconds (CPU)
  - Complex PDF with tables: ~5-10 seconds (CPU)
  - Scanned PDF with OCR: ~30-60 seconds (CPU)
  - Office documents: ~1-2 seconds (CPU)
  - Memory usage: 2-3GB peak per document
  - Concurrency: Limited to 2 parallel processes
- **Images (Multimodal LLM, default when MODEL_CHOICE supports vision):**
  - Text extraction + classification: ~1-2 seconds per image
  - API call (no local memory overhead)
  - No concurrency limits (API handles scaling)
  - Performance varies by MODEL_CHOICE (e.g., GPT-4o, Claude Sonnet, Gemini Pro Vision)
- **Images (Docling OCR, fallback):**
  - OCR processing: ~30-60 seconds per image
  - Memory usage: 2-3GB peak
  - Concurrency: Limited to 2 parallel processes

**Optimization Strategies:**
1. **Async Processing** - Process attachments in background after page sync
2. **File Size Limits** - Skip files > 50MB (configurable)
3. **Caching** - Cache processed documents by SHA-256 hash
4. **Selective Processing** - Only process supported formats
5. **Feature Flag** - `docling_enabled` configuration option

**Expected Benefits:**
- **10x increase** in searchable content (attachments + images become full-text searchable)
- **Better RAG quality** through structured document understanding
- **Richer metadata** (document structure, content types, complexity metrics)
- **Code snippet extraction** from technical PDFs
- **Table data** from spreadsheets embedded in markdown
- **Fast image understanding** via multimodal LLM (~1-2s per image vs 30-60s OCR)
- **Automatic fallback** to Docling OCR for non-multimodal models (no manual configuration needed)
- **Flexible MODEL_CHOICE support** - works with any LLM configured in RAG Settings

**Implementation Status:**
- Phase 1 (Epic 2): Hybrid approach - Docling for documents + multimodal LLM for images (2-3 days)
- Phase 2 (Post-Epic 2): Optimization and caching (1-2 weeks)
- Phase 3 (Future): Advanced metadata extraction (2-3 weeks)

**Implementation Files:**
- **Processor**: `python/src/server/services/confluence/docling_processor.py` (~120 lines)
  - `process_attachment()` - PRIMARY: PDF/Office document processing
  - `process_image_ocr()` - SECONDARY: Image OCR fallback
- **Configuration**: `python/src/server/config/settings.py` (Confluence settings section)
  - `docling_enabled`, `docling_max_file_size_mb`, `docling_timeout_seconds`, `docling_max_concurrent`
  - `image_processing_mode` - Options: "multimodal" (default), "docling_ocr" (force), "none"
- **Tests**: `python/tests/server/services/confluence/test_docling_processor.py`

---
