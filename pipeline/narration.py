"""Stage: narration. Gemini TTS, one cached WAV per shot.

Reads:  storyboard.json -> voice, shots[].narration.text, shots[].narration.speech_metadata.style
Writes: outputs/narration/<shot>_<hash>.wav    (hash = cache.narration_inputs)
Logs:   one runs.jsonl line per TTS attempt, or a cache_hit line if the line is unchanged

Shots whose text is empty are silent; shots still containing "TODO" are skipped
so no free-tier quota is spent on placeholders.
"""
from __future__ import annotations

import wave
from pathlib import Path

from .common import config
from .common.cache import narration_inputs, speech_style, stable_hash
from .common.modelcall import run_model_step
from .common.storyboard import select_shots
from .providers import gemini

STAGE = "narration"
# Free tier: 3 TTS requests/minute (F-08). With server-delay waits, 4 attempts ride out one blocked minute.
ATTEMPTS = 4


def should_speak(shot: dict) -> bool:
    text = shot["narration"]["text"].strip()
    return bool(text) and "TODO" not in text


def audio_path(storyboard: dict, shot: dict, out_base: Path | None = None) -> Path:
    """Where this shot's narration lives. The assembly stage uses this too, so the hash is the contract."""
    h = stable_hash(narration_inputs(storyboard, shot))
    return (out_base or config.OUTPUTS) / STAGE / f"{shot['id']}_{h}.wav"


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def run(storyboard: dict, only: list[str] | None = None, *, synthesize=None,
        out_base: Path | None = None, log_path: Path | None = None) -> dict[str, Path]:
    """Generate (or reuse) narration for each shot. Returns {shot_id: wav_path}."""
    synthesize = synthesize or gemini.synthesize
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
                model=voice["model"], text=shot["narration"]["text"].strip(),
                voice_name=voice["voice_name"], style=style, style_mode=voice["style_mode"],
                language_code=language_code, out_path=p),
            attempts=ATTEMPTS, out_base=out_base, log_path=log_path,
        )
        print(f"  {sid}: {'cached' if before else 'generated'}  {wav_duration(path):5.2f} s  "
              f"{config.rel(path)}")
        done[sid] = path
    return done
