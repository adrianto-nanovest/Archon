# Confluence HTML to Markdown Processing Service

This service provides comprehensive HTML to Markdown conversion for Confluence Cloud content with support for macros, special elements, tables, and metadata extraction.

## Features

- **Macro Handlers**: Process Confluence-specific macros (code, panel, JIRA, attachments, embeds, generic)
- **Element Handlers**: Handle special HTML elements (users, links, images, simple elements)
- **Table Processing**: Convert complex Confluence tables with support for merged cells and styling
- **Metadata Extraction**: Extract structured metadata from Confluence pages
- **Asset Management**: Integration with Docling service for document processing

## Type Checking

Run MyPy to check type safety:

```bash
uv run mypy src/server/services/confluence/ --strict
```

### Known Issues

- **BeautifulSoup4 NavigableString import**: Type stubs incomplete (see inline comments in handler files)
- **Utility modules**: `table_processor.py`, `metadata_extractor.py`, and `deduplication.py` have remaining type issues that require broader refactoring (tracked separately)
- All `type: ignore` comments have justification explaining why they're needed

### Configuration

MyPy configuration is in `pyproject.toml` under the `[tool.mypy]` section:

- Python 3.12 type syntax (`str | None` instead of `Optional[str]`)
- Gradual type adoption (`disallow_untyped_defs = false`)
- BeautifulSoup4 and markdownify type stubs ignored via overrides

## Architecture

### Base Classes

- **`macro_handlers/base.py`**: Abstract base for macro processors
- **`element_handlers/base.py`**: Abstract base for element processors

All handler `process()` methods return `None` (in-place DOM modification via BeautifulSoup).

### Concrete Handlers

#### Macro Handlers
- `code_macro.py` - Code block macros
- `panel_macro.py` - Info/warning/note panels
- `jira_macro.py` - JIRA issue references
- `attachment_macro.py` - File attachments with Docling integration
- `embed_macro.py` - Embedded content
- `generic_macro.py` - Fallback for unknown macros

#### Element Handlers
- `user_handler.py` - User mentions with Confluence API resolution
- `link_handler.py` - Internal/external links with bulk API optimization
- `image_handler.py` - Images with multimodal LLM + Docling processing
- `simple_elements.py` - Time, date, status, emoticons

### Utility Modules

- `html_utils.py` - HTML manipulation helpers
- `url_converter.py` - URL conversion and normalization
- `deduplication.py` - Content deduplication utilities

## Development

### Running Tests

```bash
# Full confluence test suite
uv run pytest python/tests/server/services/confluence/ -v

# Specific test file
uv run pytest python/tests/server/services/confluence/test_confluence_processor.py -v

# Integration tests
uv run pytest python/tests/server/services/confluence/test_epic2_iv_complete.py -v
```

### Code Quality

```bash
# Linting
uv run ruff check src/server/services/confluence/

# Type checking
uv run mypy src/server/services/confluence/ --strict

# Format code
uv run ruff format src/server/services/confluence/
```

### Adding a New Handler

1. **Create handler file** in `macro_handlers/` or `element_handlers/`
2. **Inherit from base class** (`BaseMacroHandler` or `BaseElementHandler`)
3. **Implement `process()` method** with proper type annotations:
   ```python
   async def process(self, macro_tag: Tag, page_id: str, space_id: str | None = None) -> None:
       # Implementation here
   ```
4. **Register handler** in `confluence_processor.py`
5. **Write tests** in `tests/server/services/confluence/`

## Type Annotation Standards

- Use Python 3.12 union syntax: `str | None` (not `Optional[str]`)
- All handler methods must have return type annotations
- Optional parameters must use explicit `| None`
- Use `from typing import Any` for `**kwargs: Any` parameters
- Add justification comments for all `# type: ignore` directives

## Performance

- **Test Coverage**: 90%+ per handler
- **Test Suite**: ~30 seconds for 331+ tests
- **MyPy Check**: <10 seconds for full service

## Related Documentation

- Epic 2 PRD: `docs/bmad/brownfield-prd/epic-2-html-to-markdown-content-processing.md`
- Story 2.7 (Type Safety): `docs/bmad/stories/2.7.address-mypy-type-annotations.md`
- Architecture: `docs/bmad/brownfield-architecture/`
