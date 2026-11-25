"""Narration stage with a fake TTS function: proves caching per shot, offline and free."""
import wave

import pytest

from pipeline import narration
from pipeline.common.runlog import read_log


def write_tone(path, seconds=1.0, rate=24000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\x01\x00" * int(seconds * rate))


@pytest.fixture
def spoken_board(board):
    for i, s in enumerate(board["shots"]):
        s["narration"]["text"] = f"line {i + 1}"
    return board


@pytest.fixture
def fake_tts():
    calls = []

    def synthesize(*, text, out_path, style, **kw):
        calls.append({"text": text, "style": style})
        write_tone(out_path)
        return {}
    synthesize.calls = calls
    return synthesize


def run(board, tmp_path, tts, only=None):
    return narration.run(board, only, synthesize=tts, out_base=tmp_path / "out",
                         log_path=tmp_path / "runs.jsonl")


def test_first_run_generates_every_line_second_run_none(spoken_board, tmp_path, fake_tts):
    first = run(spoken_board, tmp_path, fake_tts)
    assert len(first) == 8 and len(fake_tts.calls) == 8
    run(spoken_board, tmp_path, fake_tts)
    assert len(fake_tts.calls) == 8  # nothing new
    statuses = [r["status"] for r in read_log(tmp_path / "runs.jsonl")]
    assert statuses.count("ok") == 8 and statuses.count("cache_hit") == 8


def test_editing_one_line_regenerates_only_that_shot(spoken_board, tmp_path, fake_tts):
    run(spoken_board, tmp_path, fake_tts)
    spoken_board["shots"][2]["narration"]["text"] = "a better line 3"
    run(spoken_board, tmp_path, fake_tts)
    assert len(fake_tts.calls) == 9 and fake_tts.calls[-1]["text"] == "a better line 3"


def test_pause_change_costs_no_tts_call(spoken_board, tmp_path, fake_tts):
    run(spoken_board, tmp_path, fake_tts)
    spoken_board["shots"][0]["narration"]["speech_metadata"]["pause_before_s"] = 1.5
    run(spoken_board, tmp_path, fake_tts)
    assert len(fake_tts.calls) == 8


def test_style_reaches_tts_separately_from_text(spoken_board, tmp_path, fake_tts):
    spoken_board["shots"][0]["narration"]["speech_metadata"]["style"] = "hushed"
    run(spoken_board, tmp_path, fake_tts, only=["s01"])
    assert fake_tts.calls == [{"text": "line 1", "style": "hushed"}]


def test_todo_and_silent_lines_are_skipped(board, tmp_path, fake_tts):
    board["shots"][0]["narration"]["text"] = "real line"
    board["shots"][1]["narration"]["text"] = ""
    done = run(board, tmp_path, fake_tts)
    assert list(done) == ["s01"] and len(fake_tts.calls) == 1


def paragraph_reader(calls, seconds_per_word=0.4, gap=1.0):
    """Fake continuous TTS: one tone burst per paragraph, `gap` seconds of silence between."""
    import math
    from array import array

    def synthesize(*, text, out_path, **kw):
        calls.append(text)
        rate, samples = 24000, array("h")
        samples.extend(bytes(2 * int(0.3 * rate)))
        for i, para in enumerate(text.split("\n\n")):
            if i:
                samples.extend(array("h", bytes(2 * int(gap * rate))))
            n = int(len(para.split()) * seconds_per_word * rate)
            samples.extend(array("h", (int(5000 * math.sin(2 * math.pi * 200 * k / rate))
                                       for k in range(n))))
        samples.extend(array("h", bytes(2 * int(0.5 * rate))))
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes(samples.tobytes())
    return synthesize


@pytest.fixture
def continuous_board(board):
    board["voice"]["mode"] = "continuous"
    for i, s in enumerate(board["shots"]):
        s["narration"]["text"] = " ".join(["word"] * (3 + i))   # 3..10 words
    return board


def test_continuous_mode_is_one_call_split_into_every_line(continuous_board, tmp_path):
    calls = []
    done = narration.run(continuous_board, synthesize=paragraph_reader(calls),
                         out_base=tmp_path / "out", log_path=tmp_path / "runs.jsonl")
    assert len(calls) == 1 and calls[0].count("\n\n") == 7
    assert list(done) == [s["id"] for s in continuous_board["shots"]]
    for i, (sid, path) in enumerate(done.items()):
        assert narration.wav_duration(path) == pytest.approx((3 + i) * 0.4, abs=0.05)
        assert narration.audio_path(continuous_board, continuous_board["shots"][i],
                                    tmp_path / "out") == path


def test_continuous_rerun_is_free_and_any_edit_is_one_call(continuous_board, tmp_path):
    calls = []
    kw = dict(synthesize=paragraph_reader(calls), out_base=tmp_path / "out",
              log_path=tmp_path / "runs.jsonl")
    narration.run(continuous_board, **kw)
    narration.run(continuous_board, **kw)
    assert len(calls) == 1
    continuous_board["shots"][3]["narration"]["text"] = "a new line here"
    narration.run(continuous_board, **kw)
    assert len(calls) == 2
    statuses = [r["status"] for r in read_log(tmp_path / "runs.jsonl")]
    assert statuses == ["ok", "cache_hit", "ok"]


def test_continuous_pause_change_costs_nothing(continuous_board, tmp_path):
    calls = []
    kw = dict(synthesize=paragraph_reader(calls), out_base=tmp_path / "out",
              log_path=tmp_path / "runs.jsonl")
    narration.run(continuous_board, **kw)
    continuous_board["shots"][0]["narration"]["speech_metadata"]["pause_before_s"] = 2.0
    narration.run(continuous_board, **kw)
    assert len(calls) == 1


def test_audio_path_matches_what_was_written(spoken_board, tmp_path, fake_tts):
    done = run(spoken_board, tmp_path, fake_tts)
    shot = spoken_board["shots"][4]
    assert narration.audio_path(spoken_board, shot, tmp_path / "out") == done[shot["id"]]
