"""Input-hash caching: only regenerate what changed.

Idea: for each shot and stage, collect EVERYTHING that affects the output
(prompt, style block, seed, model, parameters, hash of upstream files) into a
small dict. Hash it. Put the hash in the output filename:

    outputs/keyframes/s03_a1b2c3d4e5f6.png

If that file already exists, the inputs have not changed, so we skip the model
call. Change s03's prompt and only s03 gets a new hash, so only s03 is
regenerated. Because a shot's video inputs include its keyframe's file hash,
a new keyframe automatically means a new video too.

The *_inputs() functions below are the single place that defines "what
affects the output" for each stage.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HASH_LEN = 12


def stable_hash(inputs: dict) -> str:
    """Same inputs -> same hash, whatever order the keys are in."""
    canonical = json.dumps(inputs, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:HASH_LEN]


def file_hash(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:HASH_LEN]


def output_name(shot_id: str, inputs: dict, ext: str) -> str:
    return f"{shot_id}_{stable_hash(inputs)}.{ext.lstrip('.')}"


def character_description(storyboard: dict, shot: dict, cid: str) -> str:
    """A shot's `appearance` replaces a character's description for that shot only
    (e.g. swimming in shorts), so it is part of that shot's keyframe key and no other."""
    override = (shot.get("appearance") or {}).get(cid)
    if override:
        return override
    return next(c["description"] for c in storyboard["characters"] if c["id"] == cid)


def _character_descriptions(storyboard: dict, shot: dict) -> list[str]:
    return [character_description(storyboard, shot, c) for c in shot["characters"]]


def speech_style(storyboard: dict, shot: dict) -> str:
    """The line's own style if it has one, otherwise the film-wide voice.style."""
    meta = shot["narration"].get("speech_metadata") or {}
    return meta.get("style") or storyboard["voice"]["style"]


def narration_inputs(storyboard: dict, shot: dict) -> dict:
    """What changes the narration AUDIO. Pauses are deliberately absent: they only
    move the line in the edit, so changing one must not trigger a new TTS call."""
    voice = storyboard["voice"]
    return {
        "stage": "narration",
        "model": voice["model"],
        "voice_name": voice["voice_name"],
        "style": speech_style(storyboard, shot),
        "style_mode": voice["style_mode"],
        "language_code": voice.get("language_code") or storyboard["language"]["narration"],
        "text": shot["narration"]["text"].strip(),
    }


def keyframe_inputs(
    storyboard: dict, shot: dict, *, model: str, params: dict, reference_hashes: list[str] = ()
) -> dict:
    return {
        "stage": "keyframes",
        "model": model,
        "params": params,
        "style_block": storyboard["style_block"],
        "image_prompt": shot["image_prompt"],
        "characters": _character_descriptions(storyboard, shot),
        "references": list(reference_hashes),
        "seed": shot["seed"],
    }


def video_inputs(shot: dict, *, keyframe_hash: str, model: str, params: dict) -> dict:
    """A Wan clip is always ~5 s (params.frame_num); assembly trims or holds it to the
    shot's length. So the shot's duration is NOT in the key: retiming the narration
    must never invalidate motion clips (audio stays swappable)."""
    return {
        "stage": "shots",
        "model": model,
        "params": params,
        "method": shot["video"]["method"],
        "motion_prompt": shot["motion_prompt"],
        "keyframe": keyframe_hash,
        "seed": shot["seed"],
    }
