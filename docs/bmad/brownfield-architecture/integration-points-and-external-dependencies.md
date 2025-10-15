# Integration Points and External Dependencies

## External Services

| Service       | Purpose                        | Integration Type | Key Files                               | Status |
| ------------- | ------------------------------ | ---------------- | --------------------------------------- | ------ |
| **Supabase**  | Database & Vector Store        | SDK              | Throughout `server` service             | ✅ Active |
| **OpenAI**    | LLM for chat & embeddings      | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Google AI** | Gemini models & embeddings     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Ollama**    | Local LLM serving              | HTTP API         | `services/llm_provider_service.py`      | ✅ Active |
| **Anthropic** | Claude API                     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **Grok**      | xAI models                     | API              | `services/llm_provider_service.py`      | ✅ Active |
| **OpenRouter**| Community model hub            | API              | `services/llm_provider_service.py`      | ✅ Active |
| **GitHub API**| Version checking               | REST API         | `services/version_service.py`           | ✅ Active |
| **Confluence**| Knowledge base sync            | REST API v2      | `services/confluence/`                  | ✅ Active |

## LLM Provider Capabilities

**Chat + Embeddings:**
- OpenAI: GPT-4o, GPT-4o-mini + text-embedding-3-small/large
- Google: Gemini 1.5/2.0 models + gemini-embedding-001
- Ollama: Local models (llama3, mistral, etc.) with embedding support

**Chat Only (No Embeddings):**
- Anthropic: Claude 3.5 Sonnet, Claude 3 Opus/Haiku
- Grok: grok-3-mini, grok-3 (xAI models)
- OpenRouter: Community-hosted models (various)

**Embedding Providers (UI Enforces Restriction):**
- ✅ OpenAI, Google, Ollama ONLY
- ❌ Anthropic, Grok, OpenRouter NOT supported for embeddings

## Confluence API Integration (Implemented)

**API Documentation:**
- Confluence REST API v2: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
- Confluence CQL: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/
- Python SDK: `atlassian-python-api` v3.41.0+ (https://atlassian-python-api.readthedocs.io/)

**Dependencies (Implemented):**
```toml
# python/pyproject.toml - [dependency-groups.server]
atlassian-python-api = ">=3.41.0"  # Confluence REST API client SDK
markdownify = ">=0.11.0"            # HTML to Markdown conversion
```

**Environment Variables (Optional Configuration):**
```bash
# Can be set via .env file or Settings API (encrypted storage)
CONFLUENCE_BASE_URL=https://your-company.atlassian.net/wiki  # Required: Confluence Cloud URL (HTTPS only)
CONFLUENCE_API_TOKEN=your-api-token-here                      # Required: API token from Atlassian
CONFLUENCE_EMAIL=your-email@company.com                       # Required: Email for API authentication
```

**Configuration Pattern:**
- **Optional at startup**: Archon runs without Confluence configured
- **Required variables**: All three variables needed when creating Confluence source
- **URL validation**: Must use HTTPS (Confluence Cloud requirement)
- **Base URL only**: Don't include space paths (e.g., `/spaces/DEVDOCS`)
- **Encryption**: API tokens stored encrypted (Fernet encryption) in `archon_settings` table
- **Settings API**: Alternative to environment variables via `POST /api/credentials`

**Integration Pattern (Implemented):**
```python
from atlassian import Confluence

class ConfluenceClient:
    def __init__(self, base_url: str, api_token: str, email: str):
        self.client = Confluence(
            url=base_url,
            token=api_token,
            cloud=True  # Confluence Cloud mode
        )
        self.email = email

    async def cql_search(self, cql: str, expand: str = None):
        # CQL example: 'space = DEVDOCS AND lastModified >= "2025-10-01 10:00"'
        return self.client.cql(cql, expand=expand, limit=1000)

    async def get_page_ids_in_space(self, space_key: str) -> list[str]:
        # Lightweight deletion detection - IDs only, no content
        pages = self.client.get_all_pages_from_space(
            space=space_key, expand=None
        )
        return [p['id'] for p in pages]
```

**Implementation Files:**
- **Configuration**: `python/src/server/config/config.py` (lines 29-35, 145-189, 259-266)
  - `EnvironmentConfig` dataclass with Confluence fields
  - `validate_confluence_url()` function with HTTPS enforcement
  - Optional loading with URL validation
- **Client Service**: `python/src/server/services/confluence/` (planned/TBD)
- **Tests**: `python/tests/server/config/test_config_confluence.py` (18 unit tests)
- **Integration Tests**: `python/tests/server/config/test_confluence_settings_integration.py` (5 tests)

---
