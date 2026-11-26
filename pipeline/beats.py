"""Visual beats: several pictures inside one narration shot, each landing on a chosen word.

A narration line that lists four things (bees, birds, calves, chickens) used to sit on
ONE picture for 12 s, so the images arrived after the words (FAILURES.md F-20).
A shot can now declare `beats`: each beat has its own image and starts at the word it
illustrates (`from_word`, an index into the narration text).

Timing comes from the narration that already exists, never from a new model call: a
word's start is estimated from its share of the line's characters (Amharic speech is
close to uniform per character), and the picture lands LEAD_S before the word.

Units: every shot yields a list of visual units. Unit 0 is the shot itself (same id,
so existing keyframes, segments and clip names stay valid); beat k is "<shot>-b<k>".
Each unit has its own keyframe, segment and Wan clip contract. Narration never reads
these fields, so its hash is untouched (tests/test_beats.py).
"""
from __future__ import annotations

import re

LEAD_S = 0.15     # the picture arrives just before the word it shows
MIN_BEAT_S = 0.8  # never cut faster than this
_PUNCT = re.compile(r"[።፣፤፥፦፧፨,.;:!?\"'“”()]")


def visual_units(shot: dict) -> list[dict]:
    """The shot itself, then one shot-like dict per beat (inheriting what it doesn't set)."""
    units = [shot]
    for k, b in enumerate(shot.get("beats", []), 1):
        video = {"method": shot["video"]["method"], "fallback": shot["video"]["fallback"]}
        for key in ("focus", "safe_box"):
            if key in b:
                video[key] = b[key]
        units.append({
            "id": f"{shot['id']}-b{k}", "parent": shot["id"], "from_word": b["from_word"],
            "image_prompt": b["image_prompt"],
            "motion_prompt": b.get("motion_prompt", shot["motion_prompt"]),
            "characters": b.get("characters", []), "appearance": b.get("appearance", {}),
            "seed": b.get("seed", shot["seed"]), "video": video,
        })
    return units


def word_starts(text: str) -> list[float]:
    """Each word's start as a fraction (0-1) of the spoken line, by character share."""
    lengths = [max(len(_PUNCT.sub("", w)), 1) for w in text.split()]
    total, acc, out = sum(lengths), 0, []
    for n in lengths:
        out.append(acc / total)
        acc += n
    return out


def unit_bounds(shot: dict, slot: tuple[float, float],
                voice: tuple[float, float] | None) -> list[tuple[float, float]]:
    """(start, end) in film seconds for every visual unit of a shot."""
    units = visual_units(shot)
    s0, s1 = slot
    if len(units) == 1:
        return [slot]
    words = shot["narration"]["text"].split()
    starts = [s0]
    if voice is None:                                   # silent shot: share the slot evenly
        step = (s1 - s0) / len(units)
        starts += [s0 + step * k for k in range(1, len(units))]
    else:
        frac = word_starts(shot["narration"]["text"])
        v0, v1 = voice
        for i, u in enumerate(units[1:], 1):
            w = min(u["from_word"], len(words) - 1)
            t = v0 + (v1 - v0) * frac[w] - LEAD_S
            remaining = len(units) - i                  # units still to fit after this one
            t = max(t, starts[-1] + MIN_BEAT_S)
            t = min(t, s1 - MIN_BEAT_S * remaining)
            starts.append(t)
    ends = starts[1:] + [s1]
    return list(zip(starts, ends))
