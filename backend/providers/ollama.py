import httpx
from backend.config import settings
from backend.providers import LLMProvider


class OllamaProvider(LLMProvider):
    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def display_name(self) -> str:
        return "Ollama"

    async def generate(self, prompt: str, model: str | None = None) -> str:
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
        try:
            url = f"{settings.ollama_host}/api/tags"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5)
                return response.status_code == 200
        except httpx.RequestError:
            return False
