# Epic 2: HTML to Markdown Content Processing

**Epic Goal**: Implement modular, RAG-optimized HTML to Markdown processor with specialized handlers for converting Confluence storage format to searchable, embeddable content

**Architecture Approach**: Based on production reference implementation analysis (2000+ lines), this epic implements:
- **Modular architecture**: 18 focused handler files (~2,100 lines distributed) instead of single monolithic processor
- **RAG optimization**: Hierarchical tables (NOT standard markdown), 3-tier JIRA extraction (NOT regex-only), skip/simplify low-value elements
- **Performance**: Bulk API calls for user/page resolution (prevent N+1 queries)
- **Error isolation**: Each handler wrapped in try-except with graceful degradation

**Integration Requirements**:
- Must integrate with existing `document_storage_service.add_documents_to_supabase()` for chunking (validated in Story 1.5)
- Must return metadata matching `confluence_pages.metadata` JSONB schema
- Must preserve code blocks, handle complex tables, and extract 100% of JIRA references

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

## Story 2.2: High-Value Macro Handlers

As a **backend developer**,
I want **to implement 6 RAG-critical macro handlers for Confluence content extraction**,
so that **code blocks, panels, JIRA issues, attachments, and embedded content are preserved in searchable format**.

**Acceptance Criteria**:
1. **Code Macro Handler** (~100 lines): Extract language tags, unwrap CDATA, preserve whitespace (NO strip)
2. **Panel Macro Handler** (~120 lines): Support info/note/warning/tip with emoji prefixes (ℹ️✅⚠️❌), blockquote formatting
3. **JIRA Macro Handler - 3-Tier Extraction** (~150 lines):
   - Tier 1: Macro parameter extraction (~40% coverage)
   - Tier 2: URL pattern matching in `<a>` tags (~30% coverage)
   - Tier 3: Plain text regex on final markdown (~30% coverage)
   - Deduplication across all tiers
   - JQL table handling (if JIRA client provided)
4. **Attachment Macro Handler** (~100 lines): Extract filenames, map file type to emoji icons (📄📝📊📦📎)
5. **Embed Macro Handler** (~120 lines): Convert embed URLs for 15+ platforms (YouTube, Vimeo, Google Maps, etc.)
6. **Generic Macro Handler** (~80 lines): Fallback for unknown macros with parameter extraction

**Integration Verification**:
- IV1: Code blocks preserve whitespace and language tags (no line breaks mid-block)
- IV2: **JIRA 3-tier extraction** achieves ~100% coverage (NOT 40% regex-only)
- IV3: Panel macros render as blockquotes with correct emoji prefixes
- IV4: Attachment macros add filenames to `asset_links` metadata
- IV5: Unknown macros handled gracefully with comment placeholders

**Deliverable**: 6 macro handlers (~670 lines) with per-handler unit tests

---

## Story 2.3: RAG-Critical Element Handlers

As a **backend developer**,
I want **to implement 4 element handlers with bulk API call optimization**,
so that **user mentions, page links, images, and simple elements are processed efficiently without N+1 query anti-pattern**.

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
3. **Image Handler** (~100 lines):
   - Detect `<ac:image>` with two sources: `<ri:attachment>` (local) and `<ri:url>` (external)
   - Determine type by extension: Images (🖼️), Videos (🎬), Other (📎)
   - Add to `asset_links` metadata if attachment
4. **Simple Element Handler (Simplified)** (~80 lines):
   - Emoticons: Use `ac:emoji-fallback` attribute only (skip shortname - low RAG value)
   - Inline Comments: Strip `<ac:inline-comment-marker>` entirely (collaborative metadata, not content)
   - Time Elements: Use text content only (skip ISO datetime parsing - minimal RAG value)

**Integration Verification**:
- IV1: User/page resolution uses bulk API calls (verify single call for N items)
- IV2: Link handler correctly deduplicates JIRA links already processed by macro handler
- IV3: Simple elements simplified (60% fewer lines vs. full implementation)
- IV4: All metadata fields populated correctly (internal_links, external_links, user_mentions, asset_links)

**Deliverable**: 4 element handlers (~380 lines) with bulk API call optimization and unit tests

---

## Story 2.4: Table Processor & Metadata Extractor

As a **backend developer**,
I want **to implement hierarchical table conversion and 3-tier JIRA metadata aggregation**,
so that **complex Confluence tables are RAG-optimized and JIRA coverage reaches ~100%**.

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
2. **Metadata Extractor** (~150 lines):
   - Aggregate JIRA links from all 3 tiers (macros + URLs + regex)
   - Deduplicate user mentions by account ID
   - Deduplicate internal/external links by URL
   - Deduplicate asset links by filename
   - Calculate content metrics: word_count, content_length
   - Build metadata dict matching `confluence_pages.metadata` schema

**Integration Verification**:
- IV1: Table conversion uses hierarchical format (verify `<!-- TABLE_START -->`, `## Row`, `### Column`)
- IV2: Colspan/rowspan handling duplicates content across all spanned cells
- IV3: 3-tier JIRA aggregation deduplicates across all sources (no duplicate issue keys)
- IV4: Metadata schema matches `confluence_pages.metadata` JSONB structure (6 required fields)
- IV5: Hierarchical tables maintain context across chunk boundaries (RAG-optimized)

