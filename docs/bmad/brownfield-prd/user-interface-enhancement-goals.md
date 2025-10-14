# User Interface Enhancement Goals

## Integration with Existing UI

The Confluence feature UI will follow Archon's **vertical slice architecture** pattern established in `archon-ui-main/src/features/`. All components will be housed in a new `src/features/confluence/` directory, maintaining complete feature independence while adhering to established design patterns.

**Consistency Requirements:**
- **TanStack Query v5**: All data fetching via query hooks (`useConfluenceQueries.ts`) with standardized stale times from `shared/config/queryPatterns.ts`
- **Radix UI Primitives**: Reuse existing primitives from `features/ui/primitives/` (Dialog, Select, Button, Progress, Badge)
- **Tron-Inspired Glassmorphism**: Match existing styling with cyan/blue accent colors, backdrop blur effects, and subtle animations
- **Smart Polling**: Sync status updates using `useSmartPolling` hook for visibility-aware refresh intervals
- **Optimistic Updates**: Source creation/deletion using `createOptimisticEntity` and `replaceOptimisticEntity` patterns from `shared/utils/optimistic.ts`

## Modified/New Screens and Views

**New: Confluence Source Management Panel** (`/knowledge` page extension)
- Add "Confluence" tab alongside existing "Web Crawl" and "Document Upload" tabs
- Source configuration form with fields: Confluence URL, API Token (encrypted), Space Key
- Source card display showing space metadata, last sync timestamp, page count
- Sync status indicator with progress bar (leveraging existing ProgressTracker visualization)

**Modified: Knowledge Base Search Results** (`/knowledge` page)
- Enhance result cards with Confluence-specific metadata badges:
  - Space key tag (e.g., "DEVDOCS")
  - JIRA issue links (clickable chips)
  - Page hierarchy breadcrumbs using materialized path
- Filter sidebar additions:
  - "Source Type" filter: Web, Upload, **Confluence** (new)
  - "Confluence Space" multi-select dropdown
  - "Contains JIRA Links" boolean toggle

**New: Confluence Sync History Modal**
- Accessible from source card "View Sync History" action
- Table displaying: Sync timestamp, Pages added/updated/deleted, Duration, Status
- Error logs for failed syncs with retry button

**Modified: Settings Page** (`/settings`)
- Add "Confluence Integration" section in "Knowledge Base" settings category
- Deletion detection strategy selector: Weekly reconciliation, Every sync, On-demand
- Sync schedule configuration (future: automated periodic sync)

## UI Consistency Requirements

**Visual Design:**
- Match existing knowledge source card layout (thumbnail area, metadata section, action buttons)
- Use consistent color coding: Cyan for Confluence (distinct from blue for web, green for uploads)
- Maintain 16px padding, 8px gap spacing, 4px border radius standards

**Interaction Patterns:**
- Source creation follows existing modal workflow (Create → Configure → Sync trigger)
- Deletion requires confirmation dialog matching existing "Delete Source" pattern
- Sync progress displays in existing global progress notification area (top-right)

**Accessibility:**
- All new components use Radix UI primitives ensuring ARIA compliance
- Keyboard navigation support for Confluence-specific filters
- Screen reader announcements for sync status changes

**Error Handling:**
- API errors display using existing toast notification system (`features/ui/hooks/useToast.ts`)
- Network failures show retry mechanism with exponential backoff feedback
- Validation errors inline on form fields (Confluence URL format, API token)

---
