"""Stage: narration. Gemini TTS, two modes (storyboard voice.mode):

per_line (default): one TTS call per shot.
    Writes outputs/narration/<shot>_<hash>.wav (hash = cache.narration_inputs).
    Editing one line costs one call. But each call is independent, so the voice
    and delivery can drift between lines, and a full read costs one call per shot.

continuous: the whole narration in ONE TTS call, so one voice and one flow throughout.
    Writes outputs/narration/full_<hash>.wav, then splits it at the pauses into
    outputs/narration/<shot>_<hash>.cont.wav (see common/silence.py) and a
    full_<hash>.split.json report. Any edit costs one call (the whole read).
    A pause inside a line can look exactly like a line break, so a split can be
    wrong even when its ratios look fine (F-12). Verified corrections for a
    specific read go in narration_splits.json (committed); check with asr-check.
    Per-line speech_metadata.style is ignored: one read has one style.

Either way, the assembly stage finds each shot's audio with audio_path().
Silent and TODO lines are skipped, so no quota is spent on placeholders.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

from .common import config
from .common.cache import file_hash, narration_inputs, speech_style, spoken_text, stable_hash
from .common.modelcall import run_model_step
from .common.silence import SplitError, split_lines, write_segment
from .common.storyboard import select_shots
from .providers import gemini

STAGE = "narration"
# Free tier: 3 TTS requests/minute (F-08). With server-delay waits, 4 attempts ride out one blocked minute.
ATTEMPTS = 4
# Asked of the model in continuous mode, so line breaks become clear pauses to split at
PAUSE_HINT = "Leave a clear pause of about two seconds between paragraphs"
SPLIT_RATIO_WARN = (0.5, 2.0)  # a line's share of time vs its share of words
PAD_S = 0.1  # handle around each segment so soft onsets are not clipped (F-12)


def should_speak(shot: dict) -> bool:
    text = shot["narration"]["text"].strip()
    return bool(text) and "TODO" not in text


def mode(storyboard: dict) -> str:
    return storyboard["voice"].get("mode", "per_line")


def continuous_inputs(storyboard: dict) -> dict:
    voice = storyboard["voice"]
    return {
        "stage": STAGE, "mode": "continuous",
        "model": voice["model"], "voice_name": voice["voice_name"], "style": voice["style"],
        "style_mode": voice["style_mode"],
        "language_code": voice.get("language_code") or storyboard["language"]["narration"],
        "lines": [[s["id"], spoken_text(storyboard, s["narration"]["text"].strip())]
                  for s in storyboard["shots"] if should_speak(s)],
        "pause_hint": PAUSE_HINT,
    }


def split_overrides(read_name: str, path: Path | None = None,
                    audio_hash: str | None = None) -> dict[str, list[float]]:
    """Verified corrections for one specific read, e.g. {"s03": [19.02, 23.16]}.

    Keyed by the read's file name (full_<hash>), because a new read is a new
    recording with new timings: corrections never leak onto another take.
    The name is a hash of the *inputs*, so a fresh clone re-reading the same
    text gets the same name but a different recording (TTS is not
    deterministic). An entry's `audio_hash` pins it to the exact recording
    it was verified on; a different recording gets the automatic split.
    """
    p = Path(path or config.SPLIT_OVERRIDES)
    if not p.exists():
        return {}
    entry = json.loads(p.read_text(encoding="utf-8")).get(read_name) or {}
    pinned = entry.get("audio_hash")
    if pinned and audio_hash and pinned != audio_hash:
        print(f"  note: split corrections for {read_name} were verified on another recording "
              f"({pinned}, this one is {audio_hash}); using the automatic split. Check with asr-check.")
        return {}
    return {sid: [float(a), float(b)] for sid, (a, b) in entry.get("spans", {}).items()}


def apply_overrides(spans: list[tuple[float, float]], ids: list[str],
                    overrides: dict[str, list[float]], total: float) -> list[tuple[float, float]]:
    """Replace the automatic span of each overridden line, then check the result is sane."""
    unknown = sorted(set(overrides) - set(ids))
    if unknown:
        raise SplitError(f"{config.SPLIT_OVERRIDES.name}: unknown shot ids {unknown}")
    out = [tuple(overrides[sid]) if sid in overrides else span for sid, span in zip(ids, spans)]
    for sid, (a, b) in zip(ids, out):
        if not 0 <= a < b <= total + 0.01:
            raise SplitError(f"{config.SPLIT_OVERRIDES.name}: {sid} span {a}-{b} is outside the read")
    for (sid1, (_, end1)), (sid2, (start2, _)) in zip(zip(ids, out), zip(ids[1:], out[1:])):
        if end1 > start2:
            raise SplitError(f"{config.SPLIT_OVERRIDES.name}: {sid1} ends after {sid2} starts; "
                             "correct the neighbouring line too")
    return out


def pad_spans(spans: list[tuple[float, float]], total: float, pad: float) -> list[tuple[float, float]]:
    """Give each segment a little handle so soft first/last syllables below the silence
    threshold are not clipped, never reaching past the middle of the gap to a neighbour."""
    out = []
    for i, (a, b) in enumerate(spans):
        lo = (spans[i - 1][1] + a) / 2 if i else 0.0
        hi = (b + spans[i + 1][0]) / 2 if i + 1 < len(spans) else total
        out.append((max(lo, a - pad), min(hi, b + pad)))
    return out


def audio_path(storyboard: dict, shot: dict, out_base: Path | None = None) -> Path:
    """Where this shot's narration lives. The assembly stage uses this too, so the hash is the contract."""
    folder = (out_base or config.OUTPUTS) / STAGE
    if mode(storyboard) == "continuous":
        return folder / f"{shot['id']}_{stable_hash(continuous_inputs(storyboard))}.cont.wav"
    return folder / f"{shot['id']}_{stable_hash(narration_inputs(storyboard, shot))}.wav"


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def run(storyboard: dict, only: list[str] | None = None, *, synthesize=None,
        out_base: Path | None = None, log_path: Path | None = None) -> dict[str, Path]:
    """Generate (or reuse) narration. Returns {shot_id: wav_path}."""
    synthesize = synthesize or gemini.synthesize
    if mode(storyboard) == "continuous":
        return _run_continuous(storyboard, only, synthesize, out_base, log_path)
    return _run_per_line(storyboard, only, synthesize, out_base, log_path)


