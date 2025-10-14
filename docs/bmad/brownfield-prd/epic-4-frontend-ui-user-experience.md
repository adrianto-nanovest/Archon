# Epic 4: Frontend UI & User Experience

**Epic Goal**: Implement Confluence source management UI with sync monitoring, following vertical slice architecture and existing design patterns

**Integration Requirements**:
- Follow TanStack Query patterns from existing features
- Reuse Radix UI primitives and Tron-inspired styling
- Integrate with existing Knowledge Base page layout

## Story 4.1: Create Confluence Vertical Slice Foundation

As a **frontend developer**,
I want **to create the `features/confluence/` directory structure with services, hooks, types**,
so that **Confluence UI follows established vertical slice architecture**.

**Acceptance Criteria**:
1. Create directory: `archon-ui-main/src/features/confluence/`
2. Create `services/confluenceService.ts` with API methods: `listSources()`, `createSource()`, `triggerSync()`, `getStatus()`, `deleteSource()`
3. Create `hooks/useConfluenceQueries.ts` with query key factory: `confluenceKeys.all`, `confluenceKeys.lists()`, `confluenceKeys.detail(id)`
4. Create `types/index.ts` with TypeScript types: `ConfluenceSource`, `ConfluenceSyncStatus`, `CreateSourceRequest`
5. Implement query hooks: `useConfluenceSources()`, `useConfluenceDetail(id)`, `useCreateSource()`, `useTriggerSync()`, `useDeleteSource()`
6. Use `STALE_TIMES.normal` (30s) for lists, `STALE_TIMES.frequent` (5s) for sync status

**Integration Verification**:
- IV1: Query keys follow standardized factory pattern from `shared/config/queryPatterns.ts`
- IV2: Service client uses shared `apiClient.ts` with ETag support
- IV3: Types match backend API response schemas exactly

## Story 4.2: Implement Confluence Source Management UI

As a **frontend developer**,
I want **to create Confluence tab in Knowledge page with source cards and creation modal**,
so that **users can create, view, and manage Confluence sources**.

**Acceptance Criteria**:
1. Add "Confluence" tab to `/knowledge` page alongside Web Crawl and Document Upload
2. Create `components/ConfluenceSourceCard.tsx` showing: space key, page count, last sync timestamp, status badge
3. Create `components/NewConfluenceSourceModal.tsx` with form fields: Confluence URL, API Token (password input), Space Key, Deletion Strategy
4. Implement optimistic create using `createOptimisticEntity()` from shared utils
5. Use Radix UI primitives: Dialog (modal), Select (deletion strategy), Button, Badge (status)
6. Apply Tron-inspired styling: cyan accent color, glassmorphism backdrop, subtle animations
7. Add validation: URL format, API token presence, space key pattern (uppercase letters)

**Integration Verification**:
- IV1: Source creation follows same UX flow as web crawl creation (modal → form → create)
- IV2: Optimistic update shows new source immediately, replaced with server data on success
- IV3: Deletion confirmation dialog matches existing pattern from other features

## Story 4.3: Implement Sync Status and Progress Monitoring

As a **frontend developer**,
I want **to create sync status display with real-time progress updates**,
so that **users can monitor Confluence sync operations**.

**Acceptance Criteria**:
1. Create `components/ConfluenceSyncStatus.tsx` showing: sync state, progress percentage, pages processed, estimated time remaining
2. Use `useSmartPolling` hook for sync status updates (5s interval when tab focused, pause when hidden)
3. Display progress bar using Radix Progress primitive with cyan fill
4. Show sync logs in expandable section (last 10 log entries)
5. Add "Sync Now" button on source card (triggers manual sync, disabled during active sync)
6. Display error state with retry button if sync fails
7. Success state shows: pages added/updated/deleted, duration

**Integration Verification**:
- IV1: Progress updates use existing `ProgressTracker` backend service (no new polling infrastructure)
- IV2: Smart polling pauses when browser tab hidden (visibility-aware)
- IV3: Error handling follows existing toast notification pattern

## Story 4.4: Enhance Search UI with Confluence Filters

As a **frontend developer**,
I want **to add Confluence-specific filters to search sidebar and metadata to result cards**,
so that **users can leverage Confluence metadata for refined searches**.

**Acceptance Criteria**:
1. Modify `features/knowledge/components/SearchFilters.tsx` to add: Source Type filter (Web/Upload/Confluence), Confluence Space multi-select, "Has JIRA Links" toggle
2. Enhance `features/knowledge/components/SearchResultCard.tsx` for Confluence results: space badge, JIRA issue chips (clickable), hierarchy breadcrumbs (using path)
3. Use Radix Badge component for space tags (cyan background)
4. JIRA chips link to external JIRA instance (configurable base URL)
5. Breadcrumbs truncate at 5 levels with "..." for deeper paths
6. Add filter persistence using URL query params (restore filters on page reload)

**Integration Verification**:
- IV1: Filters apply correctly to search API request (verify network tab)
- IV2: Confluence metadata displays only for Confluence results (null for web/upload)
- IV3: Filter UI matches existing design patterns (same spacing, colors, interactions)

---
