# Story 2: Implement HTML to Markdown Processor

## Status
Not Needed (changed into Epic)

## Story

**As a** backend developer,
**I want** to create modular `ConfluenceProcessor` with specialized handlers for converting Confluence HTML to RAG-optimized Markdown,
**so that** Confluence content can be chunked and embedded with maximum search effectiveness using existing infrastructure.

## Acceptance Criteria

1. **Modular Architecture**: Create 18 focused handler files (~2,100 lines distributed) instead of single monolithic processor
2. **Main Orchestrator**: `confluence_processor.py` (~200 lines) coordinates two-pass processing pipeline
3. **High-Value Macro Handlers**: Implement 6 RAG-critical macro handlers (code, panel, JIRA, attachment, embed, generic fallback)
4. **Special Element Handlers**: Implement 4 element handlers (links, users, images, simplified elements)
5. **Table Processor**: Hierarchical markdown conversion (~350 lines) with colspan/rowspan support
6. **Metadata Extractor**: 3-tier JIRA extraction + comprehensive metadata aggregation (~150 lines)
7. **RAG Optimization**: Skip TOC macro, simplify emoticons/time/inline-comments (minimal RAG value)
8. **Error Isolation**: Each handler wrapped in try-except with graceful degradation
9. **Returns tuple**: `(markdown_content: str, metadata: dict)` matching `confluence_pages.metadata` schema
10. **Performance**: Bulk API calls for user/page resolution (prevent N+1 queries)

## Tasks / Subtasks

### Phase 1: Core Infrastructure (Must-Have)

- [ ] **Task 1.1: Create Modular Directory Structure** (AC: 1)
  - [ ] Create directory: `python/src/server/services/confluence/`
  - [ ] Create directory: `python/src/server/services/confluence/macro_handlers/`
  - [ ] Create directory: `python/src/server/services/confluence/element_handlers/`
  - [ ] Create directory: `python/src/server/services/confluence/utils/`
  - [ ] Create file: `python/src/server/services/confluence/__init__.py`
  - [ ] Create file: `python/src/server/services/confluence/macro_handlers/__init__.py`
  - [ ] Create file: `python/src/server/services/confluence/element_handlers/__init__.py`
  - [ ] Create file: `python/src/server/services/confluence/utils/__init__.py`

- [ ] **Task 1.2: Implement Handler Base Classes** (AC: 8)
  - [ ] Create file: `macro_handlers/base.py` with `BaseMacroHandler` abstract class
  - [ ] Add `async def process(macro_tag, page_id, space_id)` abstract method
  - [ ] Implement error isolation pattern (try-except wrapper)
  - [ ] Create file: `element_handlers/base.py` with `BaseElementHandler` abstract class
  - [ ] Add `async def process(soup, space_id)` abstract method
  - [ ] Document graceful degradation strategy in docstrings

- [ ] **Task 1.3: Implement Main Orchestrator** (AC: 2)
  - [ ] Create file: `confluence_processor.py` (~200 lines)
  - [ ] Implement `ConfluenceProcessor` class with dependency injection pattern
  - [ ] Implement `async def html_to_markdown(html: str, page_id: str, space_id: str) -> tuple[str, dict]`
  - [ ] Implement two-pass processing pipeline:
    - Pass 1: Process Confluence macros (macro expansion)
    - Pass 2: Process special HTML elements (links, users, images)
    - Pass 3: Process tables (hierarchical conversion)
    - Pass 4: Convert to markdown (markdownify)
    - Pass 5: Extract metadata (3-tier JIRA + aggregation)
  - [ ] Register all macro handlers with error isolation
  - [ ] Register all element handlers with error isolation
  - [ ] Add comprehensive logging for debugging

### Phase 2: High-Value Macro Handlers (RAG-Critical)

- [ ] **Task 2.1: Implement Code Macro Handler** (AC: 3)
  - [ ] Create file: `macro_handlers/code_macro.py` (~100 lines)
  - [ ] Extract language parameter from `<ac:parameter ac:name="language">`
  - [ ] Unwrap CDATA from `<ac:plain-text-body>` using BeautifulSoup
  - [ ] **CRITICAL**: Preserve whitespace (use `get_text(strip=False)`)
  - [ ] Format as fenced code block: ````language\ncode\n````
  - [ ] Fallback to empty language tag if parameter missing
  - [ ] Reference: Section 1.1 of HTML Processing Analysis (lines 54-87)

