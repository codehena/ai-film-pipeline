"""Stage: assembly with FFmpeg (no AI: same inputs, same output).

Step 2: radio cut  - narration over placeholder music on a black screen.
Step 4: final cut  - shots cut to the storyboard timing, score ducked under the
        voice (sidechaincompress), burned-in English subtitles, loudnorm to
        -14 LUFS / -1 dBTP, AI end card, exported as 9:16 and 16:9.

Reads:  storyboard.json + outputs of every earlier stage
Writes: outputs/cuts/
Status: stub.
"""
from .common import NotBuiltYet


def run(storyboard: dict, only: list[str] | None = None) -> None:
    raise NotBuiltYet("assemble stage (Step 2 radio cut, Step 4 final cut; needs FFmpeg)")
