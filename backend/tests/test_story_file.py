from datetime import datetime
from pathlib import Path

import pytest

from backend import story_file
from backend.story_file import (
    InvalidStoryFormat,
    InvalidStoryId,
    append_paragraph,
    complete_current,
    create_story,
    list_stories,
    load_story,
    parse_story_file,
    stories_dir,
    story_path,
)


@pytest.fixture(autouse=True)
def stories_tmp_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    story_file.clear_cache()
    yield tmp_path
    story_file.clear_cache()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestCreateAndLoad:
    def test_create_writes_expected_format(self):
        story = create_story("a bar of soap", "The soap was old.")
        path = stories_dir() / f"{story.story_id}.txt"

        assert story.story_id.startswith("a_bar_of_soap_")
        assert story.current == "The soap was old."
        assert story.paragraphs == []
        assert path.read_text(encoding="utf-8") == (
            "Premise: a bar of soap\n\nThe soap was old.\n"
        )

    def test_load_round_trip(self):
        created = create_story("a bar of soap", "The soap was old.")
        loaded = load_story(created.story_id)

        assert loaded is not None
        assert loaded.story_id == created.story_id
        assert loaded.premise == "a bar of soap"
        assert loaded.current == "The soap was old."
        assert loaded.paragraphs == []

    def test_premise_is_stored_verbatim_and_single_line(self):
        story = create_story("  A hero\nwith a dream  ", "Opening line.")
        loaded = load_story(story.story_id)
        assert loaded.premise == "A hero with a dream"

    def test_empty_premise_falls_back_to_untitled(self):
        story = create_story("   ", "Opening line.")
        assert story.premise == "untitled"

    def test_multiline_opening_is_flattened(self):
        story = create_story("premise", "line one\nline two")
        assert story.current == "line one line two"


class TestCompletion:
    def test_complete_current_appends_metadata_underneath(self):
        story = create_story("premise", "First paragraph.")
        completed_at = datetime(2026, 10, 29, 12, 46, 10)
        record = complete_current(story, 312.4, 1, completed_at=completed_at)

        assert record.text == "First paragraph."
        assert story.current is None
        assert len(story.paragraphs) == 1

        content = story.path.read_text(encoding="utf-8")
        assert content == (
            "Premise: premise\n\n"
            "First paragraph.\n"
            "Date: 2026-10-29 12:46:10\n"
            "Speed: 312.4 CPM | Tier: 1 (negative)\n"
        )

    def test_append_paragraph_after_completion(self):
        story = create_story("premise", "First paragraph.")
        complete_current(story, 312.4, 1, completed_at=datetime(2026, 10, 29, 12, 46, 10))
        append_paragraph(story, "Second paragraph.")

        assert story.current == "Second paragraph."
        assert story.path.read_text(encoding="utf-8") == (
            "Premise: premise\n\n"
            "First paragraph.\n"
            "Date: 2026-10-29 12:46:10\n"
            "Speed: 312.4 CPM | Tier: 1 (negative)\n"
            "\nSecond paragraph.\n"
        )

        loaded = load_story(story.story_id)
        assert loaded is not None
        assert loaded.current == "Second paragraph."
        assert len(loaded.paragraphs) == 1
        assert loaded.paragraphs[0].speed_cpm == 312.4
        assert loaded.paragraphs[0].outcome_tier == 1

    def test_complete_twice_raises(self):
        story = create_story("premise", "First.")
        complete_current(story, 300, 2)
        with pytest.raises(ValueError):
            complete_current(story, 300, 2)

    def test_append_twice_raises(self):
        story = create_story("premise", "First.")
        with pytest.raises(ValueError):
            append_paragraph(story, "Second.")

    def test_metadata_like_paragraph_is_escaped(self):
        tricky = "Date: 2026-10-29 12:46:10"
        story = create_story("premise", tricky)
        complete_current(story, 100, 2)
        append_paragraph(story, "Speed: 300 CPM | Tier: 4 (very positive)")

        loaded = load_story(story.story_id)
        assert loaded is not None
        assert loaded.paragraphs[0].text == tricky
        assert loaded.current == "Speed: 300 CPM | Tier: 4 (very positive)"


