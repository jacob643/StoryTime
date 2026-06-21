import asyncio
import concurrent.futures

import pytest
from backend.providers.mock import MockProvider, _extract_tier_from_prompt, MOCK_RESPONSES
from backend.prompt_engine import OUTCOME_DIRECTIONS, build_prompt


@pytest.fixture
def provider():
    return MockProvider()


def _run(coro):
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def test_mock_generate_returns_response_for_each_tier(provider):
    for tier in range(5):
        prompt = build_prompt("Test story", ["previous paragraph"], outcome_tier=tier)
        result = _run(provider.generate(prompt))
        assert result == MOCK_RESPONSES[tier]
        assert result.endswith(".") or result.endswith("?")
        assert len(result) > 20


def test_mock_generate_without_tier_in_prompt_defaults_to_tier_2(provider):
    prompt = "Tell me a story about dragons."
    result = _run(provider.generate(prompt))
    assert result == MOCK_RESPONSES[2]


def test_mock_is_available_returns_true(provider):
    assert _run(provider.is_available()) is True


def test_extract_tier_from_prompt_all_tiers():
    for tier, phrasings in OUTCOME_DIRECTIONS.items():
        prompt = f"Continue the story with {phrasings[0]}."
        assert _extract_tier_from_prompt(prompt) == tier


def test_extract_tier_from_prompt_matches_any_phrasing():
    for tier, phrasings in OUTCOME_DIRECTIONS.items():
        for phrasing in phrasings:
            prompt = f"Continue the story with {phrasing}."
            assert _extract_tier_from_prompt(prompt) == tier


def test_extract_tier_from_prompt_no_match_defaults_to_2():
    assert _extract_tier_from_prompt("Some random prompt") == 2


def test_mock_responses_all_have_tier_label():
    for tier, resp in MOCK_RESPONSES.items():
        if tier == 0:
            assert "Very negative" in resp
        elif tier == 1:
            assert "Negative" in resp
        elif tier == 2:
            assert "Neutral" in resp
        elif tier == 3:
            assert "Positive" in resp
        elif tier == 4:
            assert "Very positive" in resp


def test_mock_provider_attributes(provider):
    assert provider.provider_id == "mock"
    assert provider.display_name == "Mock LLM"


def test_mock_list_models_returns_empty(provider):
    assert _run(provider.list_models()) == []
