# Intro Project Analysis and Context

## Existing Project Overview

### Analysis Source
**IDE-based fresh analysis** - Using the comprehensive brownfield architecture document at `docs/bmad/brownfield-architecture.md`

### Current Project State

**Archon** is a microservices-based RAG (Retrieval Augmented Generation) system designed for knowledge base management and task tracking for AI coding assistants.

**Current Version**: 0.1.0
**Architecture**: Monolithic repository with Docker orchestration for three distinct services:
- **Server** (port 8181): Main backend with FastAPI, handles knowledge base, projects, tasks, settings
- **MCP Server** (port 8051): Model Context Protocol server for IDE integration
- **Agents Service** (port 8052): AI agents service using PydanticAI

**Core Capabilities**:
- Multi-LLM provider orchestration (OpenAI, Google, Ollama, Anthropic, Grok, OpenRouter)
- Document ingestion pipeline with chunking and embeddings
- Hybrid search with vector similarity + keyword + reranking
- Web crawling with domain filtering
- Project and task management (optional feature)
- Migration tracking and version checking system

## Available Documentation Analysis

✅ **Document-project analysis available** - Using existing technical documentation from `brownfield-architecture.md`

**Key Documents Available**:
- ✅ **Tech Stack Documentation** - Comprehensive tech stack table in architecture doc
- ✅ **Source Tree/Architecture** - Complete project structure and module organization
- ✅ **API Documentation** - All API endpoints documented with examples
- ✅ **External API Documentation** - LLM providers, Supabase, GitHub API integration details
- ✅ **Technical Debt Documentation** - Known issues, incomplete features, architecture constraints
- ✅ **Coding Standards** - References to CLAUDE.md, PRPs/ai_docs pattern guides
- ✅ **Database Schema** - Complete SQL schema with migration tracking

## Enhancement Scope Definition

### Enhancement Type
✅ **Integration with New Systems** - Confluence Cloud integration for RAG system

### Enhancement Description
Integrate 4000+ Confluence Cloud pages into Archon's RAG system using Direct Confluence API approach (not Google Drive intermediary). Implementation uses Hybrid Database Schema with dedicated `confluence_pages` metadata table + unified `archon_crawled_pages` chunks, leveraging 90% code reuse from existing infrastructure.

### Impact Assessment
✅ **Moderate Impact (some existing code changes)**
- New Confluence-specific services (~800 lines)
- Minimal modifications to existing knowledge service
- Database migration for new tables
- 90% code reuse of existing document storage and search infrastructure

## Goals and Background Context

### Goals
- Enable RAG-powered search across 4000+ Confluence Cloud documentation pages
- Provide code implementation assistance using internal documentation
- Support automated documentation generation from Confluence knowledge base
- Maintain sub-second search response times with efficient incremental sync
- Preserve existing web crawl and document upload functionality

### Background Context

The Archon system currently supports web crawling and document uploads for knowledge base ingestion. However, the primary internal documentation lives in Confluence Cloud (4000+ pages), which is not efficiently accessible to the RAG system. Manual exports or Google Drive intermediary approaches were considered but rejected in favor of direct Confluence API integration.

The enhancement leverages extensive planning (1,333 lines in `CONFLUENCE_RAG_INTEGRATION.md`) and architectural analysis that identified a Hybrid Schema approach, enabling 90% code reuse and 1.5-2 week implementation timeline versus 3-4 weeks for alternative approaches.

## Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial PRD Draft | 2025-10-07 | 1.0 | Created brownfield PRD for Confluence integration based on architecture v3.0 | John (PM) |

---
