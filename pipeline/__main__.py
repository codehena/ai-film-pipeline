"""Command line entry point.

    py -m pipeline validate              check storyboard.json
    py -m pipeline narration --shot s03  run one stage (optionally for one shot)
    py -m pipeline film                  run every stage in order, skipping cached work

(On Mac/Linux use `python3` instead of `py`.)
"""
from __future__ import annotations

import argparse
import sys

from . import assemble, keyframes, music, narration, shots, smoke
from .common import NotBuiltYet, config
from .common.storyboard import StoryboardError, film_duration, load_json, validate

STAGES = {
    "narration": narration.run,
    "keyframes": keyframes.run,
    "shots": shots.run,
    "music": music.run,
    "assemble": assemble.run,
}
FILM_ORDER = ("narration", "keyframes", "shots", "music", "assemble")
MAX_WARNINGS_SHOWN = 8


def check_storyboard(path, *, show_warnings: bool = True) -> dict:
    data = load_json(path)
    warnings = validate(data)
    print(f"storyboard OK ({len(data['shots'])} shots, {film_duration(data):g} s incl. end card)")
    if show_warnings and warnings:
        print(f"warning: {len(warnings)} TODO placeholder(s) left, e.g.:")
        for w in warnings[:MAX_WARNINGS_SHOWN]:
            print(f"  - {w}")
        if len(warnings) > MAX_WARNINGS_SHOWN:
            print(f"  ... and {len(warnings) - MAX_WARNINGS_SHOWN} more")
    return data


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pipeline", description="Heritage Short film pipeline")
    p.add_argument("--storyboard", default=str(config.STORYBOARD), help="path to storyboard.json")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check storyboard.json against the schema and rules")
    sub.add_parser("smoke", help="call each provider once and log latency")
    for name in STAGES:
        sp = sub.add_parser(name, help=f"run the {name} stage")
        sp.add_argument("--shot", action="append", metavar="ID",
                        help="only this shot (repeatable), e.g. --shot s03")
    sub.add_parser("film", help="run every stage in order (cached work is skipped)")
    return p


def main(argv: list[str] | None = None) -> int:
    # Amharic and other scripts print correctly on the Windows console
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            check_storyboard(args.storyboard)
            return 0
        config.load_env()
        if args.command == "smoke":
            smoke.run()
            return 0
        data = check_storyboard(args.storyboard, show_warnings=False)
        if args.command == "film":
            for name in FILM_ORDER:
                print(f"== {name} ==")
                STAGES[name](data, only=None)
        else:
            STAGES[args.command](data, only=args.shot)
        return 0
    except StoryboardError as e:
        print(e, file=sys.stderr)
        return 1
    except config.MissingSecret as e:
        print(f"missing secret: {e}", file=sys.stderr)
        return 1
    except NotBuiltYet as e:
        print(f"not built yet: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
