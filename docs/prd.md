# Confluence Knowledge Base Enhancement PRD

## Intro Project Analysis and Context

### Existing Project Overview

#### Analysis Source

-   IDE-based fresh analysis
-   Reference document: `docs/brownfield-architecture.md`

#### Current Project State

Archon is a microservices-based application designed to provide a knowledge base and task management system for AI coding assistants. It consists of a React frontend, a FastAPI backend, an MCP server for AI client communication, and an agents service for AI operations. The backend uses Supabase (PostgreSQL with pgvector) for data storage.

### Available Documentation Analysis

Using existing project analysis from `docs/brownfield-architecture.md`.

-   [x] Tech Stack Documentation
-   [x] Source Tree/Architecture
-   [ ] Coding Standards (partially inferred)
-   [x] API Documentation (inferred from code structure)
-   [x] External API Documentation
-   [ ] UX/UI Guidelines
-   [x] Technical Debt Documentation

### Enhancement Scope Definition

#### Enhancement Type

-   [x] New Feature Addition
-   [x] Integration with New Systems

#### Enhancement Description

This enhancement will add the capability to create a knowledge base from a Confluence space. The content for the knowledge base will be sourced from files stored in a structured Google Drive folder, which mirrors the Confluence space. The system will process these files, create vector embeddings, and store them in a separate vector database table, along with Confluence-specific metadata.

#### Impact Assessment

-   [x] Moderate Impact (some existing code changes)
-   [x] Major Impact (architectural changes required for the new data ingestion pipeline)

### Goals and Background Context

#### Goals

-   To allow users to create a knowledge base from their Confluence spaces.
-   To leverage Google Drive as a source for Confluence content.
-   To store and query Confluence-specific metadata.
-   To provide a seamless way to keep the Confluence knowledge base in sync with the content in Google Drive.

#### Background Context

Many teams use Confluence as their primary knowledge base. This feature will allow them to easily bring that knowledge into Archon, making it available to their AI coding assistants. By using Google Drive as an intermediary, we can provide a flexible and user-friendly way to manage the content that is ingested into the knowledge base.

### Change Log

| Change          | Date       | Version | Description      | Author |
| --------------- | ---------- | ------- | ---------------- | ------ |
| Initial Draft   | 2025-08-21 | 1.0     | First draft of PRD | John (PM) |

## Requirements

### Functional

1.  **FR1**: The system shall provide a mechanism to create a new knowledge base source of type "Confluence".
2.  **FR2**: When creating a Confluence knowledge base, the user shall provide a link to a Google Drive folder.
3.  **FR3**: The system shall periodically scan the specified Google Drive folder for new, updated, or deleted content.
4.  **FR4**: The system shall process the files in the `content` subfolder, chunk them, and create vector embeddings.
5.  **FR5**: The system shall read the corresponding metadata from the files in the `metadata` subfolder and associate it with the content chunks.
6.  **FR6**: The system shall store the content chunks, their embeddings, and metadata in the `archon_crawled_pages` table.
7.  **FR7**: The system shall provide an API endpoint to trigger the synchronization process manually.
8.  **FR8**: The system shall handle errors gracefully during the synchronization process and log them for debugging.

### Non Functional

1.  **NFR1**: The synchronization process shall be designed to be efficient and not significantly impact the performance of the main application.
2.  **NFR2**: The integration with the Google Drive API must be secure, with credentials stored safely.
3.  **NFR3**: The system should be able to handle large volumes of data from Confluence spaces with many pages.

### Compatibility Requirements

1.  **CR1**: The new data ingestion pipeline must not interfere with the existing document upload and web crawling functionality.
2.  **CR2**: The database schema changes must be backward compatible.
3.  **CR3**: The new feature should be integrated into the existing UI in a consistent manner.

## Technical Constraints and Integration Requirements

### Existing Technology Stack

-   **Languages**: Python 3.11+
-   **Frameworks**: FastAPI
-   **Database**: PostgreSQL (via Supabase)
-   **Infrastructure**: Docker
-   **External Dependencies**: Supabase Python Client, OpenAI/Gemini API

