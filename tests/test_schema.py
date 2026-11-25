import pytest

from pipeline.common.storyboard import (
    StoryboardError, film_duration, load_json, select_shots, validate,
)


def problems(board, schema):
    with pytest.raises(StoryboardError) as info:
        validate(board, schema)
    return "\n".join(info.value.problems)


def test_real_storyboard_is_valid(real_board, schema):
    validate(real_board, schema)
    assert 60 <= film_duration(real_board) <= 90


def test_fixture_storyboard_is_valid(board, schema):
    validate(board, schema)


def test_missing_field_is_reported(board, schema):
    del board["shots"][2]["image_prompt"]
    assert "shots[2]" in problems(board, schema)
    assert "image_prompt" in problems(board, schema)


def test_typo_in_field_name_is_rejected(board, schema):
    board["shots"][0]["imagePrompt"] = "oops"
    assert "imagePrompt" in problems(board, schema)


def test_too_few_shots(board, schema):
    board["shots"] = board["shots"][:5]
    assert "shots" in problems(board, schema)


def test_film_too_long(board, schema):
    for s in board["shots"]:
        s["duration_s"] = 15
    assert "between 60 and 90" in problems(board, schema)


def test_duplicate_shot_ids(board, schema):
    board["shots"][1]["id"] = board["shots"][0]["id"]
    assert "duplicate shot ids" in problems(board, schema)


def test_unknown_character(board, schema):
    board["shots"][0]["characters"] = ["nobody"]
    assert "'nobody' is not defined" in problems(board, schema)


def test_music_cue_past_end_of_film(board, schema):
    board["music_cues"][-1]["end_s"] = 500
    assert "ends at 500" in problems(board, schema)


def test_end_card_must_mention_ai(board, schema):
    board["end_card"]["text"] = "Thanks for watching"
    assert "end_card.text" in problems(board, schema)


def test_speech_metadata_rejects_unknown_cues(board, schema):
    board["shots"][0]["narration"]["speech_metadata"]["volume"] = 11
    assert "volume" in problems(board, schema)


def test_speech_metadata_is_optional(board, schema):
    del board["shots"][0]["narration"]["speech_metadata"]
    validate(board, schema)


def test_style_mode_must_be_known(board, schema):
    board["voice"]["style_mode"] = "telepathy"
    assert "style_mode" in problems(board, schema)


def test_todo_placeholders_are_warnings_not_errors(board, schema):
    warnings = validate(board, schema)
    assert any("title" in w for w in warnings)
    board_clean = {**board, "title": "Real title"}
    assert not any(w.startswith("title") for w in validate(board_clean, schema))


def test_broken_json_gives_line_number(tmp_path):
    bad = tmp_path / "storyboard.json"
    bad.write_text('{"title": "x",\n "shots": [}', encoding="utf-8")
    with pytest.raises(StoryboardError) as info:
        load_json(bad)
    assert "line 2" in str(info.value)


def test_select_shots(board):
    assert [s["id"] for s in select_shots(board, ["s03"])] == ["s03"]
    assert len(select_shots(board)) == len(board["shots"])
    with pytest.raises(StoryboardError):
        select_shots(board, ["s99"])


def test_still_from_must_name_another_existing_shot(board, schema):
    board["shots"][1]["video"]["still"] = {"from": "s01", "zoom": [1.2, 1.5]}
    validate(board, schema)
    board["shots"][1]["video"]["still"] = {"from": "s99"}
    assert "video.still.from 's99'" in problems(board, schema)
    board["shots"][1]["video"]["still"] = {"from": board["shots"][1]["id"]}
    assert "must be another existing shot" in problems(board, schema)


def test_focus_must_be_fractions(board, schema):
    board["shots"][0]["video"]["focus"] = [1.4, 0.5]
    assert "focus" in problems(board, schema)
