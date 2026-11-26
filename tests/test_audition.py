import wave
from pathlib import Path

from pipeline import audition
from pipeline.common.retry import PermanentError
from pipeline.common.runlog import read_log


def fake_tts(calls, bad=()):
    def synthesize(*, voice_name, text, style, out_path, **kw):
        calls.append((voice_name, text, style))
        if voice_name in bad:
            raise PermanentError(f"400 unknown voice {voice_name}")
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
            w.writeframes(b"\x01\x00" * 24000)
    return synthesize


def run(board, tmp_path, voices, tts):
    board["shots"][0]["narration"]["text"] = "opening line"
    return audition.run(board, "s01", voices, synthesize=tts,
                        out_base=tmp_path, log_path=tmp_path / "runs.jsonl")


def test_one_take_per_voice_same_text_and_style(board, tmp_path):
    calls = []
    results = run(board, tmp_path, ["A", "B", "C"], fake_tts(calls))
    assert all(isinstance(p, Path) and p.exists() for p in results.values())
    assert {c[0] for c in calls} == {"A", "B", "C"}
    assert len({(c[1], c[2]) for c in calls}) == 1   # only the voice varies
    assert len({p.name for p in results.values()}) == 3


def test_rerun_is_cached(board, tmp_path):
    calls = []
    run(board, tmp_path, ["A", "B"], fake_tts(calls))
    run(board, tmp_path, ["A", "B"], fake_tts(calls))
    assert len(calls) == 2
    assert [r["status"] for r in read_log(tmp_path / "runs.jsonl")].count("cache_hit") == 2


def test_bad_voice_does_not_stop_the_others(board, tmp_path):
    calls = []
    results = run(board, tmp_path, ["A", "Nope", "C"], fake_tts(calls, bad={"Nope"}))
    assert isinstance(results["Nope"], PermanentError)
    assert isinstance(results["A"], Path) and isinstance(results["C"], Path)


def test_audition_does_not_change_the_storyboard(board, tmp_path):
    before = board["voice"]["voice_name"]
    run(board, tmp_path, ["A"], fake_tts([]))
    assert board["voice"]["voice_name"] == before
