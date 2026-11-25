"""Stage: moving shots. Wan 2.2 TI2V-5B image-to-video runs on a Kaggle GPU, not here.

    py -m pipeline shots                    # status: which shots have a clip, which fall back
    py -m pipeline shots --export DIR       # job bundle for notebooks/wan22_shots.ipynb
    py -m pipeline shots --import DIR       # copy finished clips (and their log lines) back

Contract: a clip is expected at outputs/shots/<shot>_<hash>.mp4, where the hash covers the
motion prompt, the take number, the model settings and the keyframe's FILE hash. A new
keyframe therefore means a new clip is expected, and an old clip is never used against a
new picture. Shots without a clip are animated with a Ken Burns move in assembly
(render.py), so the film never waits on the GPU queue.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import keyframes, render
from .common import MissingInput, config
from .common.cache import file_hash, stable_hash, video_inputs
from .common.runlog import read_log
from .common.storyboard import select_shots

STAGE = "shots"
MODEL = "Wan2.2-TI2V-5B"
# 121 frames = 5.04 s at 24 fps (TI2V-5B's native length); 1280*704 = its 720p landscape size
PARAMS = {"size": "1280*704", "frame_num": 121, "fps": 24}
EXPORT_W, EXPORT_H = 1280, 704


def wants_clip(shot: dict) -> bool:
    return shot["video"]["method"] in ("wan_i2v", "hunyuan_i2v") and not shot["video"].get("still")


def clip_inputs(storyboard: dict, shot: dict, out_base: Path | None = None) -> dict:
    kf = keyframes.keyframe_path(storyboard, shot, out_base)
    if not kf.exists():
        raise MissingInput(f"{shot['id']}: keyframe missing; run `py -m pipeline keyframes`")
    return video_inputs(shot, keyframe_hash=file_hash(kf), model=MODEL, params=PARAMS)


def clip_path(storyboard: dict, shot: dict, out_base: Path | None = None) -> Path:
    h = stable_hash(clip_inputs(storyboard, shot, out_base))
    return (out_base or config.OUTPUTS) / STAGE / f"{shot['id']}_{h}.mp4"


def status(storyboard: dict, out_base: Path | None = None) -> dict[str, str]:
    out = {}
    for shot in storyboard["shots"]:
        if not wants_clip(shot):
            out[shot["id"]] = "ken burns (by design)"
        elif clip_path(storyboard, shot, out_base).exists():
            out[shot["id"]] = "clip"
        else:
            out[shot["id"]] = "ken burns (no clip yet)"
    return out


def export_job(storyboard: dict, dest: Path, only: list[str] | None = None,
               out_base: Path | None = None) -> Path:
    """Write job.json + 16:9 keyframe crops for every shot that still needs a clip."""
    dest = Path(dest)
    (dest / "keyframes").mkdir(parents=True, exist_ok=True)
    ffmpeg = config.find_tool("ffmpeg")
    jobs = []
    for shot in select_shots(storyboard, only):
        if not wants_clip(shot) or clip_path(storyboard, shot, out_base).exists():
            continue
        kf = keyframes.keyframe_path(storyboard, shot, out_base)
        img = dest / "keyframes" / f"{shot['id']}.jpg"
        x, y, w, h = render.crop_window(*render.image_size(kf), EXPORT_W / EXPORT_H,
                                        tuple(shot["video"].get("focus", (0.5, 0.5))))
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(kf), "-vf",
                        f"crop={w}:{h}:{x}:{y},scale={EXPORT_W}:{EXPORT_H}:flags=lanczos",
                        "-q:v", "2", str(img)], check=True)
        jobs.append({"shot": shot["id"], "image": f"keyframes/{img.name}",
                     "prompt": shot["motion_prompt"], "seed": shot["seed"],
                     "out": clip_path(storyboard, shot, out_base).name})
    job = {"stage": STAGE, "model": MODEL, "params": PARAMS, "jobs": jobs}
    (dest / "job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  exported {len(jobs)} shot(s) to {dest} (upload this folder as a Kaggle dataset)")
    return dest / "job.json"


def _merge_runs(fragment: Path, log_path: Path | None) -> int:
    """Append notebook log lines that are not already in runs.jsonl."""
    if not fragment.exists():
        return 0
    known = {(r["ts"], r["stage"], r["shot"], r["attempt"]) for r in read_log(log_path)}
    added = 0
    with open(log_path or config.RUNS_LOG, "a", encoding="utf-8", newline="") as f:
        for line in fragment.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if (r["ts"], r["stage"], r["shot"], r["attempt"]) not in known:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                added += 1
    return added


def import_clips(storyboard: dict, src: Path, out_base: Path | None = None,
                 log_path: Path | None = None) -> list[str]:
    """Copy clips whose names match the current contract; anything else is reported, not used."""
    src = Path(src)
    folder = config.output_dir(STAGE, out_base)
    found = {p.name: p for p in src.rglob("*.mp4")}
    imported = []
    for shot in storyboard["shots"]:
        if not wants_clip(shot):
            continue
        name = clip_path(storyboard, shot, out_base).name
        if name in found:
            if render.media_duration(found[name]) < 1.0:
                raise MissingInput(f"{name} is not a usable video (shorter than 1 s)")
            shutil.copy2(found[name], folder / name)
            imported.append(shot["id"])
    stale = sorted(set(found) - {clip_path(storyboard, s, out_base).name
                                 for s in storyboard["shots"] if wants_clip(s)})
    added = _merge_runs(src / "runs_fragment.jsonl", log_path)
    print(f"  imported clips for {imported or 'no shots'}; merged {added} log line(s)")
    if stale:
        print(f"  ignored {len(stale)} clip(s) that match no current shot (old keyframe or prompt): {stale}")
    return imported


def run(storyboard: dict, only: list[str] | None = None, *, export: Path | None = None,
        import_dir: Path | None = None, out_base: Path | None = None,
        log_path: Path | None = None) -> dict[str, str]:
    if export:
        export_job(storyboard, export, only, out_base)
    if import_dir:
        import_clips(storyboard, import_dir, out_base, log_path)
    st = status(storyboard, out_base)
    for sid, state in st.items():
        print(f"  {sid}: {state}")
    return st
