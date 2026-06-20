from __future__ import annotations

from backend.logger import logger

OUTCOME_DIRECTIONS: dict[int, str] = {
    0: "an even worse situation with no clear way out",
    1: "a significant setback that makes things more difficult",
    2: "a minor challenge that the protagonist pushes through",
    3: "a small success that aids the journey",
    4: "a great improvement to the situation, a significant advance",
}


def build_prompt(
    initial_context: str,
    history: list[str],
    outcome_tier: int,
    outcome_directions: dict[int, str] | None = None,
    max_words: int = 80,
) -> str:
    parts: list[str] = []

    parts.append(
        f"You are writing an interactive story. The premise is: {initial_context}"
    )

    if history:
        parts.append("So far the story has unfolded as follows:\n" + "\n".join(
            f"- {p}" for p in history
        ))

    directions = outcome_directions if outcome_directions is not None else OUTCOME_DIRECTIONS
    direction = directions.get(outcome_tier, directions[2])
    parts.append(
        f"Continue the story with {direction}. "
        f"The paragraph should be exactly {max_words} words long, nothing else."
    )

    assembled = "\n\n".join(parts)
    logger.debug("build_prompt: outcome_tier=%d history_len=%d prompt_len=%d max_words=%d",
                 outcome_tier, len(history), len(assembled), max_words)
    return assembled


NEUTRAL_FALLBACK = (
    "Meanwhile, the situation remained unchanged, "
    "and the story continued at its own pace."
)


def build_first_paragraph_prompt(user_input: str, max_words: int = 80) -> str:
    logger.debug("build_first_paragraph_prompt: user_input=%s max_words=%d", user_input, max_words)
    return (
        f"Write the first paragraph of a story about: {user_input}\n\n"
        f"The paragraph should be exactly {max_words} words long. Write only the paragraph, nothing else."
    )


def validate_llm_response(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) < 10:
        return False
    if stripped[-1] not in {".", "!", "?"}:
        return False
    return True


def parse_llm_response(raw: str) -> str:
    raw = raw.strip()

    prefixes = [
        "Here's the next paragraph:",
        "Here is the next paragraph:",
        "Next paragraph:",
    ]
    for prefix in prefixes:
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()

    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].strip()

    if raw and raw[-1] not in {".", "!", "?"}:
        raw += "."

    return raw
