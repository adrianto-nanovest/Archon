# Confluence RAG Integration Guide

## Executive Summary

This guide outlines the approach for integrating 4000+ Confluence Cloud pages into Archon's RAG system for code implementation assistance and documentation generation.

## Decision: RAG vs MCP

### Chosen Approach: **RAG (Recommended)**

For a knowledge base of 4000+ pages used for code implementation and documentation generation, RAG provides superior capabilities compared to MCP.

### Comparison

| Feature | RAG (Archon) | MCP Confluence |
|---------|--------------|----------------|
| **Search Type** | Hybrid (vector + keyword + graph) | Keyword-only |
| **Performance** | <100ms (local pgvector) | 200-500ms (API calls) |
| **Offline Support** | ✅ Yes | ❌ No |
| **Code Extraction** | ✅ Pre-indexed | ❌ Runtime parsing |
| **Rate Limits** | ✅ None | ❌ 10-100 req/min |
| **Context Efficiency** | ✅ Optimized chunks | ❌ Raw API responses |
| **Semantic Search** | ✅ Vector embeddings | ❌ Limited |
| **Reranking** | ✅ Optional CrossEncoder | ❌ No |
| **Cost** | Storage only | API calls + storage |

### When to Use MCP Instead

- Need to CREATE/UPDATE Confluence pages (write operations)
- Content changes extremely frequently (hourly)
- Occasional lookups only (<10 queries/day)
- Real-time data access is critical

### Hybrid Approach (Future)

Consider combining both:
- **RAG for reads**: Search and retrieval
- **MCP for writes**: Create pages, update documentation

## Data Pipeline Architecture

### Option A: Google Drive Staging (❌ NOT Recommended)

```
Confluence API → Download .md → Upload GDrive → Download from GDrive → RAG
```

**Problems:**
- Double latency and storage costs
- Sync complexity (two systems to manage)
- Version mismatch risks
- Asset handling complications
- No incremental update support

### Option B: Direct API to RAG (✅ RECOMMENDED)

```
Confluence API → Process & Chunk → Supabase → RAG Search
```

**Benefits:**
- Single source of truth (Confluence)
- Simpler architecture (one fewer system)
- Better metadata capture (space, labels, authors)
- Direct asset handling
- Leverages existing Archon infrastructure

## Handling Updates & Deletions

### Current Archon Capabilities

**Supported:**
- ✅ Update source metadata
- ✅ Delete entire sources
- ✅ Manual re-crawl trigger

**Missing:**
- ❌ Incremental sync
- ❌ Automatic change detection
- ❌ Soft delete tracking

### Incremental Sync Strategy

#### 1. Metadata Schema Extension

Store in `archon_sources.metadata`:
```json
{
  "source_type": "confluence",
  "confluence_space_key": "DEVDOCS",
  "confluence_base_url": "https://company.atlassian.net",
  "last_sync_timestamp": "2025-10-01T10:00:00Z",
  "sync_mode": "incremental",
  "total_pages": 4127,
  "sync_frequency_hours": 24
}
```

#### 2. Confluence API Integration

**For Updates:**
```python
# Use Confluence CQL (Confluence Query Language)
GET /wiki/rest/api/content/search
?cql=lastModified >= '2025-10-01' AND space = 'DEVDOCS'
```

**For Deletions:**
```python
# Track page IDs in crawled_pages.metadata
# Compare current Confluence page list vs stored IDs
# Detect missing pages and mark as deleted
```

#### 3. Database Schema Changes

```sql
-- Extend archon_sources
ALTER TABLE archon_sources
ADD COLUMN last_sync_at TIMESTAMPTZ,
ADD COLUMN sync_status TEXT DEFAULT 'active',
ADD COLUMN sync_error TEXT;

-- Extend archon_crawled_pages
ALTER TABLE archon_crawled_pages
ADD COLUMN confluence_page_id TEXT,
ADD COLUMN confluence_version INTEGER,
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE,
ADD COLUMN deleted_at TIMESTAMPTZ;

-- Create index for efficient sync queries
CREATE INDEX idx_confluence_page_id
ON archon_crawled_pages(confluence_page_id)
WHERE confluence_page_id IS NOT NULL;
```

### Sync Frequency Recommendations

| Sync Type | Frequency | Duration (est.) | Use Case |
|-----------|-----------|-----------------|----------|
| **Full Re-sync** | Weekly | 15-30 min | Catch structural changes |
| **Incremental** | Daily | 2-5 min | Normal updates |
| **On-Demand** | Manual | Varies | Immediate needs |

## Implementation Phases