class TestParsing:
    def test_last_unwritten_paragraph_is_current(self):
        path = _write(
            stories_dir() / "story_12345678.txt",
            "Premise: test\n\n"
            "First.\nDate: 2026-10-29 12:46:10\nSpeed: 300.0 CPM | Tier: 2 (neutral)\n\n"
            "Second unwritten.\n",
        )
        story = parse_story_file(path)
        assert len(story.paragraphs) == 1
        assert story.current == "Second unwritten."

    def test_last_completed_paragraph_has_no_current(self):
        path = _write(
            stories_dir() / "story_12345678.txt",
            "Premise: test\n\n"
            "First.\nDate: 2026-10-29 12:46:10\nSpeed: 300.0 CPM | Tier: 2 (neutral)\n",
        )
        story = parse_story_file(path)
        assert len(story.paragraphs) == 1
        assert story.current is None

    def test_blank_lines_are_ignored(self):
        path = _write(
            stories_dir() / "story_12345678.txt",
            "\n\nPremise: test\n\n\nFirst.\n\n\n"
            "Date: 2026-10-29 12:46:10\nSpeed: 300.0 CPM | Tier: 2 (neutral)\n\n\n",
        )
        story = parse_story_file(path)
        assert len(story.paragraphs) == 1

    def test_partial_metadata_fills_defaults(self):
        path = _write(
            stories_dir() / "story_12345678.txt",
            "Premise: test\n\nFirst.\nDate: 2026-10-29 12:46:10\n",
        )
        story = parse_story_file(path)
        assert story.paragraphs[0].speed_cpm == 0.0
        assert story.paragraphs[0].outcome_tier == 2

    def test_non_final_uncompleted_paragraph_is_recovered(self):
        path = _write(
            stories_dir() / "story_12345678.txt",
            "Premise: test\n\nFirst.\nSecond.\n"
            "Date: 2026-10-29 12:46:10\nSpeed: 300.0 CPM | Tier: 2 (neutral)\n",
        )
        story = parse_story_file(path)
        assert [p.text for p in story.paragraphs] == ["First.", "Second."]
        assert story.paragraphs[0].outcome_tier == 2
        assert story.current is None

    def test_missing_premise_header_is_invalid(self):
        path = _write(stories_dir() / "story_12345678.txt", "First.\n")
        with pytest.raises(InvalidStoryFormat):
            parse_story_file(path)

    def test_empty_file_is_invalid(self):
        path = _write(stories_dir() / "story_12345678.txt", "\n\n")
        with pytest.raises(InvalidStoryFormat):
            parse_story_file(path)

    def test_metadata_before_paragraph_is_invalid(self):
        path = _write(
            stories_dir() / "story_12345678.txt",
            "Premise: test\nDate: 2026-10-29 12:46:10\n",
        )
        with pytest.raises(InvalidStoryFormat):
            parse_story_file(path)

    def test_empty_premise_is_invalid(self):
        path = _write(stories_dir() / "story_12345678.txt", "Premise:   \n\nFirst.\n")
        with pytest.raises(InvalidStoryFormat):
            parse_story_file(path)

    def test_no_paragraphs_is_invalid(self):
        path = _write(stories_dir() / "story_12345678.txt", "Premise: test\n\n")
        with pytest.raises(InvalidStoryFormat):
            parse_story_file(path)

    def test_old_format_is_ignored_by_listing(self, stories_tmp_dir):
        directory = stories_dir()
        directory.mkdir(parents=True, exist_ok=True)
        _write(directory / "old_style_deadbeef.txt", "\n--- Paragraph 1 ---\nDate: x\n\nOld text\n")
        create_story("new story", "New text.")

        summaries = list_stories()
        assert len(summaries) == 1
        assert summaries[0].premise == "new story"

    def test_invalid_story_load_raises(self):
        stories_dir().mkdir(parents=True, exist_ok=True)
        _write(stories_dir() / "bad_deadbeef.txt", "not a story\n")
        with pytest.raises(InvalidStoryFormat):
            load_story("bad_deadbeef")


class TestListing:
    def test_summaries_and_sorting(self):
        first = create_story("first story", "One.")
        complete_current(first, 300, 2)
        second = create_story("second story", "Two.")

        summaries = list_stories()
        assert [s.premise for s in summaries] == ["second story", "first story"]

        by_id = {s.story_id: s for s in summaries}
        assert by_id[first.story_id].paragraph_count == 1
        assert by_id[first.story_id].has_current is False
        assert by_id[first.story_id].last_speed_cpm == 300.0
        assert by_id[first.story_id].last_outcome_tier == 2
        assert by_id[second.story_id].paragraph_count == 0
        assert by_id[second.story_id].has_current is True
        assert by_id[second.story_id].last_speed_cpm is None

    def test_listing_cache_invalidates_after_write(self):
        story = create_story("cached story", "One.")
        assert list_stories()[0].paragraph_count == 0

        complete_current(story, 300, 2)
        assert list_stories()[0].paragraph_count == 1
        assert list_stories()[0].has_current is False

    def test_missing_directory_returns_empty(self):
        assert list_stories() == []


class TestValidation:
    @pytest.mark.parametrize(
        "story_id",
        ["../escape", "a/b", "a\\b", "", "UPPER", "has space", "x" * 130],
    )
    def test_invalid_story_ids_rejected(self, story_id):
        with pytest.raises(InvalidStoryId):
            story_path(story_id)

    def test_valid_story_id_accepted(self):
        path = story_path("a_bar_of_soap_e2dfb6f5")
        assert path.name == "a_bar_of_soap_e2dfb6f5.txt"
