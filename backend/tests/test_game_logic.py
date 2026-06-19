import pytest

from backend.game_logic import (
    ScoringParams,
    compute_outcome_tier,
    compute_speed_stats,
    get_outcome_label,
    split_text,
)


# ── split_text ──────────────────────────────────────────────────────────

class TestSplitText:
    def test_empty_text(self):
        assert split_text("") == []

    def test_shorter_than_target(self):
        assert split_text("hello") == ["hello"]

    def test_exactly_target(self):
        assert split_text("a" * 50) == ["a" * 50]

    def test_two_full_splits(self):
        text = "a" * 100
        result = split_text(text)
        assert result == ["a" * 50, "a" * 50]

    def test_merge_small_last_split_into_previous(self):
        text = "a" * 120  # 50 + 50 + 20 → last 20 < 30 → merge
        result = split_text(text)
        assert len(result) == 2
        assert result[-1] == "a" * 70

    def test_keep_last_split_when_above_minimum(self):
        text = "a" * 130  # 50 + 50 + 30
        result = split_text(text)
        assert len(result) == 3
        assert result[-1] == "a" * 30

    def test_complex_301_chars(self):
        text = "a" * 301
        result = split_text(text)
        assert len(result) >= 6
        assert all(len(s) >= 30 for s in result)

    def test_single_char_text(self):
        assert split_text("x") == ["x"]


# ── compute_speed_stats ─────────────────────────────────────────────────

class TestComputeSpeedStats:
    def test_empty_list_returns_defaults(self):
        avg, std = compute_speed_stats([])
        assert avg == 300.0
        assert std == 10.0

    def test_single_value(self):
        avg, std = compute_speed_stats([350.0])
        assert avg == 350.0
        assert std == 10.0

    def test_two_values(self):
        avg, std = compute_speed_stats([300.0, 320.0])
        assert avg == 310.0
        assert std > 0

    def test_stddev_floored_to_min(self):
        avg, std = compute_speed_stats([300.0, 301.0])
        assert avg == 300.5
        assert std == 10.0

    def test_stddev_above_min(self):
        avg, std = compute_speed_stats([200.0, 400.0])
        assert avg == 300.0
        assert std > 10.0


# ── compute_outcome_tier (fixed fallback) ───────────────────────────────

class TestComputeOutcomeTierFixed:
    def test_tier_0_below_30(self):
        assert compute_outcome_tier(0) == 0
        assert compute_outcome_tier(15) == 0
        assert compute_outcome_tier(29.9) == 0

    def test_tier_1_30_to_50(self):
        assert compute_outcome_tier(30) == 1
        assert compute_outcome_tier(40) == 1
        assert compute_outcome_tier(49.9) == 1

    def test_tier_2_50_to_75(self):
        assert compute_outcome_tier(50) == 2
        assert compute_outcome_tier(62.5) == 2
        assert compute_outcome_tier(74.9) == 2

    def test_tier_3_75_to_100(self):
        assert compute_outcome_tier(75) == 3
        assert compute_outcome_tier(88) == 3
        assert compute_outcome_tier(99.9) == 3

    def test_tier_4_100_and_above(self):
        assert compute_outcome_tier(100) == 4
        assert compute_outcome_tier(150) == 4
        assert compute_outcome_tier(1e6) == 4

    def test_negative_speed_returns_tier_0(self):
        assert compute_outcome_tier(-5) == 0


# ── compute_outcome_tier (adaptive mode) ────────────────────────────────

class TestComputeOutcomeTierAdaptive:
    def test_at_exact_average_is_tier_2(self):
        assert compute_outcome_tier(300, avg=300, stddev=10) == 2

    def test_slightly_below_average_is_tier_2(self):
        assert compute_outcome_tier(295, avg=300, stddev=10) == 2

    def test_slightly_above_average_is_tier_2(self):
        assert compute_outcome_tier(305, avg=300, stddev=10) == 2

    def test_below_tier_1_boundary_is_tier_1(self):
        assert compute_outcome_tier(294, avg=300, stddev=10) == 1

    def test_above_tier_3_boundary_is_tier_3(self):
        assert compute_outcome_tier(306, avg=300, stddev=10) == 3

    def test_far_below_is_tier_0(self):
        assert compute_outcome_tier(284, avg=300, stddev=10) == 0

    def test_far_above_is_tier_4(self):
        assert compute_outcome_tier(316, avg=300, stddev=10) == 4

    def test_at_exact_boundary_tier_0_1(self):
        assert compute_outcome_tier(284, avg=300, stddev=10) == 0
        assert compute_outcome_tier(285, avg=300, stddev=10) == 1

    def test_stddev_floor_applies(self):
        assert compute_outcome_tier(305, avg=300, stddev=1) == 2

    def test_negative_speed_fixed_still_tier_0(self):
        assert compute_outcome_tier(-5, avg=300, stddev=50) == 0


# ── get_outcome_label ───────────────────────────────────────────────────

class TestGetOutcomeLabel:
    def test_all_tiers_have_labels(self):
        expected = ["very negative", "negative", "neutral", "positive", "very positive"]
        for tier, label in enumerate(expected):
            assert get_outcome_label(tier) == label

    def test_out_of_range_returns_neutral(self):
        assert get_outcome_label(-1) == "neutral"
        assert get_outcome_label(99) == "neutral"