### Phase 1: Confluence Crawler (Week 1-2)

**Files to Create:**
- `python/src/server/services/crawling/strategies/confluence.py`
- `python/src/server/services/confluence_client.py`

**Tasks:**
1. Implement Confluence API client using `atlassian-python-api`
2. Create `ConfluenceCrawlStrategy` class
3. Handle pagination for 4000+ pages
4. Extract page content, metadata, attachments
5. Support space-based and CQL-based crawling

**API Integration:**
```python
from atlassian import Confluence

confluence = Confluence(
    url='https://company.atlassian.net',
    token='your-api-token'
)

# Get all pages in a space
pages = confluence.get_all_pages_from_space(
    space='DEVDOCS',
    start=0,
    limit=100,
    expand='body.storage,version,metadata.labels'
)
```

### Phase 2: Incremental Sync (Week 3)

**Files to Create:**
- `python/src/server/services/confluence_sync_service.py`
- `python/src/server/api_routes/confluence_api.py`

**Tasks:**
1. Implement change detection using CQL
2. Handle page updates (detect version changes)
3. Handle page deletions (soft delete)
4. Handle page moves/renames
5. Add manual sync trigger endpoint

**Change Detection Logic:**
```python
async def detect_changes(self, source_id: str):
    # Get last sync timestamp
    last_sync = await self.get_last_sync_timestamp(source_id)

    # Query Confluence for changes
    cql = f"lastModified >= '{last_sync}' AND space = 'DEVDOCS'"
    changed_pages = confluence.cql(cql)

    # Compare with stored pages
    stored_page_ids = await self.get_stored_page_ids(source_id)
    confluence_page_ids = {p['id'] for p in all_pages}

    # Detect deletions
    deleted_ids = stored_page_ids - confluence_page_ids

    return {
        'updated': changed_pages,
        'deleted': deleted_ids
    }
```

### Phase 3: Enhanced Search (Week 4)

**Tasks:**
1. Extract page hierarchy (parent-child relationships)
2. Index Confluence labels as tags
3. Enable filtering by space, label, author
4. Enhance code block extraction for Confluence format

**Graph Relationships (Optional):**
```python
# Store in crawled_pages.metadata
{
  "confluence_parent_id": "123456",
  "confluence_children_ids": ["789012", "345678"],
  "confluence_labels": ["api", "authentication", "jwt"],
  "confluence_space": "DEVDOCS",
  "confluence_author": "john.doe@company.com"
}
```

### Phase 4: Testing & Optimization (Week 5)

**Tasks:**
1. Load test with 4000+ pages
2. Optimize chunking strategy for Confluence structure
3. Tune hybrid search weights for Confluence content
4. Create user documentation
5. Add monitoring and alerting

## Technical Implementation Details

### Confluence Content Processing

**HTML to Markdown Conversion:**
```python
from markdownify import markdownify as md

def process_confluence_page(page):
    # Get storage format (HTML)
    html_content = page['body']['storage']['value']

    # Convert to markdown
    markdown = md(html_content)

    # Extract code blocks
    code_blocks = extract_code_blocks(markdown)

    return {
        'content': markdown,
        'code_blocks': code_blocks,
        'metadata': extract_metadata(page)
    }
```

### Attachment Handling

```python
async def process_attachments(page_id: str):
    attachments = confluence.get_attachments_from_content(page_id)

    for attachment in attachments['results']:
        if attachment['mediaType'].startswith('image/'):
            # Download and store image
            image_data = confluence.download_attachment(attachment['id'])
            await store_attachment(page_id, attachment, image_data)
```

### Code Block Extraction

```python
def extract_code_blocks(markdown: str) -> list:
    """Extract code blocks from Confluence markdown"""
    pattern = r'```(\w+)?\n(.*?)```'
    blocks = re.findall(pattern, markdown, re.DOTALL)

    return [
        {
            'language': lang or 'text',
            'content': code.strip(),
            'summary': generate_code_summary(code)
        }
        for lang, code in blocks
    ]
```

### Progress Tracking

Use existing Archon progress infrastructure:
```python
from src.server.utils.progress.progress_tracker import ProgressTracker

progress = ProgressTracker(operation_id, operation_type="confluence_sync")

await progress.update(
    status="syncing",
    progress=50,
    log=f"Processed {processed}/{total_pages} pages",
    total_pages=total_pages,
    processed_pages=processed
)
```

## Frontend Integration

### Knowledge Base UI Updates

**Add Confluence Source Form:**
- Confluence URL input
- Space key input
- API token (encrypted credential storage)
- Sync frequency selector

