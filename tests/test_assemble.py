import json
import subprocess
import wave

import pytest

from pipeline import assemble, narration
from pipeline.common import MissingInput, config
from pipeline.common.runlog import read_log


def tone(path, seconds, rate=24000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\x10\x00" * int(seconds * rate))


def meta(board, i, **kw):
    board["shots"][i]["narration"]["speech_metadata"].update(kw)


def test_line_starts_after_pause_before(board):
    meta(board, 0, pause_before_s=0.5)
    lines, _ = assemble.plan_timeline(board, {"s01": 3.0})
    assert lines[0].start == 0.5 and lines[0].end == 3.5 and lines[0].overrun_s == 0


def test_long_line_reports_overrun_and_recommendation(board):
    slot = board["shots"][0]["duration_s"]            # 7 s in the placeholder
    meta(board, 0, pause_before_s=0.3, pause_after_s=0.5)
    lines, _ = assemble.plan_timeline(board, {"s01": slot + 1.0})
    assert lines[0].overrun_s == pytest.approx(1.8)
    assert lines[0].recommended_s == 9.0               # 0.3 + 8 + 0.5 = 8.8 -> 9.0


def test_overrunning_line_pushes_the_next_line_not_overlaps(board):
    lines, _ = assemble.plan_timeline(board, {"s01": 9.0, "s02": 2.0})
    assert lines[1].start >= lines[0].end + assemble.MIN_GAP_S


def test_total_includes_end_card_and_any_spill(board):
    planned = sum(s["duration_s"] for s in board["shots"]) + board["end_card"]["duration_s"]
    _, total = assemble.plan_timeline(board, {})
    assert total == planned
    last = board["shots"][-1]["id"]
    _, longer = assemble.plan_timeline(board, {last: 20.0})
    assert longer > planned


def test_srt_has_timed_cues_and_end_card(board):
    board["shots"][0]["narration"]["subtitle_en"] = "The road to the market"
    lines, total = assemble.plan_timeline(board, {"s01": 2.0})
    srt = assemble.build_srt(lines, board["end_card"], total)
    assert "00:00:00,300 --> 00:00:02,300\nThe road to the market" in srt
    last_cue = srt.strip().split("\n\n")[-1]
    assert " ".join(last_cue.splitlines()[2:]) == board["end_card"]["text"]


def test_subtitles_wrap_to_two_lines_without_losing_words():
    text = "word " * 30
    wrapped = assemble.wrap_subtitle(text.strip())
    assert len(wrapped.splitlines()) <= 2
    assert wrapped.split() == text.split()


def test_narration_track_places_audio_at_start_times(board, tmp_path):
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    tone(a, 1.0); tone(b, 1.0)
    lines, total = assemble.plan_timeline(board, {"s01": 1.0, "s02": 1.0})
    out = tmp_path / "track.wav"
    assemble.build_narration_track(lines, {"s01": a, "s02": b}, total, out)
    with wave.open(str(out)) as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(total, abs=0.01)
        w.setpos(int(lines[1].start * 24000) + 10)
        assert w.readframes(1) != b"\x00\x00"           # s02 audio is where planned


def test_mixed_audio_formats_are_refused(board, tmp_path):
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    tone(a, 1.0, rate=24000); tone(b, 1.0, rate=16000)
    lines, total = assemble.plan_timeline(board, {"s01": 1.0, "s02": 1.0})
    with pytest.raises(MissingInput):
        assemble.build_narration_track(lines, {"s01": a, "s02": b}, total, tmp_path / "t.wav")


def test_missing_narration_is_a_clear_error(board, tmp_path):
    board["shots"][0]["narration"]["text"] = "spoken line"
    with pytest.raises(MissingInput, match="narration missing"):
        assemble.run(board, out_base=tmp_path)


def _has_ffmpeg():
    try:
        config.find_tool("ffmpeg")
        return True
    except config.MissingTool:
        return False


@pytest.mark.skipif(not _has_ffmpeg(), reason="FFmpeg not installed")
def test_radio_cut_end_to_end_and_cached_rerun(board, tmp_path):
    for i, s in enumerate(board["shots"]):
        s["narration"]["text"] = f"line {i}"
        s["narration"]["subtitle_en"] = f"Subtitle {i}"
    log = tmp_path / "runs.jsonl"
    narration.run(board, synthesize=lambda out_path, **kw: tone(out_path, 2.0),
                  out_base=tmp_path, log_path=log)
    cut = assemble.run(board, out_base=tmp_path, log_path=log)
    assert cut.exists() and cut.stat().st_size > 10_000

    probe = subprocess.run([config.find_tool("ffprobe"), "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type", "-of", "json", str(cut)],
                           capture_output=True, text=True)
    info = json.loads(probe.stdout)
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
    _, total = assemble.plan_timeline(board, {s["id"]: 2.0 for s in board["shots"]})
    assert float(info["format"]["duration"]) == pytest.approx(total, abs=0.15)

    lr = json.loads(cut.with_name(cut.name.replace(".mp4", ".loudness.json")).read_text())
    assert lr["problems"] == [], lr                     # -14 LUFS +-0.5, TP <= -1, linear pass
    assert not list(tmp_path.glob("cuts/*.mix.wav")) and not list(tmp_path.glob("cuts/*.master.wav"))

    again = assemble.run(board, out_base=tmp_path, log_path=log)
    assert again == cut
    cut_rows = [r for r in read_log(log) if r["stage"] == "cuts"]
    assert [r["status"] for r in cut_rows] == ["ok", "cache_hit"]
