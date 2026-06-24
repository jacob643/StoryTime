import asyncio

from backend.config import settings
from backend.providers import LLMProvider
from backend.providers.ollama import OllamaProvider
from backend.providers.openai_compatible import OpenAICompatibleProvider
from backend.settings_manager import get_settings
from backend.logger import logger


RETRY_DELAY: float = 1.0


class ProviderRegistry:
    def __init__(self):
        self._ollama = OllamaProvider()
        self._custom: OpenAICompatibleProvider | None = None
        self._sync_custom()

    def _sync_custom(self) -> None:
        gs = get_settings()
        if gs.custom_endpoint:
            self._custom = OpenAICompatibleProvider(
                base_url=gs.custom_endpoint,
                api_key=gs.custom_api_key,
            )
        else:
            self._custom = None

    @property
    def active(self) -> LLMProvider:
        gs = get_settings()
        if gs.provider == "custom" and self._custom is not None:
            return self._custom
        return self._ollama

    @property
    def active_model(self) -> str | None:
        gs = get_settings()
        if gs.provider == "custom":
            return gs.custom_model or None
        return gs.ollama_model or settings.default_model

    async def generate(self, prompt: str, model: str | None = None) -> str:
        resolved_model = model or self.active_model
        logger.debug("Registry.generate provider=%s model=%s prompt_len=%d",
                     type(self.active).__name__, resolved_model, len(prompt))
        try:
            result = await self.active.generate(prompt, resolved_model)
            logger.debug("Registry.generate success response_len=%d", len(result))
            return result
        except Exception:
            logger.warning("Registry.generate first attempt failed, retrying after %.1fs", RETRY_DELAY)
            await asyncio.sleep(RETRY_DELAY)
            result = await self.active.generate(prompt, resolved_model)
            logger.debug("Registry.generate retry success response_len=%d", len(result))
            return result

    async def is_available(self) -> bool:
        return await self.active.is_available()

    async def discover(self) -> list[dict]:
        result = []
        ollama_models = await self._ollama.list_models()
        result.append({"provider": "ollama", "available": len(ollama_models) > 0, "models": ollama_models})
        if self._custom is not None:
            custom_models = await self._custom.list_models()
            result.append({"provider": "custom", "available": len(custom_models) > 0, "models": custom_models})
        return result

    def refresh(self) -> None:
        self._sync_custom()


registry = ProviderRegistry()
