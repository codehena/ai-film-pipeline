"""Stage: narration. Gemini TTS, one audio file per shot.

Reads:  storyboard.json -> voice, language.narration, shots[].narration.text
Writes: outputs/narration/<shot>_<hash>.wav   (hash from cache.narration_inputs)
Status: stub. Built in Step 2 (radio cut).
"""
from .common import NotBuiltYet


def run(storyboard: dict, only: list[str] | None = None) -> None:
    raise NotBuiltYet("narration stage (Step 2: radio cut)")
