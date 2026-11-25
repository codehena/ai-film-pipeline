import wave

import pytest

from pipeline import asr_check, narration
from pipeline.common import MissingInput
from pipeline.common.runlog import read_log


def tone(path, seconds=1.0):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(b"\x01\x00" * int(seconds * 24000))


@pytest.fixture
def voiced(board, tmp_path):
    for i, s in enumerate(board["shots"]):
        s["narration"]["text"] = f"ቃል {i}"
    narration.run(board, synthesize=lambda out_path, **kw: tone(out_path),
                  out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    return board


def test_every_segment_is_transcribed_once_then_cached(voiced, tmp_path):
    calls = []
    fake = lambda model, path: calls.append(path) or "heard words"
    rows = asr_check.run(voiced, transcribe=fake, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    assert len(rows) == len(voiced["shots"]) == len(calls)
    asr_check.run(voiced, transcribe=fake, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    assert len(calls) == len(voiced["shots"])               # cached by segment file hash
    assert sum(1 for r in read_log(tmp_path / "runs.jsonl") if r["stage"] == "qa") == len(calls)


def test_similarity_ignores_punctuation_and_spaces():
    assert asr_check.similarity("ቡና የሌለው ቤት፣ ባዶ ነው።", "ቡና የሌለው ቤት ባዶ ነው") == 1.0
    assert asr_check.similarity("ከብቶች ወደ መስክ", "አንዳንዴም ይናፍቀኛል") < 0.4


def test_missing_narration_is_a_clear_error(board, tmp_path):
    board["shots"][0]["narration"]["text"] = "ቃል"
    with pytest.raises(MissingInput):
        asr_check.run(board, transcribe=lambda m, p: "", out_base=tmp_path)


def test_finished_lines_survive_a_quota_error(voiced, tmp_path):
    from pipeline.common.retry import PermanentError
    calls = []

    def flaky(model, path):
        calls.append(path)
        if len(calls) == 3:
            raise PermanentError("429 per day limit")
        return "heard"

    with pytest.raises(PermanentError):
        asr_check.run(voiced, transcribe=flaky, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    done = []
    asr_check.run(voiced, transcribe=lambda m, p: done.append(p) or "heard",
                  out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    assert len(done) == len(voiced["shots"]) - 2   # the 2 finished lines were kept
