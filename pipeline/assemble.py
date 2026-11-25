"""Stage: assembly with FFmpeg (no AI: same inputs give the same output).

Mode "radio" (Phase 1 prototype, built now):
  narration over a placeholder pad on a black screen, with burned-in English
  subtitles. The pad is ducked under the voice (sidechaincompress) and the mix
  is normalised to -14 LUFS / -1 dBTP in two passes (common/loudness.py), with the
  measurements written to radio_<hash>.loudness.json. Its main job is to show whether each line
  fits its shot: the timing report recommends shot durations from the measured
  narration.

Mode "final" (Phase 3, later): pictures, chosen score, end card, 9:16 + 16:9.

Reads:  storyboard.json + outputs/narration/
Writes: outputs/cuts/radio_<hash>.mp4 (+ .srt, .narration.wav, .timing.md, .loudness.json)
"""
from __future__ import annotations

import json
import math
import subprocess
import textwrap
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

from . import narration
from .common import MissingInput, NotBuiltYet, config, loudness
from .common.cache import file_hash
from .common.modelcall import run_model_step

STAGE = "cuts"
# bump when the FFmpeg recipe changes, so old cuts are not reused
# 2: two-pass loudness (pre-gain + limiter + linear loudnorm) replaced single-pass loudnorm (F-11)
# 3: adaptive limiter rounds + 4x oversampled limiter (draft 4 mix fell back to dynamic)
RECIPE_VERSION = 3
MIN_GAP_S = 0.25    # never let two lines touch
RADIO_SIZE = "1280x720"
SUB_MAX_CHARS = 40  # per subtitle line, at most two lines

# Brief's suggested starting point for natural ducking (Appendix B)
DUCK = "threshold=0.02:ratio=6:attack=300:release=1500"
LOUDNESS = {"target_i": loudness.TARGET_I, "target_tp": loudness.TARGET_TP,
            "limit_dbfs": loudness.LIMIT_DBFS, "makeup_db": loudness.MAKEUP_DB,
            "margin_db": loudness.MARGIN_DB, "oversample_hz": loudness.OVERSAMPLE_HZ,
            "method": "two-pass linear"}
# Placeholder pad: an open fifth (A2 + E3 + A3) with a slow swell. No melody to fight the voice.
PAD_EXPR = ("0.20*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.07*t))"
            "+0.12*sin(2*PI*164.81*t)+0.08*sin(2*PI*220*t)")


@dataclass
class Line:
    shot: str
    slot_start: float
    slot_end: float
    start: float | None = None   # when the narration actually starts
    end: float | None = None
    audio: str | None = None
    subtitle: str = ""
    overrun_s: float = 0.0       # how far line + pause_after spills past the slot
    recommended_s: float | None = None


def plan_timeline(storyboard: dict, durations: dict[str, float],
                  audio: dict[str, Path] | None = None) -> tuple[list[Line], float]:
    """Place each line in its shot's slot. Pure function: easy to test, no FFmpeg."""
    lines: list[Line] = []
    t = 0.0
    free_from = 0.0  # earliest time the next line may start
    for shot in storyboard["shots"]:
        meta = shot["narration"].get("speech_metadata") or {}
        before, after = meta.get("pause_before_s", 0.0), meta.get("pause_after_s", 0.0)
        line = Line(shot=shot["id"], slot_start=t, slot_end=t + shot["duration_s"],
                    subtitle=shot["narration"]["subtitle_en"].strip())
        if shot["id"] in durations:
            d = durations[shot["id"]]
            line.start = round(max(t + before, free_from), 3)
            line.end = round(line.start + d, 3)
            line.overrun_s = round(max(0.0, line.end + after - line.slot_end), 3)
            line.recommended_s = math.ceil((before + d + after) * 2) / 2  # to the next 0.5 s
            line.audio = config.rel(audio[shot["id"]]) if audio else None
            free_from = line.end + max(after, MIN_GAP_S)
        lines.append(line)
        t = line.slot_end
    total = round(max(t, free_from) + storyboard["end_card"]["duration_s"], 3)
    return lines, total