- [ ] **Task 2.2: Implement Panel Macro Handler** (AC: 3)
  - [ ] Create file: `macro_handlers/panel_macro.py` (~120 lines)
  - [ ] Support panel types: info, note, warning, tip, panel
  - [ ] Map panel types to emoji prefixes:
    - `info` → ℹ️
    - `tip` → ✅
    - `note` → ⚠️
    - `warning` → ❌
    - `panel` → (no emoji)
  - [ ] Extract rich text body using markdownify.markdownify()
  - [ ] Format as blockquote with `> ` prefix per line
  - [ ] Support nested content (bold, italic, links, lists)
  - [ ] Reference: Section 1.2 of HTML Processing Analysis (lines 90-123)

- [ ] **Task 2.3: Implement JIRA Macro Handler - 3-Tier Extraction** (AC: 6, **CRITICAL**)
  - [ ] Create file: `macro_handlers/jira_macro.py` (~150 lines)
  - [ ] **Tier 1: Macro Parameter Extraction** (~40% coverage)
    - Extract `key` parameter from `<ac:parameter ac:name="key">`
    - Build JIRA URL: `{jira_base_url}/browse/{issue_key}`
    - Add to metadata: `jira_issue_links.append({'issue_key': key, 'issue_url': url})`
  - [ ] **Tier 2: URL Pattern Matching** (~30% coverage)
    - Find all `<a href>` tags in HTML
    - Extract JIRA key from URL pattern: `/browse/([A-Z]+-\d+)`
    - Add to metadata if not already processed (deduplication)
  - [ ] **Tier 3: Plain Text Regex** (~30% coverage)
    - After markdown conversion, scan text with pattern: `\b([A-Z]+-\d+)\b`
    - Use word boundaries to prevent false positives
    - Deduplicate against Tier 1 and Tier 2 results
  - [ ] Implement JQL table handling (if JIRA client provided):
    - Detect `jqlQuery` parameter
    - Execute JQL query (async API call)
    - Build HTML table with dynamic columns
    - Track each row's issue key in metadata
  - [ ] Implement deduplication helper: `_is_jira_already_processed(issue_key)`
  - [ ] **CRITICAL**: Must implement all 3 tiers (60-70% coverage loss if regex-only)
  - [ ] Reference: Section 1.6 of HTML Processing Analysis (lines 225-343)

- [ ] **Task 2.4: Implement Attachment Macro Handler** (AC: 5)
  - [ ] Create file: `macro_handlers/attachment_macro.py` (~100 lines)
  - [ ] Extract filename from `<ri:attachment ri:filename="...">`
  - [ ] Map file extensions to emoji icons:
    - pdf → 📄
    - doc/docx → 📝
    - xls/xlsx → 📊
    - ppt/pptx → 📊
    - zip/rar → 📦
    - Default → 📎
  - [ ] Add to `asset_links` metadata
  - [ ] Format as markdown link: `[{emoji} {filename}](ASSET_PLACEHOLDER_{filename})`
  - [ ] Wrap with newlines to separate from surrounding content
  - [ ] Reference: Section 1.7 of HTML Processing Analysis (lines 346-384)

- [ ] **Task 2.5: Implement Embed Macro Handler** (AC: 5)
  - [ ] Create file: `macro_handlers/embed_macro.py` (~120 lines)
  - [ ] Extract URL from nested `<ri:url ri:value="...">`
  - [ ] Extract title from `<ac:parameter ac:name="title">`
  - [ ] Convert embed URLs to original URLs (15+ platforms):
    - YouTube: `/embed/ID` → `watch?v=ID`
    - Vimeo: `/video/ID` → `/ID`
    - Google Maps: Extract coordinates from `pb` parameter
    - Twitter, Instagram, TikTok, SoundCloud, Spotify, Twitch, CodePen, GitHub Gist, JSFiddle
  - [ ] Add to `external_links` metadata: `{'title': title, 'url': original_url}`
  - [ ] Format as markdown link
  - [ ] Reference: Section 1.8 of HTML Processing Analysis (lines 387-453)

- [ ] **Task 2.6: Implement Generic Macro Handler (Fallback)** (AC: 8)
  - [ ] Create file: `macro_handlers/generic_macro.py` (~80 lines)
  - [ ] Extract macro name from `ac:name` attribute
  - [ ] Extract all parameters into dictionary
  - [ ] Build comment: `<!-- Unsupported Confluence Macro: {name} {params} -->`
  - [ ] Try to extract content from `<ac:rich-text-body>`
  - [ ] Format as comment + content (if available)
  - [ ] Fallback message if content extraction fails
  - [ ] Reference: Section 1.9 of HTML Processing Analysis (lines 456-493)