def _run_per_line(storyboard, only, synthesize, out_base, log_path) -> dict[str, Path]:
    voice = storyboard["voice"]
    language_code = voice.get("language_code") or storyboard["language"]["narration"]
    done: dict[str, Path] = {}

    for shot in select_shots(storyboard, only):
        sid = shot["id"]
        if not should_speak(shot):
            reason = "silent" if not shot["narration"]["text"].strip() else "TODO placeholder"
            print(f"  {sid}: skipped ({reason})")
            continue
        inputs = narration_inputs(storyboard, shot)
        style = speech_style(storyboard, shot)
        params = {"voice": voice["voice_name"], "style": style,
                  "style_mode": voice["style_mode"], "language_code": language_code}
        before = audio_path(storyboard, shot, out_base).exists()

        path = run_model_step(
            stage=STAGE, shot=sid, provider="gemini", model=voice["model"], params=params,
            seed=None, inputs=inputs, ext="wav",
            produce=lambda p, shot=shot, style=style: synthesize(
                model=voice["model"], text=spoken_text(storyboard, shot["narration"]["text"].strip()),
                voice_name=voice["voice_name"], style=style, style_mode=voice["style_mode"],
                language_code=language_code, out_path=p),
            attempts=ATTEMPTS, out_base=out_base, log_path=log_path,
        )
        print(f"  {sid}: {'cached' if before else 'generated'}  {wav_duration(path):5.2f} s  "
              f"{config.rel(path)}")
        done[sid] = path
    return done


def _run_continuous(storyboard, only, synthesize, out_base, log_path) -> dict[str, Path]:
    voice = storyboard["voice"]
    if only:
        print("  note: continuous mode always reads the whole narration (--shot ignored)")
    overrides = [s["id"] for s in storyboard["shots"]
                 if (s["narration"].get("speech_metadata") or {}).get("style")]
    if overrides:
        print(f"  note: per-line style ignored in continuous mode for {overrides}")
    inputs = continuous_inputs(storyboard)
    lines = inputs["lines"]
    if not lines:
        print("  nothing to read (every line is silent or TODO)")
        return {}
    style = f"{voice['style']}. {PAUSE_HINT}"
    params = {"voice": voice["voice_name"], "style": style, "style_mode": voice["style_mode"],
              "language_code": inputs["language_code"], "mode": "continuous", "lines": len(lines)}

    full = run_model_step(
        stage=STAGE, shot="full", provider="gemini", model=voice["model"], params=params,
        seed=None, inputs=inputs, ext="wav",
        produce=lambda p: synthesize(
            model=voice["model"], text="\n\n".join(text for _, text in lines),
            voice_name=voice["voice_name"], style=style, style_mode=voice["style_mode"],
            language_code=inputs["language_code"], out_path=p),
        attempts=ATTEMPTS, out_base=out_base, log_path=log_path,
    )

    by_id = {s["id"]: s for s in storyboard["shots"]}
    targets = {sid: audio_path(storyboard, by_id[sid], out_base) for sid, _ in lines}
    report_path = full.with_name(full.name.replace(".wav", ".split.json"))
    overrides = split_overrides(full.stem, audio_hash=file_hash(full))
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    fresh = (isinstance(report, dict) and report.get("overrides") == overrides
             and report.get("pad_s") == PAD_S
             and all(p.exists() for p in targets.values()))
    if not fresh:
        words = [len(text.split()) for _, text in lines]
        spans = split_lines(full, words)
        ids = [sid for sid, _ in lines]
        spans = apply_overrides(spans, ids, overrides, wav_duration(full))
        spans = pad_spans(spans, wav_duration(full), PAD_S)
        for sid, (start, end) in zip(ids, spans):
            write_segment(full, start, end, targets[sid])
        speech = sum(e - s for s, e in spans)
        rows = []
        for sid, wc, (start, end) in zip(ids, words, spans):
            ratio = ((end - start) / speech) / (wc / sum(words))
            rows.append({"shot": sid, "start": round(start, 3), "end": round(end, 3), "words": wc,
                         "time_vs_word_share": round(ratio, 2),
                         "source": "override" if sid in overrides else "auto"})
        report = {"overrides": overrides, "pad_s": PAD_S, "lines": rows}
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  split full read into {len(spans)} lines"
              + (f" ({len(overrides)} corrected from {config.SPLIT_OVERRIDES.name})" if overrides else ""))

    done: dict[str, Path] = {}
    lo, hi = SPLIT_RATIO_WARN
    for row in report["lines"]:
        flag = "" if lo <= row["time_vs_word_share"] <= hi else "  <-- check this split by ear"
        src = "  (corrected)" if row["source"] == "override" else ""
        path = targets[row["shot"]]
        print(f"  {row['shot']}: {row['start']:6.2f}-{row['end']:6.2f} s  {wav_duration(path):5.2f} s  "
              f"{row['words']:2} words  share x{row['time_vs_word_share']}{src}{flag}")
        done[row["shot"]] = path
    print(f"  full read: {config.rel(full)}  ({wav_duration(full):.2f} s)")
    return done
