# High Level Architecture

## Technical Summary

Archon is a **microservices-based RAG system** designed to provide knowledge base management and task tracking for AI coding assistants. It uses a monolithic repository with Docker orchestration for three distinct services: server (port 8181), MCP server (port 8051), and agents service (port 8052).

**Current Version:** 0.1.0
**Database:** Supabase (PostgreSQL 15+ with pgvector extension)
**Architecture Pattern:** Vertical slice (frontend) + Service layer (backend)

## Actual Tech Stack

| Category          | Technology           | Version | Notes                                      |
| ----------------- | -------------------- | ------- | ------------------------------------------ |
| **Backend**       |                      |         |                                            |
| Runtime           | Python               | 3.12    | Required for latest typing features        |
| Framework         | FastAPI              | 0.104+  | Async-first with lifespan events           |
| Package Manager   | uv                   | latest  | Faster than pip, lockfile support          |
| Web Crawler       | crawl4ai             | 0.6.2   | Advanced async crawling with JS rendering  |
| **Database**      |                      |         |                                            |
| Primary DB        | PostgreSQL           | 15+     | via Supabase cloud or local                |
| Vector Store      | pgvector             | 0.5+    | Extension for embeddings (1536 dimensions) |
| DB Client         | asyncpg + Supabase SDK | 0.29+ / 2.15.1 | Direct SQL + Supabase helpers    |
| **AI/ML**         |                      |         |                                            |
| LLM SDK           | openai               | 1.71.0  | Universal client (works with compatible APIs) |
| Document Processing | pypdf2, pdfplumber, python-docx | 3.0+ | Basic extraction (no Docling yet) |
| **Frontend**      |                      |         |                                            |
| Framework         | React                | 18      | via Vite dev server                        |
| State Management  | TanStack Query       | v5      | Query-centric architecture (no Redux!)     |
| Styling           | Tailwind CSS         | 3.4.17  | Tron-inspired glassmorphism                |
| UI Primitives     | Radix UI             | various | Headless accessible components             |
| **Infrastructure**|                      |         |                                            |
| Orchestration     | Docker Compose       | latest  | Multi-service development environment      |
| Build Tool        | Makefile             | -       | Common workflow shortcuts                  |

## Repository Structure Reality Check

- **Type:** Monorepo
- **Package Manager:** `uv` (Python), `npm` (Frontend & Docs)
- **Service Split:** Three distinct Python services in `python/src/` directory
- **Build System:** Docker Compose for orchestration, Makefile for developer workflows
- **No ORM:** Direct SQL via asyncpg/Supabase client (no SQLAlchemy, no Alembic!)
- **Migration Strategy:** Manual SQL scripts in `migration/` with checksum tracking

---
