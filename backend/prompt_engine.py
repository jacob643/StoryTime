from __future__ import annotations

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
        "Write only a single paragraph, nothing else."
    )

    return "\n\n".join(parts)


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
