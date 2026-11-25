"""Stage: assembly with FFmpeg (no AI: same inputs give the same output).

Mode "radio" (Phase 1 prototype, built now):
  narration over a placeholder pad on a black screen, with burned-in English
  subtitles. The pad is ducked under the voice (sidechaincompress) and the mix
  is normalised to -14 LUFS / -1 dBTP in two passes (common/loudness.py), with the
  measurements written to radio_<hash>.loudness.json. Its main job is to show whether each line
  fits its shot: the timing report recommends shot durations from the measured
  narration.

Mode "final": the film. For every shot, a motion clip if one was imported
  (shots.clip_path), otherwise a Ken Burns move on its keyframe (render.py). The same
  audio chain as the radio cut, with the chosen score (music.score_path) in place
  of the placeholder pad, the end card as a card, and one export per storyboard
  aspect ratio (16:9 and 9:16) with subtitles placed for that frame.

Reads:  storyboard.json + outputs/narration/ (+ keyframes/, shots/, music/ for final)
Writes: outputs/cuts/radio_<hash>.mp4 or final-16x9_<hash>.mp4 / final-9x16_<hash>.mp4
        (+ .srt, .timing.md, .loudness.json; reusable parts in outputs/cuts/parts/)
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import textwrap
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

from . import keyframes, music, narration, render, shots
from .common import MissingInput, config, loudness
from .common.cache import file_hash, stable_hash
from .common.modelcall import run_model_step

STAGE = "cuts"
# bump when the FFmpeg recipe changes, so old cuts are not reused
# 2: two-pass loudness (pre-gain + limiter + linear loudnorm) replaced single-pass loudnorm (F-11)
# 3: adaptive limiter rounds + 4x oversampled limiter (draft 4 mix fell back to dynamic)
# 4: long subtitles split into consecutive cues (draft 4 lines were up to 75 chars wide)
RECIPE_VERSION = 4
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
            # up to the next 0.1 s (was 0.5 s, which added 0-0.5 s of arbitrary silence per line)
            line.recommended_s = math.ceil(round((before + d + after) * 10, 6)) / 10
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


def wrap_subtitle(text: str, width: int = SUB_MAX_CHARS) -> str:
    """At most two lines, ~`width` chars each. A too-long subtitle gets wider lines, never lost
    words (split_caption keeps that from happening in practice)."""
    lines = textwrap.wrap(text, width)
    while len(lines) > 2:
        width += 4
        lines = textwrap.wrap(text, width)
    return "\n".join(lines)


CUE_MAX_CHARS = 2 * SUB_MAX_CHARS + 4  # what fits on two ~40-character lines


def split_caption(text: str, limit: int = CUE_MAX_CHARS) -> list[str]:
    """Split a long subtitle into consecutive cues at sentence and clause breaks, so each
    cue fits on two short lines. Words are never dropped or reordered."""
    if len(text) <= limit:
        return [text]
    pieces = [p for p in re.split(r"(?<=[.;:!?,])\s+", text) if p]
    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 1 + len(piece) <= limit:
            chunks[-1] += " " + piece
        else:
            chunks.append(piece)
    return chunks


def build_srt(lines: list[Line], end_card: dict, total: float, *, width: int = SUB_MAX_CHARS,
              end_card_cue: bool = True) -> str:
    """Subtitles for the timeline. `width` is the characters per row (narrower for 9:16);
    the final cut draws the end card as a card, so it passes end_card_cue=False."""
    cues = []
    for line in lines:
        if line.start is not None and line.subtitle:
            end = max(line.end, line.start + 1.0)  # at least 1 s on screen
            parts = split_caption(line.subtitle, 2 * width + 4)
            chars = sum(len(p) for p in parts)
            t = line.start
            for k, part in enumerate(parts):         # time shared in proportion to length
                t_end = end if k == len(parts) - 1 else t + (end - line.start) * len(part) / chars
                cues.append((t, t_end, wrap_subtitle(part, width)))
                t = t_end
    if end_card_cue:
        cues.append((total - end_card["duration_s"], total, wrap_subtitle(end_card["text"], width)))
    return "\n".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{txt}\n"
                     for i, (a, b, txt) in enumerate(cues, 1))


def ffmpeg_mix_cmd(ffmpeg: str, track: str, total: float, out: str,
                   score: str | None = None) -> list[str]:
    """Step 1: narration + music ducked under it (the chosen score trimmed to the film,
    or the placeholder pad). No loudness processing yet."""
    music_in = (["-i", score] if score else
                ["-f", "lavfi", "-i", f"aevalsrc='{PAD_EXPR}':s=48000:d={total:.3f}"])
    trim = (f"aresample=48000,aformat=channel_layouts=mono,atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
            if score else "")
    graph = (
        "[0:a]aresample=48000,asplit=2[voice][sc];"
        f"[1:a]{trim}volume=0.5,afade=t=in:d=2,afade=t=out:st={max(0, total - 3):.3f}:d=3[pad];"
        f"[pad][sc]sidechaincompress={DUCK}[ducked];"
        "[voice][ducked]amix=inputs=2:normalize=0:duration=first[aout]"
    )
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", track, *music_in,
            "-filter_complex", graph, "-map", "[aout]", "-t", f"{total:.3f}", out]


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


def run_ffmpeg(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[-800:]}")


def collect_narration(storyboard: dict, out_base: Path | None = None):
    """Every spoken line's audio and the timeline built from it (shared by both modes)."""
    audio: dict[str, Path] = {}
    for shot in storyboard["shots"]:
        if narration.should_speak(shot):
            p = narration.audio_path(storyboard, shot, out_base)
            if not p.exists():
                raise MissingInput(f"{shot['id']}: narration missing; run `py -m pipeline narration`")
            audio[shot["id"]] = p
    durations = {sid: narration.wav_duration(p) for sid, p in audio.items()}
    lines, total = plan_timeline(storyboard, durations, audio)
    return audio, lines, total


