# Confluence Integration Guide

This guide walks you through setting up Confluence Cloud integration with Archon's RAG system.

## Prerequisites

Before you begin, ensure you have:

- Confluence Cloud account (not Confluence Server/Data Center)
- Admin access to the Confluence space you want to sync
- Archon v0.2.0+ installed and running

## Step 1: Generate Confluence API Token

### 1.1 Navigate to Atlassian API Tokens

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Log in with your Atlassian account

### 1.2 Create New Token

1. Click **"Create API token"**
2. **Label:** Enter a descriptive name (e.g., "Archon RAG Integration")
3. Click **"Create"**
4. **IMPORTANT:** Copy the token immediately - it won't be shown again!

### 1.3 Token Security

- Archon encrypts tokens using Fernet encryption before storage
- Tokens are never logged or exposed in error messages
- Tokens can be revoked anytime in Atlassian account settings

## Step 2: Find Your Confluence URL and Space Key

### 2.1 Confluence Cloud URL

Your Confluence Cloud URL looks like:

```
https://your-company.atlassian.net/wiki
```

### 2.2 Space Key

1. Navigate to the Confluence space you want to sync
2. Look at the URL - the space key is after `/spaces/`:
   ```
   https://your-company.atlassian.net/wiki/spaces/DEVDOCS/overview
                                                   ^^^^^^^
                                                 Space Key
   ```
3. Space keys are typically uppercase (e.g., `DEVDOCS`, `ENG`, `PROJ`)

## Step 3: Configure Confluence Source

### Option A: Environment Variables

Add to your `.env` file:

```bash
CONFLUENCE_BASE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_API_TOKEN=your-api-token-here
CONFLUENCE_EMAIL=your-email@company.com
```

### Option B: Settings API

Create a source via API:

```bash
curl -X POST http://localhost:8181/api/confluence/sources \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://your-company.atlassian.net/wiki",
    "api_token": "your-api-token",
    "email": "your-email@company.com",
    "space_key": "DEVDOCS",
    "deletion_strategy": "weekly_reconciliation"
  }'
```

### Deletion Detection Strategies

- **weekly_reconciliation** (default): Checks for deleted pages once per week
- **every_sync**: Checks after each sync (more API calls)
- **on_demand**: Never checks automatically

## Step 4: Trigger Sync

### Start Initial Sync

```bash
curl -X POST http://localhost:8181/api/confluence/{source_id}/sync
```

### Monitor Progress

```bash
curl http://localhost:8181/api/confluence/{source_id}/status
```

Response includes:
- `status`: "syncing" or "idle"
- `total_pages`: Number of pages synced
- `sync_metrics`: Pages added/updated/deleted
- `active_operation`: Progress of current sync

## Step 5: Search Confluence Content

Confluence content is searchable through the standard RAG search:

```bash
curl -X POST http://localhost:8181/api/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication middleware"}'
```

Results include Confluence pages with:
- Space key badge
- Page title and content excerpt
- JIRA issue links (if present)
- Hierarchy breadcrumbs

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/confluence/sources` | Create Confluence source |
| GET | `/api/confluence/sources` | List all Confluence sources |
| POST | `/api/confluence/{id}/sync` | Trigger manual sync |
| GET | `/api/confluence/{id}/status` | Get sync status |
| DELETE | `/api/confluence/{id}` | Delete source (CASCADE) |
| GET | `/api/confluence/{id}/pages` | List pages in space |

### Create Source Request

```json
{
  "base_url": "https://company.atlassian.net/wiki",
  "api_token": "api-token",
  "email": "user@company.com",
  "space_key": "DEVDOCS",
  "deletion_strategy": "weekly_reconciliation"
}
```

### Sync Status Response

```json
{
  "status": "idle",
  "last_sync": "2025-12-12T10:30:00Z",
  "total_pages": 4000,
  "sync_metrics": {
    "pages_added": 4000,
    "pages_updated": 0,
    "pages_deleted": 0,
    "duration_seconds": 754
  },
  "active_operation": null
}
```

## Troubleshooting

### Authentication Failed

**Cause:** Invalid API token or incorrect URL

**Solutions:**
- Regenerate API token in Atlassian account settings
- Verify URL format: `https://your-company.atlassian.net/wiki`
- Check that API token has read permissions

### Space Not Found

**Cause:** Incorrect space key or no access

**Solutions:**
- Verify space key (case-sensitive, usually uppercase)
- Ensure read access to the Confluence space
- Try accessing the space in browser with same account

### Rate Limit Exceeded (429)

**Cause:** Too many API calls

**Solutions:**
- Wait 1 hour for rate limit reset
- Use "weekly_reconciliation" deletion strategy
- Reduce sync frequency

### Sync Takes Too Long

**Cause:** Large space (5,000+ pages)

**Solutions:**
- Initial sync can take 15+ minutes for large spaces
- Incremental syncs are fast (only changed pages)
- Consider splitting into smaller spaces

## Architecture Overview

Confluence integration uses a **Hybrid Schema** approach:

1. **confluence_pages** table stores rich metadata (~15KB per page)
2. **archon_crawled_pages** table stores chunks (unified with web crawls)
3. **90% code reuse** with existing document storage and search

### Data Pipeline

```
Confluence API → CQL Query (changed pages only)
              → HTML Processing (5-pass pipeline)
              → Metadata Extraction (JIRA, mentions, links)
              → Chunking & Embedding (reuses existing service)
              → Unified Search (no UNION queries needed)
```

### Files

**Backend Services:** `python/src/server/services/confluence/`
**API Routes:** `python/src/server/api_routes/confluence_api.py`
**Migrations:** `migration/0.1.0/901_add_confluence_pages.sql`

## Support

- **Backend Logs:** `docker compose logs -f archon-server`
- **GitHub Issues:** Report bugs with error messages and steps to reproduce
- **Documentation:** See `docs/bmad/CONFLUENCE_RAG_INTEGRATION.md` for detailed architecture