### Phase 3: RAG-Critical Element Handlers

- [ ] **Task 3.1: Implement Link Handler** (AC: 5, 10)
  - [ ] Create file: `element_handlers/link_handler.py` (~120 lines)
  - [ ] **Internal Page Links**:
    - Find all `<ac:link><ri:page ri:content-title="...">` elements
    - Extract unique page titles (deduplication)
    - **Bulk API call**: `find_page_by_title(space_id, titles)` for all titles at once
    - Store metadata: `{'page_id': id, 'page_title': title, 'page_url': url}`
    - Replace all occurrences with markdown link
  - [ ] **External Links**:
    - Find all `<a href="http...">` tags
    - Filter to external links (http/https)
    - Check if JIRA link already processed (deduplication)
    - Add Google Drive icon detection:
      - `/document/` → 📄
      - `/spreadsheets/` → 📊
      - `/presentation/` → 🎭
      - `/forms/` → 📝
    - Add to `external_links` metadata
  - [ ] Reference: Sections 2.6 and 2.8 of HTML Processing Analysis

- [ ] **Task 3.2: Implement User Handler** (AC: 5, 10)
  - [ ] Create file: `element_handlers/user_handler.py` (~100 lines)
  - [ ] Find all `<ac:link><ri:user ri:account-id="...">` elements
  - [ ] Extract unique account IDs (deduplication)
  - [ ] **Bulk API call**: `get_users_by_account_ids(account_ids)` (single call for all users)
  - [ ] Cache user information to avoid duplicate lookups
  - [ ] Store metadata: `{'account_id': id, 'display_name': name, 'profile_url': url}`
  - [ ] Replace `<ac:link>` with markdown link: `[display_name](profile_url)`
  - [ ] Reference: Section 2.5 of HTML Processing Analysis (lines 642-673)

- [ ] **Task 3.3: Implement Image Handler** (AC: 5)
  - [ ] Create file: `element_handlers/image_handler.py` (~100 lines)
  - [ ] Detect `<ac:image>` tags with two sources:
    - `<ri:attachment ri:filename="...">` (local files)
    - `<ri:url ri:value="...">` (external images)
  - [ ] Determine type by extension:
    - Images: jpg, jpeg, png, gif, svg, webp, bmp, tiff → 🖼️
    - Videos: mp4, avi, mov, wmv, flv, webm, mkv → 🎬
    - Other → 📎
  - [ ] Add to `asset_links` metadata if attachment
  - [ ] Format as markdown link with emoji prefix
  - [ ] Reference: Section 2.4 of HTML Processing Analysis (lines 587-639)

- [ ] **Task 3.4: Implement Simple Element Handler (Simplified)** (AC: 7)
  - [ ] Create file: `element_handlers/simple_elements.py` (~80 lines)
  - [ ] **Emoticons** (SIMPLIFIED):
    - Use `ac:emoji-fallback` attribute only (skip shortname processing)
    - Minimal implementation (low RAG value)
  - [ ] **Inline Comments** (SIMPLIFIED):
    - Strip `<ac:inline-comment-marker>` entirely
    - Preserve text content only
    - No metadata processing (collaborative metadata, not document content)
  - [ ] **Time Elements** (SIMPLIFIED):
    - Use text content only (skip ISO datetime parsing)
    - Minimal implementation (context more important than format)
  - [ ] Reference: Section 2 of HTML Processing Analysis (RAG Optimization Strategy)

### Phase 4: Table Processing (Hierarchical Strategy)

