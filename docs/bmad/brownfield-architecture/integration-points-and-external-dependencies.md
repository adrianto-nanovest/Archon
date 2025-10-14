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
| **Confluence**| Knowledge base sync (future)   | REST API v2      | TBD: `services/confluence/`             | 📝 Planned |

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

## Confluence API Integration (To Implement)

**API Documentation:**
- Confluence REST API v2: https://developer.atlassian.com/cloud/confluence/rest/v2/intro/
- Confluence CQL: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/
- Python SDK: `atlassian-python-api` (https://atlassian-python-api.readthedocs.io/)

**Integration Pattern:**
```python
from atlassian import Confluence

class ConfluenceClient:
    def __init__(self, base_url: str, api_token: str):
        self.client = Confluence(url=base_url, token=api_token)

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

---
