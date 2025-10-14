# Confluence Integration Setup Guide

**Version:** 1.0
**Last Updated:** 2025-10-07
**Estimated Setup Time:** 10 minutes

---

## Overview

This guide walks you through setting up Confluence Cloud integration with Archon's RAG system. You'll learn how to generate API tokens, configure sources, trigger syncs, and use advanced search features.

---

## Prerequisites

Before you begin, ensure you have:

- ✅ **Confluence Cloud Account** (not Confluence Server/Data Center)
- ✅ **Admin Access** to the Confluence space you want to sync
- ✅ **Archon v0.2.0+** installed and running
- ✅ **API Token Generation Permission** (usually requires Confluence admin role)

---

## Step 1: Generate Confluence API Token

### 1.1 Navigate to Atlassian API Tokens

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Log in with your Atlassian account

### 1.2 Create New Token

1. Click **"Create API token"**
2. **Label:** Enter a descriptive name (e.g., "Archon RAG Integration")
3. Click **"Create"**
4. **IMPORTANT:** Copy the token immediately - it won't be shown again!

### 1.3 Store Token Securely

- ⚠️ **Never share your API token** or commit it to version control
- ✅ Archon encrypts tokens using bcrypt before storing in database
- ✅ Tokens are never logged or exposed in error messages

---

## Step 2: Find Your Confluence Cloud URL

### 2.1 Identify Your Instance URL

Your Confluence Cloud URL typically looks like:

```
https://your-company.atlassian.net/wiki
```

**How to find it:**
1. Open Confluence in your browser
2. Copy the base URL (everything before `/spaces/` or `/pages/`)
3. Example: `https://acme-corp.atlassian.net/wiki`

### 2.2 Find Your Space Key

1. Navigate to the Confluence space you want to sync
2. Look at the URL - the space key is after `/spaces/`:
   ```
   https://your-company.atlassian.net/wiki/spaces/DEVDOCS/overview
                                                         ^^^^^^^
                                                       Space Key
   ```
3. Space keys are typically uppercase (e.g., `DEVDOCS`, `ENG`, `PROJ`)

---

## Step 3: Create Confluence Source in Archon

### 3.1 Navigate to Confluence Tab

1. Open Archon UI (default: `http://localhost:3737`)
2. Go to **Knowledge Base** page (left sidebar)
3. Click **"Confluence"** tab

### 3.2 Add New Source

1. Click **"New Confluence Source"** button
2. Fill in the form:

   **Confluence URL:**
   ```
   https://your-company.atlassian.net/wiki
   ```

   **Space Key:**
   ```
   DEVDOCS
   ```

   **API Token:**
   ```
   [Paste your API token from Step 1]
   ```

   **Deletion Detection Strategy:**
   - **Weekly Reconciliation** (default) - Checks for deleted pages once per week
   - **Every Sync** - Checks after each sync (more API calls)
   - **On-Demand** - Never checks automatically (manual trigger only)

3. Click **"Create Source"**

### 3.3 Verify Source Created

- You should see a new Confluence source card with:
  - Space key badge
  - Status: "Not Synced"
  - Action buttons: "Sync Now", "Edit", "Delete"

---

## Step 4: Trigger Initial Sync

### 4.1 Start Sync

1. On your Confluence source card, click **"Sync Now"**
2. Confirmation dialog appears - click **"Start Sync"**

### 4.2 Monitor Progress

- **Progress Bar:** Shows percentage complete
- **Pages Processed:** Counter updates in real-time
- **Estimated Time:** Displayed for syncs >100 pages
- **Sync Log:** Expandable section shows detailed activity

**Example Progress:**
```
Syncing Confluence Space: DEVDOCS
Progress: 1,247 / 4,000 pages (31%)
Estimated Time Remaining: 8 minutes
```

### 4.3 Sync Completion

When sync finishes, you'll see:

- ✅ **Status: Synced** with timestamp
- 📊 **Sync Metrics:**
  - Pages Added: 4,000
  - Pages Updated: 0
  - Pages Deleted: 0
  - Duration: 12m 34s
  - API Calls Made: 127

---

## Step 5: Search Confluence Content

### 5.1 Basic Search

1. Go to **Knowledge Base → Search** tab
2. Enter your search query
3. Results now include Confluence pages alongside web crawls and uploads

**Confluence Result Cards Show:**
- 🏷️ Space badge (e.g., "DEVDOCS")
- 📄 Page title and content excerpt
- 🔗 JIRA issue links (if present)
- 📁 Hierarchy breadcrumbs (e.g., "Parent → Child → Current Page")

### 5.2 Advanced Filters

