from backend.game_logic import compute_outcome_tier, get_outcome_label


class TestComputeOutcomeTier:
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


class TestGetOutcomeLabel:
    def test_all_tiers_have_labels(self):
        expected = ["very negative", "negative", "neutral", "positive", "very positive"]
        for tier, label in enumerate(expected):
            assert get_outcome_label(tier) == label

    def test_out_of_range_returns_neutral(self):
        assert get_outcome_label(-1) == "neutral"
        assert get_outcome_label(99) == "neutral"
