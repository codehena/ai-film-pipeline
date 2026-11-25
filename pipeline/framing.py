"""Framing review: draw every crop the film will use onto the keyframes.

    py -m pipeline framing [--shot s04]     -> outputs/qa/framing.png

For each visual unit (a shot or one of its beats), on its keyframe:
  green  the safe box (heads, faces, key action) that must stay in frame
  red    the 16:9 crop, thin red: its tightest moment of the Ken Burns move
  blue   the 9:16 crop, thin blue: its tightest moment
Anything outside a box is cut in that export. Built from the same functions the
renderer uses (render.crop_window, render.fit_move), so it shows what will happen,
not an approximation. No model calls.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import beats, keyframes, render
from .common import config
from .common.storyboard import select_shots

TILE = 420


def unit_boxes(unit: dict, src_wh: tuple[int, int]) -> list[tuple[str, tuple[int, int, int, int], int]]:
    """(colour, (x, y, w, h), thickness) for every rectangle to draw on this unit's keyframe."""
    video = unit["video"]
    focus = tuple(video.get("focus", (0.5, 0.5)))
    box = tuple(video["safe_box"]) if video.get("safe_box") else None
    move = render.move_for(unit)
    sw, sh = src_wh
    out = []
    if box:
        out.append(("green", (round(box[0] * sw), round(box[1] * sh),
                              round((box[2] - box[0]) * sw), round((box[3] - box[1]) * sh)), 6))
    for key, colour in (("16:9", "red"), ("9:16", "blue")):
        ow, oh = render.FORMATS[key]
        x, y, w, h = render.crop_window(sw, sh, ow / oh, focus, box)
        out.append((colour, (x, y, w, h), 8))
        if box:
            fitted, fy = render.fit_move(move, render.box_in_window(box, src_wh, (x, y, w, h)))
        else:
            fitted, fy = move, min(max((focus[1] * sh - y) / h, 0.0), 1.0)
        z = max(fitted.zoom)
        d = fitted.drift[fitted.zoom.index(z)]
        zw, zh = w / z, h / z
        zx = x + min(max(d * w - zw / 2, 0), w - zw)
        zy = y + min(max(fy * h - zh / 2, 0), h - zh)
        out.append((colour, (round(zx), round(zy), round(zw), round(zh)), 3))
    return out


def run(storyboard: dict, only: list[str] | None = None, out_base: Path | None = None) -> Path:
    ffmpeg = config.find_tool("ffmpeg")
    qa = config.output_dir("qa", out_base)
    tiles = []
    for shot in select_shots(storyboard, only):
        for unit in beats.visual_units(shot):
            src = shot
            if unit["video"].get("still"):
                src = next(s for s in storyboard["shots"] if s["id"] == unit["video"]["still"]["from"])
            kf = keyframes.keyframe_path(storyboard, src if unit is shot else unit, out_base)
            if not kf.exists():
                print(f"  {unit['id']}: keyframe missing, skipped")
                continue
            draw = ",".join(f"drawbox=x={x}:y={y}:w={w}:h={h}:color={c}:t={t}"
                            for c, (x, y, w, h), t in unit_boxes(unit, render.image_size(kf)))
            tile = qa / f"framing_{unit['id']}.png"
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(kf), "-vf",
                            f"{draw},scale={TILE}:{TILE}", str(tile)], check=True)
            tiles.append(tile)
    if not tiles:
        raise FileNotFoundError("no keyframes to review; run `py -m pipeline keyframes`")
    cols = min(len(tiles), 5)
    blank = qa / "framing_blank.png"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c=white:s={TILE}x{TILE}", "-frames:v", "1", str(blank)], check=True)
    padded = tiles + [blank] * (-len(tiles) % cols)          # fill the last row
    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for t in padded:
        args += ["-i", str(t)]
    rows = len(padded) // cols
    graph = [("".join(f"[{r * cols + c}:v]" for c in range(cols)) +
              (f"hstack={cols}" if cols > 1 else "null") + f"[row{r}]") for r in range(rows)]
    graph.append("".join(f"[row{r}]" for r in range(rows)) + (f"vstack={rows}" if rows > 1 else "null"))
    sheet = qa / "framing.png"
    subprocess.run(args + ["-filter_complex", ";".join(graph), "-frames:v", "1", str(sheet)], check=True)
    for t in tiles + [blank]:
        t.unlink(missing_ok=True)
    print(f"  framing sheet ({len(tiles)} units): {config.rel(sheet)}")
    return sheet