Use the search sidebar to filter Confluence results:

**Source Type Filter:**
- Select **"Confluence"** to show only Confluence pages
- Or combine with "Web" and "Upload" for unified search

**Confluence Space Filter:**
- Multi-select dropdown
- Example: Select "DEVDOCS" and "ENG" to search only those spaces

**JIRA Links Filter:**
- Toggle **"Has JIRA Links"** to find pages linked to JIRA issues

**Hierarchy Filter (coming soon):**
- Search within specific page hierarchies
- Example: "Find all pages under '/Engineering/Backend/'"

### 5.3 Search Tips

**Best Practices:**
- Use specific terms from your Confluence documentation
- Combine keyword search with space filters for precision
- Check JIRA-linked pages when troubleshooting issues
- Use quotes for exact phrases: `"installation guide"`

**Example Queries:**
- `authentication middleware` + Space: DEVDOCS → Find auth docs
- `PROJ-123` → Find all pages mentioning JIRA ticket PROJ-123
- `database migration` + Has JIRA Links: Yes → Find migration docs with tickets

---

## Step 6: Incremental Syncs

### 6.1 How Incremental Sync Works

Archon uses **CQL (Confluence Query Language)** to fetch only changed pages:

```
CQL: space = DEVDOCS AND lastModified >= "2025-10-07 14:30"
```

This means:
- ✅ Only modified pages are fetched (fast!)
- ✅ API calls minimized (respects rate limits)
- ✅ Bandwidth optimized (no full space re-crawl)

### 6.2 Trigger Incremental Sync

1. On your Confluence source card, click **"Sync Now"**
2. Archon automatically fetches only pages modified since last sync

**Example Incremental Sync:**
```
Last Sync: 2025-10-07 10:00 AM
New Sync: 2025-10-07 2:00 PM
Pages Modified: 23 (out of 4,000 total)
Duration: 47 seconds
```

### 6.3 Sync Frequency Recommendations

| Space Size | Update Frequency | Recommended Sync Schedule |
|------------|------------------|---------------------------|
| <100 pages | High (hourly)    | Every 2 hours             |
| 100-1,000  | Medium (daily)   | Once per day              |
| 1,000-5,000| Low (weekly)     | 2-3 times per week        |
| 5,000+     | Very low         | Weekly or on-demand       |

---

## Step 7: Manage Confluence Sources

### 7.1 Edit Source

1. Click **"Edit"** button on source card
2. Update: Confluence URL, API token, Space Key, or deletion strategy
3. Click **"Save Changes"**

**Note:** Changing Space Key creates a new source (old data deleted via CASCADE)

### 7.2 View Sync History

1. Click **"View Sync History"** button
2. Modal shows:
   - Sync timestamps
   - Pages added/updated/deleted per sync
   - Duration and status (success/failed)
   - Error logs (if sync failed)

### 7.3 Delete Source

1. Click **"Delete"** button on source card
2. Confirmation dialog warns: **"This will delete all Confluence pages and chunks. This action cannot be undone."**
3. Type source name to confirm
4. Click **"Delete Permanently"**

**What Happens:**
- ✅ `confluence_pages` rows deleted
- ✅ `archon_crawled_pages` chunks deleted (CASCADE)
- ✅ Search results no longer show deleted Confluence pages
- ❌ Cannot be undone (re-sync required to restore)

---

## Troubleshooting

### Common Issues

#### 1. "Authentication Failed" Error

**Cause:** Invalid API token or incorrect Confluence URL

**Solutions:**
- Regenerate API token in Atlassian account settings
- Verify Confluence URL format: `https://your-company.atlassian.net/wiki`
- Ensure API token has admin permissions for the space

#### 2. "Space Not Found" Error

**Cause:** Incorrect space key or no access to space

**Solutions:**
- Double-check space key (case-sensitive, usually uppercase)
- Verify you have at least read access to the Confluence space
- Try accessing the space in browser with same account

#### 3. Sync Takes Too Long (>15 minutes)

**Cause:** Large space (5,000+ pages) or slow network

**Solutions:**
- Check network connectivity to Confluence Cloud
- Monitor sync progress - if stuck, check logs for errors
- Consider splitting into multiple smaller spaces
- Verify no Confluence API rate limiting (429 errors in logs)

#### 4. Missing Pages in Search Results

**Cause:** Incremental sync didn't catch deleted pages

**Solutions:**
- Change deletion detection strategy to "Every Sync"
- Manually trigger deletion check: Settings → Confluence → "Check for Deletions"
- Re-sync entire space (delete source and re-create)

