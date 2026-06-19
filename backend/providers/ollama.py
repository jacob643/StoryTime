import httpx
from backend.config import settings
from backend.providers import LLMProvider
from backend.providers.mock import MockProvider


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self._mock = MockProvider()

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return "Ollama"

    async def generate(self, prompt: str, model: str | None = None) -> str:
        if settings.mock_llm:
            return await self._mock.generate(prompt, model)
        url = f"{settings.ollama_host}/api/generate"
        payload = {
            "model": model or settings.default_model,
            "prompt": prompt,
            "stream": False,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=settings.ollama_timeout)
            response.raise_for_status()
            data = response.json()
            return data["response"]

    async def is_available(self) -> bool:
        if settings.mock_llm:
            return await self._mock.is_available()
        try:
            url = f"{settings.ollama_host}/api/tags"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5)
                return response.status_code == 200
        except httpx.RequestError:
            return False

    async def list_models(self) -> list[str]:
        if settings.mock_llm:
            return await self._mock.list_models()
        try:
            url = f"{settings.ollama_host}/api/tags"
            async with httpx.AsyncClient() as client:
                r = await client.get(url, timeout=5)
                r.raise_for_status()
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except httpx.RequestError:
            return []
