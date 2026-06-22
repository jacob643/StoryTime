from __future__ import annotations

import math
from dataclasses import dataclass, field

from backend.logger import logger

TARGET_SPLIT_SIZE = 50
MIN_SPLIT_SIZE = 30
MAX_ROLLING_WINDOW = 50

OUTCOME_LABELS: list[str] = [
    "very negative",
    "negative",
    "neutral",
    "positive",
    "very positive",
]

FIXED_THRESHOLDS: list[float] = [300, 350, 400, 450]

DEFAULT_AVG_CPM = 300.0
DEFAULT_MIN_STDDEV_CPM = 10.0


@dataclass
class ScoringParams:
    mode: str = "split"
    min_stddev_cpm: float = DEFAULT_MIN_STDDEV_CPM
    tier_0_max_sigma: float = -1.5
    tier_1_max_sigma: float = -0.5
    tier_2_max_sigma: float = 0.5
    tier_3_max_sigma: float = 1.5
    fixed_thresholds: list[float] | None = None


def split_text(text: str, target: int = TARGET_SPLIT_SIZE, minimum: int = MIN_SPLIT_SIZE) -> list[str]:
    if not text:
        return []
    if len(text) <= target:
        return [text]

    splits: list[str] = []
    pos = 0
    while len(text) - pos >= target + minimum:
        splits.append(text[pos:pos + target])
        pos += target
    remaining = len(text) - pos
    if remaining >= minimum:
        splits.append(text[pos:])
    else:
        splits[-1] += text[pos:]
    logger.debug("split_text: text_len=%d target=%d -> %d splits of lengths %s",
                 len(text), target, len(splits), [len(s) for s in splits])
    return splits


def compute_speed_stats(speeds: list[float], min_stddev: float = DEFAULT_MIN_STDDEV_CPM) -> tuple[float, float]:
    if not speeds:
        return (DEFAULT_AVG_CPM, min_stddev)
    mean = sum(speeds) / len(speeds)
    if len(speeds) < 2:
        return (mean, min_stddev)
    variance = sum((s - mean) ** 2 for s in speeds) / (len(speeds) - 1)
    stddev = max(math.sqrt(variance), min_stddev)
    return (mean, stddev)


def compute_outcome_tier(
    speed_cpm: float,
    *,
    avg: float | None = None,
    stddev: float | None = None,
    params: ScoringParams | None = None,
) -> int:
    if speed_cpm < 0:
        return 0

    p = params or ScoringParams()

    thresholds = p.fixed_thresholds if p.mode == "fixed" else None
    if thresholds is None and (avg is None or stddev is None):
        thresholds = FIXED_THRESHOLDS
    if thresholds is not None:
        for tier, bound in enumerate(thresholds):
            if speed_cpm < bound:
                return tier
        return 4

    diff = speed_cpm - avg
    z = diff / stddev

    if z < p.tier_0_max_sigma:
        return 0
    if z < p.tier_1_max_sigma:
        return 1
    if z <= p.tier_2_max_sigma:
        return 2
    if z <= p.tier_3_max_sigma:
        return 3
    return 4


def compute_tier_boundaries(
    avg: float | None = None,
    stddev: float | None = None,
    params: ScoringParams | None = None,
) -> list[float]:
    p = params or ScoringParams()
    if p.mode == "fixed":
        thresholds = p.fixed_thresholds or FIXED_THRESHOLDS
        return [round(b) for b in thresholds]
    if avg is None or stddev is None:
        return [round(b) for b in FIXED_THRESHOLDS]
    return [
        max(0, round(avg + p.tier_0_max_sigma * stddev)),
        max(0, round(avg + p.tier_1_max_sigma * stddev)),
        max(0, round(avg + p.tier_2_max_sigma * stddev)),
        max(0, round(avg + p.tier_3_max_sigma * stddev)),
    ]


def get_outcome_label(tier: int) -> str:
    if 0 <= tier < len(OUTCOME_LABELS):
        return OUTCOME_LABELS[tier]
    return OUTCOME_LABELS[2]
