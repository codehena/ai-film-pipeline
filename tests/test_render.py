"""Final-cut building blocks: geometry, moves, the Kaggle contracts, and a small real render."""
import json
import subprocess
import wave

import pytest

from pipeline import assemble, keyframes, music, narration, render, shots
from pipeline.common import MissingInput, config


# ---------------------------------------------------------------- pure geometry
@pytest.mark.parametrize("ratio,expect_wh", [(16 / 9, (1024, 576)), (9 / 16, (576, 1024))])
def test_one_square_keyframe_gives_both_ratios(ratio, expect_wh):
    x, y, w, h = render.crop_window(1024, 1024, ratio)
    assert (w, h) == expect_wh and (x, y) == ((1024 - w) // 2, (1024 - h) // 2)


def test_focus_moves_the_window_but_never_outside_the_image():
    x, _, w, _ = render.crop_window(1024, 1024, 9 / 16, (0.1, 0.5))
    assert x == 0                                  # clamped at the left edge
    x, _, w, _ = render.crop_window(1024, 1024, 9 / 16, (0.9, 0.5))
    assert x + w == 1024                           # clamped at the right edge
    _, y, _, h = render.crop_window(1024, 1024, 16 / 9, (0.5, 0.52))
    assert 0 < y < 1024 - h


@pytest.mark.parametrize("prompt,zoom,drift", [
    ("slow push-in, mist drifting", (1.0, 1.10), (0.5, 0.5)),
    ("slow pull-back, smoke rising", (1.12, 1.0), (0.5, 0.5)),
    ("slow pan left to right, cattle walking", (1.12, 1.12), (0.42, 0.58)),
    ("camera static, bees moving", (1.0, 1.04), (0.5, 0.5)),
])
def test_move_is_read_from_the_motion_prompt(prompt, zoom, drift):
    m = render.move_for({"motion_prompt": prompt, "video": {"method": "wan_i2v", "fallback": "ken_burns"}})
    assert m.zoom == zoom and m.drift == drift


def test_explicit_still_zoom_wins():
    shot = {"motion_prompt": "static", "video": {"method": "ken_burns", "fallback": "still",
                                                 "still": {"from": "s08", "zoom": [1.5, 1.9]}}}
    assert render.move_for(shot).zoom == (1.5, 1.9)


def test_frame_bounds_do_not_drift():
    bounds = [(0.0, 7.1), (7.1, 19.6), (19.6, 24.7), (24.7, 27.7)]
    frames = render.frame_bounds(bounds)
    assert sum(frames) == round(27.7 * render.FPS)  # cumulative rounding: no drift


def test_subtitles_are_narrower_for_vertical(board):
    board["shots"][0]["narration"]["subtitle_en"] = (
        "But our home was never empty. These things made me love growing up in the countryside.")
    lines, total = assemble.plan_timeline(board, {"s01": 6.0})
    v = assemble.build_srt(lines, board["end_card"], total, width=26, end_card_cue=False)
    rows = [r for cue in v.strip().split("\n\n") for r in cue.splitlines()[2:]]
    assert max(len(r) for r in rows) <= 30
    assert board["end_card"]["text"].split()[0] not in v      # the card is drawn, not subtitled


# ---------------------------------------------------------------- contracts with fakes
def _jpeg(path, colour="0x6a8f4e"):
    subprocess.run([config.find_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-f",
                    "lavfi", "-i", f"color=c={colour}:s=256x256", "-frames:v", "1", str(path)],
                   check=True)


@pytest.fixture
def pictured(board, tmp_path):
    """Fixture storyboard with fake keyframes and fake narration on disk."""
    for i, s in enumerate(board["shots"]):
        s["narration"]["text"] = f"line {i}"
        s["narration"]["subtitle_en"] = f"Subtitle number {i}"

    def gen(*, model, prompt, params, out_path, references=()):
        _jpeg(out_path)
    keyframes.run(board, generate=gen, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")

    def tts(out_path, **kw):
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
            w.writeframes(b"\x10\x00" * 24000 * 2)
    narration.run(board, synthesize=tts, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    return board


def test_clip_contract_follows_the_keyframe_file(pictured, tmp_path):
    shot = pictured["shots"][0]
    before = shots.clip_path(pictured, shot, tmp_path).name
    _jpeg(keyframes.keyframe_path(pictured, shot, tmp_path), colour="0x112233")   # a new picture
    assert shots.clip_path(pictured, shot, tmp_path).name != before


def test_export_then_import_round_trip(pictured, tmp_path):
    job = json.loads(shots.export_job(pictured, tmp_path / "job", out_base=tmp_path).read_text())
    assert len(job["jobs"]) == sum(shots.wants_clip(s) for s in pictured["shots"])
    first = job["jobs"][0]
    assert render.image_size(tmp_path / "job" / first["image"]) == (shots.EXPORT_W, shots.EXPORT_H)
    done = tmp_path / "kaggle_out"
    done.mkdir()
    subprocess.run([config.find_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-f",
                    "lavfi", "-i", "testsrc=s=320x176:r=24:d=2", str(done / first["out"])], check=True)
    (done / "stale_old.mp4").write_bytes(b"")
    log = tmp_path / "runs.jsonl"
    (done / "runs_fragment.jsonl").write_text(json.dumps(
        {"ts": "2026-11-26T10:00:00Z", "run_id": "kaggle", "stage": "shots", "shot": first["shot"],
         "provider": "kaggle", "model": shots.MODEL, "params": shots.PARAMS, "seed": 1,
         "input_hash": None, "status": "ok", "attempt": 1, "latency_s": 600.0, "gpu_s": 600.0,
         "cost_usd_list": None, "output": first["out"], "error": None}) + "\n")
    assert shots.import_clips(pictured, done, tmp_path, log) == [first["shot"]]
    assert shots.import_clips(pictured, done, tmp_path, log) == [first["shot"]]
    assert sum(1 for line in log.read_text().splitlines() if '"run_id": "kaggle"' in line) == 1
    assert shots.status(pictured, tmp_path)[first["shot"]] == "clip"


def test_music_hash_ignores_cue_times_but_not_the_music(pictured):
    a = music.candidate_path(pictured, 1).name
    pictured["music_cues"][0]["end_s"] += 3          # a retime moves cue times
    assert music.candidate_path(pictured, 1).name == a
    pictured["music_cues"][0]["caption"] += ", with masinqo"
    assert music.candidate_path(pictured, 1).name != a


def test_chosen_score_must_exist(pictured, tmp_path):
    assert music.score_path(pictured, tmp_path) is None          # nothing chosen: placeholder pad
    pictured["score"]["chosen"] = 2
    with pytest.raises(MissingInput, match="music --import"):
        music.score_path(pictured, tmp_path)


# ---------------------------------------------------------------- a small real render
@pytest.fixture
def small_formats(monkeypatch):
    monkeypatch.setattr(render, "FORMATS", {"16:9": (320, 180), "9:16": (180, 320)})
    monkeypatch.setattr(render, "UPSCALE", 2)


def test_final_cut_renders_both_ratios_on_the_timeline(pictured, tmp_path, small_formats):
    outs = assemble.run_final(pictured, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    assert set(outs) == {"16:9", "9:16"}
    _, total = assemble.plan_timeline(pictured, {s["id"]: 2.0 for s in pictured["shots"]})
    for ratio, path in outs.items():
        assert render.image_size(path) == render.FORMATS[ratio]
        assert render.media_duration(path) == pytest.approx(total, abs=0.1)
        lr = json.loads(path.with_name(path.name.replace(".mp4", ".loudness.json")).read_text())
        assert lr["problems"] == []
    again = assemble.run_final(pictured, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    assert again == outs                                # cached: no re-render


def test_card_is_centred_in_legacy_alignment():
    assert "Alignment=10" in render.card_style("16:9") and "Alignment=10" in render.card_style("9:16")


def test_clause_without_punctuation_is_split_between_words():
    text = "my brother and I went side by side to the spring to fetch water."
    parts = assemble.split_caption(text, 2 * 26 + 4)
    assert len(parts) == 2 and " ".join(parts) == text
    assert all(len(r) <= 30 for p in parts for r in assemble.wrap_subtitle(p, 26).splitlines())


def test_subtitle_rows_are_balanced():
    assert assemble.wrap_subtitle("my brother and I went side by", 26) == "my brother and\nI went side by"


def test_a_style_change_invalidates_the_final_cut(pictured, tmp_path, small_formats, monkeypatch):
    first = assemble.run_final(pictured, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    monkeypatch.setattr(render, "card_style", lambda r: "Alignment=10,FontSize=30")
    second = assemble.run_final(pictured, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    assert all(first[r] != second[r] for r in first)          # no stale cut from the cache


def test_beats_become_their_own_segments_on_the_timeline(pictured, tmp_path, small_formats):
    from pipeline import beats, framing
    shot = pictured["shots"][1]
    shot["beats"] = [{"from_word": 1, "image_prompt": "a second picture"}]   # text "line 1": 2 words
    shot["video"]["safe_box"] = [0.3, 0.1, 0.7, 0.4]

    def gen(*, model, prompt, params, out_path, references=()):
        _jpeg(out_path, colour="0x884422")
    keyframes.run(pictured, [shot["id"]], generate=gen, out_base=tmp_path,
                  log_path=tmp_path / "runs.jsonl")
    outs = assemble.run_final(pictured, out_base=tmp_path, log_path=tmp_path / "runs.jsonl")
    parts = list((tmp_path / "cuts" / "parts").glob(f"{shot['id']}-b1_*.mp4"))
    assert len(parts) == 2                                   # the beat rendered in both ratios
    _, total = assemble.plan_timeline(pictured, {s["id"]: 2.0 for s in pictured["shots"]})
    assert render.media_duration(outs["16:9"]) == pytest.approx(total, abs=0.1)
    status = shots.status(pictured, tmp_path)
    assert f"{shot['id']}-b1" in status                      # Wan contract per beat too
    sheet = framing.run(pictured, [shot["id"]], out_base=tmp_path)
    assert sheet.exists() and render.image_size(sheet)[0] == 2 * framing.TILE
