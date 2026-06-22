import httpx
from backend.providers import LLMProvider
from backend.settings_manager import get_settings
from backend.logger import logger


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._timeout = timeout

    @property
    def provider_id(self) -> str:
        return "custom"

    @property
    def display_name(self) -> str:
        return "Custom Endpoint"

    async def generate(self, prompt: str, model: str | None = None) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": get_settings().temperature,
        }
        resolved_model = payload["model"]
        logger.debug("OpenAICompatibleProvider: POST %s/chat/completions model=%s prompt_len=%d",
                     self.base_url, resolved_model, len(prompt))
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            logger.debug("OpenAICompatibleProvider: response status=%d response_len=%d",
                         r.status_code, len(content))
            return content

    async def is_available(self) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/models", headers=headers, timeout=5)
                return r.status_code in (200, 401)
        except httpx.RequestError:
            return False

    async def list_models(self) -> list[str]:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/models", headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    return [m["id"] for m in data.get("data", [])]
        except Exception:
            pass
        return []
