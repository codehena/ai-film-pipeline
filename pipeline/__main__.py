"""Command line entry point.

    py -m pipeline validate              check storyboard.json
    py -m pipeline narration --shot s03  run one stage (optionally for one shot)
    py -m pipeline film                  run every stage in order, skipping cached work

(On Mac/Linux use `python3` instead of `py`.)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import asr_check, assemble, audition, framing, keyframes, music, narration, retime, shots, smoke
from .common import MissingInput, NotBuiltYet, config
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
    p.add_argument("--debug", action="store_true", help="show full tracebacks on failure")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="check storyboard.json against the schema and rules")
    sm = sub.add_parser("smoke", help="call each provider once and log latency")
    sm.add_argument("--text-model")
    sm.add_argument("--tts-model")
    sm.add_argument("--image-model")
    for name in STAGES:
        sp = sub.add_parser(name, help=f"run the {name} stage")
        sp.add_argument("--shot", action="append", metavar="ID",
                        help="only this shot (repeatable), e.g. --shot s03")
        if name == "assemble":
            sp.add_argument("--mode", choices=["radio", "final"], default="radio")
        if name in ("shots", "music"):
            sp.add_argument("--export", metavar="DIR", help="write a Kaggle job bundle to DIR")
            sp.add_argument("--import", dest="import_dir", metavar="DIR",
                            help="copy finished Kaggle outputs (and log lines) from DIR")
    au = sub.add_parser("audition", help="speak one line in several voices to choose by ear")
    au.add_argument("--shot", default="s01", metavar="ID")
    au.add_argument("--voices", default=",".join(audition.DEFAULT_VOICES),
                    help="comma-separated Gemini voice names")
    sub.add_parser("retime", help="set each shot's duration_s from its measured narration")
    fr = sub.add_parser("framing", help="draw every 16:9/9:16 crop and safe box onto the keyframes")
    fr.add_argument("--shot", action="append", metavar="ID")
    ac = sub.add_parser("asr-check", help="transcribe each narration segment to check splits and pronunciation")
    ac.add_argument("--model", default=asr_check.MODEL)
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
            results = smoke.run(args.text_model, args.tts_model, args.image_model)
            return 0 if all(r[0] == "ok" for r in results.values()) else 1
        data = check_storyboard(args.storyboard, show_warnings=False)
        if args.command == "film":
            skipped = []
            for name in FILM_ORDER:
                print(f"== {name} ==")
                try:
                    STAGES[name](data, only=None)
                except NotBuiltYet as e:  # until every stage exists, film = what is built so far
                    print(f"  skipped: {e}")
                    skipped.append(name)
            if skipped:
                print(f"\nfilm finished with stages not built yet: {', '.join(skipped)}")
        elif args.command == "asr-check":
            asr_check.run(data, model=args.model)
        elif args.command == "framing":
            framing.run(data, args.shot)
        elif args.command == "retime":
            retime.run(data, args.storyboard)
        elif args.command == "audition":
            voices = [v.strip() for v in args.voices.split(",") if v.strip()]
            results = audition.run(data, args.shot, voices)
            ok = [v for v, r in results.items() if isinstance(r, Path)]
            print(f"\n{len(ok)} of {len(voices)} voices worked. Listen, then set "
                  "voice.voice_name in storyboard.json and run `narration`.")
            return 0 if ok else 1
        elif args.command in ("shots", "music"):
            STAGES[args.command](data, only=args.shot, export=args.export and Path(args.export),
                                 import_dir=args.import_dir and Path(args.import_dir))
        elif args.command == "assemble":
            STAGES["assemble"](data, only=args.shot, mode=args.mode)
        else:
            STAGES[args.command](data, only=args.shot)
        return 0
    except MissingInput as e:
        print(f"missing input: {e}", file=sys.stderr)
        return 1
    except StoryboardError as e:
        print(e, file=sys.stderr)
        return 1
    except config.MissingSecret as e:
        print(f"missing secret: {e}", file=sys.stderr)
        return 1
    except config.MissingTool as e:
        print(f"missing tool: {e}", file=sys.stderr)
        return 1
    except NotBuiltYet as e:
        print(f"not built yet: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # a model call failed after all retries
        if args.debug:
            raise
        print(f"stage failed: {type(e).__name__}: {str(e)[:400]}", file=sys.stderr)
        print("  every finished shot is cached; re-run the same command to continue "
              "(details in runs.jsonl, full traceback with --debug)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
