"""Picture building blocks for the final cut (FFmpeg; no AI).

- crop_window(): the largest window of a target aspect ratio around a focus point.
  One square keyframe serves both 16:9 and 9:16 because subjects are centred.
- move_for(): a Ken Burns move (zoom range, horizontal drift) read from the shot's own
  motion_prompt ("push-in", "pull-back", "pan left to right", "static" ...) or from
  an explicit `video.still.zoom`. Neighbouring shots therefore move differently.
- segment commands: still -> moving shot, motion clip -> fitted shot, end card.
- frame_bounds(): shot boundaries in whole frames from the timeline, so 10 shots never
  drift against the narration (rounding is done on cumulative times, not durations).

Pure functions are kept apart from the FFmpeg command builders so they can be tested.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .common import config

FPS = 24
FORMATS = {"16:9": (1280, 720), "9:16": (720, 1280)}
UPSCALE = 4  # zoompan moves in whole pixels; working at 4x resolution removes visible jitter
CARD_BG = "0x14110f"  # warm near-black for the end card


@dataclass(frozen=True)
class Move:
    zoom: tuple[float, float]   # start, end (1.0 = the full crop window)
    drift: tuple[float, float]  # horizontal focus at start, end (0-1 of the crop window)


def image_size(path: Path) -> tuple[int, int]:
    out = subprocess.run([config.find_tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def media_duration(path: Path) -> float:
    out = subprocess.run([config.find_tool("ffprobe"), "-v", "error", "-show_entries",
                          "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    try:
        return float(json.loads(out)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return 0.0


def crop_window(src_w: int, src_h: int, ratio: float,
                focus: tuple[float, float] = (0.5, 0.5)) -> tuple[int, int, int, int]:
    """(x, y, w, h): the largest window of aspect `ratio` (w/h), centred on `focus`
    as far as the image allows. Even sizes, for yuv420p."""
    if src_w / src_h > ratio:
        h = src_h
        w = round(h * ratio)
    else:
        w = src_w
        h = round(w / ratio)
    w, h = w - w % 2, h - h % 2
    x = round(min(max(focus[0] * src_w - w / 2, 0), src_w - w))
    y = round(min(max(focus[1] * src_h - h / 2, 0), src_h - h))
    return x, y, w, h


def move_for(shot: dict) -> Move:
    video = shot["video"]
    still = video.get("still") or {}
    if still.get("zoom"):
        z0, z1 = still["zoom"]
        return Move((z0, z1), (0.5, 0.5))
    m = shot["motion_prompt"].lower()
    if "pull-back" in m or "pull back" in m or "zoom out" in m:
        return Move((1.12, 1.0), (0.5, 0.5))
    if "left to right" in m or "pan right" in m:
        return Move((1.12, 1.12), (0.42, 0.58))
    if "right to left" in m or "pan left" in m:
        return Move((1.12, 1.12), (0.58, 0.42))
    if "static" in m:
        return Move((1.0, 1.04), (0.5, 0.5))      # a breath of movement, not a frozen frame
    return Move((1.0, 1.10), (0.5, 0.5))          # push-in, follow, track: move gently forward


def frame_bounds(starts_ends: list[tuple[float, float]]) -> list[int]:
    """Frame counts per segment, rounded on cumulative times (no drift)."""
    return [round(e * FPS) - round(s * FPS) for s, e in starts_ends]


def zoompan_filter(move: Move, frames: int, focus_y: float, out_w: int, out_h: int) -> str:
    n = max(frames - 1, 1)
    z0, z1 = move.zoom
    d0, d1 = move.drift
    z = f"{z0}+({z1 - z0})*on/{n}"
    cx = f"({d0}+({d1 - d0})*on/{n})"
    x = f"max(0,min(iw-iw/zoom,{cx}*iw-iw/zoom/2))"
    y = f"max(0,min(ih-ih/zoom,{focus_y}*ih-ih/zoom/2))"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={out_w}x{out_h}:fps={FPS}"


def still_segment_cmd(ffmpeg: str, image: Path, image_wh: tuple[int, int], ratio_key: str,
                      focus: tuple[float, float], move: Move, frames: int, out: Path) -> list[str]:
    out_w, out_h = FORMATS[ratio_key]
    x, y, w, h = crop_window(*image_wh, out_w / out_h, focus)
    # focus inside the crop window, so the zoom closes in on the subject
    fy = min(max((focus[1] * image_wh[1] - y) / h, 0.0), 1.0)
    vf = (f"crop={w}:{h}:{x}:{y},scale={w * UPSCALE}:{h * UPSCALE}:flags=lanczos,"
          f"{zoompan_filter(move, frames, fy, out_w, out_h)},setsar=1,format=yuv420p")
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1",
            "-framerate", str(FPS), "-i", str(image), "-vf", vf, "-frames:v", str(frames),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-an", str(out)]


def clip_segment_cmd(ffmpeg: str, clip: Path, clip_wh: tuple[int, int], ratio_key: str,
                     focus: tuple[float, float], frames: int, out: Path) -> list[str]:
    """A motion clip cropped to the ratio; held on its last frame if the shot is longer."""
    out_w, out_h = FORMATS[ratio_key]
    x, y, w, h = crop_window(*clip_wh, out_w / out_h, focus)
    vf = (f"crop={w}:{h}:{x}:{y},scale={out_w}:{out_h}:flags=lanczos,fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration={frames / FPS + 1:.3f},setsar=1,format=yuv420p")
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip), "-vf", vf,
            "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", str(out)]


def card_style(ratio_key: str) -> str:
    size = 18 if ratio_key == "16:9" else 11
    return f"Alignment=5,FontSize={size},Outline=0,Shadow=0,PrimaryColour=&H00E8EEF2"


def card_segment_cmd(ffmpeg: str, srt_name: str, ratio_key: str, frames: int, out_name: str) -> list[str]:
    """End card: the card text centred on a warm dark background. Run with cwd = the srt's
    folder (Windows drive colons break the subtitles filter's file argument)."""
    out_w, out_h = FORMATS[ratio_key]
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            f"color=c={CARD_BG}:s={out_w}x{out_h}:r={FPS}",
            "-vf", f"subtitles={srt_name}:force_style='{card_style(ratio_key)}',setsar=1,format=yuv420p",
            "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-an", out_name]


def subtitle_style(ratio_key: str) -> str:
    """16:9: low on the frame. 9:16: larger, and lifted above the bottom ~20% that phone
    apps cover with captions and buttons (safe area)."""
    if ratio_key == "16:9":
        return "FontSize=20,Outline=1.5,Shadow=0,MarginV=30"
    return "FontSize=11,Outline=1.2,Shadow=0,MarginV=62,MarginL=16,MarginR=16"


def mux_cmd(ffmpeg: str, video: str, audio: str, srt: str, ratio_key: str, total: float,
            out: str) -> list[str]:
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", audio,
            "-vf", f"subtitles={srt}:force_style='{subtitle_style(ratio_key)}',format=yuv420p",
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total:.3f}",
            "-movflags", "+faststart", out]
