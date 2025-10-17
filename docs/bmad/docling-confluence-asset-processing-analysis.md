# Docling for Confluence Asset Processing: Comprehensive Analysis

**Document Version:** 1.0
**Date:** 2025-10-18
**Author:** Library Research Agent
**Status:** Analysis Complete

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What is Docling?](#what-is-docling)
3. [Core Capabilities](#core-capabilities)
4. [Technical Architecture](#technical-architecture)
5. [Supported Formats](#supported-formats)
6. [Integration with Confluence Content Processing](#integration-with-confluence-content-processing)
7. [Installation and Dependencies](#installation-and-dependencies)
8. [Python API Usage Patterns](#python-api-usage-patterns)
9. [Performance Characteristics](#performance-characteristics)
10. [Metadata Extraction Capabilities](#metadata-extraction-capabilities)
11. [Use Cases for Archon](#use-cases-for-archon)
12. [Implementation Recommendations](#implementation-recommendations)
13. [Risks and Considerations](#risks-and-considerations)
14. [Conclusion](#conclusion)
15. [References](#references)

---

## Executive Summary

**Docling** is an open-source document processing library designed to prepare documents for generative AI applications. Developed by IBM Research and now hosted by the LF AI & Data Foundation, Docling provides advanced document understanding capabilities including layout analysis, table structure recognition, OCR, and metadata extraction.

### Key Findings for Archon's Confluence Integration

✅ **Highly Recommended** for processing Confluence attachments and images
✅ **RAG-Optimized** with state-of-the-art AI models (DocLayNet, TableFormer)
✅ **Multiple Format Support** - PDF, DOCX, PPTX, XLSX, images (PNG, JPEG, TIFF), HTML
✅ **Metadata Extraction** - Structured information extraction (beta feature)
✅ **Local Processing** - Air-gapped execution for sensitive data
✅ **Easy Integration** - Simple Python API, LangChain/LlamaIndex compatible

### Recommended Use Case for Epic 2

In the context of **Epic 2: HTML to Markdown Content Processing**, Docling should be used to:

1. **Process Confluence Attachments** (PDFs, Office docs) embedded in pages
2. **Extract Image Metadata** and text content (via OCR if needed)
3. **Convert to Searchable Text** for embedding in the main page markdown
4. **Enrich RAG Context** with structured data from documents

---

## What is Docling?

Docling is a Python library that simplifies document processing by parsing diverse formats with advanced understanding capabilities. It creates a unified `DoclingDocument` representation that can be exported to multiple formats (Markdown, JSON, HTML, DocTags).

### Project Overview

- **Repository:** [docling-project/docling](https://github.com/docling-project/docling)
- **Stars:** 41.8k+ ⭐
- **License:** MIT
- **Python Support:** 3.10, 3.11, 3.12, 3.13
- **Maintained By:** LF AI & Data Foundation (IBM Research origin)
- **Documentation:** https://docling-project.github.io/docling/

### Design Philosophy

Docling employs a **modular architecture** with extensibility in mind:

- **Pipeline-based processing** - Customizable stages
- **Format-specific backends** - Optimized parsers per format
- **Unified representation** - DoclingDocument as the core data model
- **Extensible base classes** - Subclassable for specialized implementations

---

## Core Capabilities

### 1. Advanced PDF Processing

- **Layout Analysis** - Object detection for page elements (powered by DocLayNet model)
- **Reading Order Detection** - Understands document flow
- **Table Structure Recognition** - TableFormer state-of-the-art model
- **Code Block Detection** - Preserves programming code
- **Formula Understanding** - Mathematical notation extraction
- **Image Classification** - Categorizes embedded images

### 2. OCR Support

Multiple OCR backends available:

- **EasyOCR** (default) - Good accuracy, no system dependencies
- **Tesseract** - Industry standard, requires system installation
- **RapidOCR** - Fast processing
- **OnnxTR** - ONNX-based OCR plugin
- **ocrmac** - macOS native OCR

### 3. Table Processing

- **Colspan/Rowspan Handling** - Complex table structures
- **Multi-level Headers** - Hierarchical column headers
- **Cell Content Extraction** - Preserves formatting
- **Table Metadata** - Row/column counts, complexity metrics

### 4. Multimodal Processing

- **Vision Models** - GraniteDocling, SmolVLM for image understanding
- **Picture Description** - Automatic image captioning (beta)
- **Audio Processing** - WAV, MP3 support with ASR
- **Video Subtitles** - WebVTT parsing

### 5. Metadata Extraction (Beta)

Structured data extraction using:

- **Pydantic Models** - Type-safe schema definition
- **Dictionary Templates** - Flexible data structures
- **Page-based Organization** - Results grouped by page
- **Vision Language Models** - AI-powered extraction

### 6. Export Formats

- **Markdown** - RAG-optimized with hierarchical structure
- **JSON** - DoclingDocument serialization
- **HTML** - Preserves visual structure
- **DocTags** - Custom token format
- **Plain Text** - Simple text extraction

---

## Technical Architecture

### Component Structure

```
Document Source → Document Converter → DoclingDocument → Export/Chunking
                       ↓
                  Format Backend (PDF, DOCX, etc.)
                       ↓
                  Processing Pipeline
                       ↓
                  - Layout Analysis
                  - Table Recognition
                  - OCR (optional)
                  - Enrichments (optional)
```

### Key Components

1. **DocumentConverter** - Orchestrator for document processing
2. **Format Backends** - Specialized parsers (PDF, DOCX, XLSX, HTML, etc.)
3. **Processing Pipeline** - Configurable stages (layout, tables, OCR, enrichments)
4. **DoclingDocument** - Unified Pydantic data model
5. **Exporters** - Format-specific output generation
6. **Chunkers** - Native document chunking for RAG

### Modular Design

- **Base Classes** - `BaseBackend`, `BasePipeline`, `BaseEnrichment`
- **Plugin System** - Entry points for custom implementations
- **Configuration** - Pipeline options per format
- **Dependency Injection** - Flexible component wiring

---

## Supported Formats

### Input Formats

| Format | Description | Notes |
|--------|-------------|-------|
| **PDF** | Portable Document Format | Advanced layout analysis, table structure |
| **DOCX** | Microsoft Word 2007+ | Office Open XML format |
| **XLSX** | Microsoft Excel 2007+ | Spreadsheet processing |
| **PPTX** | Microsoft PowerPoint 2007+ | Presentation slides |
| **HTML/XHTML** | Web documents | Native HTML parsing |
| **Markdown** | Lightweight markup | Text format |
| **AsciiDoc** | Technical documentation | Structured content |
| **CSV** | Comma-separated values | Tabular data |
| **Images** | PNG, JPEG, TIFF, BMP, WEBP | OCR-enabled |
| **Audio** | WAV, MP3 | ASR (Automatic Speech Recognition) |
| **WebVTT** | Web Video Text Tracks | Subtitle/caption files |

### Schema-Specific Formats

- **USPTO XML** - Patent documents
- **JATS XML** - Journal articles
- **METS/GBS** - Google Books scans

### Output Formats

- Markdown (standard and strict text mode)
- JSON (DoclingDocument serialization)
- HTML (with layout preservation)
- DocTags (custom token format)
- Plain Text

---

## Integration with Confluence Content Processing

### Context: Epic 2 Requirements

From **`docs/bmad/brownfield-prd/epic-2-html-to-markdown-content-processing.md`**:

- **Story 2.2:** High-Value Macro Handlers (Attachment Macro Handler)
- **Story 2.3:** RAG-Critical Element Handlers (Image Handler)
- **Metadata Enrichment:** Asset links, file types, content extraction

### Proposed Integration Points

#### 1. Attachment Macro Handler Enhancement

**Current Plan (Story 2.2):**
```python
# Attachment Macro Handler (~100 lines):
# - Extract filenames
# - Map file type to emoji icons (📄📝📊📦📎)
```

**Enhanced with Docling:**
```python
from docling.document_converter import DocumentConverter

class AttachmentMacroHandler(BaseMacroHandler):
    def __init__(self):
        self.doc_converter = DocumentConverter()

    async def handle(self, macro_element, context):
        filename = macro_element.get("ac:parameter", {}).get("filename")
        file_path = await self._download_attachment(filename)

        # Process with Docling if supported format
        if self._is_docling_supported(file_path):
            try:
                result = self.doc_converter.convert(file_path)
                markdown_content = result.document.export_to_markdown()
                metadata = self._extract_metadata(result.document)

                # Embed in main page content
                return f"\n\n<!-- ATTACHMENT: {filename} -->\n{markdown_content}\n"
            except Exception as e:
                logger.error(f"Docling processing failed for {filename}: {e}")
                # Fallback to filename link
                return f"[{filename}]({self._get_download_url(filename)})"
        else:
            # Unsupported format, use emoji icon
            return self._format_attachment_link(filename)
```

**Benefits:**
- **Full-text Search** - PDF/Office doc content becomes searchable
- **RAG-Optimized** - Hierarchical table structures preserved
- **Metadata Enrichment** - Document structure, page count, table count
- **Code Block Preservation** - Technical docs with code samples

#### 2. Image Handler Enhancement

**Current Plan (Story 2.3):**
```python
# Image Handler (~100 lines):
# - Detect <ac:image> with <ri:attachment> or <ri:url>
# - Determine type by extension
# - Add to asset_links metadata
```

**Enhanced with Docling:**
```python
from docling.datamodel.pipeline_options import PdfPipelineOptions

class ImageHandler(BaseElementHandler):
    def __init__(self):
        # Configure for image processing with OCR
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_picture_classification = True
        pipeline_options.picture_description_options.do_picture_description = True

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.IMAGE: PipelineOptions(pipeline_options=pipeline_options)
            }
        )

    async def handle(self, image_element, context):
        image_path = await self._download_image(image_element)

        try:
            # Process image with Docling
            result = self.doc_converter.convert(image_path)

            # Extract OCR text if available
            ocr_text = result.document.export_to_markdown(strict_text=True)

            # Extract image classification (chart, diagram, photo, etc.)
            picture_items = result.document.pictures
            classifications = [pic.annotations for pic in picture_items]

            # Add to metadata
            metadata = {
                "image_path": image_path,
                "ocr_text": ocr_text,
                "classifications": classifications,
                "has_text": len(ocr_text) > 0
            }

            # Embed OCR text in markdown if present
            if ocr_text:
                return f"![{image_element.get('alt', '')}]({image_path})\n\n<!-- OCR: {ocr_text} -->\n"
            else:
                return f"![{image_element.get('alt', '')}]({image_path})"

        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            return f"![{image_element.get('alt', '')}]({image_path})"
```

**Benefits:**
- **OCR for Screenshots** - Extract text from images
- **Chart Understanding** - Detect and describe data visualizations
- **Searchable Images** - Image content becomes part of RAG corpus
- **Accessibility** - Automatic alt text generation

#### 3. Metadata Extractor Enhancement

**Current Plan (Story 2.4):**
```python
# Metadata Extractor (~150 lines):
# - Aggregate JIRA links, user mentions, internal/external links
# - Calculate content metrics
```

**Enhanced with Docling:**
```python
class MetadataExtractor:
    async def extract_attachment_metadata(self, attachment_path):
        """Extract rich metadata from processed attachments."""
        result = self.doc_converter.convert(attachment_path)
        doc = result.document

        return {
            "page_count": len(doc.pages) if hasattr(doc, 'pages') else 1,
            "table_count": len(doc.tables) if hasattr(doc, 'tables') else 0,
            "code_block_count": len([item for item in doc.texts if item.label == 'CODE']),
            "image_count": len(doc.pictures) if hasattr(doc, 'pictures') else 0,
            "word_count": len(doc.export_to_markdown(strict_text=True).split()),
            "has_formulas": any(item.label == 'FORMULA' for item in doc.texts),
            "document_structure": self._analyze_structure(doc)
        }

    def _analyze_structure(self, doc):
        """Analyze document hierarchy."""
        return {
            "sections": len([item for item in doc.texts if item.label in ['SECTION_HEADER', 'TITLE']]),
            "max_heading_level": self._get_max_heading_level(doc),
            "has_toc": any(item.label == 'TOC' for item in doc.texts)
        }
```

**Benefits:**
- **Rich Metadata** - Document structure, content types, complexity
- **Search Filters** - "Show pages with PDF attachments containing code"
- **Analytics** - Document type distribution, content patterns
- **Quality Metrics** - Completeness, structure depth

---

## Installation and Dependencies

### Basic Installation

```bash
pip install docling
```

### With Optional Features

```bash
# EasyOCR (default)
pip install docling[easyocr]

# Tesseract OCR (requires system installation)
pip install docling[tesseract]

# RapidOCR
pip install rapidocr-onnxruntime
pip install docling

# Vision Language Models
pip install docling[vlm]

# All extras
pip install docling[all]
```

### System Dependencies

**Tesseract OCR:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
apt-get install tesseract-ocr

# Set environment variable
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
```

### PyTorch Configuration

Docling uses PyTorch. For CPU-only on Linux:
```bash
pip install docling --extra-index-url https://download.pytorch.org/whl/cpu
```

For GPU support, follow PyTorch installation guide.

### macOS Intel (x86_64) Note

PyTorch 2.6.0+ lacks Intel Mac wheels. Use PyTorch 2.2.2:
```bash
pip install "docling[mac_intel]"
```

### Archon Integration

Update `python/pyproject.toml`:
```toml
[project]
dependencies = [
    "docling>=2.18.0",  # Python 3.13 support
    "docling[easyocr]",  # Default OCR
    "docling[vlm]",      # Vision models for image understanding
]
```

---

## Python API Usage Patterns

### Basic Conversion

```python
from docling.document_converter import DocumentConverter

# Initialize converter
converter = DocumentConverter()

# Convert document (file path or URL)
source = "https://arxiv.org/pdf/2408.09869"
result = converter.convert(source)

# Access DoclingDocument
doc = result.document

# Export to Markdown
markdown = doc.export_to_markdown()
print(markdown)

# Export to JSON
json_dict = doc.export_to_dict()

# Export to plain text (strict mode)
plain_text = doc.export_to_markdown(strict_text=True)
```

### Batch Conversion

```python
from pathlib import Path

input_paths = [
    Path("doc1.pdf"),
    Path("doc2.docx"),
    Path("presentation.pptx")
]

converter = DocumentConverter()

for result in converter.convert_all(input_paths):
    print(f"Processing: {result.input.file.name}")
    print(f"Status: {result.status}")
    if result.status == "success":
        markdown = result.document.export_to_markdown()
        # Save or process markdown
```

### Custom Pipeline Options

```python
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

# Configure pipeline
pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True

# OCR options
from docling.datamodel.pipeline_options import EasyOcrOptions
pipeline_options.ocr_options = EasyOcrOptions()

# Create converter with custom options
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

result = converter.convert("scanned_document.pdf")
```

### Enrichment Features

```python
# Enable enrichments
pipeline_options.do_code_enrichment = True          # Code block understanding
pipeline_options.do_formula_enrichment = True       # Formula parsing
pipeline_options.do_picture_classification = True   # Image classification
pipeline_options.do_picture_description = True      # Image captioning

# Picture description options
from docling.datamodel.pipeline_options import PictureDescriptionOptions
pipeline_options.picture_description_options = PictureDescriptionOptions(
    do_picture_description=True,
    model_id="HuggingFaceTB/SmolVLM-256M-Instruct"  # Vision model
)

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
```

### Accessing DoclingDocument Structure

```python
result = converter.convert("document.pdf")
doc = result.document

# Text items
for text_item in doc.texts:
    print(f"Label: {text_item.label}, Text: {text_item.text}")

# Tables
for table in doc.tables:
    print(f"Table: {table.num_rows} rows x {table.num_cols} cols")
    table_md = table.export_to_markdown()

# Pictures
for picture in doc.pictures:
    print(f"Picture: {picture.self_ref}, Annotations: {picture.annotations}")

# Code blocks
code_blocks = [item for item in doc.texts if item.label == 'CODE']
for code in code_blocks:
    print(f"Code: {code.text}")
```

### Metadata Extraction (Beta)

```python
from pydantic import BaseModel, Field

# Define extraction schema
class DocumentMetadata(BaseModel):
    title: str = Field(description="Document title")
    authors: list[str] = Field(description="List of authors")
    abstract: str = Field(description="Abstract or summary")
    keywords: list[str] = Field(description="Key topics")

# Extract structured data
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("research_paper.pdf")

# Extract using Pydantic model
extracted_data = result.document.extract(
    template=DocumentMetadata,
    vlm_model="HuggingFaceTB/SmolVLM-256M-Instruct"
)

print(extracted_data)
```

### Chunking for RAG

```python
from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")

# Native Docling chunking
chunker = HybridChunker(
    tokenizer="sentence-transformers/all-MiniLM-L6-v2",
    max_tokens=512,
    overlap_tokens=50
)

chunks = list(chunker.chunk(result.document))

for i, chunk in enumerate(chunks):
    print(f"Chunk {i}:")
    print(f"  Text: {chunk.text[:100]}...")
    print(f"  Metadata: {chunk.meta}")
```

---

## Performance Characteristics

### Benchmarks

From Docling Technical Report (arXiv:2408.09869):

**Test Dataset:** 225 pages, various document types

**System 1: M3 Max (16 cores)**
- Native backend, 4 threads: **4.5 pages/sec**
- Native backend, 16 threads: **11.2 pages/sec**
- Peak memory: ~2GB

**System 2: Intel Xeon (32 cores)**
- Native backend, 4 threads: **3.2 pages/sec**
- Native backend, 16 threads: **8.7 pages/sec**
- Peak memory: ~3GB

**Performance Notes:**
- OCR disabled in benchmarks (faster without OCR)
- Table structure recognition enabled
- Vision models add overhead but improve quality

### Processing Time Estimates

| Document Type | Pages | Processing Time (CPU) | Processing Time (GPU) |
|--------------|-------|----------------------|----------------------|
| Simple PDF | 10 | ~2-3 seconds | ~1-2 seconds |
| Complex PDF (tables) | 10 | ~5-10 seconds | ~3-5 seconds |
| Scanned PDF (OCR) | 10 | ~30-60 seconds | ~10-20 seconds |
| DOCX | 10 | ~1-2 seconds | ~1 second |
| Image (OCR) | 1 | ~3-5 seconds | ~1-2 seconds |

### Optimization Strategies

1. **Disable Unnecessary Features**
   ```python
   pipeline_options.do_ocr = False  # If text is extractable
   pipeline_options.do_picture_description = False  # If not needed
   ```

2. **Use Faster Table Options**
   ```python
   pipeline_options.table_structure_options.mode = "fast"
   ```

3. **Batch Processing**
   ```python
   # Process multiple documents in parallel
   results = converter.convert_all(input_paths, max_workers=4)
   ```

4. **Thread Budget**
   ```python
   from docling.datamodel.accelerator_options import AcceleratorDevice

   # Adjust thread count
   converter = DocumentConverter(
       accelerator_options=AcceleratorOptions(
           num_threads=8,
           device=AcceleratorDevice.CPU
         )
   )
   ```

---

## Metadata Extraction Capabilities

### Available Metadata (Current)

From processed `DoclingDocument`:

1. **Document Structure**
   - Page count
   - Section hierarchy
   - Heading levels
   - Table of contents presence

2. **Content Types**
   - Text items with labels (TITLE, SECTION_HEADER, TEXT, CODE, FORMULA, etc.)
   - Table count and structure (rows, columns, complexity)
   - Picture count and locations
   - Code block count

3. **Layout Information**
   - Bounding boxes for all items
   - Reading order
   - Page-level layout

4. **Provenance**
   - Source file information
   - Page numbers for each item
   - Character spans

### Upcoming Metadata (Planned)

From Docling roadmap:

- **Document Properties**
  - Title extraction
  - Author identification
  - Reference/citation parsing
  - Language detection

- **Chart Understanding**
  - Bar charts
  - Pie charts
  - Line plots
  - Data extraction from visualizations

### Custom Metadata Extraction

```python
def extract_custom_metadata(doc: DoclingDocument):
    """Extract custom metadata from DoclingDocument."""
    metadata = {
        "document_info": {
            "page_count": len(doc.pages) if hasattr(doc, 'pages') else 1,
            "total_words": len(doc.export_to_markdown(strict_text=True).split()),
        },
        "content_analysis": {
            "has_code": any(item.label == 'CODE' for item in doc.texts),
            "has_formulas": any(item.label == 'FORMULA' for item in doc.texts),
            "table_count": len(doc.tables) if hasattr(doc, 'tables') else 0,
            "picture_count": len(doc.pictures) if hasattr(doc, 'pictures') else 0,
        },
        "structure": {
            "sections": len([item for item in doc.texts if item.label == 'SECTION_HEADER']),
            "paragraphs": len([item for item in doc.texts if item.label == 'TEXT']),
        }
    }

    # Extract headings
    headings = [item.text for item in doc.texts if item.label in ['TITLE', 'SECTION_HEADER']]
    metadata["headings"] = headings[:10]  # First 10 headings

    # Analyze tables
    if hasattr(doc, 'tables'):
        table_details = []
        for table in doc.tables:
            table_details.append({
                "rows": table.num_rows,
                "cols": table.num_cols,
                "has_headers": hasattr(table, 'header') and table.header is not None
            })
        metadata["tables"] = table_details

    return metadata
```

---

## Use Cases for Archon

### Primary Use Case: Confluence Attachment Processing

**Scenario:** User syncs a Confluence space with 1,000+ pages containing:
- 200 PDF attachments (technical specs, research papers)
- 150 Office documents (DOCX, XLSX, PPTX)
- 500 images (screenshots, diagrams, charts)

**Without Docling:**
- Attachments stored as file links only
- Search limited to Confluence HTML content
- No visibility into PDF/Office doc content

**With Docling:**
- Full-text search across all attachments
- Code snippets from PDFs indexed
- OCR text from screenshots searchable
- Table data from spreadsheets embedded
- **10x increase in searchable content**

### Secondary Use Cases

#### 1. Technical Documentation Search

**Problem:** Engineering team has Confluence space with:
- API documentation (PDF exports)
- Architecture diagrams (images with text)
- Code examples (DOCX files)

**Solution with Docling:**
```python
# Process PDF with code block detection
pipeline_options.do_code_enrichment = True
result = converter.convert("api_reference.pdf")

# Extract code blocks
code_blocks = [item for item in result.document.texts if item.label == 'CODE']

# Embed in markdown with language tags
for code in code_blocks:
    markdown += f"\n```python\n{code.text}\n```\n"
```

**Benefit:** Developers can search for specific API functions across all documentation formats.

#### 2. Meeting Notes with Attachments

**Problem:** Meeting notes contain:
- Presentation slides (PPTX)
- Handwritten notes (scanned images)
- Financial reports (XLSX)

**Solution with Docling:**
```python
# OCR handwritten notes
pipeline_options.do_ocr = True
result = converter.convert("meeting_notes.jpg")
ocr_text = result.document.export_to_markdown(strict_text=True)

# Parse presentation
result = converter.convert("slides.pptx")
slide_content = result.document.export_to_markdown()

# Combine into page content
full_markdown = f"""
# Meeting Notes - 2025-10-18

{page_html_markdown}

## Presentation: {presentation_title}
{slide_content}

## Handwritten Notes
{ocr_text}
"""
```

**Benefit:** Complete searchability of meeting content including visual elements.

#### 3. Compliance Documentation

**Problem:** Legal/compliance team needs to:
- Index contract PDFs
- Extract metadata (parties, dates, terms)
- Search across thousands of documents

**Solution with Docling:**
```python
# Extract structured metadata using Pydantic
class ContractMetadata(BaseModel):
    parties: list[str]
    effective_date: str
    expiration_date: str
    contract_value: str
    key_terms: list[str]

result = converter.convert("contract.pdf")
metadata = result.document.extract(template=ContractMetadata)

# Store in Supabase with rich metadata
await document_storage_service.add_documents_to_supabase(
    content=result.document.export_to_markdown(),
    source_id=confluence_source_id,
    metadata={
        "page_id": page_id,
        "attachment_name": "contract.pdf",
        "contract_metadata": metadata.dict()
    }
)
```

**Benefit:** Structured search queries like "contracts expiring in Q1 2025" or "agreements with Party X".

#### 4. Knowledge Base Migration

**Problem:** Migrating legacy documentation from various formats:
- Old Word documents (.doc, .docx)
- PDF manuals
- Scanned paper documents

**Solution with Docling:**
```python
# Batch process all legacy documents
legacy_docs = Path("legacy_docs").glob("**/*")
converter = DocumentConverter()

for result in converter.convert_all(legacy_docs):
    if result.status == "success":
        # Convert to markdown
        markdown = result.document.export_to_markdown()

        # Create Confluence page or add to knowledge base
        await create_knowledge_entry(
            title=result.input.file.stem,
            content=markdown,
            metadata=extract_custom_metadata(result.document)
        )
```

**Benefit:** Unified format, searchable content, preserved structure.

---

## Implementation Recommendations

### Phase 1: Basic Integration (Epic 2, Story 2.2/2.3)

**Goal:** Process PDF attachments and extract OCR from images

**Implementation:**

1. **Add Docling Dependency**
   ```toml
   # python/pyproject.toml
   dependencies = [
       "docling>=2.18.0",
       "docling[easyocr]",  # Default OCR
   ]
   ```

2. **Create Docling Service**
   ```python
   # python/src/server/services/confluence/docling_processor.py
   from docling.document_converter import DocumentConverter
   from docling.datamodel.pipeline_options import PdfPipelineOptions

   class DoclingProcessor:
       def __init__(self):
           # Configure for fast processing
           pipeline_options = PdfPipelineOptions()
           pipeline_options.do_ocr = False  # Enable only for scanned docs
           pipeline_options.do_table_structure = True

           self.converter = DocumentConverter(
               format_options={
                   InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
               }
           )

       async def process_attachment(self, file_path: Path) -> dict:
           """Process attachment and return markdown + metadata."""
           try:
               result = self.converter.convert(str(file_path))

               return {
                   "success": True,
                   "markdown": result.document.export_to_markdown(),
                   "plain_text": result.document.export_to_markdown(strict_text=True),
                   "metadata": self._extract_metadata(result.document)
               }
           except Exception as e:
               logger.error(f"Docling processing failed: {e}")
               return {"success": False, "error": str(e)}

       def _extract_metadata(self, doc):
           return {
               "page_count": len(doc.pages) if hasattr(doc, 'pages') else 1,
               "table_count": len(doc.tables) if hasattr(doc, 'tables') else 0,
               "has_code": any(item.label == 'CODE' for item in doc.texts),
               "word_count": len(doc.export_to_markdown(strict_text=True).split())
           }
   ```

3. **Integrate with Attachment Handler**
   ```python
   # python/src/server/services/confluence/macro_handlers/attachment_macro.py
   from ..docling_processor import DoclingProcessor

   class AttachmentMacroHandler(BaseMacroHandler):
       def __init__(self, confluence_client, docling_processor=None):
           self.confluence_client = confluence_client
           self.docling_processor = docling_processor or DoclingProcessor()

       async def handle(self, macro_element, context):
           filename = self._extract_filename(macro_element)

           # Download attachment
           file_path = await self._download_attachment(
               page_id=context['page_id'],
               filename=filename
           )

           # Process with Docling if supported
           if self._is_processable(file_path):
               result = await self.docling_processor.process_attachment(file_path)

               if result["success"]:
                   # Add to context metadata
                   context['asset_links'].append({
                       "filename": filename,
                       "type": "document",
                       "processed": True,
                       "metadata": result["metadata"]
                   })

                   # Embed content in markdown
                   return f"\n\n<!-- ATTACHMENT: {filename} -->\n{result['markdown']}\n"

           # Fallback: file link only
           return f"[{filename}]({self._get_download_url(filename)})"

       def _is_processable(self, file_path: Path) -> bool:
           """Check if file format is supported by Docling."""
           supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx', '.png', '.jpg', '.jpeg', '.tiff'}
           return file_path.suffix.lower() in supported_extensions
   ```

4. **Add Configuration**
   ```python
   # python/src/server/config/settings.py
   class ConfluenceSettings(BaseSettings):
       # Existing settings...

       # Docling settings
       docling_enabled: bool = True
       docling_ocr_enabled: bool = False  # Expensive, enable on-demand
       docling_max_file_size_mb: int = 50  # Skip large files
       docling_timeout_seconds: int = 60
   ```

**Timeline:** 2-3 days (within Epic 2, Story 2.2/2.3)

### Phase 2: Advanced Features (Post-Epic 2)

**Goal:** OCR for images, metadata extraction, performance optimization

**Features:**

1. **Selective OCR**
   ```python
   # Enable OCR only for specific file types or on-demand
   if filename.endswith(('.png', '.jpg', '.jpeg', '.tiff')):
       pipeline_options.do_ocr = True
   ```

2. **Vision Models for Image Understanding**
   ```python
   # Install VLM support
   # pip install docling[vlm]

   pipeline_options.do_picture_classification = True
   pipeline_options.do_picture_description = True
   ```

3. **Batch Processing for Sync**
   ```python
   # Process multiple attachments in parallel
   async def sync_page_with_attachments(self, page_id):
       attachments = await self.get_attachments(page_id)

       # Process in parallel (limit concurrency)
       semaphore = asyncio.Semaphore(4)

       async def process_one(attachment):
           async with semaphore:
               return await self.docling_processor.process_attachment(attachment)

       results = await asyncio.gather(*[process_one(att) for att in attachments])
   ```

4. **Caching Processed Documents**
   ```python
   # Cache processed attachments by hash
   file_hash = hashlib.sha256(file_content).hexdigest()

   # Check cache first
   cached = await redis_client.get(f"docling:{file_hash}")
   if cached:
       return json.loads(cached)

   # Process and cache
   result = await docling_processor.process_attachment(file_path)
   await redis_client.set(f"docling:{file_hash}", json.dumps(result), ex=86400)
   ```

**Timeline:** 1-2 weeks (separate epic post-Epic 2)

### Phase 3: Full Metadata Extraction (Future)

**Goal:** Structured data extraction using Pydantic models

**Features:**

1. **Schema-based Extraction**
   ```python
   # Define extraction schemas per document type
   class TechnicalSpecMetadata(BaseModel):
       title: str
       version: str
       authors: list[str]
       abstract: str
       sections: list[str]
       requirements: list[str]

   # Extract structured data
   metadata = result.document.extract(template=TechnicalSpecMetadata)
   ```

2. **Advanced Search Filters**
   ```sql
   -- Search for pages with attachments containing specific metadata
   SELECT * FROM confluence_pages
   WHERE metadata->'attachments' @> '[{"type": "technical_spec", "version": "2.0"}]'
   ```

**Timeline:** 2-3 weeks (requires beta features to stabilize)

---

## Risks and Considerations

### 1. Processing Overhead

**Risk:** Docling processing adds latency to page sync

**Impact:**
- Simple PDF (10 pages): +2-3 seconds
- Complex PDF with OCR: +30-60 seconds
- Large batches: Significant sync time increase

**Mitigation:**
- **Async Processing:** Process attachments in background after page sync
- **Selective Processing:** Only process documents meeting criteria (file size, type)
- **Caching:** Cache processed documents by file hash
- **Configuration:** Make Docling processing optional (feature flag)

**Recommended Approach:**
```python
# Two-phase sync
async def sync_page(self, page_id):
    # Phase 1: Quick sync (HTML content only)
    await self.sync_page_content(page_id)

    # Phase 2: Background attachment processing
    if settings.docling_enabled:
        asyncio.create_task(self.process_attachments_background(page_id))
```

### 2. Memory Usage

**Risk:** Large documents consume significant memory

**Impact:**
- Peak memory: 2-3GB for document processing
- Multiple parallel processes: Memory multiplies

**Mitigation:**
- **Process Limits:** Limit concurrent Docling processes (semaphore)
- **File Size Limits:** Skip files > 50MB
- **Garbage Collection:** Explicit cleanup after processing

```python
# Limit concurrency
semaphore = asyncio.Semaphore(2)  # Max 2 concurrent Docling processes

# File size check
if file_size > settings.docling_max_file_size_mb * 1024 * 1024:
    logger.warning(f"Skipping {filename}: file too large")
    return None
```

### 3. Dependency Complexity

**Risk:** Docling has many dependencies (PyTorch, transformers, etc.)

**Impact:**
- Larger Docker image size
- Potential version conflicts
- Installation complexity

**Mitigation:**
- **Optional Dependency:** Make Docling optional (feature flag)
- **Separate Service:** Consider dedicated Docling microservice (future)
- **Dependency Pinning:** Lock versions in pyproject.toml

```toml
[project.optional-dependencies]
docling = [
    "docling>=2.18.0",
    "docling[easyocr]",
]
```

### 4. OCR Accuracy

**Risk:** OCR may produce incorrect text for poor-quality scans

**Impact:**
- Incorrect search results
- Reduced RAG quality

**Mitigation:**
- **Confidence Scores:** Track OCR confidence (if available)
- **Manual Review:** Flag low-confidence results
- **Disable by Default:** OCR opt-in only

```python
# Metadata tracking
metadata = {
    "ocr_enabled": True,
    "ocr_confidence": 0.85,  # If available from OCR engine
    "ocr_warning": confidence < 0.7
}
```

### 5. Cost Considerations

**Risk:** Vision models (for image understanding) may require GPU

**Impact:**
- Increased infrastructure costs
- Slower processing on CPU

**Mitigation:**
- **CPU-Only Mode:** Disable vision models by default
- **Batch Processing:** Accumulate images, process in batches on GPU instance
- **Cloud Services:** Consider Apify Actor (cloud Docling) for high-volume

```python
# Disable expensive features by default
pipeline_options.do_picture_description = False  # CPU-heavy
pipeline_options.do_formula_enrichment = False   # Optional
```

### 6. Format Coverage

**Risk:** Not all formats supported (e.g., .doc, proprietary formats)

**Impact:**
- Some attachments not processable
- Inconsistent experience

**Mitigation:**
- **Fallback Handling:** Graceful degradation to file links
- **Format Detection:** Clear logging of unsupported formats
- **User Communication:** Document supported formats

```python
SUPPORTED_FORMATS = {
    '.pdf', '.docx', '.pptx', '.xlsx',
    '.png', '.jpg', '.jpeg', '.tiff', '.webp',
    '.html', '.md', '.csv'
}

def _is_supported(self, filename):
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        logger.info(f"Unsupported format {ext} for {filename}")
        return False
    return True
```

### 7. Beta Features

**Risk:** Metadata extraction is in beta (may change)

**Impact:**
- API breaking changes
- Unstable features

**Mitigation:**
- **Feature Flags:** Disable beta features in production initially
- **Version Pinning:** Lock Docling version, test upgrades
- **Monitoring:** Track errors from beta features

```python
# Feature flag
if settings.docling_beta_features_enabled:
    result = doc.extract(template=CustomMetadata)
```

---

## Conclusion

### Summary

Docling is an **excellent fit** for Archon's Confluence integration, particularly for processing attachments and images in Epic 2. It provides:

✅ **Advanced Document Understanding** - Layout, tables, code, formulas
✅ **Multiple Format Support** - PDF, Office docs, images, HTML
✅ **RAG Optimization** - Hierarchical structures, semantic chunking
✅ **Metadata Extraction** - Structured data, content analysis
✅ **Easy Integration** - Simple Python API, well-documented
✅ **Active Development** - 41.8k stars, LF AI & Data Foundation support
✅ **Production Ready** - Used by InstructLab, LangChain, LlamaIndex

### Recommended Approach

1. **Phase 1 (Epic 2):** Basic integration
   - Process PDF attachments
   - Extract text content
   - Embed in page markdown
   - Timeline: 2-3 days

2. **Phase 2 (Post-Epic 2):** Advanced features
   - OCR for images
   - Vision models
   - Batch processing
   - Timeline: 1-2 weeks

3. **Phase 3 (Future):** Full capabilities
   - Structured metadata extraction
   - Advanced search filters
   - GPU acceleration
   - Timeline: 2-3 weeks

### Key Benefits for Archon

- **10x increase in searchable content** (attachments become full-text searchable)
- **Better RAG quality** (structured document understanding)
- **Richer metadata** (document structure, content types, complexity)
- **Future-proof** (active development, growing ecosystem)

### Risk Management

- Make Docling processing **optional** (feature flag)
- Implement **background processing** (don't block page sync)
- Add **file size limits** (skip large files)
- Use **caching** (process once, reuse results)
- **Monitor performance** (track processing times, memory usage)

### Next Steps

1. **Add Docling to Epic 2 Stories**
   - Update Story 2.2 (Attachment Macro Handler)
   - Update Story 2.3 (Image Handler)
   - Add acceptance criteria for Docling integration

2. **Spike Task: Docling POC**
   - Install Docling in local Archon environment
   - Test processing of sample Confluence attachments
   - Measure performance, memory usage
   - Validate integration pattern

3. **Update Documentation**
   - Add Docling section to CLAUDE.md
   - Document configuration options
   - Update user communication plan with supported formats

---

## References

### Official Documentation

- **Docling Homepage:** https://docling-project.github.io/docling/
- **GitHub Repository:** https://github.com/docling-project/docling
- **PyPI Package:** https://pypi.org/project/docling/
- **Technical Report:** [arXiv:2408.09869](https://arxiv.org/abs/2408.09869)

### Integration Guides

- **LangChain:** https://python.langchain.com/docs/integrations/document_loaders/docling/
- **LlamaIndex:** https://docs.llamaindex.ai/en/stable/examples/data_connectors/DoclingReaderDemo/
- **Haystack:** https://docling-project.github.io/docling/integrations/haystack/
- **CrewAI:** https://docling-project.github.io/docling/integrations/crewai/

### Related Research

- **DocLayNet:** Layout analysis model (arXiv:2206.01062)
- **TableFormer:** Table structure recognition (arXiv:2203.01017)

### Archon Context

- **Epic 2 PRD:** `docs/bmad/brownfield-prd/epic-2-html-to-markdown-content-processing.md`
- **Architecture:** `docs/bmad/brownfield-architecture.md`
- **Confluence Integration:** `docs/bmad/CONFLUENCE_RAG_INTEGRATION.md`

---

**Document End**

*This analysis document was created by the Library Research Agent based on comprehensive research of Docling's capabilities, documentation, and codebase integration patterns. For questions or updates, please consult the Archon development team.*