- [ ] **Task 4.1: Implement Table Processor** (AC: 4, **RAG-CRITICAL**)
  - [ ] Create file: `table_processor.py` (~350 lines)
  - [ ] **CRITICAL**: Use hierarchical markdown format (NOT standard markdown tables)
    - Reason: 35% of Confluence tables have colspan/rowspan (unsupported in standard markdown)
    - Reason: 60% have nested content (code blocks, lists)
    - Reason: Hierarchical structure maintains context for RAG embeddings
  - [ ] Implement hierarchical conversion:
    - Convert to `## Row` → `### Column` structure
    - Wrap with `<!-- TABLE_START -->` and `<!-- TABLE_END -->` markers
    - Add table summary comment: `<!-- Table Summary: {cols} columns, {rows} rows, ... -->`
    - Add column headers comment: `<!-- Column Headers: [...] -->`
  - [ ] Handle colspan/rowspan with content duplication:
    - Fill all spanned cells with same content
    - Mark original cell vs duplicated cells
    - Track span locations in metadata
  - [ ] Build multi-level header matrix:
    - Handle rowspan in headers (vertical spanning)
    - Handle colspan in headers (horizontal spanning)
    - Combine multi-row headers with " - " separator
  - [ ] Calculate context-aware heading levels:
    - Detect surrounding section level from HTML headings
    - Row heading level = section level + 1
    - Column heading level = section level + 2
    - Cap at #### to prevent over-nesting
  - [ ] Add metadata enrichment:
    - Table complexity score (simple/medium/complex)
    - Table purpose inference (deployment/checklist/comparison/etc.)
    - Span location tracking
  - [ ] Reference: Section 4 of HTML Processing Analysis (lines 1014-1282)

### Phase 5: Metadata Extraction (3-Tier JIRA + Aggregation)

- [ ] **Task 5.1: Implement Metadata Extractor** (AC: 6, 9)
  - [ ] Create file: `metadata_extractor.py` (~150 lines)
  - [ ] Aggregate metadata from all handlers:
    - JIRA issue links (3-tier extraction: macros + URLs + regex)
    - User mentions (deduplicated by account ID)
    - Internal page links (deduplicated by page ID)
    - External links (deduplicated by URL)
    - Asset links (deduplicated by filename)
  - [ ] Calculate content metrics:
    - Word count: `len(markdown_content.split())`
    - Content length: `len(markdown_content)`
  - [ ] Build comprehensive metadata dict matching schema:
    ```python
    {
      'jira_issue_links': [{'issue_key': str, 'issue_url': str}],
      'user_mentions': [{'account_id': str, 'display_name': str, 'profile_url': str}],
      'internal_links': [{'page_id': str, 'page_title': str, 'page_url': str}],
      'external_links': [{'title': str, 'url': str}],
      'asset_links': [filename_str],  # Enriched with API data later
      'word_count': int,
      'content_length': int
    }
    ```
  - [ ] Reference: Section 3 of HTML Processing Analysis (lines 787-1012)

### Phase 6: Utility Modules

- [ ] **Task 6.1: Implement HTML Utilities** (AC: 8)
  - [ ] Create file: `utils/html_utils.py` (~100 lines)
  - [ ] Implement BeautifulSoup helper functions
  - [ ] Implement whitespace normalization:
    - Code block preservation (no strip)
    - Header text cleaning (collapse multiple spaces, remove newlines)
    - Table cell content cleaning (3+ newlines → 2)
  - [ ] Implement UTF-8 encoding safety for emoji
  - [ ] Reference: Section 5.3 of HTML Processing Analysis (lines 1356-1396)

- [ ] **Task 6.2: Implement URL Converter** (AC: 5)
  - [ ] Create file: `utils/url_converter.py` (~100 lines)
  - [ ] Implement iframe embed URL conversion (15+ platforms)
  - [ ] YouTube, Vimeo, Google Maps coordinate extraction
  - [ ] Generic fallback: convert `/embed/` to `/`
  - [ ] Reference: Section 1.8 of HTML Processing Analysis (lines 419-446)

- [ ] **Task 6.3: Implement Deduplication Utilities** (AC: 6)
  - [ ] Create file: `utils/deduplication.py` (~100 lines)
  - [ ] Implement `_is_jira_already_processed(issue_key)` - check by key
  - [ ] Implement `_is_jira_url_already_processed(url)` - check by URL
  - [ ] Implement set-based deduplication for asset links
  - [ ] Reference: Section 3.1 of HTML Processing Analysis (lines 847-859)

### Phase 7: Testing & Documentation

