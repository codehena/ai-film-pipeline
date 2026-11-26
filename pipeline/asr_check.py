"""ASR round-trip check: transcribe every narration segment and show it next to the script.

    py -m pipeline asr-check

Why: the continuous read is split at pauses, and a pause inside a line can look
exactly like a line break. A split can be wrong even when its time/word ratio
looks fine (FAILURES.md F-12). Hearing the words back is real evidence. It also
shows where the TTS pronunciation might be unclear (a word the recogniser
mishears is worth a native speaker's ear).

The recogniser is imperfect at Amharic, so this is evidence for a human to
read, not an automatic pass/fail. The `similarity` score (0-1) only ranks lines
to look at first.

Cached per segment file hash in outputs/narration/<read>.asr.json, so re-running
after an unrelated change makes no calls. Every call is logged (stage "qa").
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from . import narration
from .common import MissingInput, config
from .common.cache import file_hash, spoken_text
from .common.modelcall import logged_call
from .providers import gemini

MODEL = "gemini-3.5-flash"  # 3.8/3.7 flash returned 503 "high demand" on 2026-11-25 (F-12)
_PUNCT = re.compile(r"[\s።፣፤፥፦፧፨,.;:!?\"'“”]+")


def similarity(script: str, heard: str) -> float:
    a, b = _PUNCT.sub("", script), _PUNCT.sub("", heard)
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 2)


def run(storyboard: dict, *, model: str = MODEL, transcribe=None,
        out_base: Path | None = None, log_path: Path | None = None) -> list[dict]:
    transcribe = transcribe or gemini.transcribe
    spoken = [s for s in storyboard["shots"] if narration.should_speak(s)]
    if not spoken:
        return []
    paths = {s["id"]: narration.audio_path(storyboard, s, out_base) for s in spoken}
    missing = [sid for sid, p in paths.items() if not p.exists()]
    if missing:
        raise MissingInput(f"no narration for {missing}; run `py -m pipeline narration` first")

    first = paths[spoken[0]["id"]]
    read = first.name.split("_")[1].split(".")[0]
    cache_path = first.parent / f"asr_{read}.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    rows = []
    for shot in spoken:
        sid, path = shot["id"], paths[shot["id"]]
        fh = file_hash(path)
        hit = cache.get(sid)
        if hit and hit["file_hash"] == fh and hit["model"] == model:
            heard = hit["heard"]
        else:
            heard = logged_call(lambda path=path: transcribe(model, path), stage="qa", shot=sid,
                                provider="gemini", model=model,
                                params={"task": "asr round-trip", "file_hash": fh},
                                log_path=log_path)
            cache[sid] = {"file_hash": fh, "model": model, "heard": heard}
            # save after every line: a quota error mid-run must not throw away finished work (F-12)
            cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
        # compare with what the TTS was given (respellings included), not the written line
        script = spoken_text(storyboard, shot["narration"]["text"].strip())
        rows.append({"shot": sid, "script": script, "heard": heard,
                     "similarity": similarity(script, heard)})
    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")

    for r in rows:
        print(f"  {r['shot']}  similarity {r['similarity']:.2f}\n"
              f"      script: {r['script']}\n      heard:  {r['heard']}")
    print(f"\n  saved {config.rel(cache_path)}. Read the pairs: does each segment start and end "
          "with its own line's words?")
    return rows
