# LLM Provider System

## Design Goals

1. **Ollama as primary** — auto-discovery, zero configuration for the common case
2. **Custom endpoints as power-user option** — any OpenAI-compatible API
3. **Provider abstraction** — game logic never talks directly to a specific API
4. **Graceful degradation** — when a provider is unavailable, clear error messages guide the user
5. **Extensible** — new providers can be added in a single file without touching game logic

## Provider Interface

```python
class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 500,
        temperature: float = 0.8,
        timeout: float = 30.0
    ) -> str:
        """Send a prompt to the LLM and return the text response."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return a list of available model identifiers."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the backend is reachable and functional."""
        ...

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider type (e.g. 'ollama')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI (e.g. 'Ollama (Local)')."""
        ...
```

## Ollama Provider

### Auto-Discovery

Ollama exposes a REST API at `http://localhost:11434`. The provider:

1. **Availability check**: `GET /api/tags` — if this responds, Ollama is running
2. **Model listing**: Parse the `models` array from `/api/tags` response, extract `name` fields
3. **Generation**: `POST /api/generate` with the prompt, model name, and generation params

### Implementation Sketch

```python
class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=5.0)

    async def is_available(self) -> bool:
        try:
            r = await self.client.get(f"{self.base_url}/api/tags")
            return r.status_code == 200
        except httpx.RequestError:
            return False

    async def list_models(self) -> list[str]:
        r = await self.client.get(f"{self.base_url}/api/tags")
        r.raise_for_status()
        data = r.json()
        return [m["name"] for m in data.get("models", [])]

    async def generate(self, prompt, model, max_tokens=500, temperature=0.8, timeout=30.0):
        payload = {
            "model": model,
            "prompt": prompt,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
            "stream": False
        }
        r = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=timeout
        )
        r.raise_for_status()
        return r.json()["response"]
```

### Connection Test

The settings panel should have a "Test Connection" button that calls `is_available()` and reports the result, plus the number of models found.

## OpenAI-Compatible Provider

### Design

Many backends expose an OpenAI-compatible API:
- **OpenAI** (GPT-4, GPT-4o-mini)
- **Anthropic via proxy** (using OpenAI SDK compatibility layer)
- **LM Studio** (local)
- **text-generation-webui** (local)
- **vLLM** (local/cloud)

The user provides:
- Base URL (e.g. `https://api.openai.com/v1`)
- API key (optional, for local backends that don't require auth)
- Model name (text input, not a dropdown — since we can't auto-discover remote models)

### Implementation Sketch

```python
class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def is_available(self) -> bool:
        try:
            r = await self.client.get(f"{self.base_url}/models")
            return r.status_code in (200, 401)  # 401 = key needed but server is up
        except httpx.RequestError:
            return False

    async def list_models(self) -> list[str]:
        """May not work without auth; return user-configured model name as fallback."""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            r = await self.client.get(f"{self.base_url}/models", headers=headers)
            if r.status_code == 200:
                data = r.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            pass
        return []  # fallback — user types model name manually

    async def generate(self, prompt, model, max_tokens=500, temperature=0.8, timeout=30.0):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        r = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=timeout
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
```

## Provider Registry

```python
class ProviderRegistry:
    """Manages available providers and the active provider instance."""

    def __init__(self):
        self.ollama = OllamaProvider()
        self.custom: OpenAICompatibleProvider | None = None
        self._active: LLMProvider | None = None

    async def discover(self) -> list[ProviderInfo]:
        """Check which providers are available and return info for UI."""
        providers = []
        # Always check Ollama
        ollama_available = await self.ollama.is_available()
        ollama_models = await self.ollama.list_models() if ollama_available else []
        providers.append(ProviderInfo(
            id="ollama", name="Ollama (Local)",
            available=ollama_available, models=ollama_models
        ))
        # If custom endpoint is configured, check it
        if self.custom:
            custom_available = await self.custom.is_available()
            custom_models = await self.custom.list_models() if custom_available else []
            providers.append(ProviderInfo(
                id="custom", name="Custom Endpoint",
                available=custom_available, models=custom_models
            ))
        return providers

    def set_active(self, provider_id: str, model: str, custom_endpoint: str = "", api_key: str = ""):
        if provider_id == "ollama":
            self._active = self.ollama
        elif provider_id == "custom":
            self.custom = OpenAICompatibleProvider(custom_endpoint, api_key)
            self._active = self.custom
        self._active_model = model
```

## User-Facing Configuration

### Settings UI Options

The user can configure the provider through the settings panel:

```
Provider Selection:
  (●) Ollama (auto-detected) — Model: [dropdown of discovered models]
  ( ) Custom Endpoint — URL: [text input] — Model: [text input] — Key: [password input]
```

### Configuration Persistence

Saved to `~/.storytime/user.cfg`:

```json
{
  "provider": "ollama",
  "model": "llama3.2:3b",
  "custom_endpoint": "",
  "api_key": "",
  "paragraph_length": 20
}
```

### Discovery Flow (on app start)

```
App starts
  │
  ├──> Ping Ollama GET /api/tags
  │     ├── Success → populate model dropdown, select default
  │     └── Fail → show "Ollama not found" banner
  │
  ├──> Load saved config
  │     └── If custom endpoint saved, attempt health check
  │
  └──> Render UI with available providers
```

## Future Providers (Extensibility)

| Provider | How to Add |
|---|---|
| Anthropic | New `AnthropicProvider` using Anthropic Python SDK or direct API |
| LM Studio | Reuses `OpenAICompatibleProvider` (it's OpenAI-compatible) |
| text-generation-webui | Same — uses OpenAI-compatible endpoint |
| Google Gemini | New `GeminiProvider` using Google AI SDK |
| Groq | Reuses `OpenAICompatibleProvider` with Groq's endpoint URL |

The pattern for adding a new provider:
1. Create `providers/newprovider.py`
2. Implement `LLMProvider` interface
3. Register in `ProviderRegistry`
4. Add UI toggle in settings panel
