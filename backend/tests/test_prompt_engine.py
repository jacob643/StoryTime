from backend.prompt_engine import build_prompt, build_first_paragraph_prompt, parse_llm_response, validate_llm_response, OUTCOME_DIRECTIONS, NEUTRAL_FALLBACK


class TestBuildPrompt:
    def test_no_history_tier_2(self):
        result = build_prompt(
            initial_context="A lone detective in a rainy city.",
            history=[],
            outcome_tier=2,
        )
        assert "A lone detective in a rainy city." in result
        assert OUTCOME_DIRECTIONS[2] in result
        assert "Write only a single paragraph" in result
        assert "So far" not in result

    def test_with_history(self):
        result = build_prompt(
            initial_context="A fantasy world.",
            history=["The hero entered the cave.", "A dragon appeared."],
            outcome_tier=4,
        )
        assert "The hero entered the cave." in result
        assert "A dragon appeared." in result
        assert OUTCOME_DIRECTIONS[4] in result

    def test_all_tiers_produce_different_directions(self):
        results = {}
        for tier in range(5):
            results[tier] = build_prompt("Test.", [], outcome_tier=tier)
        for tier in range(5):
            assert OUTCOME_DIRECTIONS[tier] in results[tier]

    def test_outcome_tier_out_of_range_defaults_to_tier_2(self):
        result = build_prompt("Test.", [], outcome_tier=99)
        assert OUTCOME_DIRECTIONS[2] in result

    def test_negative_tier_defaults_to_tier_2(self):
        result = build_prompt("Test.", [], outcome_tier=-1)
        assert OUTCOME_DIRECTIONS[2] in result


class TestParseLlmResponse:
    def test_strips_quotes(self):
        assert parse_llm_response('"Hello world."') == "Hello world."

    def test_strips_next_paragraph_prefix(self):
        raw = "Here's the next paragraph: The hero ran."
        assert parse_llm_response(raw) == "The hero ran."

    def test_strips_alt_prefix(self):
        raw = "Next paragraph: The end."
        assert parse_llm_response(raw) == "The end."

    def test_adds_period_if_missing(self):
        assert parse_llm_response("Hello world") == "Hello world."

    def test_preserves_exclamation_and_question_mark(self):
        assert parse_llm_response("Run!") == "Run!"
        assert parse_llm_response("Really?") == "Really?"

    def test_empty_string(self):
        assert parse_llm_response("") == ""

    def test_whitespace_only(self):
        assert parse_llm_response("   ") == ""

    def test_strip_prefix_with_quotes(self):
        raw = 'Here is the next paragraph: "Into the void."'
        assert parse_llm_response(raw) == 'Into the void.'


class TestBuildFirstParagraphPrompt:
    def test_wraps_user_input(self):
        result = build_first_paragraph_prompt("a cat who solves mysteries")
        assert "a cat who solves mysteries" in result
        assert result.startswith("Write the first paragraph of a story about:")
        assert "200 characters" in result
        assert "nothing else" in result

    def test_custom_max_chars(self):
        result = build_first_paragraph_prompt("test", max_chars=150)
        assert "150 characters" in result


class TestValidateLlmResponse:
    def test_valid_response(self):
        assert validate_llm_response("The hero advanced through the dark forest.") is True

    def test_empty_string(self):
        assert validate_llm_response("") is False

    def test_whitespace_only(self):
        assert validate_llm_response("   ") is False

    def test_too_short(self):
        assert validate_llm_response("Hi.") is False

    def test_missing_punctuation(self):
        assert validate_llm_response("The hero advanced") is False

    def test_exclamation_valid(self):
        assert validate_llm_response("Run for your life!") is True

    def test_question_valid(self):
        assert validate_llm_response("What was that?") is True

    def test_neutral_fallback_is_valid(self):
        assert validate_llm_response(NEUTRAL_FALLBACK) is True