**Display Sync Status:**
- Last sync timestamp
- Sync status (active, syncing, error)
- Manual sync trigger button
- View sync logs

### Search Enhancements

**Confluence-specific Filters:**
- Filter by Confluence space
- Filter by labels
- Filter by author
- Filter by date range

## API Endpoints

### New Endpoints

```python
POST   /api/knowledge/confluence/sources     # Create Confluence source
GET    /api/knowledge/confluence/sources     # List Confluence sources
POST   /api/knowledge/confluence/{id}/sync   # Trigger sync
GET    /api/knowledge/confluence/{id}/status # Get sync status
DELETE /api/knowledge/confluence/{id}        # Delete source
```

### Request/Response Examples

**Create Confluence Source:**
```json
POST /api/knowledge/confluence/sources
{
  "confluence_url": "https://company.atlassian.net",
  "space_key": "DEVDOCS",
  "api_token": "your-token",
  "sync_frequency_hours": 24,
  "knowledge_type": "technical",
  "tags": ["documentation", "api"]
}

Response: 201 Created
{
  "source_id": "company.atlassian.net_DEVDOCS",
  "progress_id": "conf_sync_abc123",
  "status": "syncing"
}
```

## Configuration

### Environment Variables

```bash
# .env
CONFLUENCE_API_TIMEOUT=30
CONFLUENCE_MAX_PAGES_PER_REQUEST=100
CONFLUENCE_MAX_CONCURRENT_REQUESTS=5
CONFLUENCE_RETRY_ATTEMPTS=3
CONFLUENCE_SYNC_BATCH_SIZE=50
```

### Credential Storage

Use existing Archon credential service:
```python
from src.server.services.credential_service import credential_service

await credential_service.set_credential(
    key=f"confluence_token_{source_id}",
    value=api_token,
    category="confluence",
    is_encrypted=True
)
```

## Error Handling & Monitoring

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `401 Unauthorized` | Invalid/expired token | Update API token |
| `403 Forbidden` | Insufficient permissions | Grant read access to space |
| `404 Not Found` | Space/page deleted | Remove from tracking |
| `429 Rate Limited` | Too many requests | Implement backoff |
| `500 Server Error` | Confluence downtime | Retry with exponential backoff |

### Logging Strategy

```python
from src.server.config.logfire_config import safe_logfire_info, safe_logfire_error

safe_logfire_info(
    f"Confluence sync started | source_id={source_id} | space={space_key}"
)

safe_logfire_error(
    f"Confluence sync failed | source_id={source_id} | error={str(e)}",
    exc_info=True
)
```

## Performance Optimization

### Chunking Strategy for Confluence

```python
# Confluence pages often have clear structure
def chunk_confluence_page(content: str, metadata: dict):
    # Split by headers (h1, h2, h3)
    sections = split_by_headers(content)

    chunks = []
    for section in sections:
        # Target 500-1000 tokens per chunk
        if len(section) > 1000:
            # Further split long sections
            chunks.extend(chunk_by_sentences(section, max_size=1000))
        else:
            chunks.append(section)

    return chunks
```

### Batch Processing

```python
async def sync_space_incremental(self, source_id: str):
    changed_pages = await self.detect_changes(source_id)

    # Process in batches of 50
    batch_size = 50
    for i in range(0, len(changed_pages), batch_size):
        batch = changed_pages[i:i+batch_size]
        await asyncio.gather(*[
            self.process_page(page) for page in batch
        ])
```

### Caching Strategy

```python
# Cache space metadata for 1 hour
@lru_cache(maxsize=100)
async def get_space_metadata(space_key: str):
    return await confluence.get_space(space_key)
```

## Testing Strategy

### Unit Tests

```python
# tests/test_confluence_sync.py
async def test_detect_changes():
    service = ConfluenceSyncService()
    changes = await service.detect_changes('test_source')
    assert 'updated' in changes
    assert 'deleted' in changes

async def test_process_page():
    page = load_test_fixture('confluence_page.json')
    result = await service.process_page(page)
    assert result['content']
    assert result['code_blocks']
```

### Integration Tests

```python
async def test_full_sync_flow():
    # Create source
    source_id = await create_confluence_source(
        space_key='TESTSPACE'
    )

    # Wait for initial sync
    await wait_for_sync_completion(source_id)

    # Verify pages stored
    pages = await get_stored_pages(source_id)
    assert len(pages) > 0

    # Test search
    results = await search_documents(
        query="authentication",
        filter_metadata={"source": source_id}
    )
    assert len(results) > 0
```

### Load Testing