#### 5. "Rate Limit Exceeded" (429 Error)

**Cause:** Too many API calls in short period

**Solutions:**
- Wait 1 hour for rate limit to reset (100,000 calls/day limit)
- Reduce sync frequency
- Use "Weekly Reconciliation" deletion strategy (fewer API calls)
- Check for multiple concurrent syncs (stop duplicates)

### Getting Help

**Still stuck? Here's how to get support:**

1. **Check Logs:**
   - Backend: `docker compose logs -f archon-server`
   - Frontend: Browser DevTools → Console tab

2. **Search Existing Issues:**
   - [GitHub Issues](https://github.com/your-repo/archon/issues?q=is%3Aissue+label%3Aconfluence)

3. **Report a Bug:**
   - Click **"Give Feedback"** button in Confluence tab
   - Or open [GitHub Issue](https://github.com/your-repo/archon/issues/new) with:
     - Error message (sanitize any sensitive data)
     - Steps to reproduce
     - Confluence space size and URL format
     - Archon version (`Settings → About`)

4. **Community Support:**
   - Join Discord/Slack (if available)
   - Ask in GitHub Discussions

---

## FAQ

### Q: Can I sync multiple Confluence spaces?

**A:** Yes! Create a separate source for each space. Each source syncs independently.

### Q: Does this work with Confluence Server or Data Center?

**A:** Not yet. Currently only Confluence Cloud (atlassian.net) is supported. Server/Data Center support is planned for v0.3.0.

### Q: Will syncing affect my Confluence performance?

**A:** No. Archon only reads data via Confluence API (no writes). Incremental syncs use CQL queries optimized for minimal impact.

### Q: Can I search across multiple spaces at once?

**A:** Yes! Use the "Confluence Space" filter with multiple selections, or leave unfiltered to search all spaces.

### Q: How much does this cost (Confluence API usage)?

**A:** Confluence Cloud API is included in your Atlassian subscription at no extra cost. Rate limits: 10 req/sec, 100,000 req/day (typically sufficient for daily syncs).

### Q: What happens if I delete a page in Confluence?

**A:** Depends on your deletion detection strategy:
- **Weekly Reconciliation:** Detected within 7 days
- **Every Sync:** Detected on next sync
- **On-Demand:** Never detected automatically (manual trigger required)

Deleted pages are removed from search results after detection.

### Q: Can I filter which pages are synced?

**A:** Currently syncs entire space. Fine-grained filtering (by label, author, date) is planned for v0.3.0. Workaround: Use Confluence space organization to control scope.

### Q: Is my API token secure?

**A:** Yes. Tokens are:
- Encrypted with bcrypt before database storage
- Never logged or exposed in UI/errors
- Transmitted only over HTTPS
- Revocable in Atlassian account settings anytime

### Q: Can I use Confluence Personal Access Tokens (PAT)?

**A:** Not yet. Currently only supports API tokens. PAT support planned for v0.3.0.

---

## Advanced Topics

### Custom CQL Queries (Future Feature)

Future versions will support custom CQL filters:

```
space = DEVDOCS AND label = "public" AND type = "page"
```

This will allow syncing only specific subsets of pages.

### Automated Periodic Syncs (Future Feature)

v0.3.0 will add scheduled syncs:

- Configure sync interval (hourly, daily, weekly)
- Background job runs automatically
- Email notifications on sync failures

### Metadata Enrichment API (Future Feature)

Expose Confluence metadata via API:

```bash
GET /api/confluence/{source_id}/pages/{page_id}/metadata
```

Returns JIRA links, user mentions, hierarchy, etc.

---

## Appendix: Confluence API Token Permissions

### Required Permissions

Your Confluence API token needs:

- ✅ **Read** access to space(s) you want to sync
- ✅ **CQL query** permission (usually included with read access)
- ✅ **Space listing** permission (to fetch space metadata)

### Recommended Permissions

For best experience, your Atlassian account should have:

- ✅ **Space Admin** role (for full metadata access)
- ✅ **View** permission on all pages in space

### Not Required

The following permissions are NOT needed:

- ❌ Write access to Confluence pages
- ❌ Delete permission
- ❌ Space creation permission

---

## Support & Feedback

**Documentation Feedback:**
- Found an error in this guide? [Edit on GitHub](https://github.com/your-repo/archon/edit/main/docs/bmad/confluence-integration-guide.md)

**Feature Requests:**
- Suggest improvements in [GitHub Discussions](https://github.com/your-repo/archon/discussions)

**Security Issues:**
- Report privately to security@your-company.com

---

*Last updated: 2025-10-07 | Archon v0.2.0*