- [ ] **Task 7.1: Create Comprehensive Unit Tests** (AC: All)
  - [ ] Create test directory: `python/tests/server/services/confluence/`
  - [ ] Create subdirectories: `macro_handlers/`, `element_handlers/`
  - [ ] **Per-Handler Unit Tests** (12 test files):
    - `test_code_macro.py` - Code block extraction, language tags, whitespace preservation
    - `test_panel_macro.py` - Info/note/warning/tip, emoji prefixes, nested content
    - `test_jira_macro.py` - **3-tier extraction**, deduplication, JQL tables
    - `test_attachment_macro.py` - File icons, metadata tracking, placeholder URLs
    - `test_embed_macro.py` - URL conversion for 15+ platforms
    - `test_generic_macro.py` - Unknown macro fallback, parameter extraction
    - `test_link_handler.py` - Page/external links, bulk API calls, Google Drive icons
    - `test_user_handler.py` - User mention resolution, bulk API calls, caching
    - `test_image_handler.py` - Attachment vs external, type detection, metadata
    - `test_simple_elements.py` - Simplified emoticons/time/inline-comments
  - [ ] **Integration Tests** (`test_confluence_processor.py`):
    - Test macro handling (all 6 macro types)
    - Test 3-tier JIRA extraction (verify all 3 tiers extract unique issues)
    - Test table hierarchical format (verify `<!-- TABLE_START -->`, row/column headings)
    - Test colspan/rowspan handling (verify content duplication)
    - Test error handling (malformed HTML graceful degradation)
  - [ ] **Table Processor Tests** (`test_table_processor.py`):
    - Test hierarchical structure generation
    - Test colspan/rowspan content duplication
    - Test multi-level header matrix
    - Test metadata enrichment (complexity, purpose)
  - [ ] **Metadata Extractor Tests** (`test_metadata_extractor.py`):
    - Test 3-tier JIRA aggregation
    - Test deduplication across all tiers
    - Test metadata schema compliance
  - [ ] Reference: Section 6.3 of HTML Processing Analysis (lines 1667-1761)

- [ ] **Task 7.2: Integration Verification** (IV1, IV2, IV3)
  - [ ] **IV1: Code Block Integrity**
    - Test Confluence code macro: `<ac:structured-macro ac:name="code">...</ac:structured-macro>`
    - Expected: Fenced code block with language tag: ````python\nprint("test")\n````
    - Verify: No line breaks inserted within code content
  - [ ] **IV2: JIRA Link Extraction - 3-Tier Coverage**
    - Test Tier 1: Macro parameter extraction
    - Test Tier 2: URL pattern matching in `<a>` tags
    - Test Tier 3: Plain text regex on final markdown
    - Verify: All three tiers extract unique issues (no duplicates)
    - Verify: Combined coverage ~100% (not 40% regex-only)
  - [ ] **IV3: Metadata Schema Compliance**
    - Validate metadata dict keys: all 6 required fields
    - Validate nested structure: arrays of objects
    - Ensure compatibility with JSONB storage in `confluence_pages` table

- [ ] **Task 7.3: Create Implementation Documentation**
  - [ ] Update CLAUDE.md with Confluence processor patterns
  - [ ] Document modular architecture in brownfield-architecture.md
  - [ ] Add handler base class patterns to developer guide
  - [ ] Document 3-tier JIRA extraction strategy (critical for other developers)

## Dev Notes

### Architecture Decisions (Based on Production Reference)

**Source:** `docs/bmad/confluence-html-processing-analysis.md` (2000+ lines production code analysis)

#### 1. Modular File Structure (18 focused files)
**Rationale**: Replace single 2000+ line monolithic processor with focused, testable modules
- **Debuggability**: Isolate issues to specific handler
- **Testability**: Unit test each handler independently
- **Maintainability**: Add new macros without touching existing handlers
- **Performance**: Easier to profile and optimize individual handlers
- **Team Collaboration**: Multiple developers can work on different handlers simultaneously

#### 2. RAG Optimization Strategy
**Skip TOC Macro** (Section 1.5):
- No searchable content generated
- Navigation UI only
- Returns placeholder comment

**Simplify Low-Value Elements**:
- **Emoticons** (Section 2.1): Use `ac:emoji-fallback` only (skip complex shortname processing)
- **Inline Comments** (Section 2.2): Strip marker entirely (collaborative metadata, not content)
- **Time Elements** (Section 2.7): Use text content only (skip ISO datetime parsing)
- **Impact**: Minimal RAG value (<5% search relevance), 60% fewer lines in simple_elements.py

**Keep High-Value Elements**:
- Code blocks (language-tagged searchable snippets)
- Panels/Status (highlighted important information)
- JIRA macros (3-tier extraction = 100% coverage)
- Attachments/Images (document references)
- User mentions (collaboration context)
- Page links (knowledge graph connections)
- Hierarchical tables (RAG-optimized structure)

