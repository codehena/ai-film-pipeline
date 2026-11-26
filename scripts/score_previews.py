"""Listening previews: the final audio chain (narration + ducked score, two-pass loudness)
once per imported score candidate, so `score.chosen` is picked by ear, not by guess.

    py scripts/score_previews.py          ->  outputs/previews/score_c<n>.m4a

Uses the same functions as `assemble --mode final`, so a preview sounds like the film.
No model calls; local FFmpeg only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import assemble, music  # noqa: E402
from pipeline.common import config, loudness  # noqa: E402
from pipeline.common.storyboard import load_storyboard  # noqa: E402


def main() -> int:
    storyboard = load_storyboard()
    ffmpeg = config.find_tool("ffmpeg")
    audio, lines, total = assemble.collect_narration(storyboard)
    folder = config.OUTPUTS / "previews"
    folder.mkdir(parents=True, exist_ok=True)
    made = 0
    for n in range(1, storyboard["score"]["candidates"] + 1):
        cand = music.candidate_path(storyboard, n)
        if not cand.exists():
            print(f"  c{n}: missing ({cand.name}); run `py -m pipeline music --import`")
            continue
        master, report = assemble.master_audio(ffmpeg, folder, f"score_c{n}", lines, audio, total, cand)
        out = folder / f"score_c{n}.m4a"
        assemble.run_ffmpeg([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", master.name,
                             "-c:a", "aac", "-b:a", "192k", out.name], folder)
        master.unlink(missing_ok=True)
        (folder / f"score_c{n}.narration.wav").unlink(missing_ok=True)
        m = loudness.measure(ffmpeg, out)
        print(f"  c{n}: {out}  ({m['input_i']} LUFS, true peak {m['input_tp']} dBTP)")
        made += 1
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