def build_narration_track(lines: list[Line], audio: dict[str, Path], total: float,
                          out: Path) -> None:
    """Join the per-shot WAVs with silence so each starts at its planned time."""
    fmt = None
    with wave.open(str(out), "wb") as dst:
        written = 0
        for line in lines:
            if line.start is None:
                continue
            with wave.open(str(audio[line.shot]), "rb") as src:
                this = (src.getnchannels(), src.getsampwidth(), src.getframerate())
                if fmt is None:
                    fmt = this
                    dst.setnchannels(this[0]); dst.setsampwidth(this[1]); dst.setframerate(this[2])
                elif this != fmt:
                    raise MissingInput(f"{line.shot}: audio format {this} differs from {fmt}")
                frame_bytes = fmt[0] * fmt[1]
                gap = max(0, round(line.start * fmt[2]) - written)
                dst.writeframes(b"\x00" * gap * frame_bytes)
                frames = src.readframes(src.getnframes())
                dst.writeframes(frames)
                written += gap + len(frames) // frame_bytes
        if fmt is None:
            raise MissingInput("no narration audio yet: run `py -m pipeline narration` first")
        tail = max(0, round(total * fmt[2]) - written)
        dst.writeframes(b"\x00" * tail * fmt[0] * fmt[1])


def _ts(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def wrap_subtitle(text: str) -> str:
    """At most two lines, ~40 chars each. A too-long subtitle gets wider lines, never lost words
    (and the timing report is the place to notice it should be shortened)."""
    width = SUB_MAX_CHARS
    lines = textwrap.wrap(text, width)
    while len(lines) > 2:
        width += 4
        lines = textwrap.wrap(text, width)
    return "\n".join(lines)


def build_srt(lines: list[Line], end_card: dict, total: float) -> str:
    cues = []
    for line in lines:
        if line.start is not None and line.subtitle:
            end = max(line.end, line.start + 1.0)  # at least 1 s on screen
            cues.append((line.start, end, wrap_subtitle(line.subtitle)))
    cues.append((total - end_card["duration_s"], total, wrap_subtitle(end_card["text"])))
    return "\n".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{txt}\n"
                     for i, (a, b, txt) in enumerate(cues, 1))


def ffmpeg_mix_cmd(ffmpeg: str, track: str, total: float, out: str) -> list[str]:
    """Step 1: narration + placeholder pad ducked under it. No loudness processing yet."""
    graph = (
        "[0:a]aresample=48000,asplit=2[voice][sc];"
        f"[1:a]volume=0.5,afade=t=in:d=2,afade=t=out:st={max(0, total - 3):.3f}:d=3[pad];"
        f"[pad][sc]sidechaincompress={DUCK}[ducked];"
        "[voice][ducked]amix=inputs=2:normalize=0:duration=first[aout]"
    )
    return [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", track,
        "-f", "lavfi", "-i", f"aevalsrc='{PAD_EXPR}':s=48000:d={total:.3f}",
        "-filter_complex", graph, "-map", "[aout]", "-t", f"{total:.3f}", out,
    ]


def ffmpeg_radio_mux_cmd(ffmpeg: str, audio: str, srt: str, total: float, out: str) -> list[str]:
    """Step 3: the normalised audio + black picture with burned-in subtitles."""
    return [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", audio,
        "-f", "lavfi", "-i", f"color=c=black:s={RADIO_SIZE}:r=24:d={total:.3f}",
        "-filter_complex",
        f"[1:v]subtitles={srt}:force_style='FontSize=22,Outline=1,MarginV=40'[vout]",
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-t", f"{total:.3f}",
        "-movflags", "+faststart", out,
    ]


def timing_report(lines: list[Line], total: float, planned_total: float) -> str:
    rows = ["| shot | slot (s) | line starts | line length | overrun | recommended duration_s |",
            "|---|---|---|---|---|---|"]
    for ln in lines:
        if ln.start is None:
            rows.append(f"| {ln.shot} | {ln.slot_end - ln.slot_start:g} | – | silent | – | – |")
            continue
        flag = f"**+{ln.overrun_s:g} s**" if ln.overrun_s else "fits"
        rows.append(f"| {ln.shot} | {ln.slot_end - ln.slot_start:g} | {ln.start:.2f} | "
                    f"{ln.end - ln.start:.2f} | {flag} | {ln.recommended_s:g} |")
    rows.append(f"\nPlanned length {planned_total:g} s; radio cut length {total:g} s.")
    return "\n".join(rows)


