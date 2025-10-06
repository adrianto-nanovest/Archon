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

This enhancement will add the capability to create a knowledge base from a Confluence space. The content for the knowledge base will be sourced from files stored in a structured Google Drive folder, which is intended to be a curated, exported mirror of a Confluence space. The system will process these files, create vector embeddings, and store them in the vector database, along with Confluence-specific metadata.

#### Impact Assessment

-   [x] Moderate Impact (some existing code changes)
-   [x] Major Impact (architectural changes required for the new data ingestion pipeline)

### Goals and Background Context

#### Goals

-   To allow users to create a knowledge base from their Confluence spaces.
-   To leverage a curated Google Drive folder as a decoupled and flexible source for Confluence content.
-   To store and query Confluence-specific metadata to maintain context.
-   To provide a robust way to synchronize the Confluence knowledge base with the content in Google Drive.

#### Background Context

Many teams use Confluence as their primary knowledge base. This feature will allow them to bring that knowledge into Archon for use by AI coding assistants. Using Google Drive as an intermediary provides a "decoupled content pipeline." This approach allows for manual curation and management of the content to be ingested, avoids potential complexities of direct Confluence API access in restricted environments, and provides a clear, auditable source of truth for the knowledge base content.

### Change Log

| Change | Date | Version | Description | Author |
| --- | --- | --- | --- | --- |
| Initial Draft | 2025-08-21 | 1.0 | First draft of PRD | John (PM) |
| Revision | 2025-08-25 | 1.1 | Added detail on GDrive structure, CRUD handling, and asset management. Refined stories. | Sarah (PO) |

## Requirements

### Google Drive Structure Requirements

1.  **GDR1**: The linked Google Drive folder must contain three sub-folders: `content`, `metadata`, and `assets`.
2.  **GDR2**: The `content` folder will contain Confluence page content, saved in Markdown (`.md`) format.
3.  **GDR3**: The `metadata` folder will contain JSON files (`.json`) corresponding to each content file.
4.  **GDR4**: The `assets` folder will contain images and other attachments referenced in the content files.
5.  **GDR5**: File Naming Convention: A content file and its metadata file must share the same base name (e.g., `content/My-Page-Title-12345.md` and `metadata/My-Page-Title-12345.json`, where `12345` is the Confluence Page ID).
6.  **GDR6**: Metadata JSON Schema: Each `.json` file must contain the following key-value pairs:
    -   `confluencePageId`: string (e.g., "12345")
    -   `confluenceSpaceId`: string (e.g., "KB")
    -   `title`: string
    -   `author`: string
    -   `lastModified`: ISO 8601 timestamp string
    -   `parentPageId`: string or null

### Functional

1.  **FR1**: The system shall provide a mechanism to create a new knowledge base source of type "Confluence".
2.  **FR2**: When creating a Confluence knowledge base, the user shall provide a link to a Google Drive folder that adheres to the specified structure (GDR1-6).
3.  **FR3**: The system shall periodically scan the specified Google Drive folder to detect new, updated, and deleted content and metadata files.
4.  **FR4**: **Content Creation**: For each new `.md` and corresponding `.json` file pair, the system shall:
    1.  Process and chunk the Markdown content.
    2.  Create vector embeddings for the chunks.
    3.  Store the chunks, embeddings, and associated metadata in the `archon_crawled_pages` table.
5.  **FR5**: **Content Updates**: If an existing `.md` file in Google Drive is updated (based on file modification timestamp), the system shall re-process, re-chunk, and update the corresponding entries in the database.
6.  **FR6**: **Content Deletion**: If a `.md` file is deleted from Google Drive, the system shall remove all associated content chunks and metadata from the `archon_crawled_pages` table.
7.  **FR7**: **Asset Handling**: The system shall identify asset links within the Markdown content, upload the corresponding files from the `assets` folder to a designated storage solution (e.g., Supabase Storage), and rewrite the links in the content to point to the new location.
8.  **FR8**: The system shall provide an API endpoint to trigger the synchronization process manually.
9.  **FR9**: The system shall provide user feedback on the status of the synchronization (e.g., in-progress, completed, failed) via an API endpoint.
10. **FR10**: The system shall handle errors gracefully during the synchronization process (e.g., missing metadata, broken asset links) and log them for debugging.

### Non-Functional

1.  **NFR1**: The synchronization process shall be asynchronous and designed to be efficient, not significantly impacting the performance of the main application.
2.  **NFR2**: The integration with the Google Drive API must be secure, with credentials stored safely using the existing `credential_service`.
3.  **NFR3**: The system should be scalable to handle Confluence spaces with up to 10,000 pages and associated assets.

### Out of Scope

-   Direct, real-time, bi-directional synchronization with the Confluence API. The Google Drive folder is the single source of truth.
-   An automated tool for exporting Confluence spaces into the specified Google Drive structure. This is assumed to be a manual or externally scripted process for this epic.
-   Handling of complex, non-standard Confluence macros or content types not representable in Markdown.

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
-   **External Dependencies**: Supabase Python Client, OpenAI/Gemini API, Google Drive API Client

### Integration Approach

