# Epic 5: Testing, Performance & Documentation

**Epic Goal**: Validate integration with comprehensive testing, optimize performance for 4000+ pages, and update documentation

**Integration Requirements**:
- Load test sync with 4000+ page mock dataset
- Validate all existing functionality remains intact
- Update brownfield architecture documentation

## Story 5.1: Implement Backend Integration Tests

As a **QA engineer**,
I want **to create comprehensive integration tests for Confluence sync and search**,
so that **all critical paths are validated before production deployment**.

**Acceptance Criteria**:
1. Create `python/tests/server/services/confluence/test_confluence_integration.py`
2. Test: Full sync workflow (create source → sync → verify chunks in database)
3. Test: Incremental sync (modify page → sync → verify only changed page updated)
4. Test: Deletion detection (delete page in Confluence → sync → verify removed from database)
5. Test: Search with metadata filters (space, JIRA, hierarchy)
6. Test: Atomic chunk updates (sync during active search, verify no empty results)
7. Use mock Confluence API responses (no actual API calls in tests)
8. All tests pass with >90% code coverage for new Confluence services

**Integration Verification**:
- IV1: Existing knowledge base tests (web crawl, upload) still pass (no regressions)
- IV2: CASCADE DELETE test verifies complete cleanup of pages and chunks
- IV3: Concurrent sync test validates no race conditions in chunk updates

## Story 5.2: Implement Frontend Component Tests

As a **QA engineer**,
I want **to create Vitest tests for Confluence UI components**,
so that **user interactions and data flows are validated**.

**Acceptance Criteria**:
1. Create `archon-ui-main/src/features/confluence/tests/` directory
2. Test: Source creation flow (form validation, optimistic update, success/error states)
3. Test: Sync status polling (smart polling behavior, visibility awareness)
4. Test: Search filters (filter application, URL param persistence)
5. Test: Query hook behavior (cache updates, invalidation, stale time)
6. Use React Testing Library for component tests, msw for API mocking
7. All tests pass with >85% code coverage for Confluence feature

**Integration Verification**:
- IV1: Mock service methods match actual API contracts (type-safe)
- IV2: Query pattern tests validate correct stale times and key factories
- IV3: Existing feature tests (knowledge, projects) still pass

## Story 5.3: Perform Load Testing and Optimization

As a **performance engineer**,
I want **to load test Confluence sync with 4000+ pages and optimize bottlenecks**,
so that **performance requirements (15min sync, <500ms search) are met**.

**Acceptance Criteria**:
1. Create mock Confluence dataset: 4000 pages, varying sizes (1KB-75KB), 7-level hierarchy
2. Execute full sync, measure: total duration, memory usage, API calls made, database query time
3. Validate: Sync completes <15min, memory increase <20%, progress updates every 50 pages
4. Execute search benchmarks: 100 queries with metadata filters, measure p50/p95/p99 latency
5. Validate: p95 latency <500ms, index usage confirmed in query plans
6. Identify and optimize top 3 bottlenecks (if any exceed thresholds)
7. Document performance characteristics in PRD appendix

**Integration Verification**:
- IV1: Existing web crawl performance unaffected by Confluence additions
- IV2: Database connection pool handles concurrent sync + search load
- IV3: Frontend renders 4000+ source pages list with pagination (no UI lag)

## Story 5.4: Update Documentation and Architecture Docs

As a **technical writer**,
I want **to update brownfield architecture and CLAUDE.md with Confluence integration details**,
so that **future developers have accurate system documentation**.

**Acceptance Criteria**:
1. Update `docs/bmad/brownfield-architecture.md` section "Confluence Integration Architecture" with implementation reality
2. Add Confluence API endpoints to "API Specifications" section
3. Update "Source Tree and Module Organization" with new confluence/ directory
4. Update `CLAUDE.md` with Confluence development commands and file locations
5. Create `docs/confluence-integration-guide.md` with: setup instructions, API token generation, sync configuration
6. Update `migration/0.1.0/DB_UPGRADE_INSTRUCTIONS.md` for migration 010
7. Add Confluence to MCP tools documentation (if applicable)

**Integration Verification**:
- IV1: Architecture doc accurately reflects implemented code (no planned vs actual discrepancies)
- IV2: New developer can follow CLAUDE.md to understand Confluence feature structure
- IV3: Migration instructions tested on fresh database (successful upgrade path)

## Story 5.5: User Communication and Training Materials

As a **product manager**,
I want **to create user-facing documentation, changelog, and training materials for Confluence integration**,
so that **users understand how to use the new feature and are notified of its availability**.

**Acceptance Criteria**:
1. Create comprehensive user guide: `docs/bmad/confluence-user-communication-plan.md` with:
   - Step-by-step setup instructions (API token generation, source creation)
   - Sync monitoring and troubleshooting
   - Advanced search features and filters
   - FAQ and common issues
2. Create changelog entry: `docs/bmad/CHANGELOG-v0.2.0.md` with:
   - Feature highlights (headline: Confluence Cloud Integration)
   - Technical changes (new APIs, dependencies, database schema)
   - Security enhancements
   - Upgrade instructions for users and developers
   - Known issues and workarounds
3. Create in-app changelog modal component: `archon-ui-main/src/features/shared/components/ChangelogModal.tsx`
   - Displays on first login after upgrade to v0.2.0
   - Highlights key features with screenshots
   - "What's New" badge in settings menu
4. Add "Give Feedback" button in Confluence tab UI for user input
5. Create support documentation: Troubleshooting guide, error message explanations, rollback procedures

**User Communication Strategy**:
- Announcement: In-app modal on first v0.2.0 login
- Documentation: Linked from Confluence tab help icon
- Community: Post in Discord/Slack/GitHub Discussions
- Email: Optional announcement to registered users (if applicable)

**Integration Verification**:
- IV1: User guide tested by non-technical team member (successful setup)
- IV2: Changelog modal displays correctly on upgrade (tested with version check)
- IV3: Feedback button functional (logs submitted successfully)

**Deliverables**:
- User setup guide (Markdown)
- Changelog entry (Markdown)
- In-app changelog modal (React component)
- Feedback mechanism (UI + backend logging)
- Support FAQ document

---