```python
# Test with 4000+ pages
async def test_large_space_sync():
    start = time.time()
    await sync_space('LARGESPACE')  # 4000+ pages
    duration = time.time() - start

    assert duration < 1800  # Should complete in < 30 minutes
```

## Migration Path

### Step-by-Step Migration

1. **Backup existing data**
   ```bash
   pg_dump archon > archon_backup_$(date +%Y%m%d).sql
   ```

2. **Run database migrations**
   ```bash
   cd python
   uv run alembic upgrade head
   ```

3. **Deploy Confluence integration**
   ```bash
   docker compose down
   docker compose up --build -d
   ```

4. **Create Confluence source via UI**
   - Navigate to Knowledge Base
   - Click "Add Source" → "Confluence Space"
   - Enter credentials and space key
   - Start initial sync

5. **Monitor progress**
   - Check Progress tab for sync status
   - Review logs: `docker compose logs -f archon-server`

6. **Verify search**
   - Test RAG search with Confluence content
   - Check code example extraction
   - Validate metadata indexing

## Alternative: Quick Start (Limited API Access)

If you have limited API access or want to start immediately:

### Export & Upload Method

1. **Export from Confluence**
   - Go to Space Tools → Content Tools → Export
   - Select "HTML" format
   - Download export package

2. **Upload to Archon**
   - Use existing file upload feature
   - Drag & drop exported HTML files
   - Archon will process and index

**Pros:**
- ✅ Works immediately
- ✅ No API credentials needed
- ✅ Same RAG capabilities

**Cons:**
- ❌ No incremental sync
- ❌ Manual re-export for updates
- ❌ No metadata preservation

## Maintenance & Operations

### Regular Maintenance Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| **Monitor sync status** | Daily | Check for failed syncs |
| **Review error logs** | Daily | Identify and fix sync issues |
| **Verify search quality** | Weekly | Ensure results are relevant |
| **Update API tokens** | As needed | Rotate tokens before expiry |
| **Cleanup deleted pages** | Monthly | Remove soft-deleted pages |
| **Optimize vector indices** | Monthly | Run `VACUUM` on embeddings |

### Monitoring Queries

```sql
-- Check sync status
SELECT
  source_id,
  last_sync_at,
  sync_status,
  metadata->>'confluence_space_key' as space,
  metadata->>'total_pages' as pages
FROM archon_sources
WHERE metadata->>'source_type' = 'confluence';

-- Find failed syncs
SELECT * FROM archon_sources
WHERE sync_status = 'error'
AND metadata->>'source_type' = 'confluence';

-- Count pages by space
SELECT
  metadata->>'confluence_space' as space,
  COUNT(*) as page_count
FROM archon_crawled_pages
WHERE metadata->>'source_type' = 'confluence'
AND is_deleted = false
GROUP BY space;
```

## Cost Analysis

### Storage Estimation

For 4000 pages:
- **Average page size**: 5KB markdown
- **Total content**: ~20MB
- **Embeddings** (1536 dims): ~25MB
- **Code examples**: ~10MB
- **Total storage**: ~55MB

### API Cost (if using Confluence Cloud)

- **Initial sync**: 4000 API calls (one-time)
- **Daily incremental**: ~50-100 API calls
- **Atlassian API limits**: Free tier = 10 req/min

**No additional costs** - uses existing Archon infrastructure.

## Expected Outcomes

After full implementation:

- ✅ **4000+ Confluence pages indexed** for RAG search
- ✅ **Hybrid search** (vector + keyword + optional graph)
- ✅ **Daily incremental sync** with automatic change detection
- ✅ **Code example extraction** from Confluence code blocks
- ✅ **Sub-100ms search performance** with pgvector
- ✅ **Offline capability** after initial sync
- ✅ **Advanced filtering** by space, labels, authors
- ✅ **Deletion tracking** with soft deletes
- ✅ **Version awareness** to avoid unnecessary re-processing

## Support & Resources

### Atlassian API Documentation

- [Confluence REST API](https://developer.atlassian.com/cloud/confluence/rest/v2/intro/)
- [Confluence CQL](https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/)
- [Confluence Python API](https://atlassian-python-api.readthedocs.io/)

### Archon Resources

- Architecture: `PRPs/ai_docs/ARCHITECTURE.md`
- RAG Implementation: `python/src/server/services/search/rag_service.py`
- Crawling Service: `python/src/server/services/crawling/crawling_service.py`
- Hybrid Search: `python/src/server/services/search/hybrid_search_strategy.py`

### Community

- GitHub Issues: https://github.com/your-org/archon/issues
- Discussions: https://github.com/your-org/archon/discussions