def run(storyboard: dict, only: list[str] | None = None, *, mode: str = "radio",
        out_base: Path | None = None, log_path: Path | None = None) -> Path:
    if mode != "radio":
        raise NotBuiltYet("assemble --mode final (Step 4: pictures, score, both aspect ratios)")
    if only:
        print("  note: --shot is ignored by assemble; the cut always covers the whole film")

    audio: dict[str, Path] = {}
    for shot in storyboard["shots"]:
        if narration.should_speak(shot):
            p = narration.audio_path(storyboard, shot, out_base)
            if not p.exists():
                raise MissingInput(f"{shot['id']}: narration missing; run `py -m pipeline narration`")
            audio[shot["id"]] = p
    durations = {sid: narration.wav_duration(p) for sid, p in audio.items()}
    lines, total = plan_timeline(storyboard, durations, audio)
    srt_text = build_srt(lines, storyboard["end_card"], total)
    planned = sum(s["duration_s"] for s in storyboard["shots"]) + storyboard["end_card"]["duration_s"]

    inputs = {
        "stage": STAGE, "mode": "radio", "recipe": RECIPE_VERSION,
        "audio": {sid: file_hash(p) for sid, p in audio.items()},
        "timeline": [asdict(ln) | {"audio": None} for ln in lines], "srt": srt_text,
        "total": total, "duck": DUCK, "loudness": LOUDNESS, "pad": PAD_EXPR,
    }
    ffmpeg = config.find_tool("ffmpeg")

    def run_ffmpeg(cmd: list[str], cwd: Path) -> None:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[-800:]}")

    def produce(tmp: Path) -> None:
        folder = tmp.parent
        stem = tmp.name.split(".")[0]                      # radio_<hash>
        track, srt = folder / f"{stem}.narration.wav", folder / f"{stem}.srt"
        mix, master = folder / f"{stem}.mix.wav", folder / f"{stem}.master.wav"
        build_narration_track(lines, audio, total, track)
        srt.write_text(srt_text, encoding="utf-8")
        # run inside the cuts folder so the subtitles filter gets a plain relative
        # file name (Windows drive colons break FFmpeg filter syntax)
        run_ffmpeg(ffmpeg_mix_cmd(ffmpeg, track.name, total, mix.name), folder)
        report = loudness.normalize(ffmpeg, mix, master)
        run_ffmpeg(ffmpeg_radio_mux_cmd(ffmpeg, master.name, srt.name, total, tmp.name), folder)
        delivered = loudness.measure(ffmpeg, tmp)          # what the listener actually gets
        report |= {"final_i": float(delivered["input_i"]), "final_tp": float(delivered["input_tp"]),
                   "final_lra": float(delivered["input_lra"])}
        report["problems"] = loudness.problems(report)
        (folder / f"{stem}.loudness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        mix.unlink(missing_ok=True)
        master.unlink(missing_ok=True)

    out = run_model_step(
        stage=STAGE, shot="radio", provider="local", model="ffmpeg",
        params={"mode": "radio", "size": RADIO_SIZE, "duck": DUCK, "loudness": LOUDNESS},
        seed=None, inputs=inputs, ext="mp4", produce=produce, attempts=1,
        out_base=out_base, log_path=log_path,
    )
    stem = out.name.split(".")[0]
    report = timing_report(lines, total, planned)
    out.with_name(stem + ".timing.md").write_text(report, encoding="utf-8")
    print(report)
    lr_path = out.with_name(stem + ".loudness.json")
    if lr_path.exists():
        lr = json.loads(lr_path.read_text(encoding="utf-8"))
        print(f"\n  loudness: {lr['final_i']} LUFS, true peak {lr['final_tp']} dBTP "
              f"(raw mix {lr['raw_i']} LUFS; pre-gain {lr['pre_gain_db']} dB, limiter "
              f"{lr['limit_dbfs']} dBFS, final pass {lr['final_pass']})")
        for p in lr["problems"]:
            print(f"  WARNING: {p}")
    print(f"\n  radio cut: {config.rel(out)}")
    return out
