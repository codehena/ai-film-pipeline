import json

import pytest

from pipeline import retime
from pipeline.common.storyboard import StoryboardError, film_duration, load_json


def spoken(board):
    for i, s in enumerate(board["shots"]):
        s["narration"]["text"] = f"line {i}"
        s["narration"]["speech_metadata"] = {"pause_before_s": 0.3, "pause_after_s": 0.5}
    return board


LINE_S = 6.5        # 0.3 + 6.5 + 0.5 = 7.3 -> rounded up to 7.5; 8 shots -> 60 s + 3 s end card
EXPECTED_S = 7.5


def test_durations_follow_measured_lines(board):
    spoken(board)
    before = [s["duration_s"] for s in board["shots"]]
    new = retime.retimed(board, {s["id"]: LINE_S for s in board["shots"]})
    assert all(s["duration_s"] == EXPECTED_S for s in new["shots"])
    assert [s["duration_s"] for s in board["shots"]] == before   # input not mutated


def test_silent_shots_keep_their_duration(board):
    spoken(board)
    board["shots"][2]["narration"]["text"] = ""
    keep = board["shots"][2]["duration_s"]
    durations = {s["id"]: LINE_S for i, s in enumerate(board["shots"]) if i != 2}
    assert retime.retimed(board, durations)["shots"][2]["duration_s"] == keep


def test_music_cues_on_shot_boundaries_move_with_their_shot(board):
    spoken(board)
    starts = retime._shot_starts(board)
    board["music_cues"] = [
        {"id": "m1", "start_s": 0, "end_s": starts[5], "caption": "a"},
        {"id": "m2", "start_s": starts[5], "end_s": film_duration(board), "caption": "b"},
    ]
    new = retime.retimed(board, {s["id"]: LINE_S for s in board["shots"]})
    new_starts = retime._shot_starts(new)
    assert new["music_cues"][0]["end_s"] == new["music_cues"][1]["start_s"] == new_starts[5]
    assert new["music_cues"][1]["end_s"] == film_duration(new)


def test_refuses_a_film_longer_than_90_seconds(board):
    spoken(board)
    with pytest.raises(StoryboardError, match="between 60 and 90"):
        retime.retimed(board, {s["id"]: 12.0 for s in board["shots"]})


def test_run_writes_one_field_per_line(board, tmp_path, monkeypatch):
    spoken(board)
    monkeypatch.setattr(retime.narration, "audio_path", lambda b, s, o=None: tmp_path / "x.wav")
    monkeypatch.setattr(retime.narration, "wav_duration", lambda p: LINE_S)
    (tmp_path / "x.wav").write_bytes(b"x")
    out = tmp_path / "storyboard.json"
    retime.run(board, out)
    text = out.read_text(encoding="utf-8")
    assert '\n      "duration_s": 7.5,' in text
    assert load_json(out)["shots"][0]["duration_s"] == EXPECTED_S
    json.loads(text)
    assert b"\r\n" not in out.read_bytes()  # LF on every OS, as .gitattributes stores it