#### 3. Hierarchical Tables (NOT Standard Markdown Tables)
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

#### 4. 3-Tier JIRA Extraction (CRITICAL)
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

#### 5. Bulk API Calls (Performance Optimization)
**Problem**: N+1 query anti-pattern for user/page resolution
- 100 user mentions = 100 individual API calls → **SLOW**

**Solution**: Bulk API calls
- Extract all unique account IDs → Single bulk call: `get_users_by_account_ids(account_ids)`
- Extract all unique page titles → Single bulk call: `find_pages_by_titles(space_id, titles)`
- **Performance**: 50x faster user/page link resolution

#### 6. Error Isolation per Handler
**Pattern**: Each handler wrapped in try-except
- **Benefit**: One handler failure doesn't break entire page conversion
- **Graceful Degradation**: Unknown macros handled by generic fallback
- **Logging**: Errors logged with context (macro name, page ID) for debugging

#### 7. Two-Pass Processing Pipeline
**Pass 1: Macro Expansion** (Confluence-specific)
- Process all `<ac:structured-macro>` tags
- Extract structured data (JIRA keys, attachments, etc.)
- Replace with intermediate HTML or markdown

**Pass 2: Standard HTML Conversion**
- Process special elements (users, links, images)
- Process tables (hierarchical conversion)
- Convert to markdown (markdownify)
- Extract metadata (3-tier JIRA + aggregation)

**Rationale**: Macro structure lost after HTML→Markdown conversion (must process first)

### Implementation Checklist (Critical Items)

**MUST-HAVE (Phase 1-5):**
- [ ] Modular structure: 18 focused handler files (NOT single monolithic file)
- [ ] 3-tier JIRA extraction (macros + URLs + regex) - NOT regex-only
- [ ] Hierarchical tables (NOT standard markdown tables)
- [ ] Bulk API calls (user/page resolution) - NOT individual calls
- [ ] Error isolation per handler (try-except wrapper)
- [ ] Skip TOC macro (no RAG value)
- [ ] Simplify emoticons/time/inline-comments (minimal implementation)

**NICE-TO-HAVE (Phase 6-7):**
- [ ] Comprehensive unit tests (12 handler test files)
- [ ] Integration tests (full page conversion)
- [ ] Table metadata enrichment (complexity, purpose)
- [ ] Performance profiling

### Common Pitfalls to Avoid

1. **DON'T create monolithic processor** - Use 18 focused handler files (Section 6.1)
2. **DON'T use regex-only for JIRA** - Implement all 3 tiers (60-70% coverage loss otherwise) (Section 3.1)
3. **DON'T use standard markdown tables** - Use hierarchical format (Section 4.1, RAG-optimized)
4. **DON'T skip deduplication** - JIRA/link/user data will have duplicates across tiers
5. **DON'T forget async/await** - User/page link resolution requires API calls
6. **DON'T strip whitespace in code blocks** - Breaks code formatting (Section 1.1)
7. **DON'T process macros after HTML conversion** - Structure lost, too late
8. **DON'T over-engineer TOC/emoji/time handlers** - Skip or simplify (low RAG value)

### File Structure Summary

```
python/src/server/services/confluence/
├── __init__.py                          # Public API exports
├── confluence_processor.py              # Main orchestrator (~200 lines)
│
├── macro_handlers/                      # Macro processing modules
│   ├── __init__.py
│   ├── base.py                          # BaseMacroHandler abstract class
│   ├── code_macro.py                    # Code block handler (~100 lines)
│   ├── panel_macro.py                   # Info/Note/Warning/Tip panels (~120 lines)
│   ├── jira_macro.py                    # JIRA integration - 3-tier extraction (~150 lines)
│   ├── attachment_macro.py              # View-file + images (~100 lines)
│   ├── embed_macro.py                   # Iframe/external content (~120 lines)
│   └── generic_macro.py                 # Unknown macro fallback (~80 lines)
│
├── element_handlers/                    # Special HTML elements
│   ├── __init__.py
│   ├── base.py                          # BaseElementHandler abstract class
│   ├── link_handler.py                  # Page links + external links (~120 lines)
│   ├── user_handler.py                  # User mentions with API resolution (~100 lines)
│   ├── image_handler.py                 # ac:image processing (~100 lines)
│   └── simple_elements.py               # Emoticons, time, inline comments (~80 lines)
│
├── table_processor.py                   # Complete table conversion (~350 lines)
│   ├── TableProcessor class
│   ├── Hierarchical markdown generation
│   ├── Colspan/rowspan handling
│   └── Metadata enrichment
│
├── metadata_extractor.py                # Metadata aggregation (~150 lines)
│   ├── JIRA links (3-tier: macros + URLs + regex)
│   ├── User mentions
│   ├── Internal/external links
│   └── Assets
│
└── utils/
    ├── __init__.py
    ├── html_utils.py                    # BeautifulSoup helpers, whitespace normalization (~100 lines)
    ├── url_converter.py                 # Iframe embed URL conversion (~100 lines)
    └── deduplication.py                 # Link/issue deduplication logic (~100 lines)
```

