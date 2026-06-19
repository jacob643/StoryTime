from __future__ import annotations

OUTCOME_THRESHOLDS: list[tuple[float, float]] = [
    (0, 30),
    (30, 50),
    (50, 75),
    (75, 100),
    (100, float("inf")),
]

OUTCOME_LABELS: list[str] = [
    "very negative",
    "negative",
    "neutral",
    "positive",
    "very positive",
]


def compute_outcome_tier(speed_cpm: float) -> int:
    if speed_cpm < 0:
        return 0
    for tier, (low, high) in enumerate(OUTCOME_THRESHOLDS):
        if low <= speed_cpm < high:
            return tier
    return 4


def get_outcome_label(tier: int) -> str:
    if 0 <= tier < len(OUTCOME_LABELS):
        return OUTCOME_LABELS[tier]
    return OUTCOME_LABELS[2]
