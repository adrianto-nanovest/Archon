# Archon Brownfield Architecture Document

## Introduction

This document captures the CURRENT STATE of the Archon codebase, including technical debt, workarounds, and real-world patterns. It serves as a reference for AI agents working on enhancements.

### Document Scope

Focused on areas relevant to: **Adding a Confluence Knowledge Base feature using Google Drive as a source.**

### Change Log

| Date       | Version | Description                 | Author    |
| ---------- | ------- | --------------------------- | --------- |
| 2025-08-21 | 1.0     | Initial brownfield analysis | Winston (Architect) |

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System

-   **Main Entry**: `python/src/server/main.py`
-   **Configuration**: `.env.example`, `python/src/server/config/`
-   **Core Business Logic**: `python/src/server/services/`
-   **API Definitions**: `python/src/server/api_routes/`
-   **Database Models**: The database schema is managed via SQL scripts in `migration/`. There are no ORM models.
-   **Knowledge Management**: `python/src/server/services/knowledge/knowledge_item_service.py`
-   **Document Storage**: `python/src/server/services/storage/document_storage_service.py`

### Enhancement Impact Areas

-   `python/src/server/services/knowledge/knowledge_item_service.py`: Will need to handle a new 'confluence' source type.
-   `python/src/server/services/storage/document_storage_service.py`: Will be used to ingest the Confluence content.
-   `python/src/server/api_routes/`: A new endpoint will be required to trigger the Confluence sync process.
-   A new service will be created to handle the logic of reading from Google Drive and preparing the data for ingestion.

## High Level Architecture

### Technical Summary

Archon is a microservices-based application designed to provide a knowledge base and task management system for AI coding assistants. It consists of a React frontend, a FastAPI backend, an MCP server for AI client communication, and an agents service for AI operations. The backend uses Supabase (PostgreSQL with pgvector) for data storage.

### Actual Tech Stack

| Category    | Technology | Version | Notes                               |
| ----------- | ---------- | ------- | ----------------------------------- |
| Runtime     | Python     | 3.11+   | As per Dockerfile                   |
| Framework   | FastAPI    | latest  |                                     |
| Database    | PostgreSQL | latest  | via Supabase                        |
| Vector Store| pgvector   | latest  | via Supabase                        |
| Frontend    | React      | latest  | via Vite                            |

### Repository Structure Reality Check

-   Type: Monorepo
-   Package Manager: `pip` (via `requirements.txt`) for Python, `npm` for UI and docs.
-   Notable: The Python code is split into three distinct services (`server`, `mcp`, `agents`) within the `python/src` directory.

## Source Tree and Module Organization

### Project Structure (Actual)

```text
archon/
├── python/
│   ├── src/
│   │   ├── server/        # Core business logic and APIs
│   │   │   ├── api_routes/  # FastAPI routers
│   │   │   ├── services/    # Business logic services
│   │   │   │   ├── knowledge/ # Knowledge base management
│   │   │   │   └── storage/   # Document ingestion and storage
│   │   │   └── main.py      # Server entry point
│   │   ├── mcp/           # MCP server logic
│   │   └── agents/        # AI agents logic
├── archon-ui-main/      # React frontend
├── docs/                # Docusaurus documentation
└── migration/           # SQL database migration scripts
```

### Key Modules and Their Purpose

-   **`server`**: The main backend service. It handles all business logic, including knowledge base management, document processing, and API endpoints.
-   **`knowledge_item_service.py`**: Manages the metadata for knowledge bases (called "sources"). It interacts with the `archon_sources` table.
-   **`document_storage_service.py`**: Handles the ingestion of documents into the vector store. It chunks documents, creates embeddings, and stores them in the `archon_crawled_pages` table.

## Data Models and APIs

### Data Models

The database schema is defined in `migration/complete_setup.sql`. The key tables for this feature are:

-   **`archon_sources`**: Stores metadata about each knowledge base source. A new source will be created for each Confluence space.
-   **`archon_crawled_pages`**: Stores the chunks of content from the knowledge base, along with their embeddings and metadata.

### API Specifications

The existing APIs are defined in `python/src/server/api_routes/`. A new API endpoint will be needed to trigger the synchronization of the Confluence knowledge base.

## Technical Debt and Known Issues

-   The system currently relies on local file system access for document uploads. The new feature will require integration with a cloud storage provider (Google Drive), which will be a new pattern.
-   There is no existing framework for background jobs. The Confluence sync process could be long-running, so a simple background task management system might be needed.

## Integration Points and External Dependencies

### External Services

| Service       | Purpose              | Integration Type | Key Files                               |
| ------------- | -------------------- | ---------------- | --------------------------------------- |
| Supabase      | Database & Vector Store | SDK              | Throughout the `server` service         |
| OpenAI/Gemini | LLM for embeddings   | API              | `services/embeddings/embedding_service.py` |

## Development and Deployment

### Local Development Setup

As described in the `README.md`, local development is done via `docker-compose`.

### Build and Deployment Process

The project is deployed as a set of Docker containers.

## Enhancement Impact Analysis: Confluence Knowledge Base

### Files That Will Need Modification

-   `python/src/server/services/knowledge/knowledge_item_service.py`: Minor changes may be needed to accommodate a 'confluence' source type or metadata.
-   `python/src/server/api_routes/`: A new file will be added to define the API endpoint for triggering the Confluence sync.

### New Files/Modules Needed

-   **`python/src/server/services/confluence_sync_service.py`**: A new service to orchestrate the synchronization process. This service will be responsible for:
    -   Authenticating with Google Drive.
    -   Reading the `content`, `asset`, and `metadata` folders.
    -   Chunking the content files.
    -   Preparing the data and metadata for ingestion.
    -   Calling `document_storage_service.add_documents_to_supabase` to ingest the data.
-   **`python/src/server/api_routes/confluence_routes.py`**: A new API router to expose the sync functionality.
-   **`python/src/server/services/background_task_manager.py`**: A simple background task manager might be needed to run the sync process asynchronously.

### Integration Considerations

-   **Google Drive API**: The new `confluence_sync_service` will need to integrate with the Google Drive API to read the files. This will require adding the Google Drive client library to the project's dependencies.
-   **Error Handling**: The sync process needs robust error handling to manage issues with file access, API failures, and data processing.
-   **Security**: The Google Drive API credentials will need to be stored securely, likely using the existing `credential_service`.
