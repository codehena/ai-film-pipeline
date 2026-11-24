"""Stage: moving shots. Wan 2.2 image-to-video runs on Kaggle (GPU).

This local stage will:
  1. write a job file listing shots whose video hash is not cached yet,
  2. import finished clips (and their runs.jsonl lines) from the Kaggle notebook,
  3. make a Ken Burns pan-and-zoom with FFmpeg for any shot that failed or uses method ken_burns.

Reads:  storyboard.json -> shots[].motion_prompt, video, seed + the shot's keyframe
Writes: outputs/shots/<shot>_<hash>.mp4
Status: stub. Built in Step 3.
"""
from .common import NotBuiltYet


def run(storyboard: dict, only: list[str] | None = None) -> None:
    raise NotBuiltYet("shots stage (Step 3: Kaggle + Ken Burns fallback)")
