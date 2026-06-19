from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @abstractmethod
    async def generate(self, prompt: str, model: str | None = None) -> str: ...

    @abstractmethod
    async def is_available(self) -> bool: ...

    @abstractmethod
    async def list_models(self) -> list[str]: ...