-   **Database Integration Strategy**: A new source type will be added to the `archon_sources` table. The content will be stored in the existing `archon_crawled_pages` table, potentially with new columns in the metadata field to accommodate Confluence-specific data.
-   **API Integration Strategy**: A new set of API endpoints will be created under a `/confluence` route to manage the knowledge base, trigger synchronization, and check sync status.
-   **Frontend Integration Strategy**: The frontend will be updated to allow users to create and manage Confluence knowledge bases and view synchronization status.
-   **Testing Integration Strategy**: New unit and integration tests will be added to cover the new functionality, including file handling and CRUD operations.

### Code Organization and Standards

-   **File Structure Approach**: The new code will be organized into a new `confluence_sync_service.py` within the `services` directory, and a new `confluence_routes.py` in the `api_routes` directory.
-   **Naming Conventions**: Existing naming conventions will be followed.
-   **Coding Standards**: The code will adhere to the existing style (PEP 8, Black).

### Deployment and Operations

-   **Build Process Integration**: The new Google Drive dependency will be added to the `requirements.server.txt` file.
-   **Deployment Strategy**: The new feature will be deployed as part of the existing `archon-server` container.
-   **Monitoring and Logging**: The new service will use the existing logging configuration, with detailed logs for sync operations.

### Risk Assessment and Mitigation

-   **Technical Risks**: The synchronization logic for handling creates, updates, and deletes must be robust. Asset link rewriting could be complex.
-   **Integration Risks**: The new data ingestion pipeline could interfere with the existing ones if not implemented carefully.
-   **Deployment Risks**: The new dependencies could cause issues during deployment.
-   **Mitigation Strategies**:
    -   Develop a comprehensive test suite for the Google Drive sync logic.
    -   Design the synchronization process to be idempotent and fault-tolerant.
    -   Use a feature flag to enable/disable the new feature.

## Epic and Story Structure

### Epic Approach

**Epic Structure Decision**: This enhancement will be structured as a single epic, as it represents a single, cohesive feature.

## Epic 1: Confluence Knowledge Base Integration

**Epic Goal**: To provide users with the ability to create and manage a knowledge base from a Confluence space, using a curated Google Drive folder as a content source.

**Integration Requirements**: The new feature must integrate seamlessly with the existing knowledge base management system, and the new data ingestion pipeline must not interfere with existing functionality.

### Story 1.1: Create Confluence Knowledge Base Source

As a user,
I want to create a new knowledge base source of type "Confluence",
so that I can link it to a Google Drive folder containing my Confluence content.

#### Acceptance Criteria

1.  AC1: The user can select "Confluence" as a source type in the UI.
2.  AC2: The user can provide a name, description, and a Google Drive folder URL for the new source.
3.  AC3: The system validates that the provided URL points to a valid Google Drive folder.
4.  AC4: A new record is created in the `archon_sources` table with the appropriate metadata.

#### Integration Verification

1.  IV1: Creating a Confluence source does not affect the creation of other source types.

### Story 1.2: Implement Google Drive Synchronization Service

As a developer,
I want a service that can synchronize content from a structured Google Drive folder to the knowledge base,
so that Confluence pages and assets can be ingested, updated, and deleted in Archon.

#### Acceptance Criteria

1.  AC1: The service can authenticate with the Google Drive API using stored credentials.
2.  AC2: The service can list files from the `content`, `metadata`, and `assets` folders and identify new, updated, and deleted files since the last sync.
3.  AC3: **For new content**, the service correctly parses the Markdown and metadata, chunks the content, ingests it via `document_storage_service`, and handles any associated assets.
4.  AC4: **For updated content**, the service correctly identifies and replaces the existing content and metadata in the database.
5.  AC5: **For deleted content**, the service correctly removes all associated data from the database.
6.  AC6: **For assets**, the service uploads them to storage and correctly rewrites the links in the stored content.
7.  AC7: The service logs its progress and any errors encountered during the sync process.

#### Integration Verification

1.  IV1: The new service correctly uses the existing `document_storage_service` and `credential_service`.
2.  IV2: Database transactions are handled correctly to prevent partial updates on failure.

### Story 1.3: Create API Endpoints for Synchronization

As a developer,
I want API endpoints to manage and monitor the Confluence synchronization process,
so that it can be controlled and observed from the UI or other services.

#### Acceptance Criteria

1.  AC1: A new POST endpoint `/api/confluence/sync/{source_id}` is created to trigger the sync process.
2.  AC2: The endpoint triggers the `confluence_sync_service` to run the synchronization as a background task and returns a success response immediately.
3.  AC3: A new GET endpoint `/api/confluence/sync/status/{source_id}` is created to report the status of the latest sync job (e.g., `pending`, `running`, `success`, `failed`, `last_completed_at`).

#### Integration Verification

1.  IV1: The new endpoints are properly secured and integrated with the existing FastAPI application.

### Story 1.4: Display Confluence Source and Sync Status in UI

As a user,
I want to see the status of my Confluence knowledge base synchronization,
so that I know if the content is up-to-date or if there were any problems.

#### Acceptance Criteria

1.  AC1: The UI lists Confluence knowledge bases along with other source types.
2.  AC2: The UI displays the last sync time and the current status (e.g., "Syncing...", "Up to date", "Failed").
3.  AC3: The user can manually trigger a new synchronization from the UI.
4.  AC4: If a sync fails, the UI provides a way to view basic error information.

#### Integration Verification

1.  IV1: The frontend correctly calls the new API endpoints to fetch status and trigger synchronization.
