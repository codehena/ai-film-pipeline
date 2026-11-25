"""Retime: let the measured narration set the shot lengths.

    py -m pipeline retime

For every spoken shot, duration_s becomes the radio cut's recommendation
(pause_before + line + pause_after, rounded up to 0.5 s). Silent shots keep
their duration. Music cue times that sat exactly on a shot start (or on the
film's end) move with that shot, so the spotting survives the retime.

The result is validated before anything is written (e.g. it refuses to make
the film longer than 90 s), and storyboard.json is rewritten with one field
per line so `git diff` shows exactly which durations changed.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from . import narration
from .assemble import plan_timeline
from .common import MissingInput, config
from .common.storyboard import film_duration, validate

EPS = 0.01


def _shot_starts(board: dict) -> list[float]:
    t, starts = 0.0, []
    for s in board["shots"]:
        starts.append(round(t, 3))
        t += s["duration_s"]
    return starts


def _move(value: float, old_starts, new_starts, old_total, new_total) -> float:
    if abs(value - old_total) < EPS:
        return new_total
    for old, new in zip(old_starts, new_starts):
        if abs(value - old) < EPS:
            return new
    return min(value, new_total)


def retimed(storyboard: dict, durations: dict[str, float]) -> dict:
    """A new storyboard with measured durations. Pure function: no files touched."""
    lines, _ = plan_timeline(storyboard, durations)
    new = copy.deepcopy(storyboard)
    for shot, line in zip(new["shots"], lines):
        if line.recommended_s is not None:
            shot["duration_s"] = line.recommended_s
    old_starts, new_starts = _shot_starts(storyboard), _shot_starts(new)
    old_total, new_total = film_duration(storyboard), film_duration(new)
    for cue in new["music_cues"]:
        cue["start_s"] = _move(cue["start_s"], old_starts, new_starts, old_total, new_total)
        cue["end_s"] = _move(cue["end_s"], old_starts, new_starts, old_total, new_total)
    validate(new)  # raises StoryboardError, e.g. if the film would exceed 90 s
    return new


def run(storyboard: dict, path: Path | None = None, out_base: Path | None = None) -> dict:
    durations = {}
    for shot in storyboard["shots"]:
        if narration.should_speak(shot):
            audio = narration.audio_path(storyboard, shot, out_base)
            if not audio.exists():
                raise MissingInput(f"{shot['id']}: no narration yet; run `py -m pipeline narration`")
            durations[shot["id"]] = narration.wav_duration(audio)
    new = retimed(storyboard, durations)

    print("| shot | line (s) | duration_s before | after |\n|---|---|---|---|")
    for old, cur in zip(storyboard["shots"], new["shots"]):
        line = f"{durations[old['id']]:.2f}" if old["id"] in durations else "silent"
        mark = "" if old["duration_s"] == cur["duration_s"] else "  *"
        print(f"| {old['id']} | {line} | {old['duration_s']:g} | {cur['duration_s']:g}{mark} |")
    print(f"\nfilm length {film_duration(storyboard):g} s -> {film_duration(new):g} s")
    for cue in new["music_cues"]:
        print(f"music {cue['id']}: {cue['start_s']:g}-{cue['end_s']:g} s")

    target = Path(path or config.STORYBOARD)
    target.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {config.rel(target)} (review with `git diff storyboard.json`)")
    return new
