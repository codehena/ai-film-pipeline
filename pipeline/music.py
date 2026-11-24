"""Stage: music. ACE-Step 1.5 runs on Kaggle (GPU); this stage writes the job and imports candidates.

Reads:  storyboard.json -> music_cues
Writes: outputs/music/<cue>_<hash>_cand<N>.wav, plus the chosen candidate
Status: stub. Built in Step 3.
"""
from .common import NotBuiltYet


def run(storyboard: dict, only: list[str] | None = None) -> None:
    raise NotBuiltYet("music stage (Step 3: Kaggle)")