def master_audio(ffmpeg: str, folder: Path, stem: str, lines: list[Line], audio: dict[str, Path],
                 total: float, score: Path | None = None) -> tuple[Path, dict]:
    """Narration track + ducked music, normalised (two-pass). Returns the WAV and its report."""
    track, mix, master = (folder / f"{stem}.narration.wav", folder / f"{stem}.mix.wav",
                          folder / f"{stem}.master.wav")
    build_narration_track(lines, audio, total, track)
    run_ffmpeg(ffmpeg_mix_cmd(ffmpeg, track.name, total, mix.name,
                              str(score) if score else None), folder)
    report = loudness.normalize(ffmpeg, mix, master)
    mix.unlink(missing_ok=True)
    return master, report


def finish_loudness(ffmpeg: str, delivered: Path, report: dict, report_path: Path) -> dict:
    """Measure what the viewer actually gets and record it next to the file."""
    m = loudness.measure(ffmpeg, delivered)
    report = report | {"final_i": float(m["input_i"]), "final_tp": float(m["input_tp"]),
                       "final_lra": float(m["input_lra"])}
    report["problems"] = loudness.problems(report)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def print_loudness(report_path: Path) -> None:
    if report_path.exists():
        lr = json.loads(report_path.read_text(encoding="utf-8"))
        print(f"  loudness: {lr['final_i']} LUFS, true peak {lr['final_tp']} dBTP "
              f"(final pass {lr['final_pass']})")
        for p in lr["problems"]:
            print(f"  WARNING: {p}")


def run(storyboard: dict, only: list[str] | None = None, *, mode: str = "radio",
        out_base: Path | None = None, log_path: Path | None = None):
    if only:
        print("  note: --shot is ignored by assemble; the cut always covers the whole film")
    if mode == "final":
        return run_final(storyboard, out_base=out_base, log_path=log_path)

    audio, lines, total = collect_narration(storyboard, out_base)
    srt_text = build_srt(lines, storyboard["end_card"], total)
    planned = sum(s["duration_s"] for s in storyboard["shots"]) + storyboard["end_card"]["duration_s"]
    inputs = {
        "stage": STAGE, "mode": "radio", "recipe": RECIPE_VERSION,
        "audio": {sid: file_hash(p) for sid, p in audio.items()},
        "timeline": [asdict(ln) | {"audio": None} for ln in lines], "srt": srt_text,
        "total": total, "duck": DUCK, "loudness": LOUDNESS, "pad": PAD_EXPR,
    }
    ffmpeg = config.find_tool("ffmpeg")

    def produce(tmp: Path) -> None:
        folder = tmp.parent
        stem = tmp.name.split(".")[0]                      # radio_<hash>
        srt = folder / f"{stem}.srt"
        srt.write_text(srt_text, encoding="utf-8")
        master, report = master_audio(ffmpeg, folder, stem, lines, audio, total)
        # run inside the cuts folder so the subtitles filter gets a plain relative
        # file name (Windows drive colons break FFmpeg filter syntax)
        run_ffmpeg(ffmpeg_radio_mux_cmd(ffmpeg, master.name, srt.name, total, tmp.name), folder)
        finish_loudness(ffmpeg, tmp, report, folder / f"{stem}.loudness.json")
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
    print()
    print_loudness(out.with_name(stem + ".loudness.json"))
    print(f"\n  radio cut: {config.rel(out)}")
    return out