**Deliverable**: Table processor (~350 lines) + metadata extractor (~150 lines) with comprehensive tests

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

## Success Metrics

### Code Quality
- No file > 350 lines (table_processor.py max)
- Test coverage: 90%+ per handler, 95%+ integration
- Error rate: <1% of macros/elements fail gracefully
- Modular architecture: 18 focused files (~2,100 lines distributed)

### RAG Performance
- JIRA coverage: 95%+ of JIRA references extracted (3-tier)
- Table searchability: 10x better retrieval vs. standard markdown tables
- Metadata completeness: 100% of user mentions, page links, assets tracked
- Chunk quality: Hierarchical tables maintain context across chunk boundaries

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
- Attachments/Images (document references)
- User mentions (collaboration context)
- Page links (knowledge graph connections)
- Hierarchical tables (RAG-optimized structure)

---

## Common Pitfalls to Avoid

1. ❌ **DON'T create monolithic processor** - Use 18 focused handler files
2. ❌ **DON'T use regex-only for JIRA** - Implement all 3 tiers (60-70% coverage loss otherwise)
3. ❌ **DON'T use standard markdown tables** - Use hierarchical format (RAG-optimized)
4. ❌ **DON'T skip deduplication** - JIRA/link/user data will have duplicates across tiers
5. ❌ **DON'T forget async/await** - User/page link resolution requires API calls
6. ❌ **DON'T strip whitespace in code blocks** - Breaks code formatting
7. ❌ **DON'T process macros after HTML conversion** - Structure lost, too late
8. ❌ **DON'T over-engineer TOC/emoji/time handlers** - Skip or simplify (low RAG value)

---

## File Structure Summary

```
python/src/server/services/confluence/
├── __init__.py                          # Public API exports
├── confluence_processor.py              # Main orchestrator (~200 lines) - Story 2.1
│
├── macro_handlers/                      # Story 2.2
│   ├── __init__.py
│   ├── base.py                          # BaseMacroHandler abstract class - Story 2.1
│   ├── code_macro.py                    # Code block handler (~100 lines)
│   ├── panel_macro.py                   # Info/Note/Warning/Tip panels (~120 lines)
│   ├── jira_macro.py                    # JIRA integration - 3-tier extraction (~150 lines)
│   ├── attachment_macro.py              # View-file + images (~100 lines)
│   ├── embed_macro.py                   # Iframe/external content (~120 lines)
│   └── generic_macro.py                 # Unknown macro fallback (~80 lines)
│
├── element_handlers/                    # Story 2.3
│   ├── __init__.py
│   ├── base.py                          # BaseElementHandler abstract class - Story 2.1
│   ├── link_handler.py                  # Page links + external links (~120 lines)
│   ├── user_handler.py                  # User mentions with API resolution (~100 lines)
│   ├── image_handler.py                 # ac:image processing (~100 lines)
│   └── simple_elements.py               # Emoticons, time, inline comments (~80 lines)
│
├── table_processor.py                   # Complete table conversion (~350 lines) - Story 2.4
├── metadata_extractor.py                # Metadata aggregation (~150 lines) - Story 2.4
│
└── utils/                               # Story 2.5
    ├── __init__.py
    ├── html_utils.py                    # BeautifulSoup helpers (~100 lines)
    ├── url_converter.py                 # Iframe embed URL conversion (~100 lines)
    └── deduplication.py                 # Link/issue deduplication (~100 lines)
```

**Total**: ~2,100 lines distributed across 18 focused files

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
- Story 1.3: Dependencies installed (`atlassian-python-api`, `markdownify`)
- Story 1.5: Infrastructure validated (`document_storage_service`, metadata schema)

**Integration Points:**
- `ConfluenceClient.find_page_by_title(space_id, title)` - Internal page link resolution
- `ConfluenceClient.get_users_by_account_ids(account_ids)` - User mention resolution (bulk)
- Optional: `JiraClient` for JQL query execution (if provided)

---

## Integration with Epic 3 (Sync Service)

```python
# In ConfluenceSyncService (Epic 3, Story 3.1)
from .confluence_processor import ConfluenceProcessor

async def sync_space(self, source_id: str, space_key: str):
    processor = ConfluenceProcessor(
        confluence_client=self.confluence_client,
        jira_client=self.jira_client  # Optional
    )

    for page in changed_pages:
        # Get HTML from API
        page_data = await self.confluence_client.get_page_content(page['id'])
        html = page_data['content_html']

        # Convert to markdown with metadata (EPIC 2)
        markdown_content, extracted_metadata = await processor.html_to_markdown(
            html=html,
            page_id=page['id'],
            space_id=page_data['space_id']
        )

        # Merge with API metadata
        full_metadata = {
            **page_data,  # ancestors, children, created_by from API
            **extracted_metadata  # jira_links, user_mentions from HTML (EPIC 2)
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
