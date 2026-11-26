"""Stage: music. ACE-Step 1.5 runs on a Kaggle GPU, not here.

    py -m pipeline music                    # status of the candidates and the chosen one
    py -m pipeline music --export DIR       # job bundle for notebooks/acestep_score.ipynb
    py -m pipeline music --import DIR       # copy the candidates (and log lines) back

The score is generated ONCE, a little longer than the film (`score.duration_s`), and
assembly trims it to the film's length with a fade-out. So its hash covers what the
music IS (cue captions, tempo, key, model, length, number of candidates), not the
cue *times*: retiming the narration never invalidates the music.

Choosing a candidate is a storyboard decision (`score.chosen`), recorded with the
reason in EXPERIMENTS.md. Until one is chosen, assembly uses the placeholder pad.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import render
from .common import MissingInput, config
from .common.cache import stable_hash
from .shots import _merge_runs

STAGE = "music"


def caption(storyboard: dict) -> str:
    """One caption for one continuous piece: the cues in order."""
    parts = [c["caption"] for c in storyboard["music_cues"]]
    instrumental = all(c.get("instrumental", True) for c in storyboard["music_cues"])
    return "; then ".join(parts) + ("; instrumental, no vocals" if instrumental else "")


def score_inputs(storyboard: dict) -> dict:
    score = storyboard["score"]
    first = storyboard["music_cues"][0]
    return {"stage": STAGE, "model": score["model"], "duration_s": score["duration_s"],
            "candidates": score["candidates"], "caption": caption(storyboard),
            "bpm": first.get("bpm"), "key": first.get("key")}


def candidate_path(storyboard: dict, n: int, out_base: Path | None = None) -> Path:
    h = stable_hash(score_inputs(storyboard))
    return (out_base or config.OUTPUTS) / STAGE / f"score_{h}_c{n}.wav"


def score_path(storyboard: dict, out_base: Path | None = None) -> Path | None:
    """The chosen candidate, or None (assembly then uses the placeholder pad)."""
    score = storyboard.get("score") or {}
    n = score.get("chosen")
    if not n:
        return None
    p = candidate_path(storyboard, n, out_base)
    if not p.exists():
        raise MissingInput(f"score.chosen = {n} but {p.name} is missing; run `music --import`")
    return p


def export_job(storyboard: dict, dest: Path) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    s = score_inputs(storyboard)
    bpms = {c.get("bpm") for c in storyboard["music_cues"]}
    keys = {c.get("key") for c in storyboard["music_cues"]}
    if len(bpms) > 1 or len(keys) > 1:
        print(f"  note: cues differ in bpm/key {bpms}/{keys}; one piece uses the first cue's")
    job = s | {"seeds": list(range(1, s["candidates"] + 1)),
               "outs": [candidate_path(storyboard, n).name for n in range(1, s["candidates"] + 1)]}
    (dest / "job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  exported the score job ({s['candidates']} candidates, {s['duration_s']} s) to {dest}")
    return dest / "job.json"


def import_scores(storyboard: dict, src: Path, film_s: float | None = None,
                  out_base: Path | None = None, log_path: Path | None = None) -> list[int]:
    src = Path(src)
    folder = config.output_dir(STAGE, out_base)
    found = {p.name: p for p in src.rglob("*.wav")}
    imported = []
    for n in range(1, storyboard["score"]["candidates"] + 1):
        name = candidate_path(storyboard, n, out_base).name
        if name in found:
            d = render.media_duration(found[name])
            if film_s and d < film_s:
                print(f"  warning: candidate {n} is {d:.1f} s, shorter than the film ({film_s:g} s)")
            shutil.copy2(found[name], folder / name)
            imported.append(n)
    added = _merge_runs(src / "runs_fragment.jsonl", log_path)
    print(f"  imported candidates {imported or 'none'}; merged {added} log line(s)")
    return imported


def run(storyboard: dict, only: list[str] | None = None, *, export: Path | None = None,
        import_dir: Path | None = None, out_base: Path | None = None,
        log_path: Path | None = None) -> dict:
    if export:
        export_job(storyboard, export)
    if import_dir:
        import_scores(storyboard, import_dir, None, out_base, log_path)
    n = storyboard["score"]["candidates"]
    have = [k for k in range(1, n + 1) if candidate_path(storyboard, k, out_base).exists()]
    chosen = storyboard["score"].get("chosen")
    print(f"  candidates present: {have or 'none'} of {n}; chosen: {chosen or 'none (placeholder pad)'}")
    return {"present": have, "chosen": chosen}