# ---------------------------------------------------------------- final cut
RENDER_VERSION = 1  # bump when render.py's picture recipe changes
SUB_WIDTH = {"16:9": SUB_MAX_CHARS, "9:16": 26}  # characters per subtitle row


def shot_visual(storyboard: dict, shot: dict, out_base: Path | None) -> dict:
    """What fills a shot: its motion clip if imported, else a Ken Burns move on a keyframe
    (its own, or another shot's for an insert via video.still.from)."""
    by_id = {s["id"]: s for s in storyboard["shots"]}
    video = shot["video"]
    focus = tuple(video.get("focus", (0.5, 0.5)))
    if shots.wants_clip(shot):
        clip = shots.clip_path(storyboard, shot, out_base)
        if clip.exists():
            return {"kind": "clip", "path": clip, "focus": focus}
    src_shot = by_id[video["still"]["from"]] if video.get("still") else shot
    kf = keyframes.keyframe_path(storyboard, src_shot, out_base)
    if not kf.exists():
        raise MissingInput(f"{shot['id']}: keyframe {kf.name} missing; run `py -m pipeline keyframes`")
    return {"kind": "still", "path": kf, "focus": focus, "move": render.move_for(shot)}


def _segment(ffmpeg: str, parts: Path, shot_id: str, ratio: str, visual: dict, frames: int) -> Path:
    """One shot, one aspect ratio: cached by everything that changes its pixels."""
    key = {"v": RENDER_VERSION, "ratio": ratio, "frames": frames, "kind": visual["kind"],
           "source": file_hash(visual["path"]), "focus": visual["focus"],
           "move": asdict(visual["move"]) if visual["kind"] == "still" else None}
    out = parts / f"{shot_id}_{ratio.replace(':', 'x')}_{stable_hash(key)}.mp4"
    if not out.exists():
        tmp = out.with_name(out.stem + ".part.mp4")
        wh = render.image_size(visual["path"])
        if visual["kind"] == "clip":
            cmd = render.clip_segment_cmd(ffmpeg, visual["path"], wh, ratio, visual["focus"], frames, tmp)
        else:
            cmd = render.still_segment_cmd(ffmpeg, visual["path"], wh, ratio, visual["focus"],
                                           visual["move"], frames, tmp)
        run_ffmpeg(cmd)
        tmp.replace(out)
    return out


def _card(ffmpeg: str, parts: Path, end_card: dict, ratio: str, frames: int) -> Path:
    text = wrap_subtitle(end_card["text"], SUB_WIDTH[ratio])
    key = {"v": RENDER_VERSION, "ratio": ratio, "frames": frames, "text": text,
           "style": render.card_style(ratio)}
    h = stable_hash(key)
    out = parts / f"card_{ratio.replace(':', 'x')}_{h}.mp4"
    if not out.exists():
        srt = parts / f"card_{h}.srt"
        srt.write_text(f"1\n{_ts(0)} --> {_ts(frames / render.FPS + 1)}\n{text}\n", encoding="utf-8")
        tmp = f"{out.stem}.part.mp4"
        run_ffmpeg(render.card_segment_cmd(ffmpeg, srt.name, ratio, frames, tmp), parts)
        (parts / tmp).replace(out)
    return out


