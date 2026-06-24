from __future__ import annotations

import random
import re
import unicodedata
from typing import Union

from backend.logger import logger

OUTCOME_DIRECTIONS: dict[int, list[str]] = {
    0: [
        "an even worse situation with no clear way out",
        "disaster strikes without warning",
        "everything falls apart in the worst possible way",
        "a catastrophic turn no one expected",
        "the situation deteriorates into chaos",
        "hope fades as things go from bad to worse",
        "a devastating blow changes everything",
        "the bottom falls out of the situation",
        "darkness closes in from all sides",
        "an irreversible tragedy unfolds",
    ],
    1: [
        "a significant setback that makes things more difficult",
        "an obstacle appears that complicates the journey",
        "a painful loss that must be endured",
        "circumstances take a turn for the worse",
        "a difficult challenge tests resolve",
        "progress is halted by unexpected trouble",
        "a costly mistake has serious consequences",
        "the path forward becomes more treacherous",
        "a troubling revelation changes the stakes",
        "trust is broken and must be rebuilt",
    ],
    2: [
        "a minor challenge that the protagonist pushes through",
        "a small hurdle that requires some effort",
        "the journey continues with a moment of uncertainty",
        "a brief moment of tension arises and passes",
        "there is a slight bump in the road ahead",
        "an ordinary obstacle turns into a learning moment",
        "a simple test of patience presents itself",
        "things remain steady with a touch of difficulty",
        "a passing inconvenience slows things down",
        "a mild complication arises but seems manageable",
    ],
    3: [
        "a small success that aids the journey",
        "a helpful coincidence brightens the path",
        "a minor victory boosts morale and momentum",
        "an unexpected advantage presents itself",
        "kindness from an unlikely source changes things",
        "a piece of luck shifts the situation slightly",
        "a small discovery proves useful",
        "things go better than expected for a moment",
        "a brief moment of triumph lifts the spirit",
        "a gentle wind of fortune pushes things forward",
    ],
    4: [
        "a great improvement to the situation, a significant advance",
        "a remarkable breakthrough changes the game entirely",
        "fortune smiles in an extraordinary way",
        "an incredible opportunity presents itself",
        "things come together better than anyone could hope",
        "a stunning victory leaves everyone in awe",
        "the path clears in a truly unexpected way",
        "a gift of fate changes the direction of the story",
        "triumph emerges from the struggle in grand fashion",
        "a brilliant stroke of genius leads to great success",
    ],
}


def _normalize_directions(directions: dict[int, Union[str, list[str]]]) -> dict[int, list[str]]:
    return {k: (v if isinstance(v, list) else [v]) for k, v in directions.items()}


def build_prompt(
    initial_context: str,
    history: list[str],
    outcome_tier: int,
    outcome_directions: dict[int, Union[str, list[str]]] | None = None,
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

    raw = outcome_directions if outcome_directions is not None else OUTCOME_DIRECTIONS
    directions = _normalize_directions(raw)
    direction = random.choice(directions.get(outcome_tier, directions[2]))
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


_SANITIZE_REPLACEMENTS: dict[str, str] = {
    "\u0153": "oe",
    "\u0152": "OE",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u2013": "-",
    "\u2014": "-",
    "\u2022": "*",
    "\u00b7": "*",
    "\u2026": "...",
}


THINKING_PATTERNS = [
    (r'<thinking>.*?</thinking>', re.DOTALL),
    (r'<reasoning>.*?</reasoning>', re.DOTALL),
    (r'\[thinking\].*?\[/thinking\]', re.DOTALL),
    (r'\[reasoning\].*?\[/reasoning\]', re.DOTALL),
]


def strip_thinking(raw: str) -> str:
    for pattern, flags in THINKING_PATTERNS:
        raw = re.sub(pattern, '', raw, flags=flags)
    return raw.strip()


def sanitize_text(text: str) -> str:
    result: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0x20 <= cp <= 0x7E or ch in {"\n", "\t"}:
            result.append(ch)
        elif ch in _SANITIZE_REPLACEMENTS:
            result.append(_SANITIZE_REPLACEMENTS[ch])
        elif 0x00A0 <= cp <= 0x00FF:
            result.append(ch)
        elif 0x0100 <= cp <= 0x017F:
            result.append(ch)
        else:
            for subch in unicodedata.normalize("NFKD", ch):
                subcp = ord(subch)
                if 0x20 <= subcp <= 0x7E or subch in {"\n", "\t"}:
                    result.append(subch)
    return "".join(result)


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

    raw = re.sub(r'\n+', ' ', raw)

    return raw.strip()