**Total**: ~2,100 lines distributed across 18 focused files (vs. 2000+ lines in single file)

### Testing Strategy

**Per-Handler Unit Tests** (12 test files):
- Test each handler independently
- Mock Confluence API client and JIRA client
- Verify handler output matches expected format
- Test error handling and graceful degradation

**Integration Tests** (1 test file):
- Test full page conversion (all handlers)
- Verify 3-tier JIRA extraction (all tiers)
- Verify hierarchical table format
- Verify metadata schema compliance
- Test malformed HTML handling

**Test Coverage Target**: 90%+ per handler, 95%+ integration

### Integration with Story 2.2 (Sync Service)

```python
# In ConfluenceSyncService (Story 2.2)
from .confluence_processor import ConfluenceProcessor

async def sync_space(self, source_id: str, space_key: str):
    processor = ConfluenceProcessor(
        confluence_client=self.confluence_client,
        jira_client=self.jira_client
    )

    for page in changed_pages:
        # Get HTML from API
        page_data = await self.confluence_client.get_page_content(page['id'])
        html = page_data['content_html']

        # Convert to markdown with metadata (THIS STORY)
        markdown_content, extracted_metadata = await processor.html_to_markdown(
            html=html,
            page_id=page['id'],
            space_id=page_data['space_id']
        )

        # Merge with API metadata
        full_metadata = {
            **page_data,  # ancestors, children, created_by from API
            **extracted_metadata  # jira_links, user_mentions from HTML
        }

        # Store in confluence_pages table
        await self.store_page_metadata(page['id'], full_metadata)

        # Chunk and embed markdown (EXISTING INFRASTRUCTURE)
        await document_storage_service.add_documents_to_supabase(
            content=markdown_content,
            source_id=source_id,
            metadata={'page_id': page['id'], **full_metadata}
        )
```

### Reference Code Location

**All line numbers reference**: `docs/bmad/examples/enhanced_renderer_sample.py` (via HTML Processing Analysis)

- **Macro Parsing**: Lines 60-390 (MacroParser class)
- **JIRA Three-Tier**: Lines 257-379 (macro), 824-842 (URLs), [regex not implemented in sample]
- **Table Processing**: Lines 1176-1936 (hierarchical conversion)
- **Metadata Extraction**: Lines 48-52 (data structures), 809-822 (deduplication)
- **Special Elements**: Lines 430-1015 (emoticons, images, users, pages, time, etc.)
- **Error Handling**: Lines 635-695 (macro isolation), 794-797 (fallback)

### Success Metrics

**Code Quality**:
- No file > 350 lines (table_processor.py max)
- Test coverage: 90%+ per handler, 95%+ integration
- Error rate: <1% of macros/elements fail gracefully

**RAG Performance**:
- JIRA coverage: 95%+ of JIRA references extracted (3-tier)
- Table searchability: 10x better retrieval vs. standard markdown tables
- Metadata completeness: 100% of user mentions, page links, assets tracked

**Maintainability**:
- New macro addition: <100 lines of code, single file
- Debug time: Isolate issues to specific handler in <5 minutes
- Test time: Run all handler unit tests in <30 seconds

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-17 | 1.0 | Initial story creation from Epic 2 | Bob (Scrum Master) |
| 2025-10-17 | 2.0 | Complete revision based on HTML Processing Analysis (2000+ line production reference) | John (Product Manager) |

## Dev Agent Record

### Agent Model Used
<!-- To be filled by Dev Agent during implementation -->

### Debug Log References
<!-- To be filled by Dev Agent during implementation -->

### Completion Notes List
<!-- To be filled by Dev Agent during implementation -->

### File List
<!-- To be filled by Dev Agent during implementation -->

## QA Results
<!-- To be filled by QA Agent after story completion -->
