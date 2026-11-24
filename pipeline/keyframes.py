"""Stage: keyframes. Reference sheet first, then one image per shot (Cloudflare Workers AI, FLUX).

Reads:  storyboard.json -> style_block, characters, shots[].image_prompt, seed
Writes: outputs/keyframes/ref_<character>_<hash>.png, outputs/keyframes/<shot>_<hash>.png
Status: stub. Built in Step 3.
"""
from .common import NotBuiltYet


def run(storyboard: dict, only: list[str] | None = None) -> None:
    raise NotBuiltYet("keyframes stage (Step 3)")
