"""Loudness normalisation to a platform target (default -14 LUFS, true peak <= -1 dBTP).

Why not single-pass `loudnorm`? (FAILURES.md F-11) Our raw mix sits around -23.5 LUFS
with peaks near -3.6 dBTP: its peaks are ~20 dB above its average. Reaching -14 LUFS
needs ~+9.5 dB, which would push peaks to about +6 dBTP. Single-pass loudnorm then
silently falls back to "dynamic" mode and stops short (we measured -15.9 LUFS).

Recipe (measured on the real radio mix, EXPERIMENTS.md EXP-04):
  1. measure the raw mix
  2. pre-gain to (target + MAKEUP_DB) and limit peaks at LIMIT_DBFS, so the
     loudness fits under the true-peak ceiling with headroom
  3. measure again and apply loudnorm with those measurements, linear=true:
     a plain, auditable gain change, no further dynamics processing
Every number is kept in a report so the result can be checked from text alone.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

TARGET_I = -14.0      # LUFS (YouTube / most social platforms)
TARGET_TP = -1.0      # dBTP ceiling
TARGET_LRA = 11.0     # LU
LIMIT_DBFS = -3.5     # limiter ceiling: leaves room for the final gain and inter-sample peaks
MAKEUP_DB = 2.0       # extra pre-gain, because limiting itself lowers integrated loudness
TOLERANCE_LU = 0.5    # how far from TARGET_I still counts as on target


class LoudnessError(Exception):
    pass


def parse_loudnorm(stderr: str) -> dict:
    """The JSON block that `loudnorm=print_format=json` prints at the end of stderr."""
    start = stderr.rfind("{")
    end = stderr.find("}", start)
    if start < 0 or end < 0:
        raise LoudnessError("no loudnorm JSON found in FFmpeg output")
    return json.loads(stderr[start:end + 1])


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise LoudnessError(f"ffmpeg failed: {result.stderr.strip()[-600:]}")
    return result.stderr


def _target() -> str:
    return f"I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"


def measure(ffmpeg: str, path: Path) -> dict:
    """Integrated loudness (input_i), true peak (input_tp), LRA, threshold of a file."""
    stats = parse_loudnorm(_run([ffmpeg, "-hide_banner", "-i", str(path), "-af",
                                 f"loudnorm={_target()}:print_format=json", "-f", "null", "-"]))
    if stats["input_i"] in ("-inf", "inf"):
        raise LoudnessError(f"{Path(path).name} is silent; nothing to normalise")
    return stats


def normalize(ffmpeg: str, src: Path, dst: Path) -> dict:
    """Write a WAV at TARGET_I / under TARGET_TP. Returns a report of every step."""
    src, dst = Path(src), Path(dst)
    raw = measure(ffmpeg, src)
    pre_gain = round(TARGET_I - float(raw["input_i"]) + MAKEUP_DB, 2)
    limit = round(10 ** (LIMIT_DBFS / 20), 4)
    limited = dst.with_name(dst.stem + ".limited.wav")
    _run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af",
          f"volume={pre_gain}dB,alimiter=limit={limit}:level=false:attack=5:release=100",
          str(limited)])
    mid = measure(ffmpeg, limited)
    applied = parse_loudnorm(_run([
        ffmpeg, "-hide_banner", "-y", "-i", str(limited), "-af",
        f"loudnorm={_target()}:measured_I={mid['input_i']}:measured_TP={mid['input_tp']}"
        f":measured_LRA={mid['input_lra']}:measured_thresh={mid['input_thresh']}"
        f":offset={mid['target_offset']}:linear=true:print_format=json",
        "-ar", "48000", str(dst)]))
    limited.unlink(missing_ok=True)
    return {
        "target_i": TARGET_I, "target_tp": TARGET_TP,
        "raw_i": float(raw["input_i"]), "raw_tp": float(raw["input_tp"]),
        "pre_gain_db": pre_gain, "limit_dbfs": LIMIT_DBFS,
        "limited_i": float(mid["input_i"]), "limited_tp": float(mid["input_tp"]),
        "final_pass": applied["normalization_type"],
    }


def problems(report: dict) -> list[str]:
    """Empty if the delivered file meets the target; otherwise what is wrong."""
    out = []
    if abs(report["final_i"] - TARGET_I) > TOLERANCE_LU:
        out.append(f"integrated loudness {report['final_i']} LUFS is not within "
                   f"{TOLERANCE_LU} LU of {TARGET_I}")
    if report["final_tp"] > TARGET_TP + 0.1:
        out.append(f"true peak {report['final_tp']} dBTP is above {TARGET_TP}")
    if report.get("final_pass") != "linear":
        out.append(f"final pass fell back to {report.get('final_pass')} (not linear)")
    return out
