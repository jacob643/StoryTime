from backend.prompt_engine import OUTCOME_DIRECTIONS
from backend.providers import LLMProvider


MOCK_RESPONSES: dict[int, str] = {
    0: (
        "Very negative: you typed far below your average, so the story takes a "
        "sharp turn for the worse. The protagonist faces an even worse situation "
        "with no clear way out."
    ),
    1: (
        "Negative: you typed below your average, so the story hits a rough patch. "
        "The protagonist encounters a significant setback that makes things more "
        "difficult."
    ),
    2: (
        "Neutral: you typed the previous paragraph roughly near your average, so "
        "you get a neutral outcome in your next paragraph. What is this story "
        "about? trying to work at NASA or a classic fantasy story in medieval "
        "times with magic?"
    ),
    3: (
        "Positive: you typed above your average, so the story rewards you with a "
        "small win. The protagonist achieves a small success that aids the journey."
    ),
    4: (
        "Very positive: you typed far above your average, so the story delivers a "
        "big breakthrough. The protagonist makes a great improvement to the "
        "situation, a significant advance."
    ),
}


def _extract_tier_from_prompt(prompt: str, default: int = 2) -> int:
    for tier, direction in OUTCOME_DIRECTIONS.items():
        if direction in prompt:
            return tier
    return default


class MockProvider(LLMProvider):
    provider_id = "mock"
    display_name = "Mock LLM"

    async def generate(self, prompt: str, model: str | None = None) -> str:
        tier = _extract_tier_from_prompt(prompt)
        return MOCK_RESPONSES[tier]

    async def is_available(self) -> bool:
        return True
