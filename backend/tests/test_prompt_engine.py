from backend.prompt_engine import (
    build_prompt,
    build_first_paragraph_prompt,
    parse_llm_response,
    sanitize_text,
    strip_thinking,
    validate_llm_response,
    OUTCOME_DIRECTIONS,
    NEUTRAL_FALLBACK,
)


def _has_tier_phrasing(result: str, tier: int) -> bool:
    return any(p in result for p in OUTCOME_DIRECTIONS[tier])


class TestBuildPrompt:
    def test_no_history_tier_2(self):
        result = build_prompt(
            initial_context="A lone detective in a rainy city.",
            history=[],
            outcome_tier=2,
        )
        assert "A lone detective in a rainy city." in result
        assert _has_tier_phrasing(result, 2)
        assert "exactly 80 words long" in result
        assert "So far" not in result

    def test_with_history(self):
        result = build_prompt(
            initial_context="A fantasy world.",
            history=["The hero entered the cave.", "A dragon appeared."],
            outcome_tier=4,
        )
        assert "The hero entered the cave." in result
        assert "A dragon appeared." in result
        assert _has_tier_phrasing(result, 4)

    def test_all_tiers_produce_different_directions(self):
        results = {}
        for tier in range(5):
            results[tier] = build_prompt("Test.", [], outcome_tier=tier)
        for tier in range(5):
            assert _has_tier_phrasing(results[tier], tier), f"tier {tier} missing"

    def test_outcome_tier_out_of_range_defaults_to_tier_2(self):
        result = build_prompt("Test.", [], outcome_tier=99)
        assert _has_tier_phrasing(result, 2)

    def test_negative_tier_defaults_to_tier_2(self):
        result = build_prompt("Test.", [], outcome_tier=-1)
        assert _has_tier_phrasing(result, 2)

    def test_custom_directions_list(self):
        custom = {2: ["custom direction two"]}
        result = build_prompt("Test.", [], outcome_tier=2, outcome_directions=custom)
        assert "custom direction two" in result

    def test_custom_directions_old_string_format(self):
        custom = {2: "old string direction"}
        result = build_prompt("Test.", [], outcome_tier=2, outcome_directions=custom)
        assert "old string direction" in result


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

    def test_collapses_newlines_to_space(self):
        assert parse_llm_response("hello\n\nworld") == "hello world."
        assert parse_llm_response("a\nb\nc") == "a b c."
        assert parse_llm_response("no newlines") == "no newlines."
        assert parse_llm_response("multi\n\n\npara") == "multi para."


class TestBuildFirstParagraphPrompt:
    def test_wraps_user_input(self):
        result = build_first_paragraph_prompt("a cat who solves mysteries")
        assert "a cat who solves mysteries" in result
        assert result.startswith("Write the first paragraph of a story about:")
        assert "80 words" in result
        assert "nothing else" in result

    def test_custom_max_words(self):
        result = build_first_paragraph_prompt("test", max_words=150)
        assert "150 words" in result


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


class TestSanitizeText:
    def test_accented_chars_kept(self):
        assert sanitize_text("São Paulo") == "São Paulo"
        assert sanitize_text("résumé") == "résumé"
        assert sanitize_text("jalapeño") == "jalapeño"
        assert sanitize_text("français") == "français"

    def test_untypeable_ligatures_replaced(self):
        assert sanitize_text("cœur") == "coeur"
        assert sanitize_text("\u0153uvre") == "oeuvre"

    def test_smart_quotes_to_straight(self):
        assert sanitize_text('\u201cHello\u201d') == '"Hello"'
        assert sanitize_text("\u2018world\u2019") == "'world'"

    def test_em_dash_to_hyphen(self):
        assert sanitize_text("wait\u2014what") == "wait-what"
        assert sanitize_text("oh\u2013really") == "oh-really"

    def test_control_chars_stripped(self):
        assert sanitize_text("hello\x00world\x01") == "helloworld"
        assert sanitize_text("line1\nline2") == "line1\nline2"

    def test_valid_ascii_unchanged(self):
        text = "The hero advanced through the dark forest."
        assert sanitize_text(text) == text

    def test_idempotent(self):
        input_text = "São Paulo, résumé, \u201chello\u201d"
        once = sanitize_text(input_text)
        twice = sanitize_text(once)
        assert once == twice

    def test_empty_string(self):
        assert sanitize_text("") == ""

    def test_round_trip_with_parse(self):
        raw = 'Here is the next paragraph: "São Paulo est belle."'
        parsed = parse_llm_response(raw)
        sanitized = sanitize_text(parsed)
        assert sanitized == "São Paulo est belle."

    def test_german_eszett_kept(self):
        assert sanitize_text("groß") == "groß"

    def test_danish_ae_kept(self):
        assert sanitize_text("Ærø") == "Ærø"


class TestStripThinking:
    def test_strips_thinking_tags(self):
        raw = "<thinking>I need to figure out what happens next.</thinking>The hero walked forward."
        assert strip_thinking(raw) == "The hero walked forward."

    def test_strips_reasoning_tags(self):
        raw = "<reasoning>Let me plan the story.</reasoning>It was a dark night."
        assert strip_thinking(raw) == "It was a dark night."

    def test_strips_bracket_thinking(self):
        raw = "[thinking]Step by step analysis[/thinking]The door creaked open."
        assert strip_thinking(raw) == "The door creaked open."

    def test_strips_bracket_reasoning(self):
        raw = "[reasoning]Consider alternatives[/reasoning]Rain began to fall."
        assert strip_thinking(raw) == "Rain began to fall."

    def test_no_thinking_content_passes_through(self):
        raw = "The sun rose over the horizon."
        assert strip_thinking(raw) == "The sun rose over the horizon."

    def test_multiple_thinking_blocks(self):
        raw = "<thinking>First thought</thinking>text<thinking>Second thought</thinking>more text"
        assert strip_thinking(raw) == "textmore text"

    def test_empty_input(self):
        assert strip_thinking("") == ""

    def test_only_thinking_content(self):
        raw = "<thinking>Just thinking about things</thinking>"
        assert strip_thinking(raw) == ""

    def test_nested_style_tags_preserved(self):
        raw = "<b>bold</b> and <i>italic</i> story text."
        assert strip_thinking(raw) == "<b>bold</b> and <i>italic</i> story text."
