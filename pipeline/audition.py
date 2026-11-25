"""Voice audition: speak one shot's line in several voices, so a human can choose by ear.

    py -m pipeline audition --shot s01 --voices Algieba,Charon,Iapetus,Umbriel

Everything except voice_name comes from storyboard.json (text, style, model), so
the comparison is fair: one variable changes. Each take is cached and logged
like any model call; a voice the model rejects is reported and the rest continue.

Writes: outputs/auditions/<shot>-<voice>_<hash>.wav
Then put the winner in storyboard.json -> voice.voice_name and run `narration`.
"""
from __future__ import annotations

import copy
from pathlib import Path

from .common import config
from .common.cache import narration_inputs, speech_style
from .common.modelcall import run_model_step
from .common.storyboard import select_shots
from .narration import ATTEMPTS, wav_duration
from .providers import gemini

STAGE = "auditions"
# Gemini prebuilt voices commonly described as male, with calm/smooth/warm character
DEFAULT_VOICES = ["Algieba", "Charon", "Iapetus", "Umbriel", "Orus"]


def run(storyboard: dict, shot_id: str, voices: list[str], *, synthesize=None,
        out_base: Path | None = None, log_path: Path | None = None) -> dict[str, object]:
    """Returns {voice: wav_path or the exception that stopped that take}."""
    synthesize = synthesize or gemini.synthesize
    shot = select_shots(storyboard, [shot_id])[0]
    text = shot["narration"]["text"].strip()
    results: dict[str, object] = {}

    for voice_name in voices:
        board = copy.deepcopy(storyboard)
        board["voice"]["voice_name"] = voice_name
        voice = board["voice"]
        style = speech_style(board, shot)
        language_code = voice.get("language_code") or board["language"]["narration"]
        inputs = narration_inputs(board, shot) | {"stage": STAGE}
        try:
            path = run_model_step(
                stage=STAGE, shot=f"{shot_id}-{voice_name}", provider="gemini",
                model=voice["model"],
                params={"voice": voice_name, "style": style, "style_mode": voice["style_mode"],
                        "language_code": language_code},
                seed=None, inputs=inputs, ext="wav", attempts=ATTEMPTS,
                produce=lambda p, voice_name=voice_name, style=style: synthesize(
                    model=voice["model"], text=text, voice_name=voice_name, style=style,
                    style_mode=voice["style_mode"], language_code=language_code, out_path=p),
                out_base=out_base, log_path=log_path,
            )
            results[voice_name] = path
            print(f"  {voice_name:12} {wav_duration(path):5.2f} s  {config.rel(path)}")
        except Exception as e:  # one bad voice name must not stop the others
            results[voice_name] = e
            print(f"  {voice_name:12} FAILED  {type(e).__name__}: {str(e)[:160]}")
    return results