### Integration Approach

-   **Database Integration Strategy**: A new source type will be added to the `archon_sources` table. The content will be stored in the existing `archon_crawled_pages` table.
-   **API Integration Strategy**: A new set of API endpoints will be created under a `/confluence` route to manage the knowledge base and trigger synchronization.
-   **Frontend Integration Strategy**: The frontend will be updated to allow users to create and manage Confluence knowledge bases.
-   **Testing Integration Strategy**: New unit and integration tests will be added to cover the new functionality.

### Code Organization and Standards

-   **File Structure Approach**: The new code will be organized into a new `confluence_sync_service.py` within the `services` directory, and a new `confluence_routes.py` in the `api_routes` directory.
-   **Naming Conventions**: Existing naming conventions will be followed.
-   **Coding Standards**: The code will adhere to the existing style (PEP 8, Black).

### Deployment and Operations

-   **Build Process Integration**: The new Google Drive dependency will be added to the `requirements.server.txt` file.
-   **Deployment Strategy**: The new feature will be deployed as part of the existing `archon-server` container.
-   **Monitoring and Logging**: The new service will use the existing logging configuration.

### Risk Assessment and Mitigation

-   **Technical Risks**: The integration with the Google Drive API could be complex. The synchronization process could be slow for large Confluence spaces.
-   **Integration Risks**: The new data ingestion pipeline could interfere with the existing ones if not implemented carefully.
-   **Deployment Risks**: The new dependencies could cause issues during deployment.
-   **Mitigation Strategies**:
    -   Thoroughly test the Google Drive API integration.
    -   Design the synchronization process to be asynchronous and fault-tolerant.
    -   Use a feature flag to enable/disable the new feature.

## Epic and Story Structure

### Epic Approach

**Epic Structure Decision**: This enhancement will be structured as a single epic, as it represents a single, cohesive feature.

## Epic 1: Confluence Knowledge Base Integration

**Epic Goal**: To provide users with the ability to create and manage a knowledge base from a Confluence space, using Google Drive as a content source.

**Integration Requirements**: The new feature must integrate seamlessly with the existing knowledge base management system, and the new data ingestion pipeline must not interfere with existing functionality.

### Story 1.1: Create Confluence Knowledge Base Source

As a user,
I want to create a new knowledge base source of type "Confluence",
so that I can link it to a Google Drive folder containing my Confluence content.

#### Acceptance Criteria

1.  AC1: The user can select "Confluence" as a source type in the UI.
2.  AC2: The user can provide a name, description, and a Google Drive folder URL for the new source.
3.  AC3: A new record is created in the `archon_sources` table with the appropriate metadata.

#### Integration Verification

1.  IV1: Creating a Confluence source does not affect the creation of other source types.

### Story 1.2: Implement Google Drive Synchronization Service

As a developer,
I want a service that can synchronize content from a Google Drive folder to the knowledge base,
so that Confluence pages can be ingested into Archon.

#### Acceptance Criteria

1.  AC1: The service can authenticate with the Google Drive API using stored credentials.
2.  AC2: The service can list and read files from the specified `content`, `asset`, and `metadata` folders.
3.  AC3: The service can chunk the content files and prepare them for ingestion.
4.  AC4: The service calls the `document_storage_service` to ingest the content and metadata.

#### Integration Verification

1.  IV1: The new service uses the existing `document_storage_service` and `credential_service` correctly.

### Story 1.3: Create API Endpoint for Synchronization

As a developer,
I want an API endpoint to trigger the Confluence synchronization process,
so that it can be called from the UI or other services.

#### Acceptance Criteria

1.  AC1: A new POST endpoint `/api/confluence/sync/{source_id}` is created.
2.  AC2: The endpoint triggers the `confluence_sync_service` to start the synchronization process for the given source ID.
3.  AC3: The endpoint returns a success response immediately, while the sync process runs in the background.

#### Integration Verification

1.  IV1: The new endpoint is properly secured and integrated with the existing FastAPI application.