def run_final(storyboard: dict, out_base: Path | None = None,
              log_path: Path | None = None) -> dict[str, Path]:
    audio, lines, total = collect_narration(storyboard, out_base)
    ffmpeg = config.find_tool("ffmpeg")
    folder = config.output_dir(STAGE, out_base)
    parts = config.output_dir(f"{STAGE}/parts", out_base)
    score = music.score_path(storyboard, out_base)
    visuals = {s["id"]: shot_visual(storyboard, s, out_base) for s in storyboard["shots"]}
    last_end = lines[-1].slot_end
    bounds = [(ln.slot_start, ln.slot_end) for ln in lines] + [(last_end, total)]
    frames = render.frame_bounds(bounds)

    audio_key = {"audio": {sid: file_hash(p) for sid, p in audio.items()},
                 "timeline": [asdict(ln) | {"audio": None} for ln in lines], "total": total,
                 "score": file_hash(score) if score else None, "pad": None if score else PAD_EXPR,
                 "duck": DUCK, "loudness": LOUDNESS, "recipe": RECIPE_VERSION}
    master_stem = f"master_{stable_hash(audio_key)}"
    master = folder / f"{master_stem}.master.wav"
    master_report = folder / f"{master_stem}.loudness.json"

    outputs = {}
    for ratio in storyboard["format"]["aspect_ratios"]:
        tag = ratio.replace(":", "x")
        srt_text = build_srt(lines, storyboard["end_card"], total, width=SUB_WIDTH[ratio],
                             end_card_cue=False)
        inputs = {"stage": STAGE, "mode": "final", "ratio": ratio, "render": RENDER_VERSION,
                  "audio": audio_key, "srt": srt_text, "card": storyboard["end_card"],
                  "shots": [{"id": sid, "kind": v["kind"], "source": file_hash(v["path"]),
                             "focus": v["focus"], "frames": f,
                             "move": asdict(v["move"]) if v["kind"] == "still" else None}
                            for (sid, v), f in zip(visuals.items(), frames)]}

        def produce(tmp: Path, ratio=ratio, tag=tag, srt_text=srt_text) -> None:
            if not master.exists():                      # one audio master for both ratios
                _, report = master_audio(ffmpeg, folder, master_stem, lines, audio, total, score)
                master_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
            segs = [_segment(ffmpeg, parts, sid, ratio, visuals[sid], f)
                    for sid, f in zip(visuals, frames)]
            segs.append(_card(ffmpeg, parts, storyboard["end_card"], ratio, frames[-1]))
            stem = tmp.name.split(".")[0]
            listing = parts / f"{stem}.concat.txt"
            listing.write_text("".join(f"file '{p.name}'\n" for p in segs), encoding="utf-8")
            video = parts / f"{stem}.video.mp4"
            run_ffmpeg([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                        "-safe", "0", "-i", listing.name, "-c", "copy", video.name], parts)
            srt = folder / f"{stem}.srt"
            srt.write_text(srt_text, encoding="utf-8")
            run_ffmpeg(render.mux_cmd(ffmpeg, f"parts/{video.name}", master.name, srt.name, ratio,
                                      total, tmp.name), folder)
            report = json.loads(master_report.read_text(encoding="utf-8"))
            finish_loudness(ffmpeg, tmp, report, folder / f"{stem}.loudness.json")
            video.unlink(missing_ok=True)
            listing.unlink(missing_ok=True)

        out = run_model_step(
            stage=STAGE, shot=f"final-{tag}", provider="local", model="ffmpeg",
            params={"mode": "final", "ratio": ratio, "size": "x".join(map(str, render.FORMATS[ratio])),
                    "score": "chosen" if score else "placeholder pad",
                    "clips": sum(v["kind"] == "clip" for v in visuals.values())},
            seed=None, inputs=inputs, ext="mp4", produce=produce, attempts=1,
            out_base=out_base, log_path=log_path)
        outputs[ratio] = out
        print(f"\n  final {ratio}: {config.rel(out)}  ({render.media_duration(out):.2f} s)")
        print_loudness(out.with_name(out.name.split(".")[0] + ".loudness.json"))
    kinds = {sid: v["kind"] for sid, v in visuals.items()}
    print(f"  shots: {sum(k == 'clip' for k in kinds.values())} motion clip(s), "
          f"{sum(k == 'still' for k in kinds.values())} Ken Burns; music: "
          f"{'chosen score' if score else 'placeholder pad'}")
    return outputs
