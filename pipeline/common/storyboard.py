"""Load storyboard.json and check it before any stage runs.

Two layers of checks:
1. JSON Schema (schema/storyboard.schema.json): shape, types, allowed values.
2. Extra rules in Python: things a schema cannot express well, such as the
   total film length or "every character used in a shot must be defined".

If anything is wrong, StoryboardError lists every problem in plain language,
and no stage runs.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from . import config

MIN_FILM_S = 60
MAX_FILM_S = 90


class StoryboardError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        lines = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(f"storyboard has {len(self.problems)} problem(s):\n{lines}")


def load_json(path: Path | str) -> dict:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise StoryboardError([f"file not found: {path}"]) from None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise StoryboardError(
            [f"{path.name} is not valid JSON: line {e.lineno}, column {e.colno}: {e.msg}"]
        ) from None


def load_schema(path: Path | str | None = None) -> dict:
    return json.loads(Path(path or config.SCHEMA).read_text(encoding="utf-8"))


def _where(parts) -> str:
    """['shots', 3, 'seed'] -> 'shots[3].seed'"""
    out = ""
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            out += f".{p}" if out else str(p)
    return out or "(top level)"


def schema_problems(data: dict, schema: dict) -> list[str]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: [str(p) for p in e.absolute_path])
    return [f"{_where(e.absolute_path)}: {e.message}" for e in errors]


def film_duration(data: dict) -> float:
    """Total length in seconds: all shots plus the end card."""
    total = sum(s["duration_s"] for s in data["shots"]) + data["end_card"]["duration_s"]
    return round(total, 3)


def rule_problems(data: dict) -> list[str]:
    problems: list[str] = []

    ids = [s["id"] for s in data["shots"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        problems.append(f"shots: duplicate shot ids {dupes}")

    char_ids = [c["id"] for c in data["characters"]]
    char_dupes = sorted({i for i in char_ids if char_ids.count(i) > 1})
    if char_dupes:
        problems.append(f"characters: duplicate character ids {char_dupes}")

    total = film_duration(data)
    if not MIN_FILM_S <= total <= MAX_FILM_S:
        problems.append(
            f"total length is {total:g} s (shots + end card); it must be between "
            f"{MIN_FILM_S} and {MAX_FILM_S} s"
        )

    for shot in data["shots"]:
        for c in shot["characters"]:
            if c not in char_ids:
                problems.append(
                    f"shot {shot['id']}: character '{c}' is not defined in characters"
                )

    def bad_box(b):
        return b is not None and not (b[0] < b[2] and b[1] < b[3])

    shot_ids = set(ids)
    for shot in data["shots"]:
        n_words = len(shot["narration"]["text"].split())
        last = 0
        for k, beat in enumerate(shot.get("beats", []), 1):
            w = beat["from_word"]
            if w <= last or w >= max(n_words, 1):
                problems.append(f"shot {shot['id']} beat {k}: from_word {w} must increase and be "
                                f"below the line's {n_words} words")
            last = w
            if bad_box(beat.get("safe_box")):
                problems.append(f"shot {shot['id']} beat {k}: safe_box must have x0<x1, y0<y1")
            for c in beat.get("characters", []):
                if c not in char_ids:
                    problems.append(f"shot {shot['id']} beat {k}: character '{c}' is not defined")
            for c in beat.get("appearance", {}):
                if c not in beat.get("characters", []):
                    problems.append(f"shot {shot['id']} beat {k}: appearance for '{c}', who is not in the beat")
        for c in shot.get("appearance", {}):
            if c not in shot["characters"]:
                problems.append(f"shot {shot['id']}: appearance for '{c}', who is not in the shot")
        if bad_box(shot["video"].get("safe_box")):
            problems.append(f"shot {shot['id']}: video.safe_box must be [x0, y0, x1, y1] with x0<x1, y0<y1")
        src = (shot["video"].get("still") or {}).get("from")
        if src and (src not in shot_ids or src == shot["id"]):
            problems.append(f"shot {shot['id']}: video.still.from '{src}' must be another existing shot")

    for cue in data["music_cues"]:
        if cue["end_s"] <= cue["start_s"]:
            problems.append(f"music cue {cue['id']}: end_s must be after start_s")
        if cue["end_s"] > total:
            problems.append(
                f"music cue {cue['id']}: ends at {cue['end_s']:g} s but the film is {total:g} s"
            )
    return problems


def find_todos(obj, where: str = "") -> list[str]:
    """Paths of every string that still contains 'TODO' (warnings, not errors)."""
    found: list[str] = []
    if isinstance(obj, str):
        if "TODO" in obj:
            found.append(where or "(top level)")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if not where and k == "notes":  # free text for humans, may mention TODOs
                continue
            found += find_todos(v, f"{where}.{k}" if where else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += find_todos(v, f"{where}[{i}]")
    return found


def validate(data: dict, schema: dict | None = None) -> list[str]:
    """Raise StoryboardError if invalid. Return a list of warnings (TODOs left)."""
    problems = schema_problems(data, schema or load_schema())
    if not problems:  # only check rules once the shape is right, to avoid confusing errors
        problems = rule_problems(data)
    if problems:
        raise StoryboardError(problems)
    return [f"{w} is still a TODO placeholder" for w in find_todos(data)]


def load_storyboard(path: Path | str | None = None) -> dict:
    """Load and validate. Every stage calls this before doing anything."""
    data = load_json(path or config.STORYBOARD)
    validate(data)
    return data


def select_shots(data: dict, only: list[str] | None = None) -> list[dict]:
    """All shots, or just the ids in `only` (e.g. ['s03']) for a targeted re-run."""
    if not only:
        return list(data["shots"])
    known = {s["id"] for s in data["shots"]}
    unknown = [i for i in only if i not in known]
    if unknown:
        raise StoryboardError([f"unknown shot id(s): {unknown}"])
    return [s for s in data["shots"] if s["id"] in only]
